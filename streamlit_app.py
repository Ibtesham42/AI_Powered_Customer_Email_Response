import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.email.email_responder import EmailResponder


st.set_page_config(
    page_title="AI Customer Support",
    layout="wide"
)

st.title("AI Customer Email Response System")

st.write("Generate AI-powered customer support replies using RAG + LLM")


# Detect users automatically
users_path = "data/users"

users = []

if os.path.exists(users_path):

    users = os.listdir(users_path)


if len(users) == 0:

    st.warning("No users found. Please create user workspace first.")
    st.stop()


# User selector
user_id = st.selectbox(
    "Select Company / User",
    users
)


@st.cache_resource
def load_system(user):

    return EmailResponder(user)


responder = load_system(user_id)


customer_email = st.text_area(
    "Customer Email",
    height=200,
    placeholder="Paste customer email here..."
)


if st.button("Generate Response"):

    if customer_email.strip() == "":
        st.warning("Please enter a customer email.")

    else:

        with st.spinner("Generating response..."):

            response = responder.generate_reply(customer_email)

        st.subheader("Generated Email Response")

        st.text_area(
            "AI Draft Reply",
            response,
            height=250
        )