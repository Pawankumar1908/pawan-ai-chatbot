import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth
from datetime import datetime

# --- Firebase Initialization ---
# This is the cloud-safe way to initialize Firebase using Streamlit secrets.
if not firebase_admin._apps:
    try:
        creds_dict = st.secrets["firebase_credentials"]
        creds = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(creds)
    except Exception as e:
        st.error(f"Firebase Admin SDK initialization failed: {e}")
        st.stop()

db = firestore.client()

# --- Page Protection ---
# This ensures only logged-in users can see this page.
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.error("You need to log in to access this page. Please go back to the main page.")
    st.stop()

user_info = st.session_state['user_info']
# IMPORTANT: This is your admin email. Only this account can view this page.
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
    # Get a list of all users from Firebase Authentication
    user_list = [user for user in firebase_auth.list_users().iterate_all()]

    if not user_list:
        st.warning("No users found in Firebase Authentication.")
    else:
        user_emails = [user.email for user in user_list if user.email]
        selected_email = st.selectbox("Select a user to view their chat history:", user_emails)

        if selected_email:
            # Get the full user record to find their UID
            selected_user = firebase_auth.get_user_by_email(selected_email)
            selected_user_uid = selected_user.uid

            st.subheader(f"Chat History for: {selected_email}")
            st.caption(f"UID: {selected_user_uid}")

            # Fetch chat sessions for the selected user from Firestore
            sessions_ref = db.collection('users').document(selected_user_uid).collection('chat_sessions').order_by("created_at", direction=firestore.Query.DESCENDING).stream()
            sessions_data = [session.to_dict() for session in sessions_ref]

            if not sessions_data:
                st.info("This user has no saved chat sessions.")
            else:
                for session in sessions_data:
                    created_time = session.get('created_at')
                    # Format the timestamp for display
                    if isinstance(created_time, datetime):
                         time_str = created_time.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                         time_str = "Timestamp not available"
                    
                    # Use an expander for each chat session
                    with st.expander(f"Chat: \"{session.get('title', 'Untitled')}\" (Created: {time_str})"):
                        messages = session.get('messages', [])
                        if not messages:
                            st.write("This chat session is empty.")
                        else:
                            # Display each message within the session
                            for msg in messages:
                                st.markdown(f"**{msg.get('role', 'unknown').capitalize()}:**")
                                st.markdown(f"> {msg.get('content', '')}")
                            st.markdown("---")

except Exception as e:
    st.error(f"An error occurred while fetching data: {e}")

