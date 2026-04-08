import streamlit as st
import sys
import os
import pandas as pd

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

/* Metrics */
.metric-card {
    background: #f0f4ff;
    padding: 10px;
    border-radius: 8px;
    text-align: center;
}

</style>
""", unsafe_allow_html=True)


# HEADER

st.markdown("""
<div class="header">
    <div class="title-text">AI Customer Email Response System</div>
    <div class="subtitle">Smart Support powered by RAG + LLM + Ibtcode Decision Layer</div>
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


# LOAD SYSTEM

@st.cache_resource
def load_system(user):
    return EmailResponder(user)


responder = load_system(user_id)


# INPUT EMAIL CARD

st.markdown('<div class="card">', unsafe_allow_html=True)

st.subheader("Customer Email")

customer_email = st.text_area(
    "Paste Email",
    height=200,
    placeholder="Paste customer email here..."
)

generate = st.button("Generate AI Response")

st.markdown('</div>', unsafe_allow_html=True)


# OUTPUT SECTION

if generate:
    if customer_email.strip() == "":
        st.warning("Please enter a customer email.")
    else:
        with st.spinner("Analyzing email with Ibtcode Decision Layer..."):
            result = responder.generate_reply(customer_email)
        
        # Display AI Response
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("AI Generated Reply")
        st.text_area(
            "Draft Response",
            result["response"],
            height=250
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display Decision Layer Analysis
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Ibtcode Decision Layer Analysis")
        
        analysis = result["analysis"]
        
        # Create metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            emotion_color = "🔴" if analysis["emotion"] == "angry" else "🟡" if analysis["emotion"] == "frustrated" else "🔵"
            st.metric(
                label="Emotion",
                value=f"{emotion_color} {analysis['emotion']}",
                delta=f"Level {analysis['emotion_level']}/5"
            )
        
        with col2:
            st.metric(
                label="Intent",
                value=analysis["intent"].replace("_", " ").title()
            )
        
        with col3:
            risk_color = "🔴" if analysis["risk"] >= 4 else "🟡" if analysis["risk"] >= 3 else "🟢"
            st.metric(
                label="Risk Level",
                value=f"{risk_color} {analysis['risk']}/5"
            )
        
        with col4:
            urgency_color = "🔴" if analysis["urgency"] >= 4 else "🟡" if analysis["urgency"] >= 3 else "🟢"
            st.metric(
                label="Urgency",
                value=f"{urgency_color} {analysis['urgency']}/5"
            )
        
        with col5:
            st.metric(
                label="Priority",
                value=f"{analysis['priority']:.0%}",
                delta="High" if analysis["priority"] > 0.6 else "Normal"
            )
        
        st.divider()
        
        # Detailed analysis in expandable section
        with st.expander("View Detailed Decision Layer Analysis", expanded=False):
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("**Classification Results**")
                st.write(f"**Context:** {analysis['context'].replace('_', ' ').title()}")
                st.write(f"**Strategy:** {analysis['strategy'].replace('_', ' ').title()}")
                st.write(f"**Action:** {analysis['action'].replace('_', ' ').title()}")
                st.write(f"**Confidence:** {analysis['confidence']:.1%}")
            
            with col_b:
                st.markdown("**Extracted Identifiers**")
                identifiers = result["identifiers"]
                for key, value in identifiers.items():
                    if value:
                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            
            st.divider()
            st.markdown("**Decision Reasoning**")
            st.info(analysis["reasoning"])
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.success("Response generated successfully with Ibtcode Decision Layer!")