import streamlit as st
import streamlit as st

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    users = st.secrets["auth"]["users"]

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
