import streamlit as st
from financial_analyzer.microsoft_excel import ExcelHandler
from financial_analyzer.analysis_modes import FinancialAnalyzer
import pandas as pd

# Simulate loading
st.set_page_config(page_title="Debug Cash Flow", layout="wide")

# Load data
dfs = ExcelHandler.load_data('onedrive')

if dfs:
    st.write("### Raw Cash Flow Sheet")
    df = dfs.get('Cash flow')
    if df is not None:
        st.dataframe(df.head(50))
        
        st.write("### Analysis Result")
        res = FinancialAnalyzer.analyze_cash_flow_statement(dfs)
        
        if res:
            st.write("#### Operating Items DataFrame")
            operating_items = res.get('operating_items', pd.DataFrame())
            st.write(f"Shape: {operating_items.shape}")
            st.dataframe(operating_items)
            
            st.write("#### Raw Data (cleaned)")
            st.dataframe(res['raw_data'])
else:
    st.error("Failed to load data")
