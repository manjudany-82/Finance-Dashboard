import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from microsoft_excel import ExcelHandler
from analysis_modes import FinancialAnalyzer
from forecast_engine import ForecastEngine
from llm_insights import AIAnalyst
from render_layouts import render_overview, render_sales, render_ar, render_ap, render_cash, render_profit, render_forecast, render_spending
from auth import check_password
import os
import time

# Page Config
st.set_page_config(
    page_title="Enterprise Financial Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Modern Design v2.0
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* ========== DESIGN SYSTEM ========== */
    :root {
        /* Colors */
        --bg-primary: #0A0E27;
        --bg-secondary: #0F1535;
        --card-bg: rgba(255, 255, 255, 0.03);
        --card-border: rgba(255, 255, 255, 0.08);
        
        /* Accents */
        --accent-primary: #6366F1;
        --accent-success: #10B981;
        --accent-warning: #F59E0B;
        --accent-danger: #EF4444;
        --accent-info: #3B82F6;
        
        /* Text */
        --text-primary: #F9FAFB;
        --text-secondary: #9CA3AF;
        --text-muted: #6B7280;
        
        /* Effects */
        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
        --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
        --blur-glass: blur(16px);
    }
    
    /* ========== GLOBAL STYLES ========== */
    .stApp {
        background: linear-gradient(135deg, #0A0E27 0%, #0F1535 100%);
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* ========== TYPOGRAPHY ========== */
    h1 {
        font-weight: 700 !important;
        font-size: 2.5rem !important;
        letter-spacing: -0.02em !important;
        background: linear-gradient(135deg, var(--text-primary) 0%, var(--accent-primary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1.5rem !important;
    }
    
    h2 {
        font-weight: 600 !important;
        font-size: 1.75rem !important;
        letter-spacing: -0.01em !important;
        color: var(--text-primary) !important;
        margin-bottom: 1rem !important;
    }
    
    h3 {
        font-weight: 600 !important;
        font-size: 1.25rem !important;
        color: var(--text-secondary) !important;
        margin-bottom: 0.75rem !important;
    }
    
    /* ========== METRIC CARDS ========== */
    [data-testid="stMetric"] {
        background: var(--card-bg);
        backdrop-filter: var(--blur-glass);
        -webkit-backdrop-filter: var(--blur-glass);
        border: 1px solid var(--card-border);
        border-radius: 16px;
        padding: 24px;
        box-shadow: var(--shadow-md);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-lg);
        border-color: rgba(99, 102, 241, 0.3);
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        line-height: 1.2 !important;
        white-space: nowrap !important; /* Prevent strict wrapping but size should fit */
        min-width: 200px;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.875rem !important;
        font-weight: 600 !important;
    }
    
    /* ========== CONTAINERS ========== */
    .element-container {
        margin-bottom: 1rem;
    }
    
    /* Block containers */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px !important;
    }
    
    /* ========== HEADER FIX ========== */
    /* Hide the default Streamlit header */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        background: transparent !important;
    }
    
    /* Remove top toolbar background */
    .st-emotion-cache-18ni7ap,
    .st-emotion-cache-1dp5vir {
        background: transparent !important;
    }
    
    /* ========== TABS ========== */
    .stTabs {
        background: transparent;
        margin-bottom: 2rem;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: var(--card-bg);
        backdrop-filter: var(--blur-glass);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 28px;
        background-color: transparent;
        border-radius: 8px;
        color: var(--text-secondary);
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s ease;
        border-bottom: none !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(255, 255, 255, 0.05);
        color: var(--text-primary);
    }
    
    .stTabs [aria-selected="true"],
    .stTabs button[aria-selected="true"],
    .stTabs [data-baseweb="tab"][aria-selected="true"],
    div[data-baseweb="tab-list"] button[aria-selected="true"] {
        background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4) !important;
        border-bottom: none !important;
        border: none !important;
    }
    
    /* Fix dropdown appearance */
    .stSelectbox [data-baseweb="select"] {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 2px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 8px !important;
    }
    
    .stSelectbox [data-baseweb="select"] > div {
        color: var(--text-primary) !important;
        background: transparent !important;
        font-weight: 500 !important;
    }
    
    /* Dropdown menu */
    [data-baseweb="popover"] {
        background: var(--bg-secondary) !important;
    }
    
    [role="listbox"] {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--card-border) !important;
    }
    
    [role="option"] {
        background: transparent !important;
        color: var(--text-primary) !important;
    }
    
    [role="option"]:hover {
        background: rgba(255, 255, 255, 0.1) !important;
    }
    
    /* ========== BUTTONS ========== */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent-primary) 0%, #8B5CF6 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 28px;
        font-weight: 600;
        font-size: 0.9375rem;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
    }
    
    /* ========== DATAFRAMES / TABLES ========== */
    .stDataFrame {
        background: var(--card-bg);
        backdrop-filter: var(--blur-glass);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }
    
    /* ========== CHARTS ========== */
    .js-plotly-plot {
        background: var(--card-bg) !important;
        backdrop-filter: var(--blur-glass);
        border: 1px solid var(--card-border);
        border-radius: 16px;
        padding: 16px;
        box-shadow: var(--shadow-md);
    }
    
    /* ========== SIDEBAR ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0F1535 0%, #0A0E27 100%) !important;
        border-right: 1px solid var(--card-border);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #0F1535 0%, #0A0E27 100%) !important;
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    [data-testid="stSidebar"] .element-container {
        padding: 0.25rem 0 !important;
        margin-bottom: 0 !important;
    }
    
    /* Compact sidebar headers */
    [data-testid="stSidebar"] h1 {
        font-size: 1.5rem !important;
        margin-bottom: 0.5rem !important;
        margin-top: 0 !important;
    }
    
    [data-testid="stSidebar"] h2 {
        font-size: 1rem !important;
        margin-bottom: 0.5rem !important;
        margin-top: 0.5rem !important;
    }
    
    /* Sidebar text */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: var(--text-primary) !important;
    }
    
    /* Compact sidebar inputs */
    [data-testid="stSidebar"] .stSelectbox,
    [data-testid="stSidebar"] .stTextInput {
        margin-bottom: 0.5rem !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox > div > div,
    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background: rgba(30, 30, 50, 0.8) !important;
        border: 2px solid rgba(255, 255, 255, 0.3) !important;
        color: white !important;
        padding: 8px 12px !important;
        font-size: 0.875rem !important;
    }
    
    /* Sidebar dropdown text visibility fix - ALL text elements */
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"],
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span,
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] div,
    [data-testid="stSidebar"] .stSelectbox input,
    [data-testid="stSidebar"] .stSelectbox div[role="button"] {
        color: white !important;
        background: transparent !important;
        font-weight: 500 !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox svg {
        fill: white !important;
    }
    
    /* Compact sidebar buttons */
    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, var(--accent-primary) 0%, #8B5CF6 100%) !important;
        color: white !important;
        border: none !important;
        padding: 10px 20px !important;
        font-size: 0.875rem !important;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
    }
    
    /* Sidebar info boxes - compact */
    [data-testid="stSidebar"] .stAlert {
        background: var(--card-bg) !important;
        border: 1px solid var(--card-border) !important;
        color: var(--text-primary) !important;
        padding: 10px !important;
        margin: 0.5rem 0 !important;
        font-size: 0.8125rem !important;
    }
    
    /* Sidebar captions */
    [data-testid="stSidebar"] .st-emotion-cache-16idsys p,
    [data-testid="stSidebar"] caption {
        color: var(--text-secondary) !important;
        font-size: 0.75rem !important;
        margin-top: 0.25rem !important;
    }
    
    /* Sidebar dividers */
    [data-testid="stSidebar"] hr {
        margin: 0.75rem 0 !important;
    }
    
    /* ========== INPUT FIELDS ========== */
    /* Target the input element specifically and force LIGHT background with DARK text as requested */
    .stTextInput input, 
    .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        caret-color: #000000 !important; /* Cursor color */
    }
    
    /* Ensure the container doesn't have a conflicting background */
    .stTextInput > div > div {
        background-color: transparent !important;
    }

    /* Focus states */
    .stTextInput input:focus,
    .stSelectbox div[data-baseweb="select"]:focus-within {
        background-color: #ffffff !important;
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 1px var(--accent-primary) !important;
    }
    
    /* Placeholder text styling (Webkit browsers) */
    .stTextInput input::placeholder {
        color: #666666 !important;
        opacity: 1;
    }
    
    /* ========== INFO/WARNING/ERROR BOXES ========== */
    .stAlert {
        background: var(--card-bg);
        backdrop-filter: var(--blur-glass);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 16px 20px;
    }
    
    /* ========== DIVIDERS ========== */
    hr {
        border-color: var(--card-border);
        margin: 2rem 0;
    }
    
    /* ========== RESPONSIVE ========== */
    @media (max-width: 768px) {
        [data-testid="stMetricValue"] {
            font-size: 1.75rem !important;
        }
        
        h1 {
            font-size: 2rem !important;
        }
        
        h2 {
            font-size: 1.5rem !important;
        }
        
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0 16px;
            font-size: 0.875rem;
        }
    }
    
    /* ========== ANIMATIONS ========== */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .element-container {
        animation: fadeIn 0.3s ease-out;
    }

    /* ========== FIXED VISIBILITY ISSUES ========== */
    
    /* 1. Download Button High Contrast */
    [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, var(--accent-success) 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }
    [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover {
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.5);
        transform: translateY(-2px);
    }
    
    /* 2. Dropdown Menu / Popover Background */
    /* This targets the popup list container - Light Theme as requested */
    div[data-baseweb="popover"] {
        background-color: #ffffff !important;
        border: 1px solid #cccccc !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* The individual options */
    div[data-baseweb="popover"] ul li {
        color: #000000 !important;
        background-color: transparent !important;
        border-bottom: 1px solid #f0f0f0;
    }
    
    /* Hover state for options */
    div[data-baseweb="popover"] ul li:hover,
    div[data-baseweb="popover"] li[aria-selected="true"] {
        background-color: #f3f4f6 !important;
        color: #000000 !important;
        font-weight: 600;
    }
    
    /* The Selected Value inside the box */
    [data-testid="stSelectbox"] div[data-baseweb="select"] div {
        color: #000000 !important;
    }
    
    /* Force specific overrides for the white-on-white issue */
    li[role="option"] {
         background-color: #ffffff !important; 
         color: #000000 !important;
    }
    ul[role="listbox"] {
         background-color: #ffffff !important;
    }
</style>

<script>
// Force tab color update after Streamlit loads
setTimeout(function() {
    const activeTab = document.querySelector('[data-baseweb="tab"][aria-selected="true"]');
    if (activeTab) {
        activeTab.style.background = 'linear-gradient(135deg, #667EEA 0%, #764BA2 100%)';
        activeTab.style.color = 'white';
        activeTab.style.boxShadow = '0 4px 16px rgba(102, 126, 234, 0.4)';
        activeTab.style.border = 'none';
    }
    
    // Fix dropdown background and text
    const dropdowns = document.querySelectorAll('[data-testid="stSidebar"] [data-baseweb="select"]');
    dropdowns.forEach(function(dropdown) {
        dropdown.style.background = 'rgba(30, 30, 50, 0.9)';
        dropdown.style.color = 'white';
        
        // Fix all child elements
        const allElements = dropdown.querySelectorAll('*');
        allElements.forEach(function(el) {
            el.style.color = 'white';
            if (el.style.background && el.style.background.includes('white')) {
                el.style.background = 'transparent';
            }
        });
    });
    
    // Re-apply on tab clicks
    document.addEventListener('click', function(e) {
        setTimeout(function() {
            const newActiveTab = document.querySelector('[data-baseweb="tab"][aria-selected="true"]');
            if (newActiveTab) {
                newActiveTab.style.background = 'linear-gradient(135deg, #667EEA 0%, #764BA2 100%)';
                newActiveTab.style.color = 'white';
                newActiveTab.style.boxShadow = '0 4px 16px rgba(102, 126, 234, 0.4)';
                newActiveTab.style.border = 'none';
            }
            
            // Re-fix dropdowns
            const dropdowns = document.querySelectorAll('[data-testid="stSidebar"] [data-baseweb="select"]');
            dropdowns.forEach(function(dropdown) {
                dropdown.style.background = 'rgba(30, 30, 50, 0.9)';
                dropdown.style.color = 'white';
                
                const allElements = dropdown.querySelectorAll('*');
                allElements.forEach(function(el) {
                    el.style.color = 'white';
                    if (el.style.background && el.style.background.includes('white')) {
                        el.style.background = 'transparent';
                    }
                });
            });
        }, 100);
    });
}, 500);
</script>
""", unsafe_allow_html=True)

# Configuration
DEFAULT_ONEDRIVE_LINK = "https://myworksocial-my.sharepoint.com/:x:/p/dannya/EbB6qC0KAuVMtZRaFub_DgsBgirK7ySgwixiWLUOB-kZQA"

# Application State
if 'data' not in st.session_state:
    st.session_state.data = None

def main():
    # 🔒 AUTHENTICATION CHECK
    if not check_password():
        st.stop()  # Stop execution if not authenticated
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("FIN ANALYTICS 🚀")
        
        st.header("Data Source")

        # AI Insights Toggle (default ON only if API key present)
        ai_default = True if os.getenv('GEMINI_API_KEY') else False
        if 'enable_ai' not in st.session_state:
            st.session_state['enable_ai'] = ai_default
        st.session_state['enable_ai'] = st.checkbox("Enable AI Insights", value=st.session_state['enable_ai'])
        if st.session_state['enable_ai'] and not os.getenv('GEMINI_API_KEY'):
            st.warning("GEMINI_API_KEY not found — AI will use fallback rule-based insights only.")
        
        # Template Download
        try:
            with open("financial_template.xlsx", "rb") as f:
                st.download_button(
                    label="📥 Download Excel Template",
                    data=f,
                    file_name="financial_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        except FileNotFoundError:
             st.warning("Template file not found on server.")
        
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

    # --- MAIN CONTENT ---
    if not st.session_state.data:
        st.info("👈 Please load data from the sidebar to begin analysis.")
        return

    dfs = st.session_state.data
    ai = AIAnalyst()
    ai_enabled = st.session_state.get('enable_ai', False)
    
    # --- TABS NAVIGATION ---
    # Replaces the old dropdown menu logic
    tabs_list = ["Overview", "Sales Trends", "AR Collections", "AP Management", "Profitability", "Spending", "Forecast"]
    tabs = st.tabs(tabs_list)
    
    with tabs[0]: render_overview(dfs, ai, ai_enabled)
    with tabs[1]: render_sales(dfs, ai, ai_enabled)
    with tabs[2]: render_ar(dfs, ai, ai_enabled)
    with tabs[3]: render_ap(dfs, ai, ai_enabled)
    with tabs[4]: render_profit(dfs, ai, ai_enabled)
    with tabs[5]: render_spending(dfs, ai, ai_enabled)
    with tabs[6]: render_forecast(dfs, ai, ai_enabled)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application Error: {e}")
        st.exception(e)
