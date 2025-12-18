import pandas as pd
import requests
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

url = "https://myworksocial-my.sharepoint.com/:x:/p/dannya/EbB6qC0KAuVMtZRaFub_DgsBgirK7ySgwixiWLUOB-kZQA?download=1"

response = requests.get(url)
xls = pd.read_excel(BytesIO(response.content), sheet_name='MOM PL', header=4)

print("=== Checking December Column Data ===\n")
print(f"Columns: {list(xls.columns)}\n")

# Get the December column
dec_col = 'Dec 1 - Dec 18 2025'
if dec_col in xls.columns:
    print(f"December column found: '{dec_col}'")
    print(f"\nFirst 20 rows of December column:")
    print(xls[[xls.columns[0], dec_col]].head(20))
    
    # Check for non-null values
    non_null = xls[dec_col].notna().sum()
    non_zero = (xls[dec_col] != 0).sum()
    total = len(xls)
    
    print(f"\nStatistics:")
    print(f"Total rows: {total}")
    print(f"Non-null values: {non_null}")
    print(f"Non-zero values: {non_zero}")
    print(f"Sum of December column: ${xls[dec_col].sum():,.2f}")
    
    # Show rows with actual data
    has_data = xls[xls[dec_col].notna() & (xls[dec_col] != 0)]
    print(f"\nRows with actual December data ({len(has_data)} rows):")
    print(has_data[[xls.columns[0], dec_col]].head(15))
else:
    print(f"❌ December column '{dec_col}' not found")
    print(f"Available columns: {list(xls.columns)}")
