import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from firebase_admin.exceptions import FirebaseError
import requests
import json

# --- Page & Firebase Configuration ---
st.set_page_config(page_title="Pawan AI - Login", page_icon="👋")

# --- Firebase Admin SDK Initialization (Backend) ---
# This uses the "Master Key" for admin tasks like creating users.
if not firebase_admin._apps:
    try:
        creds = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(creds)
    except Exception as e:
        st.error(f"Firebase Admin SDK initialization failed: {e}")
        st.info("Please ensure the `firebase_key.json` file is in the root directory.")
        st.stop()

# --- Load Firebase Client-Side Config (for REST API) ---
# This is the "Public Address" key needed to talk to the login service.
try:
    firebase_config = json.loads(st.secrets["firebase_config_json"])
    rest_api_key = firebase_config.get("apiKey")
    if not rest_api_key:
        st.error("apiKey not found in firebase_config_json. Please check your secrets.")
        st.stop()
except (FileNotFoundError, KeyError, json.JSONDecodeError):
    st.error("Firebase client config (firebase_config_json) is missing or invalid in secrets.")
    st.stop()

# --- Custom Authentication Functions ---
def register_user(email, password):
    """Registers a new user in Firebase Authentication using the Admin SDK."""
    try:
        user = firebase_auth.create_user(email=email, password=password)
        st.success(f"Successfully registered! Please log in.")
        return True
    except FirebaseError as e:
        # Provide more user-friendly error messages
        error_message = str(e)
        if "EMAIL_EXISTS" in error_message:
            st.error("Registration failed: This email address is already in use.")
        elif "WEAK_PASSWORD" in error_message:
            st.error("Registration failed: Password should be at least 6 characters.")
        else:
            st.error(f"Registration failed: {e}")
        return False

def login_user_with_password(email, password):
    """
    Logs in a user by securely verifying their password with Firebase's REST API.
    This is the new, secure method.
    """
    signin_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={rest_api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    try:
        response = requests.post(signin_url, json=payload)
        response_data = response.json()

        if response.status_code == 200 and "localId" in response_data:
            # Login successful, get user info from Admin SDK for consistency
            user = firebase_auth.get_user(response_data["localId"])
            st.session_state['logged_in'] = True
            st.session_state['user_info'] = {'uid': user.uid, 'email': user.email}
            st.success("Login successful!")
            st.rerun() # Rerun to hide login form and show pages
            return True
        else:
            error_message = response_data.get("error", {}).get("message", "Unknown error")
            st.error(f"Login failed: {error_message.replace('_', ' ').capitalize()}")
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"A network error occurred: {e}")
        return False


# --- Main Page UI ---
st.title("Welcome to Pawan AI 👋")

# If user is already logged in, show a welcome message and logout button
if 'logged_in' in st.session_state and st.session_state['logged_in']:
    user_info = st.session_state['user_info']
    st.success(f"You are logged in as {user_info.get('email')}")
    st.info("You can now access the Chatbot and Admin pages from the sidebar.")
    if st.button("Logout"):
        del st.session_state['logged_in']
        del st.session_state['user_info']
        st.rerun()
else:
    # Show Login and Registration forms if not logged in
    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        st.subheader("Login to your Account")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if login_email and login_password:
                login_user_with_password(login_email, login_password)
            else:
                st.warning("Please enter both email and password.")

    with register_tab:
        st.subheader("Create a New Account")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        if st.button("Register"):
            if reg_email and reg_password:
                register_user(reg_email, reg_password)
            else:
                st.warning("Please enter both email and password to register.")

