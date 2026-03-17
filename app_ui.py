import streamlit as st
import os
from dotenv import load_dotenv

from app.email.email_listener import EmailListener
from app.email.email_responder import EmailResponder
from app.email.email_sender import EmailSender
from app.queue.email_queue import add_to_queue, load_queue, update_queue


load_dotenv()

EMAIL = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASSWORD")
USER_ID = os.getenv("USER_ID")


st.set_page_config(page_title="AI Email Support", layout="wide")

st.title("AI Customer Support Admin Panel")


# Initialize systems

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



#  Auto read new email


if st.button("Fetch New Emails"):

    emails = listener.fetch_unread_emails()

    if emails:

        email_data = emails[0]

        customer_email = f"""
Subject: {email_data['subject']}

{email_data['body']}
"""

        ai_reply = responder.generate_reply(customer_email)

        add_to_queue(email_data, ai_reply)

        st.success("Email added to review queue")



#  Admin Review Queue


st.header("Pending Email Replies")

queue = load_queue()


for i, item in enumerate(queue):

    if item["status"] == "pending":

        st.subheader(f"Email {i+1}")

        st.write("From:", item["sender"])
        st.write("Subject:", item["subject"])

        st.text_area(
            "Customer Email",
            item["body"],
            height=150
        )

        edited_reply = st.text_area(
            "AI Draft Reply (Edit before sending)",
            item["ai_reply"],
            height=200,
            key=i
        )

        if st.button("Send Email", key=f"send{i}"):

            sender = EmailSender(EMAIL, PASSWORD)

            sender.send_email(
                item["sender"],
                item["subject"],
                edited_reply
            )

            update_queue(i, edited_reply)

            st.success("Email sent successfully")