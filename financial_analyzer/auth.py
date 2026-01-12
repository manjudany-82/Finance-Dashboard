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

    # Support several possible placements/formats for users in st.secrets:
    # - Nested table: [auth] users = { ... }  -> st.secrets["auth"]["users"]
    # - Table form: [auth.users] demo = "..." -> st.secrets["auth.users"]
    # - Top-level: users = { ... } -> st.secrets["users"]
    # - Inline/text formats (parseable) stored under those keys.
    users_entry = None
    try:
        secrets = st.secrets
    except Exception:
        secrets = {}

    # 1) nested table: st.secrets["auth"]["users"]
    auth_val = secrets.get("auth") if isinstance(secrets, dict) else None
    if isinstance(auth_val, dict) and "users" in auth_val:
        users_entry = auth_val.get("users")
    # 2) table form: st.secrets["auth.users"]
    elif isinstance(secrets, dict) and "auth.users" in secrets:
        users_entry = secrets.get("auth.users")
    # 3) top-level users key
    elif isinstance(secrets, dict) and "users" in secrets:
        users_entry = secrets.get("users")
    # 4) maybe auth itself contains an inline map string
    elif isinstance(auth_val, str):
        parsed = _parse_inline_toml_map(auth_val)
        if parsed:
            users_entry = parsed
    else:
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
