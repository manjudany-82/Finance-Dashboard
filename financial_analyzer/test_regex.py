import pandas as pd
import re

# Test the month parsing logic
test_months = [
    "January 2025",
    "February 2025",
    "Dec 1 - Dec 18 2025",
    "December 2025",
    "Nov 2025"
]

def parse_month(m):
    m_str = str(m).strip()
    print(f"\nParsing: '{m_str}'")
    
    try:
        # Try standard datetime parsing first
        result = pd.to_datetime(m_str, errors='coerce')
        if pd.notna(result):
            print(f"  ✓ Standard parsing worked: {result}")
            return result
    except Exception as e:
        print(f"  Standard parsing failed: {e}")
    
    # Handle "Dec 1 - Dec 18 2025" format - extract month and year
    # Match patterns like "Dec 1 - Dec 18 2025" or "December 1-18 2025"
    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s*\d*\s*-?\s*\w*\s*\d*\s*(\d{4})', m_str, re.IGNORECASE)
    if match:
        month_name = match.group(1)
        year = match.group(2)
        print(f"  Regex matched: month='{month_name}', year='{year}'")
        # Create date string with first day of month
        date_str = f"{month_name} 1, {year}"
        print(f"  Creating date from: '{date_str}'")
        result = pd.to_datetime(date_str, errors='coerce')
        print(f"  ✓ Result: {result}")
        return result
    else:
        print(f"  ✗ Regex did not match")
    
    return pd.NaT

print("=== Testing Month Parsing Logic ===")
for month in test_months:
    parse_month(month)

print("\n" + "="*60)
print("Testing with actual column data simulation:")
print("="*60)

# Simulate what happens in the actual data
df = pd.DataFrame({
    'Month': test_months,
    'Value': [100, 200, 300, 400, 500]
})

print("\nBefore parsing:")
print(df)

df['Month'] = df['Month'].apply(parse_month)

print("\nAfter parsing:")
print(df)
print(f"\nNon-null months: {df['Month'].notna().sum()}")
