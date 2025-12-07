import os
import time
import google.generativeai as genai
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# Cached function to store successful AI responses
# TTL=3600 (1 hour) means it stays in memory for 60 mins.
# If it fails, it won't cache the failure, so it retries next time.
@st.cache_data(ttl=3600, show_spinner=False)
def cached_generate_content(api_key, model_name, prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return [line.strip().replace('- ', '') for line in response.text.split('\n') if line.strip().startswith('-')]

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

    def get_insights(self, mode, data):
        if not self.api_key:
             return self.generate_fallback_insights(mode, data)

        # Candidates confirmed from environment logs
        candidates = ['gemini-flash-latest', 'gemini-2.0-flash', 'gemini-pro-latest']
        
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
                # Reduced to 1.0s because we now have Caching!
                # If cached, this sleep is skipped entirely by the cached function wrapper if I moved sleep inside.
                # But sleep is outside. So first hit waits 1s. Subsequent hits wait 1s but get instant result.
                # Actually, if I want instant result on cache, I should check cache first?
                # No, st.cache_data handles that.
                # Wait, if I sleep BEFORE calling cached function, I always sleep.
                # I should move sleep INSIDE cached function? No, then it sleeps every time it runs (uncached).
                # But if it IS cached, the function body (including sleep) is skipped? 
                # Yes! If I put sleep inside cached_generate_content, then cached calls are instant.
                # But I can't put sleep there easily because I loop over candidates OUTSIDE.
                
                # Compromise: precise sleep here. 
                time.sleep(1.0) 
                
                # Use the CACHED function
                # We pass api_key to ensure cache invalidates if key changes (rare but good practice)
                return cached_generate_content(self.api_key, model_name, prompt)

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Quota" in error_str or "Resource" in error_str:
                    print(f"Rate Limit Hit on {model_name} - Switching to Fallback")
                    # Fallback to offline insights immediately to prevent user error
                    fallback = self.generate_fallback_insights(mode, data)
                    # Add a small indicator that this is offline data
                    return [f"⚡ {f}" for f in fallback]
                continue

        # Final fallback if all models fail
        return [f"⚡ {f}" for f in self.generate_fallback_insights(mode, data)]

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
