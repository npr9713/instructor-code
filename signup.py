import streamlit as st
import requests
import time

# URL for your Express server (adjust as needed)
BASE_URL = "http://localhost:3540"

def show_signup():
    st.title("Instructor Signup")

    # User inputs for signup
    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        if name and email and password:
            # Prepare the request payload
            payload = {
                "name": name,
                "email": email,
                "password": password
            }

            try:
                # Send POST request to the Express signup route
                response = requests.post(f"{BASE_URL}/t-signup", json=payload)
                data = response.json()

                # Check for success response from the server
                if response.status_code == 200 and data.get("success") == "1":
                    st.success("Instructor registered successfully! Please log in.")
                    time.sleep(3)
                    st.session_state.current_page = 'login'
                    st.rerun()

                elif response.status_code == 400 and data.get("success") == "-1":
                    st.error("Email already registered. Please try logging in.")

                else:
                    st.error(data.get("message", "An error occurred. Please try again."))

            except requests.exceptions.RequestException as e:
                st.error(f"Error connecting to server: {e}")
        else:
            st.warning("Please fill in all fields.")

