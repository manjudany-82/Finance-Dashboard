import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Load the Excel file
xls = pd.read_excel('Financial_Dash_Board_Work_Social.xlsx', sheet_name=None, header=None)

print("=== Checking MOM PL Sheet for Month Columns ===\n")

mom_df = xls.get('MOM PL')
if mom_df is not None:
    print("First 5 rows of MOM PL:")
    print(mom_df.head(5))
    print("\n" + "="*80 + "\n")
    
    # Look for month names in the first few rows
    for idx in range(min(5, len(mom_df))):
        row = mom_df.iloc[idx]
        print(f"Row {idx}: {list(row)}")
    
    print("\n" + "="*80 + "\n")
    print("Checking for month patterns in the data...")
    
    # Search for months in any cell
    months = ['January', 'February', 'March', 'April', 'May', 'June', 
              'July', 'August', 'September', 'October', 'November', 'December']
    
    found_months = []
    for col in mom_df.columns:
        for idx in range(min(10, len(mom_df))):
            cell = str(mom_df.iloc[idx][col])
            for month in months:
                if month in cell:
                    found_months.append(cell.strip())
    
    print(f"Found month columns: {list(set(found_months))}")
    
else:
    print("MOM PL sheet not found!")
