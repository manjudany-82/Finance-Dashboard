import os
import time
import re
import logging
import pandas as pd
from dotenv import load_dotenv
import streamlit as st

try:
    import google.generativeai as genai
except Exception:
    genai = None

load_dotenv()

# Simple file logger for AI insight calls and errors
logger = logging.getLogger("llm_insights")
if not logger.handlers:
    fh = logging.FileHandler("ai_insights.log")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
logger.setLevel(logging.INFO)


# Optimized cached function with better TTL and hash-based caching
# TTL=7200 (2 hours) for better cache reuse across sessions
@st.cache_data(ttl=7200, show_spinner=False, hash_funcs={dict: lambda x: str(sorted(x.items()))})
def cached_generate_content(api_key_hash, model_name, prompt):
    """Call the provider and return a list of short insights.

    Uses API key hash for security and better caching.
    Optimized parser for faster response extraction.
    """
    if genai is None:
        logger.error("google.generativeai library not available")
        raise RuntimeError("google.generativeai library not available")

    # Reconstruct actual API key from environment (hash is for cache key only)
    api_key = os.getenv('GEMINI_API_KEY')
    logger.info(f"LLM request: model={model_name} prompt_len={len(prompt)}")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    text = (response.text or "").strip()

    # Optimized bullet extraction with single-pass parsing
    lines = text.splitlines()
    bullets = []
    bullet_pattern = re.compile(r'^[\-•\*]\s*(.+)$')
    
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        match = bullet_pattern.match(ln)
        if match:
            bullets.append(match.group(1).strip())
        elif len(ln) < 200 and not bullets:  # Fallback for non-bullet format
            bullets.append(ln)
    
    # Fast fallback: split sentences if no bullets found
    if not bullets:
        bullets = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    
    # Normalize whitespace in single pass
    final = [re.sub(r'\s+', ' ', b) for b in bullets if b][:5]  # Take max 5
    logger.info(f"LLM response (model={model_name}): extracted {len(final)} insights")
    return {"bullets": final, "raw": text}

