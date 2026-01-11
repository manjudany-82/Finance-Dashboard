import streamlit as st

# Compat shim: silence any third-party calls to deprecated query param APIs by delegating
# to the new st.query_params. This avoids startup warnings from dependency imports.
def _shim_get_query_params():
    try:
        return st.query_params
    except Exception:
        return {}


def _shim_set_query_params(**kwargs):
    try:
        st.query_params.clear()
        st.query_params.update(kwargs)
    except Exception:
        pass


st.experimental_get_query_params = _shim_get_query_params
st.experimental_set_query_params = _shim_set_query_params
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from financial_analyzer.microsoft_excel import ExcelHandler
from financial_analyzer.analysis_modes import FinancialAnalyzer
from financial_analyzer.forecast_engine import ForecastEngine
from financial_analyzer.llm_insights import AIAnalyst
from financial_analyzer.render_layouts import render_overview, render_sales, render_ar, render_ap, render_cash, render_profit, render_forecast, render_spending

# Runtime-only AI insights renderer (rule-based fallback). This avoids import-time
# Streamlit/genai wiring and preserves a simple AI fallback behavior.
def render_ai_insights(dfs, ai, ai_enabled=False):
    import streamlit as st
    st.header("AI Insights (Rule-based fallback)")
    if not dfs:
        st.info("Load data from the sidebar to enable AI insights.")
        return
    analyst = ai or AIAnalyst()
    try:
        primary = None
        if isinstance(dfs, dict):
            # pick first non-empty
            for v in dfs.values():
                if hasattr(v, 'empty') and not v.empty:
                    primary = v
                    break
        elif hasattr(dfs, 'empty'):
            primary = dfs
        bullets = analyst.generate_fallback_insights("Overview", {})
        for b in bullets:
            st.markdown(f"- {b}")
    except Exception:
        st.info("Rule-based insights currently unavailable.")
from financial_analyzer.auth import check_password
import os
import time

