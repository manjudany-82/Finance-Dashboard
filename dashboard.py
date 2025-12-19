import sys
import os
from pathlib import Path

# Add the repo root to Python path for imports to work correctly
repo_root = Path(__file__).parent.absolute()
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import streamlit as st

# Page Config - MUST be the first Streamlit command
st.set_page_config(
    page_title="Enterprise Financial Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DEBUG: Verify this is the actual entrypoint
st.error("🚨 ROOT dashboard.py ENTRYPOINT LOADED 🚨")

import warnings

# Suppress deprecation warnings from any dependency still calling experimental query APIs
warnings.filterwarnings("ignore", message=".*experimental_get_query_params.*", category=DeprecationWarning)

# Compat shim: some dependencies may still call deprecated query param APIs; provide
# no-warning aliases that delegate to the new st.query_params to silence warnings.
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
from google import genai
from financial_analyzer.microsoft_excel import ExcelHandler
from financial_analyzer.analysis_modes import FinancialAnalyzer
from financial_analyzer.forecast_engine import ForecastEngine
from financial_analyzer.llm_insights import AIAnalyst
from financial_analyzer.render_layouts import render_overview, render_sales, render_ar, render_ap, render_cash, render_profit, render_forecast, render_spending
from financial_analyzer.ai_insights_tab import render_ai_insights
from financial_analyzer.auth import check_password
import time

# Select a primary dataframe from loaded data (first non-empty DataFrame found)
def _pick_primary_df(data):
    if isinstance(data, pd.DataFrame):
        return data
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, pd.DataFrame) and not value.empty:
                return value
    return None

