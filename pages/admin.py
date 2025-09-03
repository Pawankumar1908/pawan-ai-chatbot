import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth
from datetime import datetime

# --- Firebase Admin SDK Initialization ---
# This ensures Firebase is ready for use on this page.
if not firebase_admin._apps:
    try:
        # NOTE: Ensure 'firebase_key.json' is in the root directory (pawan_ai_app).
        creds = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(creds)
    except Exception as e:
        st.error(f"Firebase Admin SDK initialization failed: {e}")
        st.stop()

db = firestore.client()

# --- Page Protection ---
# This is the new, correct way to protect the page.
# It checks the custom session state variable set by app.py upon successful login.
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.error("You need to log in to access this page. Please go back to the main page.")
    st.stop()

user_info = st.session_state['user_info']
# IMPORTANT: Replace this with your actual email address to grant yourself admin access.
ADMIN_EMAIL = "bpaw19@gmail.com" 

# Verify that a user is logged in AND their email matches the admin email.
if user_info.get('email') != ADMIN_EMAIL:
    st.error("You do not have permission to view this page.")
    st.warning("Please log in with your admin account.")
    st.stop()

# --- Admin Dashboard UI ---
st.set_page_config(page_title="Admin Panel", page_icon="🔑")
st.title("🔑 Admin Panel")
st.write(f"Welcome, Admin ({user_info.get('email')}).")
st.write("View user data and their complete chat histories.")
st.markdown("---")


# --- Fetch and Display User Data ---
try:
    # Fetch all users from Firebase Authentication. This requires admin privileges.
    user_list = [user for user in firebase_auth.list_users().iterate_all()]

    if not user_list:
        st.warning("No users found in Firebase Authentication.")
    else:
        # Create a list of user emails to display in the dropdown menu.
        user_emails = [user.email for user in user_list if user.email]
        selected_email = st.selectbox("Select a user to view their chat history:", user_emails)

        if selected_email:
            # Get the full user object for the selected email to find their unique ID (UID).
            selected_user = firebase_auth.get_user_by_email(selected_email)
            selected_user_uid = selected_user.uid

            st.subheader(f"Chat History for: {selected_email}")
            st.caption(f"UID: {selected_user_uid}")

            # Fetch all chat sessions for the selected user from the Firestore database.
            sessions_ref = db.collection('users').document(selected_user_uid).collection('chat_sessions').order_by("created_at", direction=firestore.Query.DESCENDING).stream()
            sessions_data = [session.to_dict() for session in sessions_ref]

            if not sessions_data:
                st.info("This user has no saved chat sessions.")
            else:
                # Display each chat session in an expandable container for a clean look.
                for session in sessions_data:
                    created_time = session.get('created_at')
                    # Format the timestamp for better readability.
                    if isinstance(created_time, datetime):
                         time_str = created_time.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                         time_str = "Timestamp not available"
                    
                    with st.expander(f"Chat: \"{session.get('title', 'Untitled')}\" (Created: {time_str})"):
                        messages = session.get('messages', [])
                        if not messages:
                            st.write("This chat session is empty.")
                        else:
                            for msg in messages:
                                # Display each message with its role (user or assistant).
                                st.markdown(f"**{msg.get('role', 'unknown').capitalize()}:**")
                                st.markdown(f"> {msg.get('content', '')}")
                            st.markdown("---")

except Exception as e:
    st.error(f"An error occurred while fetching data: {e}")

