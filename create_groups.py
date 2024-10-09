import streamlit as st
import json
import time
import requests  # Import the requests library for making HTTP requests

BASE_URL = "http://localhost:3540"  # Your backend URL

def show_create_groups():
    st.title("Create a New Group")

    # Input for the group name
    group_name = st.text_input("Group Name")

    # Initialize email inputs if not already in session state
    if 'emails' not in st.session_state:
        st.session_state.emails = ['']  # Start with one empty input field

    # Function to add a new email input field
    def add_email_input():
        st.session_state.emails.append('')  # Add an empty string for the new input field

    # Display email input fields
    for i in range(len(st.session_state.emails)):
        st.session_state.emails[i] = st.text_input(f"Email {i + 1}", value=st.session_state.emails[i], key=f'email_{i}')

    # Button to add more email fields
    if st.button("Add Another Email"):
        add_email_input()  # Add another email input
        st.rerun()  # Refresh to show the new input field immediately

    # Button to create the group
    if st.button("Create Group"):
        if group_name and any(st.session_state.emails):  # Check if group name and at least one email is provided
            # Filter out empty emails
            emails = [email.strip() for email in st.session_state.emails if email.strip()]

            if emails:
                # Structure data for JSON
                group_data = {
                    "group_name": group_name,
                    "users": emails
                }

                # Convert to JSON format (for sending to backend or saving)
                group_json = json.dumps(group_data)

                # Set the authorization token (retrieved from session state)
                token = st.session_state.get('token', '')  # Get token from session state

                # Prepare headers for the request
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }

                # Send the JSON data to the backend
                try:
                    response = requests.post(f"{BASE_URL}/t-addgroup", headers=headers, json=group_data)

                    # Check if the request was successful
                    if response.status_code == 200:
                        st.success(f"Group '{group_name}' created with members: {', '.join(emails)}")
                    else:
                        st.error(f"Failed to create group: {response.text}")

                except requests.exceptions.RequestException as e:
                    st.error(f"Error connecting to server: {e}")

                # Show JSON output (for debugging, you can remove this line in production)
                st.json(group_json)

                # Wait for 2 seconds before clearing
                time.sleep(2)

                # Clear the fields by resetting session state
                st.session_state.emails = ['']  # Reset emails to a single empty field
                st.session_state.group_name = ''  # Reset group name
                st.rerun()  # Refresh the app to clear inputs and reset the form

            else:
                st.error("Please enter at least one valid email.")
        else:
            st.error("Please provide both a group name and at least one user email.")
