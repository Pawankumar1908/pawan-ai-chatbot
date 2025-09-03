import streamlit as st
import google.generativeai as genai
import time
import firebase_admin
from firebase_admin import credentials, firestore
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

# Get user info from the session state.
user_info = st.session_state['user_info']
user_uid = user_info['uid']

# --- Gemini API Configuration ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
except Exception:
    st.error("Google API Key is not configured correctly. Please check your secrets.")
    st.stop()

# --- Your Resume Data for RAG ---
PAWAN_RESUME_CONTEXT = """
BUDDA PAWAN KUMAR
bpawan1908@gmail.com — +91-7981456407 — Visakhapatnam, India
GitHub: https://github.com/Pawankumar1908 | LinkedIn: www.linkedin.com/in/pawan-kumar-buddha
---
SUMMARY
Computer Science undergraduate passionate about machine learning and software development. Skilled in building real-time applications using Python, IoT, and machine learning frameworks. Experienced in deploying ML models for audio processing, noise reduction, and embedded systems.
---
EDUCATION
Bachelor of Technology in Computer Science Engineering | 2022 – 2026
GITAM University, Visakhapatnam
- CGPA: 7.56

Intermediate (MPC) | 2020 – 2022
Sri Viswa Junior College, Dwarakanagar, Visakhapatnam, AP, India
- Percentage: 80%

Class X | 2020
Siva Sivani School, Marripalem, Visakhapatnam, AP, India
- Percentage: 93%
---
EXPERIENCE
AI/ML Intern – Reliance Jio | May 2025 – July 2025 | Hyderabad, India
- Worked on speaker isolation using DeepFilterNet and pretrained models.
- Optimized Python-based real-time audio pipelines.

Team Leader – AIESEC Visakhapatnam | Jan 2024 – Jan 2025
- Led marketing efforts, built external partnerships, and contributed to flagship events.
- Served as Vice President for Youth Speak Forum and Global Goals Run, managing logistics and outreach.
---
PROJECTS
→ Real-Time Fire Detection System: Deployed a CNN model using Raspberry Pi 5.
→ Smart Parking System (IoT): Used NodeMCU and ultrasonic sensors.
→ Audio Denoising with Deep Learning: Implemented models like Demucs and Conv-TasNet.
---
TECHNICAL SKILLS, CERTIFICATES & ACHIEVEMENTS

Languages: Python, C, Java, SQL
Frameworks & Libraries: Flask, OpenCV, TensorFlow, PyTorch, Pandas, Numpy, Scikit-Learn, Matplotlib
Tools: Anaconda, Arduino IDE, GitHub, Excel, PowerPoint, MySQL, SQLite
Platforms: Google Colab, Jupyter Notebook, VS Code
Domains: Machine Learning, Deep Learning, Embedded Systems, IoT
Soft Skills: Rapport Building, Stakeholder Management, People Management, Communication

Certificates:
- Oracle Cloud Infrastructure 2025 Certified AI Foundations Associate – Oracle
- Python Data Structures – Coursera
- Entrepreneurship I & II – Coursera

Achievements:
- Awarded Best Member 2024.1 – AIESEC in Visakhapatnam
- Led large-scale events like Youth Speak Forum and Global Goals Run
- Built 3+ real-time IoT/AI projects showcased in demos and tech reviews
---

"""

# --- Helper Functions & Firestore Management ---
def stream_response(prompt):
    """Streams the response from the Gemini API."""
    try:
        response_stream = model.generate_content(prompt, stream=True)
        for chunk in response_stream:
            yield chunk.text
            time.sleep(0.02)
    except Exception as e:
        st.error(f"An error occurred. Please wait and try again. Error: {e}")
        yield ""

def load_chat_history():
    """Loads all chat sessions for the current user from Firestore."""
    sessions_ref = db.collection('users').document(user_uid).collection('chat_sessions').order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    return [session.to_dict() for session in sessions_ref]

def save_chat_session(session_data):
    """Saves a chat session to Firestore."""
    session_id = session_data["session_id"]
    db.collection('users').document(user_uid).collection('chat_sessions').document(session_id).set(session_data)

# --- Session State & UI ---
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = load_chat_history()
if "current_chat_index" not in st.session_state:
    st.session_state.current_chat_index = -1

st.title("Pawan AI Chatbot 🤖")

with st.sidebar:
    st.header(f"Welcome, {user_info.get('email')}!")
    st.header("Modes")
    app_mode = st.radio("Choose the chatbot's personality:", ("Pawan - Interview Mode", "General Chatbot"), key="app_mode")
    st.markdown("---")
    st.header("Chat History")
    if st.button("➕ New Chat"):
        st.session_state.current_chat_index = -1
        st.rerun()

    for index, session in enumerate(st.session_state.chat_sessions):
        if st.button(session["title"], key=f"chat_{session['session_id']}"):
            st.session_state.current_chat_index = index
            st.rerun()

if st.session_state.current_chat_index != -1:
    current_messages = st.session_state.chat_sessions[st.session_state.current_chat_index]["messages"]
    for msg in current_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
else:
    st.info("Start a new conversation by typing a message below.")

if user_prompt := st.chat_input("Ask your question here..."):
    is_new_chat = (st.session_state.current_chat_index == -1)
    if is_new_chat:
        chat_title = user_prompt[:30] + "..."
        new_session_id = str(int(time.time() * 1000))
        new_session = {
            "session_id": new_session_id,
            "title": chat_title,
            "messages": [],
            "created_at": firestore.SERVER_TIMESTAMP
        }
        st.session_state.chat_sessions.insert(0, new_session)
        st.session_state.current_chat_index = 0

    current_session = st.session_state.chat_sessions[st.session_state.current_chat_index]
    user_message = {"role": "user", "content": user_prompt}
    current_session["messages"].append(user_message)
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        final_prompt = ""
        if app_mode == "Pawan - Interview Mode":
             final_prompt = f"CONTEXT:\n---\n{PAWAN_RESUME_CONTEXT}\n---\n\nINSTRUCTION:\nYou are Pawan. Answer the following question based ONLY on the resume in the CONTEXT. Speak in the first person. If the question is unrelated, politely state your purpose is to discuss Pawan's qualifications.\n\nQUESTION:\n{user_prompt}"
        else:
            final_prompt = user_prompt
        
        full_response = st.write_stream(stream_response(final_prompt))

    assistant_message = {"role": "assistant", "content": full_response}
    current_session["messages"].append(assistant_message)
    save_chat_session(current_session)
    
    if is_new_chat:
        st.rerun()

