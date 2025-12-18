from microsoft_excel import ExcelHandler
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

onedrive_config = {
    'url': 'https://myworksocial-my.sharepoint.com/:x:/p/dannya/EbB6qC0KAuVMtZRaFub_DgsBgirK7ySgwixiWLUOB-kZQA',
    'token': 'MOCK_TOKEN'
}

print("Loading from OneDrive and inspecting raw unpivoted data...\n")

# Manually load and inspect
import requests
from io import BytesIO

url = onedrive_config['url']
if "download=1" not in url:
    url = f"{url}?download=1"

response = requests.get(url)
xls = pd.read_excel(BytesIO(response.content), sheet_name=None, header=None)

mom_df = xls['MOM PL']
print("Raw MOM PL Header (row 4):")
print(mom_df.iloc[4])

# Process similar to microsoft_excel.py
mom_df.columns = mom_df.iloc[4]
mom_df = mom_df.iloc[5:].reset_index(drop=True)

print(f"\nColumn names after setting header: {list(mom_df.columns)}")

# Get the columns that are month columns
id_vars = [mom_df.columns[0]]  # First column is account
val_vars = [c for c in mom_df.columns if c not in id_vars and 'total' not in str(c).lower()]

print(f"\nMonth columns (val_vars): {val_vars}")

# Create small sample for testing
sample = mom_df.head(3)[id_vars + val_vars].copy()
unpivoted = sample.melt(id_vars=id_vars, value_vars=val_vars, var_name='Month', value_name='Amount')

print(f"\nUnpivoted sample (first 15 rows):")
print(unpivoted.head(15))

print(f"\nUnique 'Month' values in unpivoted data:")
print(unpivoted['Month'].unique())

# Now test parsing
print(f"\n{'='*60}")
print("Testing parse_month on actual data...")
print('='*60)

import re

def parse_month_debug(m):
    m_str = str(m).strip()
    
    # Try standard parsing
    try:
        result = pd.to_datetime(m_str, errors='coerce')
        if pd.notna(result):
            return result
    except:
        pass
    
    # Regex parsing
    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s*\d*\s*-?\s*\w*\s*\d*\s*(\d{4})', m_str, re.IGNORECASE)
    if match:
        month_name = match.group(1)
        year = match.group(2)
        date_str = f"{month_name} 1, {year}"
        return pd.to_datetime(date_str, errors='coerce')
    
    return pd.NaT

unpivoted['Month_Parsed'] = unpivoted['Month'].apply(parse_month_debug)

print("\nAfter parsing:")
print(unpivoted[['Month', 'Month_Parsed']].drop_duplicates())

# Check for December
dec_rows = unpivoted[unpivoted['Month_Parsed'].notna() & (unpivoted['Month_Parsed'].dt.month == 12)]
print(f"\nDecember rows found: {len(dec_rows)}")
if not dec_rows.empty:
    print("Sample December data:")
    print(dec_rows.head())