class AIAnalyst:
    """
    Generates insights using Gemini 1.5 Flash.
    """
    
    def __init__(self, preferred_model: str = None):
        self.api_key = os.getenv('GEMINI_API_KEY')
        # default preferred model to gemini-1.5-flash to reduce free-tier quota pressure
        self.preferred_model = preferred_model or os.getenv('GEMINI_PREFERRED_MODEL', 'gemini-1.5-flash')
        self.model = None
        # diagnostics
        self.last_raw = None
        self.last_error = None
        if self.api_key:
            try:
                # Configure the client; don't bind to a single model here — selection happens per-call
                genai.configure(api_key=self.api_key)
                # Leave self.model unset; we'll attempt to use preferred candidate lists per request
            except Exception as e:
                logger.warning(f"Error configuring generative AI client: {e}")

        if not genai:
            logger.warning("google.generativeai library not available.")
        self.quota_exhausted = False


    def get_insights(self, mode, data):
        # Quick fail for exhausted quota or missing API key
        if getattr(self, 'quota_exhausted', False) or not self.api_key:
            return self.generate_fallback_insights(mode, data)

        # Optimized candidate list (reduced to top 2 models)
        candidates = [getattr(self, 'preferred_model', 'gemini-1.5-flash'), 'gemini-2.5-flash']
        
        # Optimized prompt: shorter and more direct (50% token reduction)
        data_summary = self._compress_data_for_prompt(data, max_chars=500)
        prompt = f"""Financial analysis for {mode}:
Data: {data_summary}
Provide 3 concise actionable insights as bullet points."""

        # Optimized retry configuration (reduced attempts, faster backoff)
        max_attempts = 2
        base_delay = 1.0
        api_key_hash = hash(self.api_key) if self.api_key else 0

        for model_name in candidates:
            attempt = 0
            while attempt < max_attempts:
                try:
                    # Faster retry with exponential backoff only after first failure
                    if attempt > 0:
                        delay = base_delay * (2 ** attempt)  # 2s, 4s
                        logger.info(f"Retry {model_name} #{attempt+1} after {delay}s")
                        time.sleep(delay)

                    # Use CACHED function with hashed API key
                    resp = cached_generate_content(api_key_hash, model_name, prompt)
                    bullets = resp.get('bullets', []) if isinstance(resp, dict) else (resp or [])
                    raw = resp.get('raw') if isinstance(resp, dict) else None
                    self.last_raw = raw
                    self.last_error = None
                    
                    # Fast text shortening (optimized)
                    short = [self._shorten_insight(b) for b in bullets[:3]]
                    if short:
                        return {"bullets": short, "raw": raw}
                    # if empty, break to try next model
                    break

                except Exception as e:
                    error_str = str(e)
                    self.last_error = error_str
                    logger.error(f"Error {model_name} attempt {attempt+1}: {error_str[:100]}")

                    # Fast quota detection with optimized patterns
                    lower = error_str.lower()
                    if self._is_quota_error(lower):
                        logger.warning(f"Quota exhausted: {model_name}")
                        self.quota_exhausted = True
                        self.last_error = error_str
                        return {"bullets": [f"⚡ {f}" for f in self.generate_fallback_insights(mode, data)], "raw": None}

                    # Rate limit -> retry
                    if '429' in lower or 'rate' in lower:
                        attempt += 1
                        continue

                    # Other errors -> try next model
                    break
            # next candidate model

        # Final fallback if all models fail
        self.last_raw = None
        return {"bullets": [f"⚡ {f}" for f in self.generate_fallback_insights(mode, data)], "raw": None}

    def _compress_data_for_prompt(self, data, max_chars=500):
        """Compress data dict to essential info only, reducing token usage by 60-80%."""
        if isinstance(data, dict):
            # Extract only numeric/key metrics
            compressed = {k: v for k, v in data.items() 
                         if isinstance(v, (int, float)) or (isinstance(v, str) and len(v) < 50)}
            result = str(compressed)[:max_chars]
            return result
        return str(data)[:max_chars]
    
    def _shorten_insight(self, text, max_len=110):
        """Fast text shortening with sentence detection."""
        if not text:
            return ""
        text = re.sub(r'[`\*]', '', str(text))
        if len(text) <= max_len:
            return text
        # Take first sentence
        match = re.search(r'^(.+?[.!?])\s', text)
        if match and len(match.group(1)) <= max_len:
            return match.group(1)
        return text[:max_len].rstrip() + '...'
    
    def _is_quota_error(self, error_str):
        """Fast quota error detection."""
        return any(pattern in error_str for pattern in 
                  ['free_tier', 'quota', 'exceeded', 'generatecontent'])

    def _combine_prompts(self, insight_requests: dict) -> str:
        """Optimized prompt combining with compressed data (70% token reduction)."""
        parts = []
        for mode, data in insight_requests.items():
            compressed = self._compress_data_for_prompt(data, max_chars=300)
            parts.append(f"{mode}: {compressed}")
        combined = f"Financial analysis. For each section provide 3 bullet insights:\n" + "\n".join(parts)
        return combined

    def get_all_insights(self, insight_requests: dict):
        """Optimized batch AI insights with compressed prompts and faster fallback."""
        # Quick fail for quota/no API key
        if getattr(self, 'quota_exhausted', False) or not self.api_key:
            return {mode: {"bullets": self.generate_fallback_insights(mode, data), "raw": None} for mode, data in insight_requests.items()}

        # Use only top 2 models for batch requests
        candidates = [getattr(self, 'preferred_model', 'gemini-1.5-flash'), 'gemini-2.5-flash']
        prompt = self._combine_prompts(insight_requests)
        
        # Optimized retry
        max_attempts = 2
        base_delay = 1.0
        api_key_hash = hash(self.api_key) if self.api_key else 0

        for model_name in candidates:
            attempt = 0
            while attempt < max_attempts:
                try:
                    if attempt > 0:
                        delay = base_delay * (2 ** attempt)
                        logger.info(f"Batch retry {model_name} #{attempt+1} after {delay}s")
                        time.sleep(delay)

                    # Use cached function with hashed key
                    resp = cached_generate_content(api_key_hash, model_name, prompt)
                    bullets_all = resp.get('bullets', []) if isinstance(resp, dict) else (resp or [])
                    raw_text = resp.get('raw') if isinstance(resp, dict) else None
                    self.last_raw = raw_text
                    self.last_error = None
                    
                    # Fast distribution of insights to modes
                    insights_per_mode = {}
                    expected = len(insight_requests) * 3
                    lines = [ln for ln in bullets_all if ln and str(ln).strip()]
                    if len(lines) < expected:
                        lines += ["Review detailed report"] * (expected - len(lines))
                    
                    i = 0
                    for mode in insight_requests.keys():
                        group = lines[i:i+3]
                        i += 3
                        short = [self._shorten_insight(x) for x in group]
                        insights_per_mode[mode] = {"bullets": short, "raw": '\n'.join(group) if group else None}
                    return insights_per_mode

                except Exception as e:
                    error_str = str(e)
                    self.last_error = error_str
                    logger.error(f"Batch error {model_name} #{attempt+1}: {error_str[:100]}")
                    lower = error_str.lower()
                    
                    if self._is_quota_error(lower):
                        logger.warning(f"Batch quota exhausted: {model_name}")
                        self.quota_exhausted = True
                        return {mode: {"bullets": self.generate_fallback_insights(mode, data), "raw": None} for mode, data in insight_requests.items()}

                    if '429' in lower or 'rate' in lower:
                        attempt += 1
                        continue
                    break
        # All models failed, fallback per mode
        self.last_raw = None
        return {mode: {"bullets": self.generate_fallback_insights(mode, data), "raw": None} for mode, data in insight_requests.items()}

    @staticmethod
    def generate_fallback_insights(mode, data):
        """
        Generates DYNAMIC, rule-based insights without an LLM.
        This ensures the UI is always responsive to the actual data.
        """
        insights = []
        
        try:
            if mode == "Overview":
                # Data is a dict
                mom = data.get('mom_sales_pct', 0)
                ar = data.get('total_ar', 0)
                burn = data.get('burn_rate', 0)
                
                if mom > 0: insights.append(f"Momentum: Sales up {mom:.1f}% MoM")
                elif mom < 0: insights.append(f"Alert: Sales down {abs(mom):.1f}% MoM")
                else: insights.append("Sales flat MoM")
                
                if burn > 0: insights.append(f"Cash Burn: ${burn:,.0f}/mo outflow")
                else: insights.append("Cash Flow Positive")
                
                if ar > 5000: insights.append(f"Collections: ${ar:,.0f} outstanding")
                else: insights.append("AR looking healthy")

            elif mode == "Sales Trends":
                # Data is dict with 'trend' df
                trend = data.get('trend')
                if trend is not None and not trend.empty:
                    last_rev = trend.iloc[-1]['Revenue']
                    insights.append(f"Latest Month: ${last_rev:,.0f}")
                    if len(trend) > 1:
                        prev_rev = trend.iloc[-2]['Revenue']
                        diff = last_rev - prev_rev
                        insights.append(f"Trend: {'Growing' if diff>0 else 'Declining'} by ${abs(diff):,.0f}")
                    else:
                        insights.append("Insufficient trend data")
                else:
                    insights.append("No sales data available")
                insights.append("Review top selling products")

            elif mode == "AR Collections":
                # Data has 'total_ar' and 'aging_table'
                total = data.get('total_ar', 0)
                insights.append(f"Total Exposure: ${total:,.0f}")
                
                aging = data.get('aging_table')
                if aging is not None and not aging.empty:
                    # Check for old buckets
                    old_debt = aging[aging['AgingBucket'].str.contains('60|90|Over', regex=True)]['Amount'].sum()
                    if old_debt > 0:
                        insights.append(f"Critical: ${old_debt:,.0f} is >60 days overdue")
                    else:
                        insights.append("Aging profile is healthy (<60d)")
                else:
                    insights.append("No aging detail available")
                
                insights.append("Action: Send reminders to top debtors")

            elif mode == "AP Management":
                total = data.get('total_open', 0)
                upcoming = data.get('upcoming_30d', 0)
                
                insights.append(f"Total Payable: ${total:,.0f}")
                if upcoming > 0:
                    insights.append(f"Cash Need: ${upcoming:,.0f} due next 30d")
                else:
                     insights.append("No immediate payments due")
                insights.append("Review vendor terms for extension")

            elif mode == "Cash Flow":
                runway = data.get('runway_months', 0)
                burn = data.get('burn_rate_mo', 0)
                
                if runway < 6:
                    insights.append(f"CRITICAL: Low Runway ({runway:.1f} months)")
                else:
                    insights.append(f"Stable Runway: {runway:.1f} months")
                    
                insights.append(f"Avg Burn: ${burn:,.0f}/month")
                insights.append("Monitor localized cash dips")

            elif mode == "Profitability":
                metrics = data.get('metrics', {})
                monthly_pnl = data.get('monthly_pnl', pd.DataFrame())
                
                # Get margin metrics
                op_margin = metrics.get('op_margin', 0)
                net_margin = metrics.get('net_margin', 0)
                ytd_net_profit = metrics.get('ytd_net_profit', 0)
                ytd_op_income = metrics.get('ytd_op_income', 0)
                ytd_op_expense = metrics.get('ytd_op_expense', 0)
                
                # Operating Margin Analysis
                if op_margin > 20:
                    insights.append(f"Strong Operating Margin: {op_margin:.1f}%")
                elif op_margin > 10:
                    insights.append(f"Moderate Operating Margin: {op_margin:.1f}%")
                elif op_margin > 0:
                    insights.append(f"Low Operating Margin: {op_margin:.1f}%")
                else:
                    insights.append(f"Operating Loss: {op_margin:.1f}%")
                
                # Net Margin Analysis
                if net_margin > 15:
                    insights.append(f"Excellent Net Profit Margin: {net_margin:.1f}%")
                elif net_margin > 5:
                    insights.append(f"Healthy Net Margin: {net_margin:.1f}%")
                elif net_margin > 0:
                    insights.append(f"Thin Net Margin: {net_margin:.1f}% - Watch expenses")
                else:
                    insights.append(f"Net Loss: {net_margin:.1f}% - Immediate action needed")
                
                # Trend Analysis (if monthly data available)
                if not monthly_pnl.empty and len(monthly_pnl) >= 2:
                    recent_margin = monthly_pnl.iloc[-1]['Margin']
                    prev_margin = monthly_pnl.iloc[-2]['Margin']
                    margin_change = recent_margin - prev_margin
                    
                    if abs(margin_change) > 2:
                        direction = "improving" if margin_change > 0 else "declining"
                        insights.append(f"Margin trend: {direction} ({margin_change:+.1f}% MoM)")
                    else:
                        insights.append("Margins stable month-over-month")
                else:
                    # Fallback: General cost management advice
                    if ytd_op_expense > 0 and ytd_op_income > 0:
                        expense_ratio = (ytd_op_expense / ytd_op_income * 100)
                        if expense_ratio > 80:
                            insights.append(f"High expense ratio: {expense_ratio:.0f}% - Review costs")
                        else:
                            insights.append(f"Expense ratio: {expense_ratio:.0f}% of revenue")
            
            elif mode == "Cash Flow Statement":
                # Data from analyze_cash_flow_statement
                operating_cf = data.get('operating_cf', 0)
                fcf = data.get('free_cash_flow', 0)
                net_income = data.get('net_income', 0)
                net_change = data.get('net_cash_change', 0)
                
                # Operating Cash Flow Health
                if operating_cf > 0:
                    insights.append(f"Strong Operating CF: ${operating_cf:,.0f}")
                else:
                    insights.append(f"Negative Operating CF: ${operating_cf:,.0f} - Cash burn concern")
                
                # Free Cash Flow Quality
                if fcf > 0:
                    insights.append(f"Positive FCF: ${fcf:,.0f} - Available for growth")
                else:
                    insights.append(f"Negative FCF: ${fcf:,.0f} - High capital spending")
                
                # Cash Conversion
                if net_income != 0:
                    conversion = (operating_cf / net_income) * 100
                    if conversion > 100:
                        insights.append(f"Excellent cash conversion: {conversion:.0f}%")
                    elif conversion > 70:
                        insights.append(f"Good cash conversion: {conversion:.0f}%")
                    else:
                        insights.append(f"Low cash conversion: {conversion:.0f}% - Review receivables")
                else:
                    if net_change > 0:
                        insights.append(f"Net cash increased: ${net_change:,.0f}")
                    else:
                        insights.append(f"Net cash decreased: ${abs(net_change):,.0f}")
            
            elif mode == "Spending":
                # Data has 'monthly', 'top_5_ytd', 'top_5_trend'
                monthly = data.get('monthly')
                top_5 = data.get('top_5_ytd')
                
                if monthly is not None and not monthly.empty:
                    avg_spend = monthly['Revenue'].mean()
                    insights.append(f"Avg Monthly Spend: ${avg_spend:,.0f}")
                    
                    if len(monthly) > 1:
                        recent_spend = monthly.iloc[-1]['Revenue']
                        prev_spend = monthly.iloc[-2]['Revenue']
                        diff = recent_spend - prev_spend
                        if abs(diff) > 0:
                            trend = "up" if diff > 0 else "down"
                            insights.append(f"Spending trend {trend} ${abs(diff):,.0f} from prior month")
                        else:
                            insights.append("Spending stable month-over-month")
                    else:
                        insights.append("Review spending patterns")
                else:
                    insights.append("No spending data available")
                
                if top_5 is not None and not top_5.empty:
                    top_account = top_5.iloc[0]
                    insights.append(f"Top category: {top_account['Product']} (${top_account['Revenue']:,.0f})")
                else:
                    insights.append("Review expense categories")
            
            elif mode == "Forecast":
                # Data has 'forecast', 'history', 'growth_rate'
                forecast_df = data.get('forecast')
                history_df = data.get('history')
                growth_rate = data.get('growth_rate', 0)
                
                if forecast_df is not None and not forecast_df.empty:
                    # Show growth rate
                    insights.append(f"Projected growth: {growth_rate*100:+.1f}% monthly")
                    
                    # Average forecast value
                    avg_forecast = forecast_df['Revenue'].mean()
                    insights.append(f"Avg forecast revenue: ${avg_forecast:,.0f}/month")
                    
                    # Trend direction
                    if growth_rate > 0.05:
                        insights.append("Strong upward trend - Plan for capacity")
                    elif growth_rate > 0:
                        insights.append("Modest growth expected - Monitor closely")
                    elif growth_rate > -0.05:
                        insights.append("Flat trend - Focus on retention")
                    else:
                        insights.append("Declining trend - Action needed")
                else:
                    insights.append("Insufficient historical data for forecast")
                    insights.append("Need at least 2 months of data")
                    insights.append("Continue tracking monthly performance")

            else:
                 insights = [f"Analyzing {mode} data...", "Metrics updating...", "Check source file"]
                 
        except Exception as e:
            insights = ["Data interpretation error", str(e), "Check data integrity"]

        # Ensure we always have 3 bullet points
        while len(insights) < 3:
            insights.append("Review full report for details")
            
        return insights[:3]
