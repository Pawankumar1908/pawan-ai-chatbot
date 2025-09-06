import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore
import requests
import json
from datetime import datetime

# --- Firebase Initialization ---
# This is the new, cloud-safe way to initialize Firebase.
# It uses the credentials stored in Streamlit's Secrets Manager, which you
# pasted into the deployment settings on the Streamlit Cloud website.
if not firebase_admin._apps:
    try:
        # The st.secrets dictionary-like object is populated with the secrets
        # you added to your Streamlit Cloud app settings.
        creds_dict = st.secrets["firebase_credentials"]
        creds = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(creds)
        db = firestore.client()
    except Exception as e:
        st.error(f"Firebase initialization failed. Please check your Streamlit secrets. Error: {e}")
        st.stop()

# --- Your Web App's Firebase Configuration (from secrets) ---
# This is also read from secrets for the secure login function. This is the
# client-side configuration, not the admin credentials.
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
            # You can log the error for debugging if needed:
            # st.error(response_data.get('error', {}).get('message', 'Unknown login error'))
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {e}")
        return None

# --- Main App UI & Logic ---
st.set_page_config(page_title="Pawan AI", page_icon="🤖", layout="centered")

# Initialize session state for login status if it doesn't exist
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

# If user is already logged in, show a welcome message and a logout button.
# This prevents them from seeing the login form again.
if st.session_state['logged_in']:
    st.title(f"Welcome back, {st.session_state.user_info.get('email')}!")
    st.success("You are now logged in.")
    st.write("Navigate to the Chatbot or Admin panel using the sidebar on the left.")
    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_info'] = None
        st.rerun()
else:
    # Show the login/register forms if the user is not logged in.
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
                            # Fetch full user record to get UID
                            user = firebase_auth.get_user_by_email(email)
                            st.session_state['logged_in'] = True
                            st.session_state['user_info'] = {
                                'uid': user.uid,
                                'email': user.email
                            }
                            st.rerun() # Rerun the script to show the welcome message and hide the form
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
                            # Create a new user in Firebase Authentication
                            user = firebase_auth.create_user(email=new_email, password=new_password)
                            # Create a corresponding document in Firestore to store their data
                            db.collection('users').document(user.uid).set({'email': new_email, 'created_at': firestore.SERVER_TIMESTAMP})
                            st.success("Account created successfully! Please proceed to the Login tab.")
                        except Exception as e:
                            st.error(f"Failed to create account: {e}")
                    else:
                        st.error("Passwords do not match.")
                else:
                    st.warning("Please fill in all fields.")

