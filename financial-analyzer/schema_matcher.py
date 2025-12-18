import pandas as pd
import numpy as np

class SchemaMatcher:
    """
    Helper to map expected column names to actual columns in the dataframe using fuzzy matching.
    """
    
    ALIASES = {
        'Date': ['date', 'day', 'time', 'transaction date', 'inv date', 'bill date'],
        'Amount': ['amount', 'amt', 'value', 'total', 'balance', 'cost', 'debit', 'credit', 'revenue'],
        'Status': ['status', 'state', 'paid status', 'payment status'],
        'Description': ['description', 'desc', 'memo', 'details', 'name', 'account'],
        'Vendor': ['vendor', 'supplier', 'payee', 'name'],
        'Customer': ['customer', 'client', 'bill to', 'name'],
        'InvoiceID': ['invoice', 'invoice #', 'inv #', 'ref', 'doc num'],
        'DueDate': ['due date', 'due'],
        'Revenue': ['revenue', 'sales', 'income', 'credit'],
        'Balance': ['balance', 'total', 'net']
    }

    @staticmethod
    def get_column(df, target_name):
        """
        Returns the actual column name in df that matches target_name.
        Returns None if no match found.
        """
        # Exact match
        if target_name in df.columns:
            return target_name
            
        # Case insensitive
        col_map = {c.lower(): c for c in df.columns}
        if target_name.lower() in col_map:
            return col_map[target_name.lower()]
            
        # Aliases
        possible_names = SchemaMatcher.ALIASES.get(target_name, [])
        for alias in possible_names:
            if alias in col_map:
                return col_map[alias]
            # Partial match (careful with this)
            for col_lower in col_map:
                if alias in col_lower:
                    return col_map[col_lower]
                    
        return None

    @staticmethod
    def get_sheet(dfs, target_name):
        """
        Fuzzy match sheet name from dictionary of dataframes.
        """
        if target_name in dfs:
            return dfs[target_name]
            
        # Aliases for sheets
        SHEET_ALIASES = {
            'GL': ['general ledger', 'journal', 'transactions', 'data'],
            'AR': ['accounts receivable', 'receivables', 'invoices', 'open invoices'],
            'AP': ['accounts payable', 'payables', 'bills'],
            'Cash': ['cash flow', 'bank', 'banking', 'treasury'],
            'Sales_Monthly': ['sales', 'revenue', 'income'],
            'Expenses_Monthly': ['expenses', 'costs', 'expenditure']
        }
        
        # Case insensitive match
        keys_map = {k.lower(): k for k in dfs.keys()}
        lower_target = target_name.lower()
        if lower_target in keys_map:
            return dfs[keys_map[lower_target]]
            
        # Alias match
        aliases = SHEET_ALIASES.get(target_name, [])
        for alias in aliases:
            if alias in keys_map:
                return dfs[keys_map[alias]]
            # Partial?
            for k in keys_map:
                if alias in k:
                    return dfs[keys_map[k]]
                    
        return None

    @staticmethod
    def safe_get(df, target_name, default=None):
        """
        Safely retrieves series data using fuzzy matching.
        """
        col = SchemaMatcher.get_column(df, target_name)
        if col:
            return df[col]
        return default
