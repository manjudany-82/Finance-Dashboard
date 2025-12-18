from microsoft_excel import ExcelHandler
import pandas as pd

print("=== Testing Data Load from OneDrive with December Fix ===\n")

onedrive_config = {
    'url': 'https://myworksocial-my.sharepoint.com/:x:/p/dannya/EbB6qC0KAuVMtZRaFub_DgsBgirK7ySgwixiWLUOB-kZQA',
    'token': 'MOCK_TOKEN'
}

try:
    print("Loading data from OneDrive...")
    dfs = ExcelHandler.load_data(source="onedrive", onedrive_config=onedrive_config)
    
    if dfs:
        print("\n✅ Data loaded successfully!\n")
        print(f"Available sheets: {list(dfs.keys())}\n")
        
        # Check Sales_Monthly for December data
        if 'Sales_Monthly' in dfs:
            sales_df = dfs['Sales_Monthly']
            print(f"Sales_Monthly shape: {sales_df.shape}")
            print(f"Sales_Monthly columns: {list(sales_df.columns)}\n")
            
            # Get unique months
            if 'Month' in sales_df.columns:
                months = pd.to_datetime(sales_df['Month']).dt.strftime('%Y-%m').unique()
                print(f"Unique months in Sales_Monthly:")
                for m in sorted(months):
                    print(f"  - {m}")
                
                # Check specifically for December 2025
                dec_2025 = sales_df[pd.to_datetime(sales_df['Month']).dt.strftime('%Y-%m') == '2025-12']
                if not dec_2025.empty:
                    print(f"\n✅ SUCCESS: December 2025 data found! ({len(dec_2025)} records)")
                    print(f"Total December revenue: ${dec_2025['Revenue'].sum():,.2f}")
                else:
                    print("\n⚠️ December 2025 data NOT found")
            else:
                print("'Month' column not found in Sales_Monthly")
        else:
            print("'Sales_Monthly' sheet not found in processed data")
    else:
        print("❌ Failed to load data")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
