import streamlit as st
import hashlib

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Safely get values from session state
        username = st.session_state.get("username", "")
        password = st.session_state.get("password", "")
        
        # Get credentials from secrets
        users = st.secrets.get("users", {})
        
        if username in users and users[username] == hashlib.sha256(password.encode()).hexdigest():
            st.session_state["password_correct"] = True
            st.session_state["authenticated_user"] = username
            # Don't store password
            if "password" in st.session_state:
                del st.session_state["password"]
            if "username" in st.session_state:
                del st.session_state["username"]
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
