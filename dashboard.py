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
                import streamlit as st
                st.markdown(r"""
                <style>
                /* UI CSS moved to runtime to avoid import-time Streamlit calls */
                .tab-nav-arrow {
                    position: absolute;
                    top: 8px;
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
                    color: var(--text-primary) !important;
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
                </script>
                """, unsafe_allow_html=True)
