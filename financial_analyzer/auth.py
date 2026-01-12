import streamlit as st
import re


def _parse_inline_toml_map(s: str) -> dict:
    """Parse a simple inline TOML table string like
    { "demo" = "demo123", 'a' = 'b' }
    into a Python dict. Returns empty dict on failure.
    This uses a regex to extract quoted key/value pairs and is
    intentionally conservative (no eval).
    """
    try:
        # Find all key = value pairs where keys/values are quoted
        pattern = r"[\'\"]([^\'\"]+)[\'\"]\s*=\s*[\'\"]([^\'\"]*)[\'\"]"
        matches = re.findall(pattern, s)
        return {k: v for k, v in matches}
    except Exception:
        return {}


def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    # Support both a proper dict and inline TOML map string formats.
    users_entry = None
    try:
        users_entry = st.secrets.get("auth", {}).get("users")
    except Exception:
        # Fallback to direct indexing if necessary
        try:
            users_entry = st.secrets["auth"]["users"]
        except Exception:
            users_entry = None

    if isinstance(users_entry, dict):
        users = users_entry
    elif isinstance(users_entry, str):
        users = _parse_inline_toml_map(users_entry)
    else:
        users = {}

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users and users[username] == password:
            st.session_state.password_correct = True
            st.session_state["authenticated_user"] = username
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

    return st.session_state.password_correct

def logout():
    st.session_state.clear()
    st.experimental_rerun()
