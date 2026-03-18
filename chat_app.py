import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.email.email_responder import EmailResponder



# PAGE CONFIG


st.set_page_config(
    page_title="AI Customer Support",
    layout="wide"
)



# CUSTOM CSS (BLUE + WHITE UI)


st.markdown("""
<style>

body {
    background-color: #f5f7fb;
}

/* Header */
.header {
    background: linear-gradient(90deg, #1e3c72, #2a5298);
    padding: 20px;
    border-radius: 12px;
    color: white;
    text-align: center;
    margin-bottom: 20px;
}

/* Cards */
.card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}

/* Buttons */
.stButton>button {
    background-color: #2a5298;
    color: white;
    border-radius: 8px;
    height: 45px;
    width: 100%;
    font-weight: bold;
}

.stButton>button:hover {
    background-color: #1e3c72;
}

/* Text areas */
textarea {
    border-radius: 10px !important;
}

/* Titles */
.title-text {
    font-size: 32px;
    font-weight: bold;
}

.subtitle {
    font-size: 16px;
    color: #e0e0e0;
}

</style>
""", unsafe_allow_html=True)



# HEADER


st.markdown("""
<div class="header">
    <div class="title-text">AI Customer Email Response System</div>
    <div class="subtitle">Smart Support powered by RAG + LLM</div>
</div>
""", unsafe_allow_html=True)



# USER DETECTION


users_path = "data/users"
users = []

if os.path.exists(users_path):
    users = os.listdir(users_path)

if len(users) == 0:
    st.warning("No users found. Please create user workspace first.")
    st.stop()



# USER SELECTION CARD


st.markdown('<div class="card">', unsafe_allow_html=True)

user_id = st.selectbox(
    "Select Company / User",
    users
)

st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------
# LOAD SYSTEM
# -------------------------------

@st.cache_resource
def load_system(user):
    return EmailResponder(user)


responder = load_system(user_id)


# -------------------------------
# INPUT EMAIL CARD
# -------------------------------

st.markdown('<div class="card">', unsafe_allow_html=True)

st.subheader(" Customer Email")

customer_email = st.text_area(
    "Paste Email",
    height=200,
    placeholder="Paste customer email here..."
)

generate = st.button(" Generate AI Response")

st.markdown('</div>', unsafe_allow_html=True)



# OUTPUT CARD


if generate:

    if customer_email.strip() == "":
        st.warning("Please enter a customer email.")

    else:

        with st.spinner("Generating AI response..."):

            response = responder.generate_reply(customer_email)

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.subheader(" AI Generated Reply")

        st.text_area(
            "Draft Response",
            response,
            height=300
        )

        st.success("Response generated successfully!")

        st.markdown('</div>', unsafe_allow_html=True)