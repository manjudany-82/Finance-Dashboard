import sys
from pathlib import Path

repo_root = Path(__file__).parent.absolute()
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from pathlib import Path
import sys

# Ensure repo root is importable for `financial_analyzer` package
repo_root = Path(__file__).parent.absolute()
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from financial_analyzer import dashboard as fa_dashboard

if __name__ == "__main__":
    try:
        fa_dashboard.main()
    except Exception as e:
        try:
            import streamlit as st
            import traceback
            import logging
            st.error(f"⚠️ Application Error: {e}")
            with st.expander("Error Details"):
                st.code(traceback.format_exc())
            logging.error(f"Dashboard error: {e}", exc_info=True)
        except Exception:
            # In case Streamlit isn't available in the environment
            raise


st.subheader("Overview")

fig = px.bar(df, x="month", y="value", title="Sample Monthly Values")
