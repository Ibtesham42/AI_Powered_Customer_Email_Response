
import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Customer Support Panel", layout="wide")

# ---------- SESSION PERSIST ----------
if "token" not in st.session_state:
    st.session_state.token = None

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

st.title("Customer Support Panel")

# ---------- LOGIN ----------
if not st.session_state.token:

    st.subheader("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        res = requests.post(f"{BASE_URL}/auth/login", json={
            "email": email,
            "password": password
        })

        if res.status_code == 200:
            st.session_state.token = res.json()["access_token"]
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid credentials")

# ---------- DASHBOARD ----------
else:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # ---------- STATS ----------
    st.subheader("Overview")

    stats = requests.get(f"{BASE_URL}/dashboard/stats", headers=headers).json()

    c1, c2, c3 = st.columns(3)

    c1.markdown(f"<div class='card'> Total<br><h2>{stats['total_emails']}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'> Replied<br><h2>{stats['replied']}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'> Pending<br><h2>{stats['pending']}</h2></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ---------- HEADER + REFRESH ----------
    col1, col2 = st.columns([8, 1])

    with col1:
        st.subheader("Pending Emails for Human Review")

    with col2:
        if st.button("Refresh"):
            st.rerun()

    # ---------- FETCH EMAILS ----------
    emails = requests.get(f"{BASE_URL}/email/todo", headers=headers).json()

    # ---------- EMPTY STATE ----------
    if not emails:
        st.success("No pending emails")

    # ---------- EMAIL LIST ----------
    for email in emails:

        with st.container():
            st.markdown("----")

            left, right = st.columns([3, 1])

            # ---------- EMAIL INFO ----------
            with left:
                st.markdown(f"### {email['subject']}")
                st.caption(f"From: {email.get('sender', 'Customer')}")
                st.write(email["body"][:300] + "...")
                st.caption(f"Status: {email['status']}")

            # ---------- STATUS ----------
            with right:
                if email["status"] == "AI_GENERATED":
                    st.warning("Needs Human Review")
                elif email["status"] == "HUMAN_REVIEWED":
                    st.info("Edited")
                elif email["status"] == "SENT":
                    st.success("Sent")

            # ---------- EDIT AREA ----------
            edited_reply = st.text_area(
                "Draft Reply (Editable)",
                value=email.get("ai_reply", ""),
                key=f"edit_{email['id']}"
            )

            colA, colB = st.columns(2)

            # ---------- UPDATE ----------
            if colA.button("Update", key=f"update_{email['id']}"):
                requests.put(
                    f"{BASE_URL}/email/update-reply",
                    params={
                        "email_id": email["id"],
                        "new_reply": edited_reply
                    },
                    headers=headers
                )
                st.success("Reply updated")
                st.rerun()

            # ---------- SEND ----------
            if colB.button("Send", key=f"send_{email['id']}"):

                with st.spinner("Sending..."):

                    # update first
                    requests.put(
                        f"{BASE_URL}/email/update-reply",
                        params={
                            "email_id": email["id"],
                            "new_reply": edited_reply
                        },
                        headers=headers
                    )

                    # send
                    requests.post(
                        f"{BASE_URL}/email/send/{email['id']}",
                        headers=headers
                    )

                st.success("Email sent successfully")
                st.rerun()

