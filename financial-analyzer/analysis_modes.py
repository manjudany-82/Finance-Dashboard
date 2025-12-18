
from schema_matcher import SchemaMatcher
import pandas as pd
from datetime import datetime
import streamlit as st

# Cache for analysis results to prevent redundant calculations
_analysis_cache = {}

class FinancialAnalyzer:
    """
    Core logic for extracting KPIs and Charts for the 7 dashboards modes.
    Robust handling using SchemaMatcher.
    """
    
    @staticmethod
    def analyze_overview(dfs):
        """Mode 1: Overview - Aggregates key metrics from other modules"""
        if not dfs or not isinstance(dfs, dict):
            return {'ytd_sales': 0, 'ytd_expense': 0, 'net_profit': 0, 'net_profit_margin': 0, 'total_ar': 0, 'total_ap': 0}
        
        results = {}
        
        # 1. P&L Metrics (YTD Sales, Expense, Net)
        try:
            pnl_res = FinancialAnalyzer.analyze_profit(dfs)
            metrics = pnl_res.get('metrics', {})
            results['ytd_sales'] = metrics.get('ytd_op_income', 0)
            # Fix: Include Other Expenses in the main card
            results['ytd_expense'] = metrics.get('ytd_op_expense', 0) + metrics.get('ytd_other_expense', 0)
            results['net_profit'] = metrics.get('ytd_net_profit', 0)
            results['net_profit_margin'] = metrics.get('net_margin', 0)
        except Exception:
            results['ytd_sales'] = 0
            results['ytd_expense'] = 0
            results['net_profit'] = 0
            results['net_profit_margin'] = 0
            
        # 2. Balance Sheet Metrics (AR, AP)
        try:
            ar_res = FinancialAnalyzer.analyze_ar(dfs)
            results['total_ar'] = ar_res.get('total_ar', 0)
        except Exception:
            results['total_ar'] = 0
            
        try:
            ap_res = FinancialAnalyzer.analyze_ap(dfs)
            results['total_ap'] = ap_res.get('total_open', 0)
        except Exception:
             results['total_ap'] = 0
            
        return results

    @staticmethod
    def analyze_sales(dfs):
        """Mode 2: Sales Trends"""
        # Check cache first
        cache_key = f"sales_{id(dfs)}"
        if cache_key in _analysis_cache:
            return _analysis_cache[cache_key]
        
        df = SchemaMatcher.get_sheet(dfs, 'Sales_Monthly')
        # Default empty return
        default_res = {
            'by_product': pd.DataFrame(columns=['Product', 'Revenue']), 
            'trend': pd.DataFrame(columns=['Month', 'Revenue']),
            'product_monthly': pd.DataFrame(),
            'product_mom_growth': pd.DataFrame()
        }
        
        if df is None: return default_res
        
        prod_col = SchemaMatcher.get_column(df, 'Product') or 'Product'
        rev_col = SchemaMatcher.get_column(df, 'Revenue') or 'Amount'
        month_col = SchemaMatcher.get_column(df, 'Month') or 'Date'

        if prod_col not in df.columns or rev_col not in df.columns:
            return default_res # Cannot analyze without these

        # Group by Product
        by_product = df.groupby(prod_col)[rev_col].sum().reset_index()
        by_product.columns = ['Product', 'Revenue'] # Normalize output names
        
        # Trend over time
        if month_col in df.columns:
            trend = df.groupby(month_col)[rev_col].sum().reset_index()
            trend.columns = ['Month', 'Revenue']
        else:
            trend = pd.DataFrame(columns=['Month', 'Revenue'])
        
        # Product-wise monthly trends and MoM growth
        product_monthly = pd.DataFrame()
        product_mom_growth = pd.DataFrame()
        
        if month_col in df.columns and prod_col in df.columns:
            try:
                # Create pivot table: Products as rows, Months as columns
                df_copy = df.copy()
                df_copy[month_col] = pd.to_datetime(df_copy[month_col])
                df_copy = df_copy.sort_values(month_col)
                
                product_monthly = df_copy.pivot_table(
                    index=prod_col,
                    columns=month_col,
                    values=rev_col,
                    aggfunc='sum',
                    fill_value=0
                )
                
                # Calculate Month-on-Month growth percentage
                if len(product_monthly.columns) > 1:
                    product_mom_growth = product_monthly.copy()
                    for i in range(1, len(product_mom_growth.columns)):
                        prev_col = product_mom_growth.columns[i-1]
                        curr_col = product_mom_growth.columns[i]
                        # Calculate percentage change
                        product_mom_growth[curr_col] = (
                            (product_monthly[curr_col] - product_monthly[prev_col]) / 
                            product_monthly[prev_col].replace(0, 1) * 100
                        )
                    # First column has no previous month, set to 0
                    product_mom_growth[product_mom_growth.columns[0]] = 0
                    
            except Exception as e:
                # If pivot fails, return empty dataframes
                pass
        
        result = {
            'by_product': by_product,
            'trend': trend,
            'product_monthly': product_monthly,
            'product_mom_growth': product_mom_growth
        }
        
        # Cache result
        cache_key = f"sales_{id(dfs)}"
        _analysis_cache[cache_key] = result
        return result

    @staticmethod
    def analyze_ar(dfs):
        """Mode 3: AR Collections"""
        df = SchemaMatcher.get_sheet(dfs, 'AR')
        default_res = {
            'aging_table': pd.DataFrame(columns=['AgingBucket', 'Amount']),
            'details': pd.DataFrame(columns=['Customer', 'Amount', 'DaysOverdue'])
        }
        if df is None: return default_res
        
        # Identify columns
        # In the reported format, Col 0 is Customer, and we have buckets like 'Current', '1 - 30' etc.
        # We need to reconstruct the "Total Open" from these buckets if 'Amount' column is just Total.
        
        # Find Customer Column (likely the first one, or named 'Customer')
        cust_col = SchemaMatcher.get_column(df, 'Customer')
        if not cust_col:
             # Fallback: Use the first string column that isn't a bucket
             for col in df.columns:
                 if str(col).strip() == '': 
                     cust_col = col
                     break
        if not cust_col: cust_col = df.columns[0] # Aggressive fallback

        # Clean "Total" rows - optimized with case-insensitive vectorized operation
        if cust_col in df.columns:
            df = df[~df[cust_col].astype(str).str.contains('Total', case=False, na=False, regex=False)]

        # Find Total Amount
        amt_col = SchemaMatcher.get_column(df, 'Total') or SchemaMatcher.get_column(df, 'Amount')
        
        # If we have buckets, we can calculate aging table directly from sums
        bucket_cols = [c for c in df.columns if '30' in str(c) or '60' in str(c) or '90' in str(c) or 'Current' in str(c)]
        
        if bucket_cols:
            # We have a pre-aged report!
            aging_data = []
            for b in bucket_cols:
                aging_data.append({'AgingBucket': b, 'Amount': df[b].sum()})
            aging = pd.DataFrame(aging_data)
        else:
            # Transaction list logic (existing)
            aging = pd.DataFrame(columns=['AgingBucket', 'Amount'])
            
        # Details: Top customers by Total Balance
        if amt_col and cust_col:
            details = df[[cust_col, amt_col]].sort_values(amt_col, ascending=False).head(10)
            details.columns = ['Customer', 'Amount']
            details['DaysOverdue'] = 0 # Not available in summary report
        else:
            details = default_res['details']
        
        return {
            'aging_table': aging,
            'details': details,
            'total_ar': df[amt_col].sum() if amt_col else 0
        }

    @staticmethod
    def analyze_ap(dfs):
        """Mode 4: AP Management"""
        df = SchemaMatcher.get_sheet(dfs, 'AP')
        default_res = {
            'total_open': 0, 'upcoming_30d': 0, 
            'vendors': pd.DataFrame(columns=['Vendor', 'Amount'])
        }
        if df is None: return default_res
        
        # Find Vendor Column
        vend_col = SchemaMatcher.get_column(df, 'Vendor')
        if not vend_col:
             for col in df.columns:
                 if str(col).strip() == '': 
                     vend_col = col
                     break
        if not vend_col: vend_col = df.columns[0]
        
        # CLEANUP: Remove Total Row
        df = df[~df[vend_col].astype(str).str.contains('Total', case=False, na=False)]
        
        amt_col = SchemaMatcher.get_column(df, 'Total') or SchemaMatcher.get_column(df, 'Amount')
        
        total_open = df[amt_col].sum() if amt_col else 0
        
        # Upcoming 30d (Current + 1-30)
        upcoming_cols = [c for c in df.columns if 'Current' in str(c) or '1 - 30' in str(c)]
        upcoming_30d = 0
        for c in upcoming_cols:
            upcoming_30d += df[c].sum()
            
        if vend_col and amt_col:
             vendors = df.groupby(vend_col)[amt_col].sum().reset_index().sort_values(amt_col, ascending=False).head(10)
             vendors.columns = ['Vendor', 'Amount']
        else:
             vendors = default_res['vendors']
        
        return {
            'total_open': total_open,
            'upcoming_30d': upcoming_30d,
            'vendors': vendors
        }

    @staticmethod
    def analyze_cash(dfs):
        """Mode 5: Cash Flow"""
        df = SchemaMatcher.get_sheet(dfs, 'Cash')
        default_res = {
            'daily_trend': pd.DataFrame(columns=['Date', 'Balance']),
            'runway_months': 999, 'current_balance': 0, 'burn_rate_mo': 0
        }
        if df is None: return default_res
        
        date_col = SchemaMatcher.get_column(df, 'Date')
        bal_col = SchemaMatcher.get_column(df, 'Balance')
        inflow_col = SchemaMatcher.get_column(df, 'Inflow')
        outflow_col = SchemaMatcher.get_column(df, 'Outflow')
        
        if not date_col or not bal_col: return default_res
        
        # Daily Trend
        cols_to_use = [date_col, bal_col]
        if inflow_col: cols_to_use.append(inflow_col)
        if outflow_col: cols_to_use.append(outflow_col)
        
        daily = df.groupby(date_col)[cols_to_use[1:]].sum().reset_index()
        daily.rename(columns={date_col: 'Date', bal_col: 'Balance'}, inplace=True)
        
        # Runway
        latest_date = df[date_col].max()
        current_balance = df[df[date_col] == latest_date][bal_col].iloc[-1]
        
        avg_monthly_burn = 0
        if outflow_col:
             last_90 = df[df[date_col] > (latest_date - pd.Timedelta(days=90))]
             avg_monthly_burn = (last_90[outflow_col].sum() / 3) 
        elif bal_col:
             # Try infer negative balance changes??
             # Too complex, just default 0
             pass
             
        runway_months = current_balance / avg_monthly_burn if avg_monthly_burn > 0 else 999
        
        return {
            'daily_trend': daily,
            'runway_months': runway_months,
            'current_balance': current_balance,
            'burn_rate_mo': avg_monthly_burn
        }

    @staticmethod
    def analyze_profit(dfs):
        """Mode 6: Profitability"""
        default_res = {'monthly_pnl': pd.DataFrame(columns=['Month', 'Revenue', 'NetProfit', 'Margin'])}
        
        # Load segregated data
        df_sales = SchemaMatcher.get_sheet(dfs, 'Sales_Monthly')      # Operating Income
        df_exp = SchemaMatcher.get_sheet(dfs, 'Expenses_Monthly')     # Operating Expense
        df_other_inc = SchemaMatcher.get_sheet(dfs, 'Other_Income_Monthly')
        df_other_exp = SchemaMatcher.get_sheet(dfs, 'Other_Expenses_Monthly')
        
        # Combine for detailed view (Pivot Table)
        frames = []
        if df_sales is not None: frames.append(df_sales)
        if df_exp is not None: frames.append(df_exp)
        if df_other_inc is not None: frames.append(df_other_inc)
        if df_other_exp is not None: frames.append(df_other_exp)
        
        if not frames: return default_res
        
        df_pnl_all = pd.concat(frames, ignore_index=True)
        
        # Calculate Monthly Aggregates
        def get_monthly_sum(df):
            if df is not None and not df.empty:
                return df.groupby('Month')['Revenue'].sum()
            return pd.Series()

        s_op_inc = get_monthly_sum(df_sales)
        s_op_exp = get_monthly_sum(df_exp)
        s_oth_inc = get_monthly_sum(df_other_inc)
        s_oth_exp = get_monthly_sum(df_other_exp)
        
        # Align dates
        all_months = sorted(list(set(s_op_inc.index) | set(s_op_exp.index) | set(s_oth_inc.index) | set(s_oth_exp.index)))
        
        pnl_data = []
        for m in all_months:
            op_inc = s_op_inc.get(m, 0)
            op_exp = s_op_exp.get(m, 0)
            oth_inc = s_oth_inc.get(m, 0)
            oth_exp = s_oth_exp.get(m, 0)
            
            net_op_profit = op_inc - op_exp
            net_profit = net_op_profit + oth_inc - oth_exp
            
            pnl_data.append({
                'Month': m,
                'OperatingIncome': op_inc,
                'OperatingExpense': op_exp,
                'NetOperatingProfit': net_op_profit,
                'OtherIncome': oth_inc,
                'OtherExpense': oth_exp,
                'NetProfit': net_profit,
                'Margin': (net_profit / op_inc * 100) if op_inc != 0 else 0
            })
            
        pnl = pd.DataFrame(pnl_data)
        
        # YTD Metrics
        metrics = {
            'ytd_op_income': pnl['OperatingIncome'].sum(),
            'ytd_op_expense': pnl['OperatingExpense'].sum(),
            'ytd_net_op_profit': pnl['NetOperatingProfit'].sum(),
            'ytd_other_income': pnl['OtherIncome'].sum(),
            'ytd_other_expense': pnl['OtherExpense'].sum(),
            'ytd_net_profit': pnl['NetProfit'].sum(),
            'op_margin': (pnl['NetOperatingProfit'].sum() / pnl['OperatingIncome'].sum() * 100) if pnl['OperatingIncome'].sum() else 0,
            'net_margin': (pnl['NetProfit'].sum() / pnl['OperatingIncome'].sum() * 100) if pnl['OperatingIncome'].sum() else 0
        }
        
        # Detailed Categorization
        # Use existing 'Type' column if available (High Quality)
        if 'Type' in df_pnl_all.columns:
             df_pnl_all['Category'] = df_pnl_all['Type']
        else:
             # Fallback
             df_pnl_all['Category'] = 'Uncategorized'
             
        # Format month for display
        df_pnl_all['MonthStr'] = pd.to_datetime(df_pnl_all['Month']).dt.strftime('%b %Y')
        
        # Pivot
        detailed_pivot = df_pnl_all.pivot_table(index=['Category', 'Product'], columns='MonthStr', values='Revenue', aggfunc='sum').fillna(0)
        
        # Sort columns chronologically
        sorted_month_strs = [m.strftime('%b %Y') for m in all_months]
        existing_cols = [c for c in sorted_month_strs if c in detailed_pivot.columns]
        detailed_pivot = detailed_pivot[existing_cols]

        return {'monthly_pnl': pnl, 'metrics': metrics, 'detailed_pivot': detailed_pivot}

    @staticmethod
    def analyze_spending(dfs):
        """Mode 8: Spending Analysis"""
        try:
             df_exp = SchemaMatcher.get_sheet(dfs, 'Expenses_Monthly')
             df_other = SchemaMatcher.get_sheet(dfs, 'Other_Expenses_Monthly')
             
             frames = []
             if df_exp is not None: frames.append(df_exp)
             if df_other is not None: frames.append(df_other)
             
             if not frames: return None
             
             all_expenses = pd.concat(frames, ignore_index=True)
             
             # 1. Total Monthly Trend
             monthly = all_expenses.groupby('Month')['Revenue'].sum().reset_index()
             
             # 2. Top 5 Categories (Accounts) YTD
             by_account = all_expenses.groupby('Product')['Revenue'].sum().sort_values(ascending=False).reset_index()
             top_5 = by_account.head(5)
             
             # 3. Top 5 Trend (MoM)
             top_5_names = top_5['Product'].tolist()
             top_5_trend = all_expenses[all_expenses['Product'].isin(top_5_names)].copy()
             
             return {
                 'monthly': monthly,
                 'top_5_ytd': top_5,
                 'top_5_trend': top_5_trend
             }
        except Exception:
             return None

    @staticmethod
    def analyze_forecast(dfs):
        """Mode 7: Forecast"""
        try:
             # Base forecast on Operating Income (Sales Mode)
             res = FinancialAnalyzer.analyze_sales(dfs)
             trend = res['trend']
             if trend.empty: return None
             
             # Clean up
             trend['Revenue'] = pd.to_numeric(trend['Revenue'], errors='coerce').fillna(0)
             trend = trend.sort_values('Month')
             
             # Calculate Growth Rate (CAGR or simple avg of last 6 mos)
             # Use last 6 months for relevance
             recent = trend.tail(6).copy()
             recent['Growth'] = recent['Revenue'].pct_change()
             avg_growth = recent['Growth'].mean()
             
             # Cap extreme growth for realism (-20% to +20%)
             avg_growth = max(min(avg_growth, 0.2), -0.2)
             if pd.isna(avg_growth): avg_growth = 0
             
             # Generate Forecast
             last_date = pd.to_datetime(trend.iloc[-1]['Month'])
             last_val = trend.iloc[-1]['Revenue']
             
             future_rows = []
             current_val = last_val
             
             for i in range(1, 4):
                 next_date = last_date + pd.DateOffset(months=i)
                 current_val = current_val * (1 + avg_growth)
                 future_rows.append({
                     'Month': next_date, 
                     'Revenue': current_val,
                     'Type': 'Forecast'
                 })
                 
             forecast_df = pd.DataFrame(future_rows)
             
             trend['Type'] = 'Actual'
             
             return {
                 'history': trend,
                 'forecast': forecast_df,
                 'growth_rate': avg_growth
             }
        except Exception as e:
             print(f"Forecast Error: {e}")
             return None
    
    @staticmethod
    def analyze_cash_flow_statement(dfs):
        """Mode 9: Cash Flow Statement Analysis (from QuickBooks Statement of Cash Flows)"""
        try:
            # Direct access since the sheet name is "Cash flow" (with space)
            df = dfs.get('Cash flow')
            if df is None or df.empty:
                return None
            
            # QuickBooks format: First column has line items, second has amounts
            df_clean = df.copy()
            df_clean.columns = ['Line_Item', 'Amount']
            
            # Remove NaN rows and convert amounts
            df_clean = df_clean[df_clean['Amount'].notna()].copy()
            df_clean['Amount'] = pd.to_numeric(df_clean['Amount'], errors='coerce').fillna(0)
            
            # Extract key sections
            net_income = df_clean[df_clean['Line_Item'].str.contains('Net Income', case=False, na=False)]['Amount'].sum()
            
            # Operating Activities (between "OPERATING ACTIVITIES" and "INVESTING")
            operating_start = df_clean[df_clean['Line_Item'].str.contains('OPERATING ACTIVITIES', case=False, na=False)].index
            investing_start = df_clean[df_clean['Line_Item'].str.contains('INVESTING ACTIVITIES', case=False, na=False)].index
            financing_start = df_clean[df_clean['Line_Item'].str.contains('FINANCING ACTIVITIES', case=False, na=False)].index
            
            # Calculate section totals
            operating_cf = 0
            investing_cf = 0
            financing_cf = 0
            
            if len(operating_start) > 0:
                end_idx = investing_start[0] if len(investing_start) > 0 else len(df_clean)
                operating_section = df_clean.iloc[operating_start[0]+1:end_idx]
                operating_cf = operating_section['Amount'].sum()
            
            if len(investing_start) > 0:
                end_idx = financing_start[0] if len(financing_start) > 0 else len(df_clean)
                investing_section = df_clean.iloc[investing_start[0]+1:end_idx]
                investing_cf = investing_section['Amount'].sum()
            
            if len(financing_start) > 0:
                financing_section = df_clean.iloc[financing_start[0]+1:]
                financing_cf = financing_section['Amount'].sum()
            
            # Net change in cash
            net_cash_change = operating_cf + investing_cf + financing_cf
            
            # Key metrics
            fcf = operating_cf + investing_cf  # Free Cash Flow
            
            # Get ONLY actual cash transactions from Investing and Financing sections
            # Operating section contains reconciliation items (A/R, A/P, credit cards, etc.) which aren't actual cash
            # Only Investing and Financing sections show actual cash transactions
            
            # Find section boundaries
            operating_start_idx = operating_start[0] if len(operating_start) > 0 else 0
            investing_start_idx = investing_start[0] if len(investing_start) > 0 else len(df_clean)
            financing_start_idx = financing_start[0] if len(financing_start) > 0 else len(df_clean)
            
            # Extract only Investing and Financing sections (actual cash transactions)
            investing_items = pd.DataFrame()
            financing_items = pd.DataFrame()
            
            if len(investing_start) > 0:
                end_idx = financing_start_idx if len(financing_start) > 0 else len(df_clean)
                investing_items = df_clean.iloc[investing_start_idx+1:end_idx].copy()
            
            if len(financing_start) > 0:
                # Find where financing section ends (before "Net cash increase")
                net_increase_idx = df_clean[df_clean['Line_Item'].str.contains('Net cash increase|Net cash decrease', case=False, na=False)].index
                end_idx = net_increase_idx[0] if len(net_increase_idx) > 0 else len(df_clean)
                financing_items = df_clean.iloc[financing_start_idx+1:end_idx].copy()
            
            # Combine investing and financing items
            actual_cash_items = pd.concat([investing_items, financing_items], ignore_index=True)
            
            # Extract Operating Activities items (reconciliation items from Net Income to Cash)
            operating_items = pd.DataFrame()
            if len(operating_start) > 0:
                # In QuickBooks, operating items might be:
                # 1. Between "OPERATING ACTIVITIES" and "INVESTING ACTIVITIES"
                # 2. OR between "Net Income" and "Net cash provided by operating"
                
                # Try to find Net Income line as starting point
                net_income_idx = df_clean[df_clean['Line_Item'].str.contains('Net Income', case=False, na=False)].index
                net_cash_operating_idx = df_clean[df_clean['Line_Item'].str.contains('Net cash provided by operating|Net cash used in operating', case=False, na=False)].index
                
                # Use Net Income to Net Cash Operating as the operating section
                if len(net_income_idx) > 0 and len(net_cash_operating_idx) > 0:
                    # Get all items from Net Income through to (but not including) net cash summary
                    operating_items = df_clean.iloc[net_income_idx[0]:net_cash_operating_idx[0]].copy()
                elif len(investing_start) > 0:
                    # Fallback: use section headers
                    operating_items = df_clean.iloc[operating_start_idx+1:investing_start_idx].copy()
                
                # Exclude section summaries and headers
                operating_items = operating_items[
                    ~operating_items['Line_Item'].str.contains('net cash provided|net cash used|total|OPERATING ACTIVITIES', case=False, na=False)
                ]
            
            # Filter out section summaries and cash balance lines
            exclude_keywords = [
                'net cash provided', 'net cash used', 'total',
                'cash at beginning', 'cash at end', 'net cash increase', 'net cash decrease'
            ]
            actual_cash_items = actual_cash_items[
                ~actual_cash_items['Line_Item'].str.contains('|'.join(exclude_keywords), case=False, na=False)
            ]
            
            # Remove zero amounts
            actual_cash_items = actual_cash_items[actual_cash_items['Amount'] != 0]
            
            # Separate into inflows and outflows
            top_outflows = actual_cash_items[actual_cash_items['Amount'] < 0].nsmallest(5, 'Amount')
            top_inflows = actual_cash_items[actual_cash_items['Amount'] > 0].nlargest(5, 'Amount')
            
            return {
                'net_income': net_income,
                'operating_cf': operating_cf,
                'investing_cf': investing_cf,
                'financing_cf': financing_cf,
                'net_cash_change': net_cash_change,
                'free_cash_flow': fcf,
                'top_outflows': top_outflows,
                'top_inflows': top_inflows,
                'raw_data': df_clean,
                'operating_items': operating_items
            }
        except Exception as e:
            print(f"Cash Flow Statement Error: {e}")
            return None
