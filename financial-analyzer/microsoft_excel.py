import pandas as pd
import os
import requests
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

class ExcelHandler:
    """
    Handles loading financial data from either a local sample file or Microsoft OneDrive via Graph API.
    """
    
    REQUIRED_SHEETS = ['GL', 'AR', 'AP', 'Cash', 'Sales_Monthly', 'Expenses_Monthly']

    @staticmethod
    def load_data(source="sample", file_path=None, onedrive_config=None):
        """
        Main entry point to load data.
        
        Args:
            source (str): "sample" or "onedrive"
            file_path (str): Path to local file (used if source="sample" or "local")
            onedrive_config (dict): Config for OneDrive (url, token)
            
        Returns:
            dict: Dictionary of DataFrames for each sheet.
        """
        try:
            if source == "sample" or source == "local":
                if not file_path:
                    # Specific user file priority
                    user_file = "Financial_Dash_Board_Work_Social.xlsx"
                    if os.path.exists(user_file):
                        file_path = user_file
                    else:
                        file_path = "sample_excel.xlsx"
                
                if not os.path.exists(file_path):
                     raise FileNotFoundError(f"File not found: {file_path}")
                     
                return ExcelHandler._parse_excel(file_path)
                
            elif source == "onedrive":
                if not onedrive_config:
                    raise ValueError("OneDrive configuration missing")
                return ExcelHandler._fetch_from_graph(onedrive_config)
            
            elif source == "upload":
                if not file_path:
                    raise ValueError("No file uploaded")
                return ExcelHandler._parse_excel(file_path)

            else:
                raise ValueError(f"Unknown source: {source}")

        except Exception as e:
            import logging
            logging.error(f"Data loading error: {str(e)}")
            return None

    @staticmethod
    def _parse_excel(file_content):
        """
        Reads excel content and intelligently parses QuickBooks-style reports.
        """
        dfs = {}
        try:
            # Load all sheets, no header initially to find it dynamically
            xls = pd.read_excel(file_content, sheet_name=None, header=None)
            
            for sheet, raw_df in xls.items():
                parsed_df = ExcelHandler._autodetect_table(raw_df, sheet)
                if parsed_df is not None:
                    dfs[sheet] = parsed_df
            
            # Post-Processing for MOM PL -> Sales_Monthly
            if 'MOM PL' in dfs:
                # Transform MOM PL into Sales_Monthly format
                # Expect cols: 'Distribution account', 'January 2025', ... 'Total'
                mom_df = dfs['MOM PL']
                
                # Identify Month Columns (exclude 'Distribution account' and 'Total')
                id_vars = [c for c in mom_df.columns if 'account' in str(c).lower() or 'source' in str(c).lower()]
                if not id_vars: id_vars = [mom_df.columns[0]] # Default to first col
                
                # --- Categorization Logic ---
                # Assign a 'Type' (Income, Expense, Other Income, Other Expense)
                col_0 = id_vars[0]
                mom_df['Type'] = 'Other'
                current_main_type = 'Other' # Income, Expense
                current_sub_type = 'Operating' # Operating, Other
                
                for idx, row in mom_df.iterrows():
                    val = str(row[col_0]).strip().lower()
                    
                    # Section Headers detection
                    if val == 'income':
                        current_main_type = 'Income'
                        current_sub_type = 'Operating'
                    elif val == 'cost of goods sold':
                        current_main_type = 'COGS'
                        current_sub_type = 'Operating'
                    elif val == 'expenses' or val == 'expense':
                        current_main_type = 'Expense'
                        current_sub_type = 'Operating'
                    elif val == 'other income':
                        current_main_type = 'Income'
                        current_sub_type = 'Other'
                    elif val == 'other expenses' or val == 'other expense':
                        current_main_type = 'Expense'
                        current_sub_type = 'Other'
                    
                    # Composite Type
                    if current_main_type == 'COGS':
                        mom_df.at[idx, 'Type'] = 'COGS'
                    else:
                        mom_df.at[idx, 'Type'] = f"{current_sub_type} {current_main_type}"
                
                # Add Type to id_vars so it persists after melt
                id_vars.append('Type')
                
                val_vars = [c for c in mom_df.columns if c not in id_vars and 'total' not in str(c).lower()]
                
                unpivoted = mom_df.melt(id_vars=id_vars, value_vars=val_vars, var_name='Month', value_name='Amount')
                
                # Clean up formatting
                acct_col = id_vars[0]
                unpivoted = unpivoted[~unpivoted[acct_col].astype(str).str.contains('Total', na=False)]
                unpivoted = unpivoted[~unpivoted[acct_col].astype(str).str.contains('Net ', na=False)]
                unpivoted = unpivoted[~unpivoted[acct_col].isin(['Income', 'Expenses', 'Cost of Goods Sold', 'Gross Profit', 'Other Income', 'Other Expenses'])]
                
                # Convert Month to Date - Handle various formats including "Dec 1 - Dec 18 2025"
                def parse_month(m):
                    m_str = str(m).strip()
                    
                    # Try standard datetime parsing first
                    result = pd.to_datetime(m_str, errors='coerce')
                    if pd.notna(result):  # Only return if parsing succeeded
                        return result
                    
                    # Handle "Dec 1 - Dec 18 2025" format - extract month and year
                    import re
                    # Match patterns like "Dec 1 - Dec 18 2025" or "December 1-18 2025"
                    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s*\d*\s*-?\s*\w*\s*\d*\s*(\d{4})', m_str, re.IGNORECASE)
                    if match:
                        month_name = match.group(1)
                        year = match.group(2)
                        # Create date string with first day of month
                        date_str = f"{month_name} 1, {year}"
                        return pd.to_datetime(date_str, errors='coerce')
                    
                    return pd.NaT
                
                unpivoted['Month'] = unpivoted['Month'].apply(parse_month)
                unpivoted = unpivoted.dropna(subset=['Month', 'Amount'])
                
                # Map to standard names
                unpivoted.rename(columns={acct_col: 'Product', 'Amount': 'Revenue'}, inplace=True)
                
                # Segregate into 4 buckets
                dfs['Sales_Monthly'] = unpivoted[unpivoted['Type'] == 'Operating Income'].copy()
                dfs['Expenses_Monthly'] = unpivoted[unpivoted['Type'] == 'Operating Expense'].copy()
                dfs['Other_Income_Monthly'] = unpivoted[unpivoted['Type'] == 'Other Income'].copy()
                dfs['Other_Expenses_Monthly'] = unpivoted[unpivoted['Type'] == 'Other Expense'].copy()
                
                print("Generated P&L Segments: Sales (Op Income), Expenses (Op Exp), Other Income, Other Expenses")

            return dfs
            
        except Exception as e:
            raise RuntimeError(f"Failed to parse Excel file: {str(e)}")

    @staticmethod
    def _autodetect_table(df, sheet_name):
        """
        Finds the header row and returns the cleaned dataframe.
        """
        # Strategy: Look for specific keywords in the first 20 rows
        # Prioritize rows that look like table headers (have multiple non-null values)
        keywords = ['Date', 'Account', 'Total', 'Current', 'Distribution account', 'Type', '1 - 30', 'Balance', 'Amount']
        
        header_idx = -1
        max_score = 0
        
        for i, row in df.head(20).iterrows():
            row_str = row.astype(str).str.lower().tolist()
            # Score based on how many keywords match
            score = sum(1 for k in keywords if any(k.lower() in s for s in row_str))
            
            # Special check for Aging headers
            if 'current' in row_str and 'total' in row_str:
                score += 5
            
            if score > max_score and score > 0:
                max_score = score
                header_idx = i
        
        if header_idx != -1:
            # set header
            df.columns = df.iloc[header_idx]
            df = df.iloc[header_idx+1:].reset_index(drop=True)
            
            # Clean columns: handle 'nan' columns
            new_cols = []
            for c in df.columns:
                c_str = str(c).strip().replace('\n', ' ')
                if c_str.lower() == 'nan': c_str = f"Unnamed_{len(new_cols)}"
                new_cols.append(c_str)
            df.columns = new_cols
            
            # Remove purely empty rows or rows that are just separators
            df.dropna(how='all', inplace=True)
            
            # Type conversion
            for col in df.columns:
                 col_lower = str(col).lower()
                 # Check if date-like
                 if 'date' in col_lower or 'month' in col_lower:
                     try:
                        df[col] = pd.to_datetime(df[col])
                     except:
                        pass
                 # Check if numeric
                 elif any(x in col_lower for x in ['amount', 'balance', 'total', 'current', '1 - 30', '31 - 60', '61 - 90']):
                     # Remove currency symbols and parens
                     try:
                        clean_series = df[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.replace(')', '', regex=False).str.replace('(', '-', regex=False)
                        df[col] = pd.to_numeric(clean_series, errors='coerce').fillna(0)
                     except:
                        pass
            
            return df
        
        return None # Could not detect structure

    @staticmethod
    def _fetch_from_graph(config):
        """
        Fetches file bytes from URL (OneDrive/SharePoint or graph).
        Auto-converts share links to download links.
        """
        url = config.get('url')
        token = config.get('token')
        
        if not url:
             raise ValueError("OneDrive URL missing")
        
        # TRANSFORMATION: Handle standard SharePoint/OneDrive share links
        # If it's a view link (contains sharepoint.com or onedrive.live.com/...)
        if "sharepoint.com" in url or "onedrive.live.com" in url:
            if "download=1" not in url:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}download=1"
                print(f"Transformed to download link: {url}")

        headers = {}
        if token and token != "MOCK_TOKEN": # Only add if real token
            headers['Authorization'] = f'Bearer {token}'
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status() # Raise error for 4xx/5xx
            
            # Check if we got HTML (which means download failed or auth page)
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                raise ValueError("Link returned HTML page instead of Excel file. Ensure the link is public or direct download.")
                
            return ExcelHandler._parse_excel(BytesIO(response.content))
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network Error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Data Load Error: {str(e)}")
