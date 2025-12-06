import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class AIAnalyst:
    """
    Generates insights using Gemini 1.5 Flash.
    """
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
            print("WARNING: GEMINI_API_KEY not found. AI insights will be disabled.")

    def get_insights(self, mode, data_summary):
        """
        Generates 3 bullet points of insights based on the mode and data.
        """
        if not self.model:
            return ["AI Insights disabled (Missing API Key)", "Please add GEMINI_API_KEY to .env", "Using mock insights for now."]

        prompt = f"""
        You are a financial controller analyzing a company's data.
        MODE: {mode}
        DATA SUMMARY:
        {data_summary}

        TASK: Provide exactly 3 short, actionable, punchy bullet points (max 10 words each). 
        Focus on risks, opportunities, or anomalies.
        OUTPUT FORMAT:
        - Insight 1
        - Insight 2
        - Insight 3
        """
        
        try:
            response = self.model.generate_content(prompt)
            return [line.strip().replace('- ', '') for line in response.text.split('\n') if line.strip().startswith('-')]
        except Exception as e:
            print(f"LLM Error: {e}")
            return [f"AI Error: {str(e)[:20]}...", "Check GEMINI_API_KEY in Secrets", "Or wait 1 minute & refresh"]

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
