import pandas as pd

file_path = "Financial_Dash_Board_Work_Social.xlsx"

try:
    xls = pd.read_excel(file_path, sheet_name=None)
    print(f"File: {file_path}")
    print(f"Sheets found: {list(xls.keys())}")
    
    for sheet, df in xls.items():
        print(f"\n--- Sheet: {sheet} ---")
        print(f"Columns: {list(df.columns)}")
        print(f"First row: {df.iloc[0].values if not df.empty else 'EMPTY'}")
        
except Exception as e:
    print(f"Error reading file: {e}")
