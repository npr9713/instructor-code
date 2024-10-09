
import streamlit as st
import requests
import time
# URL for your Express server (adjust as needed)
BASE_URL = "http://localhost:3540"

def show_login():
    st.title("Login Page")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Log In"):
        if email and password:  #  Check if both fields are filled
            # Prepare the request payload
            payload = {
                "email": email,
                "password": password
            }

            try:
                # Send POST request to the Express login route
                response = requests.post(f"{BASE_URL}/t-login", json=payload)
                data = response.json()

                # Check for success response from the server
                if response.status_code == 200 and data.get("success") == "1":
                    st.session_state.token = data['token']  # Store token in session state
                    st.success("Login successful!")
                    time.sleep(2)
                    st.session_state.current_page = 'home'  # Navigate to home page
                    st.rerun()  # Refresh the app to show the new page

                elif response.status_code == 400 and data.get("success") == "-1":
                    st.error("Invalid password. Please try again.")

                else:
                    st.error(data.get("message", "An error occurred. Please try again."))

            except requests.exceptions.RequestException as e:
                st.error(f"Error connecting to server: {e}")

        else:
            st.error("Please enter both email and password.")

    st.write("Don't have an account? ")
    if st.button("Sign Up"):
        st.session_state.current_page = 'signup'  # Navigate to signup page
        st.rerun()  # Refresh the app to show the new page