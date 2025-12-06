import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set seed for reproducibility
np.random.seed(42)

def generate_dates(start_date, num_days):
    return [start_date + timedelta(days=i) for i in range(num_days)]

def generate_sample_data():
    print("Generating sample data...")
    
    # Setup dates - last 12 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    dates_daily = generate_dates(start_date, 365)
    
    months = pd.date_range(start=start_date, end=end_date, freq='M')
    
    # 1. GL Data (General Ledger)
    gl_data = []
    accounts = ['Revenue', 'Cost of Goods Sold', 'Operating Expenses', 'Cash', 'Accounts Receivable', 'Accounts Payable']
    categories = {'Revenue': ['Services', 'Product Sales'], 
                  'Operating Expenses': ['Rent', 'Salaries', 'Marketing', 'Software', 'Utilities']}
    
    for date in dates_daily:
        # Simulate daily transactions
        if date.day == 1: # Monthly Rent
            gl_data.append([date, 'Operating Expenses', 5000, 0, 'Rent', 'Monthly Office Rent'])
            gl_data.append([date, 'Cash', 0, 5000, 'Rent', 'Rent Payment'])
            
        if date.day == 15 or date.day == 30: # Salaries
            salary = 15000
            gl_data.append([date, 'Operating Expenses', salary, 0, 'Salaries', 'Payroll'])
            gl_data.append([date, 'Cash', 0, salary, 'Salaries', 'Payroll'])
            
        # Random Sales
        if np.random.random() > 0.3:
            amount = np.random.randint(500, 5000)
            cat = np.random.choice(categories['Revenue'])
            gl_data.append([date, 'Cash', amount, 0, cat, 'Client Payment'])
            gl_data.append([date, 'Revenue', 0, amount, cat, 'Service Revenue'])

    df_gl = pd.DataFrame(gl_data, columns=['Date', 'Account', 'Debit', 'Credit', 'Category', 'Description'])

    # 2. AR (Accounts Receivable)
    ar_data = []
    customers = ['TechCorp', 'InnovateInc', 'GlobalSoft', 'AlphaSolutions', 'BetaDesigns']
    for i in range(50):
        date = start_date + timedelta(days=np.random.randint(0, 330))
        due_date = date + timedelta(days=30)
        amount = np.random.randint(2000, 20000)
        customer = np.random.choice(customers)
        status = 'Paid' if (datetime.now() - due_date).days > -10 else 'Open'
        # Force some overdue
        if i % 10 == 0:
            status = 'Open'
            date = end_date - timedelta(days=100) # Very old
            due_date = date + timedelta(days=30)
            
        ar_data.append([f'INV-{1000+i}', customer, date, due_date, amount, status])
        
    df_ar = pd.DataFrame(ar_data, columns=['InvoiceID', 'Customer', 'Date', 'DueDate', 'Amount', 'Status'])

    # 3. AP (Accounts Payable)
    ap_data = []
    vendors = ['AWS', 'Google Cloud', 'WeWork', 'Salesforce', 'Fiverr']
    for i in range(40):
        date = start_date + timedelta(days=np.random.randint(0, 340))
        due_date = date + timedelta(days=15)
        amount = np.random.randint(500, 5000)
        vendor = np.random.choice(vendors)
        status = 'Paid' if np.random.random() > 0.2 else 'Open'
        ap_data.append([f'BILL-{500+i}', vendor, date, due_date, amount, status])
        
    df_ap = pd.DataFrame(ap_data, columns=['BillID', 'Vendor', 'Date', 'DueDate', 'Amount', 'Status'])

    # 4. Cash Flow
    cash_data = []
    balance = 50000
    for date in dates_daily:
        inflow = 0
        outflow = 0
        
        # Simple simulation based on gl logic/randomness
        if np.random.random() > 0.7:
            inflow = np.random.randint(1000, 8000)
        if np.random.random() > 0.6:
            outflow = np.random.randint(500, 4000)
            
        # Large expenses
        if date.day == 1: outflow += 5000 # Rent
        if date.day == 15: outflow += 15000 # Payroll
        
        balance = balance + inflow - outflow
        cash_data.append([date, inflow, outflow, balance, 'Operating'])
        
    df_cash = pd.DataFrame(cash_data, columns=['Date', 'Inflow', 'Outflow', 'Balance', 'Category'])

    # 5. Sales Monthly (for trends)
    sales_data = []
    products = ['Product A', 'Product B', 'Product C']
    base_revenue = 10000
    for month in months:
        for product in products:
            growth_factor = 1.0 + (0.02 * (month.month % 12)) # Slight growth
            if product == 'Product B': growth_factor *= 1.5 # Product B crushing it
            
            revenue = int(base_revenue * growth_factor * np.random.uniform(0.9, 1.1))
            cost = int(revenue * 0.4)
            sales_data.append([month, product, revenue, cost, 'North America'])

    df_sales = pd.DataFrame(sales_data, columns=['Month', 'Product', 'Revenue', 'Cost', 'Region'])

    # 6. Expenses Monthly
    expense_data = []
    exp_cats = ['Rent', 'Salaries', 'Marketing', 'Software', 'Travel']
    for month in months:
        for cat in exp_cats:
            amount = np.random.randint(2000, 10000)
            if cat == 'Salaries': amount = 30000
            if cat == 'Rent': amount = 5000
            expense_data.append([month, cat, amount, 'Operations'])

    df_expenses = pd.DataFrame(expense_data, columns=['Month', 'Category', 'Amount', 'Department'])

    # Write to Excel
    output_path = 'sample_excel.xlsx'
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df_gl.to_excel(writer, sheet_name='GL', index=False)
        df_ar.to_excel(writer, sheet_name='AR', index=False)
        df_ap.to_excel(writer, sheet_name='AP', index=False)
        df_cash.to_excel(writer, sheet_name='Cash', index=False)
        df_sales.to_excel(writer, sheet_name='Sales_Monthly', index=False)
        df_expenses.to_excel(writer, sheet_name='Expenses_Monthly', index=False)
    
    print(f"Successfully created {output_path}")

if __name__ == "__main__":
    generate_sample_data()
