import streamlit as st

# Initialize session state variables
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'  # Default to login page
if 'token' not in st.session_state:
    st.session_state.token = None  # Initialize token as None

# Check if the user is logged in based on the presence of the token
if st.session_state.token is not None:
    st.session_state.current_page = 'home'  # Automatically navigate to home if token exists

# Import page functions
from login import show_login
from signup import show_signup
from home import show_home

# Conditional rendering based on session state
if st.session_state.current_page == 'login':
    show_login()
elif st.session_state.current_page == 'signup':
    show_signup()
elif st.session_state.current_page == 'home':
    show_home()
