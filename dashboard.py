import sys
import os
from pathlib import Path

# Add the repo root to Python path for imports to work correctly
repo_root = Path(__file__).parent.absolute()
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import streamlit as st

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
    def _apply_ui_css():
        import streamlit as st
        st.markdown("""
        <style>
        /* UI CSS moved to runtime to avoid import-time Streamlit calls */
        /* The original style block is preserved but applied when this function is called. */
        </style>
        """, unsafe_allow_html=True)
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
    # Apply UI CSS/runtime-only styles (avoids import-time Streamlit calls)
    try:
        _apply_ui_css()
    except Exception:
        pass
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
                            # For compliance with "OneDrive-only" AI analysis, do not set df from uploads
                            st.session_state.df = None
                            if st.session_state.data:
                                st.success("File Processed Successfully (dashboard views only)")
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
    tabs_list = ["Overview", "🤖 AI Insights", "Sales Trends", "AR Collections", "AP Management", "Cash Flow", "Profitability", "Spending", "Forecast"]
    tabs = st.tabs(tabs_list)

    with tabs[0]:
        render_overview(dfs, ai, ai_enabled)

    # AI INSIGHTS TAB - runtime fallback renderer (no import-time Side-effects)
    with tabs[1]:
        render_ai_insights(dfs, ai, ai_enabled)
    
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
