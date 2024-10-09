import streamlit as st
from create_groups import show_create_groups  # Import the function from create_groups.py
from quiz_generation import quiz_generation_app


def show_home():
    if 'token' not in st.session_state:
        st.session_state.current_page = 'login'  # Redirect to login if no token
        st.rerun()  # Refresh to show the new page

    st.title("Home Page")

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    # st.write(f"Token set: {st.session_state.token}")
    # Sidebar options
    option = st.sidebar.selectbox("Select an option:",
                                  ["Generate Quiz", "Create Groups", "View Results", "Logout"])

    # Display content based on selected option
    if option == "Generate Quiz":
        quiz_generation_app()

    elif option == "Create Groups":
        show_create_groups()

    elif option == "View Results":
        st.subheader("View Quiz Results")
        st.write("Here you can view the results of quizzes taken. (Functionality to be implemented.)")

    elif option == "Logout":
        st.session_state.clear()  # Clear session state
        st.session_state.current_page = 'login'  # Redirect to login page
        st.rerun()  # Refresh the app to show the new page
