import streamlit as st
import sys
import os

# project path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.email.email_responder import EmailResponder


st.set_page_config(
    page_title="AI Customer Support",
    layout="wide"
)

st.title("AI Customer Email Response System")

st.write("Generate AI-powered customer support replies using RAG + LLM")


@st.cache_resource
def load_system():
    return EmailResponder()


responder = load_system()


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