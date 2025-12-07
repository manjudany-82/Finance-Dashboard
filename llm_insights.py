import os
import time
import re
import logging
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


# Cached function to store successful AI responses
# TTL=3600 (1 hour) means it stays in memory for 60 mins.
# If it fails, it won't cache the failure, so it retries next time.
@st.cache_data(ttl=3600, show_spinner=False)
def cached_generate_content(api_key, model_name, prompt):
    """Call the provider and return a list of short insights.

    The parser is robust: it extracts bullet lines (starting with -, •, *)
    or falls back to splitting into short sentences if bullets are not present.
    """
    if genai is None:
        logger.error("google.generativeai library not available")
        raise RuntimeError("google.generativeai library not available")

    logger.info(f"LLM request: model={model_name} prompt_len={len(prompt)}")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    text = (response.text or "").strip()

    # Try to extract bullet lines first (common formats)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    bullets = []
    for ln in lines:
        if re.match(r'^[\-•\*]\s+', ln):
            bullets.append(re.sub(r'^[\-•\*]\s*', '', ln).strip())
        elif ln.startswith('•'):
            bullets.append(ln.lstrip('•').strip())

    if not bullets:
        # Try lines that look like short statements (<= 140 chars)
        for ln in lines:
            if len(ln) < 200:
                bullets.append(ln)

    if not bullets:
        # Final fallback: split into sentences and take first 3
        sentences = re.split(r'(?<=[\.\?\!])\s+', text)
        bullets = [s.strip() for s in sentences if s.strip()]

    # Normalize to max 3 concise items
    final = [re.sub('\s+', ' ', b).strip() for b in bullets]
    logger.info(f"LLM response (model={model_name}): {final[:3]}")
    return final[:3]

class AIAnalyst:
    """
    Generates insights using Gemini 1.5 Flash.
    """
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = None
        if self.api_key:
            try:
                # Try the latest standard model first
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                print(f"Error init model: {e}")
                
        if not self.model:
            print("WARNING: AI model failed to initialize.")
            self.quota_exhausted = False


    def get_insights(self, mode, data):
        # Skip API calls if quota already exhausted
        if getattr(self, 'quota_exhausted', False):
            return [f"⚡ {f}" for f in self.generate_fallback_insights(mode, data)]
        if not self.api_key:
            return self.generate_fallback_insights(mode, data)

        # Candidates: Verified available models from user environment
        candidates = ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.0-flash-exp']
        
        prompt = f"""
        You are a financial controller analyzing a company's data.
        MODE: {mode}
        DATA SUMMARY:
        {str(data)}
        TASK: Provide exactly 3 short, actionable, punchy bullet points.
        OUTPUT FORMAT:
        - Insight 1
        - Insight 2
        - Insight 3
        """

        for model_name in candidates:
            try:
                # Throttle requests to avoid 429 Rate Limit
                time.sleep(1.5)

                # Use the CACHED function
                res = cached_generate_content(self.api_key, model_name, prompt)
                if res and len(res) >= 1:
                    return res
                # if empty, try next candidate

            except Exception as e:
                # If Rate Limit or other error, try next candidate
                error_str = str(e)
                print(f"Error on {model_name}: {error_str}")
                if "Quota" in error_str or "429" in error_str:
                    self.quota_exhausted = True
                continue

        # Final fallback if all models fail
        return [f"⚡ {f}" for f in self.generate_fallback_insights(mode, data)]

    @staticmethod
    def _combine_prompts(insight_requests: dict) -> str:
        """Combine multiple mode/data pairs into a single prompt.
        insight_requests: dict where key is mode name and value is data object.
        Returns a formatted prompt string.
        """
        parts = []
        for mode, data in insight_requests.items():
            part = f"MODE: {mode}\nDATA SUMMARY:\n{str(data)}\n"
            parts.append(part)
        combined = "You are a financial controller analyzing multiple sections. Provide insights for each section separated by '---'.\n" + "\n---\n".join(parts)
        return combined

    def get_all_insights(self, insight_requests: dict):
        """Batch request AI insights for multiple sections.
        insight_requests: dict mapping mode name to data object.
        Returns dict of mode -> list of insights.
        """
        if not self.api_key:
            # fallback for each mode
            return {mode: self.generate_fallback_insights(mode, data) for mode, data in insight_requests.items()}

        # Use same candidates list as get_insights
        candidates = ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.0-flash-exp']
        prompt = self._combine_prompts(insight_requests)
        for model_name in candidates:
            try:
                time.sleep(2.0)
                # Use cached function for the combined prompt
                raw_insights = cached_generate_content(self.api_key, model_name, prompt)
                # Split raw insights by separator '---' assuming each section returns its own lines
                # For simplicity, assume the AI returns insights in order of request, 3 per section.
                # We'll chunk them.
                insights_per_mode = {}
                # Split into lines and group every 3 lines per mode
                lines = [line.strip() for line in raw_insights if line.strip()]
                # Ensure enough lines
                expected = len(insight_requests) * 3
                if len(lines) < expected:
                    # Pad with fallback if missing
                    lines += ["(no insight)"] * (expected - len(lines))
                i = 0
                for mode in insight_requests.keys():
                    insights_per_mode[mode] = lines[i:i+3]
                    i += 3
                return insights_per_mode
            except Exception as e:
                print(f"Error on {model_name}: {e}")
                continue
        # All models failed, fallback per mode
        return {mode: [f"⚡ {f}" for f in self.generate_fallback_insights(mode, data)] for mode, data in insight_requests.items()}

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
                gp_ratio = metrics.get('gp_ratio', 0)
                np_ratio = metrics.get('np_ratio', 0)
                
                insights.append(f"Gross Margin: {gp_ratio:.1f}%")
                if np_ratio > 0:
                    insights.append(f"Net Profit Healthy: {np_ratio:.1f}%")
                else:
                    insights.append(f"Operating Loss: {np_ratio:.1f}%")
                
                insights.append("Review detailed expense categories")

            else:
                 insights = [f"Analyzing {mode} data...", "Metrics updating...", "Check source file"]
                 
        except Exception as e:
            insights = ["Data interpretation error", str(e), "Check data integrity"]

        # Ensure we always have 3 bullet points
        while len(insights) < 3:
            insights.append("Review full report for details")
            
        return insights[:3]
