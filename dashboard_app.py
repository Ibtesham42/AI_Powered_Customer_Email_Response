import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Support", layout="wide")

# ---------- STYLE ----------
st.markdown("""
    <style>
    .card {
        padding: 20px;
        border-radius: 12px;
        background-color: #1e1e1e;
        color: white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

st.title(" AI Customer Support")

# ---------- LOGIN ----------
if "token" not in st.session_state:

    st.subheader(" Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        res = requests.post(f"{BASE_URL}/auth/login", json={
            "email": email,
            "password": password
        })

        if res.status_code == 200:
            st.session_state["token"] = res.json()["access_token"]
            st.success("Welcome back!")
            st.rerun()
        else:
            st.error("Invalid credentials")

# ---------- MAIN DASHBOARD ----------
else:
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}

    #  STATS
    st.subheader(" Overview")

    stats = requests.get(f"{BASE_URL}/dashboard/stats", headers=headers).json()

    c1, c2, c3 = st.columns(3)

    c1.markdown(f"<div class='card'> Total<br><h2>{stats['total_emails']}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'> Replied<br><h2>{stats['replied']}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'> Pending<br><h2>{stats['pending']}</h2></div>", unsafe_allow_html=True)

    st.markdown("---")

    #  CREATE EMAIL
    st.subheader(" New Customer Email")

    col1, col2 = st.columns(2)

    subject = col1.text_input("Subject")
    body = col2.text_area("Customer Message")

    if st.button(" Create + Auto AI Draft"):
        with st.spinner("Generating AI reply..."):
            requests.post(
                f"{BASE_URL}/email/create",
                params={"subject": subject, "body": body},
                headers=headers
            )
        st.success("AI Draft Ready!")
        st.rerun()

    st.markdown("---")

    #  EMAIL LIST
    st.subheader(" Inbox")

    emails = requests.get(f"{BASE_URL}/email/all", headers=headers).json()

    for email in emails:

        with st.container():
            st.markdown("----")

            col1, col2 = st.columns([3, 1])

            # Email info
            with col1:
                st.markdown(f"###  {email['subject']}")
                st.write(email["body"])

            # Status badge
            with col2:
                if email["status"] == "pending":
                    st.error("Pending ")
                else:
                    st.success("Replied ")

            # AI reply editor
            edited = st.text_area(
                " AI Draft",
                value=email.get("ai_reply", ""),
                key=f"edit_{email['id']}"
            )

            colA, colB = st.columns(2)

            # Update
            if colA.button(f" Update #{email['id']}"):
                requests.put(
                    f"{BASE_URL}/email/update-reply",
                    params={
                        "email_id": email["id"],
                        "new_reply": edited
                    },
                    headers=headers
                )
                st.success("Updated!")

            # Send
            if colB.button(f" Send #{email['id']}"):
                requests.post(
                    f"{BASE_URL}/email/send",
                    params={"email_id": email["id"]},
                    headers=headers
                )
                st.success("Email Sent!")