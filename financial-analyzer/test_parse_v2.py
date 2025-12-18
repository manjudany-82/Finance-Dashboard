import pandas as pd
import re

def parse_month_v1(m):
    m_str = str(m).strip()
    print(f"Parsing: '{m_str}'")
    try:
        result = pd.to_datetime(m_str, errors='coerce')
        print(f"  pd.to_datetime result: {result}, type: {type(result)}")
        return result
    except Exception as e:
        print(f"  Exception: {e}")
        pass
    
    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s*\d*\s*-?\s*\w*\s*\d*\s*(\d{4})', m_str, re.IGNORECASE)
    if match:
        month_name = match.group(1)
        year = match.group(2)
        date_str = f"{month_name} 1, {year}"
        print(f"  Regex matched: '{date_str}'")
        return pd.to_datetime(date_str, errors='coerce')
    
    print(f"  No match, returning NaT")
    return pd.NaT

# Test
test_values = ["January 2025", "Dec 1 - Dec 18 2025", pd.Timestamp('2025-01-01')]

for val in test_values:
    result = parse_month_v1(val)
    print(f"  Final result: {result}\n")
