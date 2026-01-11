import sys
from pathlib import Path

repo_root = Path(__file__).parent.absolute()
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import streamlit as st
import pandas as pd
import plotly.express as px

# Top-level native Streamlit UI (no JS, no unsafe HTML).
try:
    st.set_page_config(page_title="Enterprise Financial Dashboard", page_icon="📊", layout="wide")
except Exception:
    pass

st.title("Enterprise Financial Dashboard")

with st.sidebar:
    st.header("Controls")
    st.write("Upload a file or use sample data to view charts and tables.")
    uploaded = st.file_uploader("Upload Excel (optional)", type=["xlsx"]) 
    if st.button("Load Sample Data"):
        st.session_state['use_sample'] = True

# Provide a simple visible dataset and chart so the UI is never blank.
if 'use_sample' in st.session_state and st.session_state['use_sample']:
    df = pd.DataFrame({"month": ["Jan","Feb","Mar","Apr"], "value": [10, 15, 8, 20]})
else:
    # fallback sample
    df = pd.DataFrame({"month": ["Jan","Feb","Mar","Apr"], "value": [5, 7, 6, 9]})

st.subheader("Overview")
fig = px.bar(df, x="month", y="value", title="Sample Monthly Values")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Data Table")
st.dataframe(df)
 

