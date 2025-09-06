import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore
import requests
import json
from datetime import datetime

# --- Firebase Initialization (NEW, SIMPLER METHOD) ---
# This method reads the entire JSON key from secrets and parses it in the code,
# which is more robust than using the TOML table format.
if not firebase_admin._apps:
    try:
        # Get the JSON string from secrets
        creds_json_str = st.secrets["firebase_secret_key_json"]
        # Convert the JSON string to a Python dictionary
        creds_dict = json.loads(creds_json_str)
        # Initialize the app with the credentials
        creds = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(creds)
    except Exception as e:
        st.error(f"Firebase initialization failed. Please check your secrets.toml. Error: {e}")
        st.stop()

db = firestore.client()

# --- Your Web App's Firebase Configuration (from secrets) ---
try:
    firebase_config = json.loads(st.secrets["firebase_config_json"])
    FIREBASE_WEB_API_KEY = firebase_config.get("apiKey")
except (KeyError, json.JSONDecodeError):
    st.error("Firebase web configuration is missing or invalid in secrets.toml.")
    st.stop()

# --- Helper Function for Secure Login ---
def secure_login(email, password):
    """Verifies user password with Firebase Auth REST API."""
    rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = json.dumps({
        "email": email,
        "password": password,
        "returnSecureToken": True
    })
    try:
        response = requests.post(rest_api_url, data=payload)
        response_data = response.json()
        if "localId" in response_data:
            return response_data
        else:
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {e}")
        return None

# --- Main App UI & Logic ---
st.set_page_config(page_title="Pawan AI", page_icon="🤖", layout="centered")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

if st.session_state['logged_in']:
    st.title(f"Welcome back, {st.session_state.user_info.get('email')}!")
    st.success("You are now logged in.")
    st.write("Navigate to the Chatbot or Admin panel using the sidebar on the left.")
    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_info'] = None
        st.rerun()
else:
    st.title("Welcome to Pawan AI 🤖")
    st.write("Please log in or register to continue.")

    choice = st.selectbox("Choose an action:", ["Login", "Register"])

    if choice == "Login":
        with st.form("login_form"):
            st.subheader("Login")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")

            if login_button:
                if email and password:
                    user_data = secure_login(email, password)
                    if user_data:
                        try:
                            user = firebase_auth.get_user_by_email(email)
                            st.session_state['logged_in'] = True
                            st.session_state['user_info'] = {
                                'uid': user.uid,
                                'email': user.email
                            }
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to fetch user details: {e}")
                    else:
                        st.error("Invalid email or password.")
                else:
                    st.warning("Please enter both email and password.")

    elif choice == "Register":
        with st.form("register_form"):
            st.subheader("Create a new account")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            register_button = st.form_submit_button("Register")

            if register_button:
                if new_email and new_password and confirm_password:
                    if len(new_password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    elif new_password == confirm_password:
                        try:
                            user = firebase_auth.create_user(email=new_email, password=new_password)
                            db.collection('users').document(user.uid).set({'email': new_email, 'created_at': firestore.SERVER_TIMESTAMP})
                            st.success("Account created successfully! Please proceed to the Login tab.")
                        except Exception as e:
                            st.error(f"Failed to create account: {e}")
                    else:
                        st.error("Passwords do not match.")
                else:
                    st.warning("Please fill in all fields.")