# Gemini Q&A function using NEW SDK and real user question
def run_gemini_test():
    st.subheader("🧪 Gemini Test")

    user_question = st.text_input("Ask a question about your financials", key="ai_insights_question")
    submit = st.button("Submit", key="ai_insights_submit")

    df = st.session_state.get("df")

    if not submit:
        return

    if df is None or getattr(df, "empty", True):
        st.warning("No financial data found. Please upload or load your data.")
        return

    normalized_q = (user_question or "").strip()
    greetings = {"hi", "hello", "hey", "hola"}
    if len(normalized_q) < 10 or normalized_q.lower() in greetings:
        st.info("👋 Ask a specific question about revenue, expenses, cash flow, or risks.")
        return

    # Simple cooldown to avoid rapid repeat calls (20s)
    last_ts = st.session_state.get("last_gemini_call_ts", 0)
    if time.time() - last_ts < 20:
        st.warning("⏳ Please wait a few seconds before asking another question.")
        return

    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

        df_as_csv = df.head(50).to_csv(index=False)
        prompt = (
            "You are a senior financial analyst.\n"
            "Use the provided financial data to answer clearly.\n"
            "Respond using clean Markdown with headings and bullet points.\n"
            "Avoid italics-heavy text.\n"
            "Keep explanations concise and business-friendly.\n\n"
            "Financial data (first 50 rows):\n"
            f"{df_as_csv}\n\n"
            "User question:\n"
            f"{normalized_q}"
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        st.session_state["last_gemini_call_ts"] = time.time()
        st.markdown(response.text)

    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            st.warning("⚠️ AI is temporarily busy due to usage limits.\nPlease wait a minute and try again.")
        else:
            st.warning(f"Gemini error: {msg}")

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
        font-size: 2rem !important;
        letter-spacing: -0.02em !important;
        background: linear-gradient(135deg, var(--text-primary) 0%, var(--accent-primary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1rem !important;
    }
    
    h2 {
        font-weight: 600 !important;
        font-size: 1.5rem !important;
        letter-spacing: -0.01em !important;
        color: var(--text-primary) !important;
        margin-bottom: 0.75rem !important;
    }
    
    h3 {
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        color: var(--text-primary) !important;
        margin-bottom: 0.5rem !important;
    }
    
    h4, h5, h6 {
        font-weight: 600 !important;
        color: var(--text-primary) !important;
    }
    
    /* Fix for markdown headings */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, 
    .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: var(--text-primary) !important;
    }
    
    /* General text */
    p, span, div, label {
        color: var(--text-primary) !important;
    }
    
    /* ========== METRIC CARDS ========== */
    [data-testid="stMetric"] {
        background: var(--card-bg);
        backdrop-filter: var(--blur-glass);
        -webkit-backdrop-filter: var(--blur-glass);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 16px;
        box-shadow: var(--shadow-md);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-lg);
        border-color: rgba(99, 102, 241, 0.3);
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        line-height: 1.2 !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px !important;
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
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }
    
    /* Section spacing */
    .stMarkdown hr {
        margin: 1.5rem 0 !important;
        border: none !important;
        border-top: 1px solid var(--card-border) !important;
        opacity: 0.5 !important;
    }
    
    /* Subheader spacing */
    .stMarkdown h3 {
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
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
        position: relative;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: var(--card-bg);
        backdrop-filter: var(--blur-glass);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 8px;
        overflow-x: auto;
        overflow-y: hidden;
        scroll-behavior: smooth;
        scrollbar-width: none; /* Firefox */
        -ms-overflow-style: none; /* IE/Edge */
        padding-left: 50px;
        padding-right: 50px;
    }
    
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        display: none; /* Chrome/Safari */
    }
    
    /* Tab navigation arrows */
    .tab-nav-arrow {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        z-index: 100;
        background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
        border: 2px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: white;
        font-size: 1.2rem;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        user-select: none;
    }
    
    .tab-nav-arrow:hover {
        background: linear-gradient(135deg, #7C8AEE 0%, #8B5CF6 100%);
        transform: translateY(-50%) scale(1.1);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
    }
    
    .tab-nav-arrow.left {
        left: 8px;
    }
    
    .tab-nav-arrow.right {
        right: 8px;
    }
    
    .tab-nav-arrow.disabled {
        opacity: 0.3;
        cursor: not-allowed;
        pointer-events: none;
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
        transition: all 0.3s ease;
    }
    
    .stDataFrame:hover {
        box-shadow: var(--shadow-md);
        border-color: rgba(99, 102, 241, 0.2);
    }
    
    /* ========== CHARTS ========== */
    .js-plotly-plot {
        background: var(--card-bg) !important;
        backdrop-filter: var(--blur-glass);
        border: 1px solid var(--card-border);
        border-radius: 16px;
        padding: 16px;
        box-shadow: var(--shadow-md);
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .js-plotly-plot:hover {
        box-shadow: var(--shadow-lg);
        border-color: rgba(99, 102, 241, 0.2);
    }
    
    /* ========== SIDEBAR ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0F1535 0%, #0A0E27 100%) !important;
        border-right: 1px solid var(--card-border);
        width: 280px !important;
        min-width: 280px !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #0F1535 0%, #0A0E27 100%) !important;
        padding-top: 0.75rem !important;
        padding-bottom: 0.75rem !important;
        width: 280px !important;
    }
    
    /* Hide default close button and add custom collapse button */
    [data-testid="stSidebar"] button[kind="header"],
    [data-testid="stSidebar"] button[kind="headerNoPadding"],
    [data-testid="stSidebar"] [data-testid="collapsedControl"],
    [data-testid="collapsedControl"],
    button[kind="header"],
    button[aria-label="Close sidebar"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }
    
    /* Custom collapse button */
    .sidebar-collapse-btn {
        position: fixed;
        top: 12px;
        left: 240px;
        z-index: 999999;
        background: rgba(99, 102, 241, 0.9) !important;
        border: 2px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        padding: 8px 12px;
        cursor: pointer;
        transition: all 0.3s ease;
        color: white;
        font-size: 1.2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    .sidebar-collapse-btn:hover {
        background: rgba(99, 102, 241, 1) !important;
        transform: translateX(-4px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
    }
    
    [data-testid="stSidebar"] .element-container {
        padding: 0.25rem 0 !important;
        margin-bottom: 0 !important;
    }
    
    /* Compact sidebar headers */
    [data-testid="stSidebar"] h1 {
        font-size: 1.25rem !important;
        margin-bottom: 0.5rem !important;
        margin-top: 0 !important;
    }
    
    [data-testid="stSidebar"] h2 {
        font-size: 0.95rem !important;
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
        box-shadow: 0 0 0 2px var(--accent-primary) !important;
        outline: 2px solid var(--accent-primary) !important;
        outline-offset: 2px !important;
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
    /* Large screens */
    @media (min-width: 1400px) {
        .block-container {
            max-width: 1600px !important;
            margin: 0 auto;
        }
    }
    
    /* Tablets and smaller laptops */
    @media (max-width: 1200px) {
        .block-container {
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0 20px;
            font-size: 0.95rem;
        }
    }
    
    /* Tablets */
    @media (max-width: 992px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }
        
        h1 {
            font-size: 2rem !important;
        }
        
        h2 {
            font-size: 1.5rem !important;
        }
    }
    
    /* Mobile */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 1rem !important;
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1.4rem !important;
        }
        
        h1 {
            font-size: 1.75rem !important;
        }
        
        h2 {
            font-size: 1.25rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0 12px;
            font-size: 0.8rem;
            height: 45px;
        }
        
        /* Stack charts vertically on mobile */
        .js-plotly-plot {
            padding: 8px;
        }
    }
    
    /* Small mobile */
    @media (max-width: 480px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 0.75rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0 8px;
            font-size: 0.75rem;
            height: 40px;
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
// (Removed old JS-based sidebar collapse — replaced by server-side toggle)
// Create tab navigation arrows
    if (!document.querySelector('.tab-nav-arrow')) {
        const tabsContainer = document.querySelector('.stTabs');
        const tabList = document.querySelector('[data-baseweb="tab-list"]');
        
        if (tabsContainer && tabList) {
            // Left arrow
            const leftArrow = document.createElement('div');
            leftArrow.className = 'tab-nav-arrow left';
            leftArrow.innerHTML = '◄';
            leftArrow.title = 'Scroll tabs left';
            
            // Right arrow
            const rightArrow = document.createElement('div');
            rightArrow.className = 'tab-nav-arrow right';
            rightArrow.innerHTML = '►';
            rightArrow.title = 'Scroll tabs right';
            
            // Scroll functionality
            leftArrow.onclick = function() {
                tabList.scrollBy({ left: -200, behavior: 'smooth' });
                setTimeout(updateArrowStates, 300);
            };
            
            rightArrow.onclick = function() {
                tabList.scrollBy({ left: 200, behavior: 'smooth' });
                setTimeout(updateArrowStates, 300);
            };
            
            // Update arrow states based on scroll position
            function updateArrowStates() {
                const scrollLeft = tabList.scrollLeft;
                const maxScroll = tabList.scrollWidth - tabList.clientWidth;
                
                if (scrollLeft <= 0) {
                    leftArrow.classList.add('disabled');
                } else {
                    leftArrow.classList.remove('disabled');
                }
                
                if (scrollLeft >= maxScroll - 1) {
                    rightArrow.classList.add('disabled');
                } else {
                    rightArrow.classList.remove('disabled');
                }
            }
            
            // Listen for scroll events
            tabList.addEventListener('scroll', updateArrowStates);
            
            // Initial state
            updateArrowStates();
            
            // Append arrows to tabs container
            tabsContainer.style.position = 'relative';
            tabsContainer.appendChild(leftArrow);
            tabsContainer.appendChild(rightArrow);
        }
    }
    
    // Force tab color update after Streamlit loads
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

# Cleanup old cache entries to prevent memory bloat
if 'cache_size' not in st.session_state:
    st.session_state.cache_size = 0

# Sidebar collapsed state (server-side toggle to avoid fragile JS)
if 'sidebar_collapsed' not in st.session_state:
    st.session_state['sidebar_collapsed'] = False

def collapse_sidebar():
    st.session_state['sidebar_collapsed'] = True
    st.experimental_rerun()



def main():
    # Handle URL-driven actions (logout / expand) before rendering
    try:
        params = st.query_params  # new query params API
    except Exception:
        params = {}

    if params.get('logout', [None])[0] == '1':
        from financial_analyzer.auth import logout as _logout
        _logout()
        return

    # 🔒 AUTHENTICATION CHECK
    if not check_password():
        st.stop()  # Stop execution if not authenticated
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("FIN ANALYTICS 🚀")
        
        # User info and logout button - more prominent
        from financial_analyzer.auth import logout
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
                            st.session_state.df = _pick_primary_df(st.session_state.data)
                            if st.session_state.data:
                                st.success("File Processed Successfully")
                         except Exception as e:
                            st.error(f"Error processing file: {e}")
                    else:
                        st.error("Please upload a file first.")
                else:
                    st.session_state.data = ExcelHandler.load_data(source="onedrive", onedrive_config={'url': onedrive_url, 'token': onedrive_token})
                    st.session_state.df = _pick_primary_df(st.session_state.data)
                    
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

    # Fallback logout in top bar (useful when sidebar is collapsed)
    if st.session_state.get("password_correct", False):
        # Always-visible floating controls (works when sidebar hidden)
        st.markdown(
            """
            <div style="position:fixed; top:12px; right:12px; z-index:999999; display:flex; gap:8px;">
                <a href="?logout=1" style="background:#ef4444;color:white;padding:8px 10px;border-radius:8px;text-decoration:none;font-weight:600;box-shadow:0 4px 12px rgba(0,0,0,0.2);">🚪 Logout</a>
            </div>
            """, unsafe_allow_html=True)

    # Inject CSS to hide the sidebar when collapsed (server-side)
    if st.session_state.get('sidebar_collapsed', False):
        st.markdown("""
            <style>
            [data-testid="stSidebar"] { margin-left: -320px !important; transition: margin 0.2s ease; }
            </style>
        """, unsafe_allow_html=True)

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
    st.error("🚨 ABOUT TO CREATE TABS 🚨")
    
    tabs_list = ["Overview", "🤖 AI Insights", "Sales Trends", "AR Collections", "AP Management", "Cash Flow", "Profitability", "Spending", "Forecast"]
    tabs = st.tabs(tabs_list)
    
    st.error("🚨 TABS CREATED 🚨")
    
    with tabs[0]: render_overview(dfs, ai, ai_enabled)
    
    # AI INSIGHTS TAB - Inline rendering to preserve all content in order
    with tabs[1]:
        # DEBUG: PROVE THIS TAB EXECUTES
        st.error("🚨 ENTERED AI INSIGHTS TAB 🚨")
        
        # Call Gemini test function
        run_gemini_test()
    
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
