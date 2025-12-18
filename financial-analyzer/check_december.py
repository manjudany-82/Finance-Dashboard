import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Load the Excel file with more columns
xls = pd.read_excel('Financial_Dash_Board_Work_Social.xlsx', sheet_name='MOM PL', header=None)

print("=== Detailed Column Analysis ===\n")
print(f"Total columns in MOM PL: {len(xls.columns)}")
print(f"Shape: {xls.shape}")
print("\nRow 4 (Header row) - All columns:")
print(xls.iloc[4])
print("\n" + "="*80 + "\n")

# Check if there's a December column
for col_idx, val in enumerate(xls.iloc[4]):
    if val and ('December' in str(val) or 'Dec' in str(val)):
        print(f"✓ Found December in column {col_idx}: {val}")
        
if not any('December' in str(val) or 'Dec' in str(val) for val in xls.iloc[4] if val):
    print("✗ No December column found in the data")
    print("\nThe Excel file only contains data through November 2025")
    print("Please update your Excel file to include December 2025 data")
