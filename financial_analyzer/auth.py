import streamlit as st
import hashlib
import hmac
import base64
import time
import os

def logout():
    """Logout the current user."""
    # Clear authentication state
    if "password_correct" in st.session_state:
        del st.session_state["password_correct"]
    if "authenticated_user" in st.session_state:
        del st.session_state["authenticated_user"]
    # Clear persistent auth token from URL using new query params API
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.rerun()

def check_password():
    """Returns `True` if the user had the correct password."""

    # Token helpers for persistent login via signed URL token
    def _secret_key():
        return str(st.secrets.get("auth_key", os.getenv('AUTH_KEY', 'CHANGE_THIS_SECRET')))

    def _make_token(username, ttl=None):
        # Default TTL = 24 hours (86400 seconds) for internal apps
        default_ttl = int(st.secrets.get('auth_ttl', os.getenv('AUTH_TTL', 86400)))
        ttl = int(ttl) if ttl is not None else default_ttl
        expiry = int(time.time()) + int(ttl)
        version = str(st.secrets.get('auth_key_version', os.getenv('AUTH_KEY_VERSION', 'v1')))
        payload = f"{username}|{expiry}|{version}"
        sig = hmac.new(_secret_key().encode(), payload.encode(), hashlib.sha256).hexdigest()
        token = base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()
        return token

    def _verify_token(token):
        try:
            raw = base64.urlsafe_b64decode(token.encode()).decode()
            username, expiry_str, version, sig = raw.split("|")
            payload = f"{username}|{expiry_str}|{version}"
            expected = hmac.new(_secret_key().encode(), payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, sig):
                return None
            if int(expiry_str) < int(time.time()):
                return None
            # Enforce key version match to allow rotation (optional)
            current_version = str(st.secrets.get('auth_key_version', os.getenv('AUTH_KEY_VERSION', 'v1')))
            if version != current_version:
                return None
            return username
        except Exception:
            return None

    # Check for persistent token in URL query params
    try:
        params = st.query_params
        token = params.get('auth', [None])[0]
        if token:
            user_from_token = _verify_token(token)
            if user_from_token:
                st.session_state['password_correct'] = True
                st.session_state['authenticated_user'] = user_from_token
                return True
    except Exception:
        # If platform doesn't support query params, continue to normal flow
        pass

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Get credentials from user input, trim whitespace
        username = st.session_state.get("username", "").strip()
        password = st.session_state.get("password", "").strip()
        
        # Get credentials from Streamlit secrets
        correct_username = st.secrets.get("APP_USERNAME", "").strip()
        correct_password = st.secrets.get("APP_PASSWORD", "").strip()
        
        # Compare credentials
        if username == correct_username and password == correct_password:
            st.session_state["password_correct"] = True
            st.session_state["authenticated_user"] = username
            # Clear sensitive data from session
            if "password" in st.session_state:
                del st.session_state["password"]
            if "username" in st.session_state:
                del st.session_state["username"]
            # Create a signed token and add to URL so refreshes persist login
            try:
                token = _make_token(username)
                # Persist auth token via new query params API
                st.query_params['auth'] = token
            except Exception:
                # If query params unavailable, ignore and rely on session state only
                pass
            # Trigger rerun to reflect authenticated state
            st.rerun()
        else:
            st.session_state["password_correct"] = False

    # Return True if password is validated
    if st.session_state.get("password_correct", False):
        return True

    # Show login form
    st.markdown("""
        <div style="text-align: center; padding: 50px 0;">
            <h1>🔒 Financial Dashboard</h1>
            <p style="color: #888;">Secure Access Required</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.text_input("Username", key="username", placeholder="Enter your username")
        st.text_input("Password", type="password", key="password", placeholder="Enter your password")
        st.button("Login", on_click=password_entered, type="primary", use_container_width=True)
        
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Invalid username or password")
    
    return False
