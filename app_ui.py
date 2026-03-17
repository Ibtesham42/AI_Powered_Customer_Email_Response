import streamlit as st
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath("."))

from app.email.email_listener import EmailListener
from app.email.email_responder import EmailResponder

load_dotenv()

EMAIL = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASSWORD")
USER_ID = os.getenv("USER_ID")

st.set_page_config(page_title="AI Email Support", layout="wide")

st.title("AI Customer Support Email System")


if "listener" not in st.session_state:
    st.session_state.listener = EmailListener(
        host="imap.gmail.com",
        email_user=EMAIL,
        password=PASSWORD
    )

if "responder" not in st.session_state:
    st.session_state.responder = EmailResponder(user_id=USER_ID)

listener = st.session_state.listener
responder = st.session_state.responder


if st.button("Read Latest Email"):

    emails = listener.fetch_unread_emails()

    if emails:

        st.session_state.email_data = emails[0]


if "email_data" in st.session_state:

    email_data = st.session_state.email_data

    st.subheader("Customer Email")

    st.write("From:", email_data["sender"])
    st.write("Subject:", email_data["subject"])

    st.text_area(
        "Email Body",
        email_data["body"],
        height=200
    )

    if st.button("Generate AI Reply"):

        customer_email = f"""
Subject: {email_data['subject']}

{email_data['body']}
"""

        response = responder.generate_reply(customer_email)

        st.session_state.ai_reply = response


if "ai_reply" in st.session_state:

    st.subheader("AI Generated Reply")

    st.text_area(
        "Draft Reply",
        st.session_state.ai_reply,
        height=300
    )