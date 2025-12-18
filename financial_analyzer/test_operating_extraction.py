from financial_analyzer.microsoft_excel import ExcelHandler
from financial_analyzer.analysis_modes import FinancialAnalyzer
import pandas as pd

# Load data
dfs = ExcelHandler.load_data('onedrive')

if dfs:
    res = FinancialAnalyzer.analyze_cash_flow_statement(dfs)
    
    if res:
        print("=== RAW DATA (df_clean) ===")
        print(res['raw_data'].to_string())
        print("\n")
        
        print("=== OPERATING ITEMS ===")
        operating_items = res.get('operating_items', pd.DataFrame())
        print(f"Shape: {operating_items.shape}")
        print(operating_items.to_string())
        print("\n")
        
        # Find indices
        df_clean = res['raw_data']
        operating_start = df_clean[df_clean['Line_Item'].str.contains('OPERATING ACTIVITIES', case=False, na=False)].index
        investing_start = df_clean[df_clean['Line_Item'].str.contains('INVESTING ACTIVITIES', case=False, na=False)].index
        
        print(f"Operating start index: {operating_start.tolist()}")
        print(f"Investing start index: {investing_start.tolist()}")
        
        if len(operating_start) > 0 and len(investing_start) > 0:
            print(f"\nRows between {operating_start[0]+1} and {investing_start[0]}:")
            section = df_clean.iloc[operating_start[0]+1:investing_start[0]]
            print(section.to_string())
