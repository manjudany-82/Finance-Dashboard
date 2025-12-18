import pandas as pd
import requests
from io import BytesIO
import re
import warnings
warnings.filterwarnings('ignore')

url = "https://myworksocial-my.sharepoint.com/:x:/p/dannya/EbB6qC0KAuVMtZRaFub_DgsBgirK7ySgwixiWLUOB-kZQA?download=1"

response = requests.get(url)
xls = pd.read_excel(BytesIO(response.content), sheet_name='MOM PL', header=None)

# Replicate the processing logic
mom_df = xls
mom_df.columns = mom_df.iloc[4]
mom_df = mom_df.iloc[5:].reset_index(drop=True)

print(f"After setting header, shape: {mom_df.shape}")
print(f"Columns: {list(mom_df.columns)}\n")

# Categorization (simplified)
col_0 = mom_df.columns[0]
mom_df['Type'] = 'Operating Income'  # Simplified for testing

# Prepare for unpivot
id_vars = [col_0, 'Type']
val_vars = [c for c in mom_df.columns if c not in id_vars and 'total' not in str(c).lower()]

print(f"ID vars: {id_vars}")
print(f"Value vars (months): {val_vars[:3]}... ({len(val_vars)} total)\n")

# Unpivot
unpivoted = mom_df.melt(id_vars=id_vars, value_vars=val_vars, var_name='Month', value_name='Amount')

print(f"After unpivot, shape: {unpivoted.shape}")
print(f"Sample unpivoted data:")
print(unpivoted.head(15))

# Filter
acct_col = id_vars[0]
before_filter = len(unpivoted)
unpivoted = unpivoted[~unpivoted[acct_col].astype(str).str.contains('Total', na=False)]
unpivoted = unpivoted[~unpivoted[acct_col].astype(str).str.contains('Net ', na=False)]
unpivoted = unpivoted[~unpivoted[acct_col].isin(['Income', 'Expenses', 'Cost of Goods Sold', 'Gross Profit', 'Other Income', 'Other Expenses'])]
after_filter = len(unpivoted)

print(f"\nAfter filtering headers: {after_filter} rows (was {before_filter})")

# Check December specifically
dec_data = unpivoted[unpivoted['Month'] == 'Dec 1 - Dec 18 2025']
print(f"\nDecember data before dropna: {len(dec_data)} rows")
print(f"December non-null amounts: {dec_data['Amount'].notna().sum()}")
print(f"December null amounts: {dec_data['Amount'].isna().sum()}")

print(f"\nSample December rows:")
print(dec_data[[acct_col, 'Amount']].head(20))

# Parse months
def parse_month(m):
    m_str = str(m).strip()
    try:
        return pd.to_datetime(m_str, errors='coerce')
    except:
        pass
    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s*\d*\s*-?\s*\w*\s*\d*\s*(\d{4})', m_str, re.IGNORECASE)
    if match:
        month_name = match.group(1)
        year = match.group(2)
        date_str = f"{month_name} 1, {year}"
        return pd.to_datetime(date_str, errors='coerce')
    return pd.NaT

unpivoted['Month'] = unpivoted['Month'].apply(parse_month)

# After parse, check December
dec_parsed = unpivoted[unpivoted['Month'].notna() & (pd.to_datetime(unpivoted['Month']).dt.month == 12)]
print(f"\nDecember after parsing: {len(dec_parsed)} rows")
print(f"December non-null amounts after parsing: {dec_parsed['Amount'].notna().sum()}")

# Drop NaN
before_dropna = len(unpivoted)
unpivoted = unpivoted.dropna(subset=['Month', 'Amount'])
after_dropna = len(unpivoted)

print(f"\nAfter dropna: {after_dropna} rows (was {before_dropna})")

# Final December check
dec_final = unpivoted[unpivoted['Month'].notna() & (pd.to_datetime(unpivoted['Month']).dt.month == 12)]
print(f"Final December rows: {len(dec_final)}")

if not dec_final.empty:
    print(f"\n✅ December data survived!")
    print(dec_final[[acct_col, 'Amount']].head())
else:
    print(f"\n❌ All December data was dropped!")
