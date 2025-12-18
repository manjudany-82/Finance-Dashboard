import pandas as pd
import requests
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# Test loading from OneDrive
onedrive_url = "https://myworksocial-my.sharepoint.com/:x:/p/dannya/EbB6qC0KAuVMtZRaFub_DgsBgirK7ySgwixiWLUOB-kZQA"

print("Testing OneDrive connection...")
print(f"URL: {onedrive_url}\n")

# Transform to download link
if "download=1" not in onedrive_url:
    separator = "&" if "?" in onedrive_url else "?"
    download_url = f"{onedrive_url}{separator}download=1"
else:
    download_url = onedrive_url

print(f"Download URL: {download_url}\n")

try:
    print("Fetching file from OneDrive...")
    response = requests.get(download_url)
    response.raise_for_status()
    
    content_type = response.headers.get('Content-Type', '')
    print(f"Content-Type: {content_type}")
    print(f"Content-Length: {len(response.content)} bytes\n")
    
    if 'text/html' in content_type:
        print("❌ ERROR: Received HTML instead of Excel file")
        print("This usually means the link is not public or needs authentication")
    else:
        print("✓ Successfully downloaded Excel file\n")
        
        # Parse Excel
        xls = pd.read_excel(BytesIO(response.content), sheet_name=None, header=None)
        print(f"Available sheets: {list(xls.keys())}\n")
        
        # Check MOM PL for December
        mom_df = xls.get('MOM PL')
        if mom_df is not None:
            print("=== MOM PL Header Row (Row 4) ===")
            header_row = mom_df.iloc[4]
            print(header_row)
            print("\n")
            
            # Check for December
            months_found = []
            for val in header_row:
                if val and 'December' in str(val):
                    months_found.append(str(val))
                elif val and any(m in str(val) for m in ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November']):
                    months_found.append(str(val))
            
            print(f"Month columns found: {months_found}")
            
            if any('December' in m for m in months_found):
                print("\n✅ SUCCESS: December 2025 data IS present in the OneDrive file!")
            else:
                print("\n⚠️ WARNING: December 2025 data NOT found in OneDrive file")
                print("Please check that the Excel file has been saved with December data")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Network Error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