def _apply_page_config():
    import streamlit as st
    try:
        st.set_page_config(
            page_title="Enterprise Financial Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    except Exception:
        # set_page_config may only be called once in a Streamlit session;
        # swallow errors when called multiple times or outside Streamlit.
        pass

# NOTE: UI CSS/JS injection removed. All UI rendering now happens in top-level
# `dashboard.py` to avoid unsafe HTML/JS and import-time side effects.
# Configuration
DEFAULT_ONEDRIVE_LINK = "https://myworksocial-my.sharepoint.com/:x:/p/dannya/EbB6qC0KAuVMtZRaFub_DgsBgirK7ySgwixiWLUOB-kZQA"

# Application State
if 'data' not in st.session_state:
    st.session_state.data = None

# Cleanup old cache entries to prevent memory bloat
if 'cache_size' not in st.session_state:
    st.session_state.cache_size = 0

# Sidebar collapsed state (server-side toggle to avoid fragile JS)
if 'sidebar_collapsed' not in st.session_state:
    st.session_state['sidebar_collapsed'] = False

def collapse_sidebar():
    st.session_state['sidebar_collapsed'] = True
    st.experimental_rerun()

def expand_sidebar():
    st.session_state['sidebar_collapsed'] = False
    st.experimental_rerun()

def main():
    try:
        _apply_page_config()
    except Exception:
        pass
    # Handle URL-driven actions (logout / expand) before rendering
    try:
        params = st.query_params
    except Exception:
        params = {}

    if params.get('logout', [None])[0] == '1':
        from auth import logout as _logout
        _logout()
        return

    if params.get('expand', [None])[0] == '1':
        st.session_state['sidebar_collapsed'] = False
        try:
            # Clear the flag using the new query params API
            st.query_params.clear()
        except Exception:
            pass
        st.experimental_rerun()

    # 🔒 AUTHENTICATION CHECK
    if not check_password():
        st.stop()  # Stop execution if not authenticated
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("FIN ANALYTICS 🚀")
        
        # User info and logout button - more prominent
        from auth import logout
        authenticated_user = st.session_state.get("authenticated_user", "User")
        
        # User display and logout (simpler button to avoid unsupported args)
        st.markdown(f"**👤 {authenticated_user}**")
        if st.button("🚪 Logout", help="Logout", key="sidebar_logout"):
            logout()

        # Collapse sidebar (server-side toggle)
        if st.button("◄ Collapse Sidebar", key="collapse_sidebar_btn"):
            collapse_sidebar()
        
        st.divider()
        
        st.header("Data Source")

        # AI Insights Toggle (default ON only if API key present)
        ai_default = bool(os.getenv('GEMINI_API_KEY'))
        if 'enable_ai' not in st.session_state:
            st.session_state['enable_ai'] = ai_default
        st.session_state['enable_ai'] = st.checkbox("Enable AI Insights", value=st.session_state['enable_ai'])
        if st.session_state['enable_ai'] and not os.getenv('GEMINI_API_KEY'):
            st.caption("⚙️ Using rule-based insights (API key not configured)")
        
        # Template Download
        template_path = "financial_template.xlsx"
        if os.path.exists(template_path):
            with open(template_path, "rb") as f:
                st.download_button(
                    label="📥 Download Excel Template",
                    data=f,
                    file_name="financial_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.caption("📋 Template not available")
        
        st.divider()

        # Source Selection
        # Default to OneDrive if link is present
        index_default = 1 if DEFAULT_ONEDRIVE_LINK and "http" in DEFAULT_ONEDRIVE_LINK else 0
        source_type = st.selectbox("Source", ["Upload Excel File", "OneDrive (Excel Link)"], index=index_default)
        
        onedrive_url = ""
        onedrive_token = ""
        uploaded_file = None
        
        if source_type == "OneDrive (Excel Link)":
            onedrive_url = st.text_input("One Drive Link", value=DEFAULT_ONEDRIVE_LINK)
            st.info("Ensure the app has permissions or paste a direct public link if applicable.")
            onedrive_token = "MOCK_TOKEN" 
        elif source_type == "Upload Excel File":
             uploaded_file = st.file_uploader("Upload your financial data", type=['xlsx'])
        
        if st.button("Load Data", type="primary"):
            with st.spinner("Processing Financial Data..."):
                if source_type == "Upload Excel File":
                    if uploaded_file:
                         try:
                            st.session_state.data = ExcelHandler.load_data(source="upload", file_path=uploaded_file)
                            if st.session_state.data:
                                st.success("File Processed Successfully")
                         except Exception as e:
                            st.error(f"Error processing file: {e}")
                    else:
                        st.error("Please upload a file first.")
                else:
                    st.session_state.data = ExcelHandler.load_data(source="onedrive", onedrive_config={'url': onedrive_url, 'token': onedrive_token})
                    
                if st.session_state.data and source_type != "Upload Excel File":
                    st.success("Data Loaded Successfully")
                    # record a timestamp so AI insight cache can be invalidated on new data
                    st.session_state['data_loaded_at'] = time.time()
                elif not st.session_state.data and source_type != "Upload Excel File":
                    st.error("Failed to load data")

        st.divider()
        st.caption("Enterprise Edition v1.1.0")
        # Preferred model selector helps avoid quota-heavy defaults
        preferred_default = os.getenv('GEMINI_PREFERRED_MODEL', 'gemini-1.5-flash')
        model_options = ['gemini-1.5-flash', 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.0-flash-exp']
        if 'preferred_model' not in st.session_state:
            st.session_state['preferred_model'] = preferred_default if preferred_default in model_options else model_options[0]
        st.session_state['preferred_model'] = st.selectbox("LLM Model (preferred)", model_options, index=model_options.index(st.session_state['preferred_model']))
        st.caption(f"Preferred model: {st.session_state['preferred_model']} — change to avoid quota issues")

    # Fallback logout/expand controls using native Streamlit widgets
    if st.session_state.get("password_correct", False):
        cols = st.columns([1, 1, 6])
        with cols[0]:
            if st.button("🚪 Logout"):
                from auth import logout as _logout
                _logout()
                return
        with cols[1]:
            if st.button("► Expand"):
                st.session_state['sidebar_collapsed'] = False
                try:
                    # Attempt to clear query params and rerun using public API
                    st.experimental_rerun()
                except Exception:
                    pass

    # Remove CSS-based sidebar hiding; rely on Streamlit APIs/state only.
    # (If you need to hide UI, toggle rendering based on `st.session_state`.)

    # --- MAIN CONTENT ---
    if not st.session_state.data:
        st.info("👈 Please load data from the sidebar to begin analysis.")
        return

    dfs = st.session_state.data
    ai = AIAnalyst(preferred_model=st.session_state.get('preferred_model'))
    ai_enabled = st.session_state.get('enable_ai', False)
    # Inform user if AI quota is exhausted so they understand why LLM may not run
    if ai_enabled and getattr(ai, 'quota_exhausted', False):
        st.warning("AI quota appears exhausted for current models — using fallback rule-based insights. Consider switching model or increasing quota.")
    # Diagnostic expander showing LLM status and last raw/error for debugging
    with st.expander("AI Diagnostics", expanded=False):
        key_present = bool(ai.api_key)
        if key_present:
            # mask the key for security
            k = ai.api_key
            masked = f"{k[:4]}...{k[-4:]}" if len(k) > 8 else "(set)"
        else:
            masked = "(not set)"

        st.write("- GEMINI_API_KEY:", masked)
        st.write("- Preferred model:", getattr(ai, 'preferred_model', None))
        st.write("- Quota exhausted:", getattr(ai, 'quota_exhausted', False))
        st.write("- Last error:", ai.last_error if getattr(ai, 'last_error', None) else "None")
        if getattr(ai, 'last_raw', None):
            with st.expander("Last raw LLM response (truncated)"):
                raw = ai.last_raw or ""
                st.text(raw[:2000])
    
    # --- TABS NAVIGATION ---
    # Replaces the old dropdown menu logic
    tabs_list = ["Overview", "🤖 AI Insights", "Sales Trends", "AR Collections", "AP Management", "Cash Flow", "Profitability", "Spending", "Forecast"]
    tabs = st.tabs(tabs_list)
    
    with tabs[0]: render_overview(dfs, ai, ai_enabled)
    with tabs[1]: render_ai_insights(dfs, ai, ai_enabled)
    with tabs[2]: render_sales(dfs, ai, ai_enabled)
    with tabs[3]: render_ar(dfs, ai, ai_enabled)
    with tabs[4]: render_ap(dfs, ai, ai_enabled)
    with tabs[5]: render_cash(dfs, ai, ai_enabled)
    with tabs[6]: render_profit(dfs, ai, ai_enabled)
    with tabs[7]: render_spending(dfs, ai, ai_enabled)
    with tabs[8]: render_forecast(dfs, ai, ai_enabled)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        st.error(f"⚠️ Application Error: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
        # Log error for debugging
        import logging
        logging.error(f"Dashboard error: {e}", exc_info=True)
        st.exception(e)
