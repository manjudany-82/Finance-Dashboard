from microsoft_excel import ExcelHandler
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Monkey-patch to add debug output
original_parse_excel = ExcelHandler._parse_excel

def debug_parse_excel(file_content):
    result = original_parse_excel(file_content)
    
    if result and 'Sales_Monthly' in result:
        sales = result['Sales_Monthly']
        print(f"\n=== DEBUG: Sales_Monthly Processing ===")
        print(f"Total rows: {len(sales)}")
        print(f"Columns: {list(sales.columns)}")
        
        # Check December specifically
        if 'Month' in sales.columns:
            sales['Month_str'] = pd.to_datetime(sales['Month']).dt.strftime('%Y-%m')
            month_counts = sales.groupby('Month_str').size()
            print(f"\nRows per month:")
            for month, count in month_counts.items():
                print(f"  {month}: {count} rows")
            
            # Show December sample
            dec_data = sales[sales['Month_str'] == '2025-12']
            if not dec_data.empty:
                print(f"\n✅ December 2025 data EXISTS:")
                print(dec_data[['Product', 'Revenue', 'Month']].head(10))
                print(f"Total December Revenue: ${dec_data['Revenue'].sum():,.2f}")
            else:
                print(f"\n⚠️ December 2025 data NOT FOUND after processing")
                
                # Check if it was in unpivoted before cleaning
                print("\nLet me check if December was dropped during cleaning...")
    
    return result

ExcelHandler._parse_excel = debug_parse_excel

print("Loading data with debug output...\n")
onedrive_config = {
    'url': 'https://myworksocial-my.sharepoint.com/:x:/p/dannya/EbB6qC0KAuVMtZRaFub_DgsBgirK7ySgwixiWLUOB-kZQA',
    'token': 'MOCK_TOKEN'
}

dfs = ExcelHandler.load_data(source="onedrive", onedrive_config=onedrive_config)

if dfs:
    print("\n✅ Load complete")
