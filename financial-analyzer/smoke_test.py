import json
import os
from llm_insights import AIAnalyst

# Simple sample data to exercise fallback and batch path
sample_requests = {
    "Overview": {"mom_sales_pct": 0.0, "total_ar": 68579, "burn_rate": 0},
    "Sales Trends": {"trend": None},
    "AR Collections": {"total_ar": 68579, "aging_table": None},
}

ai = AIAnalyst()
print("GEMINI_API_KEY present:", bool(ai.api_key))

res = ai.get_all_insights(sample_requests)
print("\nBatched insights result:\n")
print(json.dumps(res, indent=2))

# Also show fallback for a single mode
single = ai.generate_fallback_insights("Overview", sample_requests['Overview'])
print("\nFallback single (Overview):", single)

# Print last lines of ai_insights.log if exists
log_path = os.path.join(os.path.dirname(__file__), 'ai_insights.log')
if os.path.exists(log_path):
    print("\n--- ai_insights.log (last 20 lines) ---")
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()[-20:]
        print(''.join(lines))
else:
    print('\nNo log file found at', log_path)
