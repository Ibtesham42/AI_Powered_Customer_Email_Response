
import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(page_title="Customer Support Panel", layout="wide")

# ---------- SESSION ----------
if "token" not in st.session_state:
    st.session_state.token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

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
        try:
            res = requests.post(f"{BASE_URL}/auth/login", json={
                "email": email,
                "password": password
            })

            if res.status_code == 200:
                data = res.json()
                st.session_state.token = data["access_token"]
                st.session_state.refresh_token = data.get("refresh_token")
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

        except:
            st.error("Backend not running")

# ---------- DASHBOARD ----------
else:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # ---------- LOGOUT ----------
    if st.button("Logout"):
        try:
            requests.post(
                f"{BASE_URL}/auth/logout",
                json={"refresh_token": st.session_state.refresh_token or ""},
            )
        except Exception:
            pass
        st.session_state.token = None
        st.session_state.refresh_token = None
        st.rerun()

    # ---------- STATS ----------
    st.subheader("Overview")

    try:
        res = requests.get(f"{BASE_URL}/dashboard/stats", headers=headers)
        stats = res.json() if res.status_code == 200 else {}
    except:
        st.error("Backend not reachable")
        stats = {}

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.markdown(f"<div class='card'> Total<br><h2>{stats.get('total_emails', 0)}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'> New<br><h2>{stats.get('new', 0)}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'> AI Generated<br><h2>{stats.get('ai_generated', 0)}</h2></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card'> Reviewed<br><h2>{stats.get('reviewed', 0)}</h2></div>", unsafe_allow_html=True)
    c5.markdown(f"<div class='card'> Sent<br><h2>{stats.get('sent', 0)}</h2></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ---------- UPLOAD ----------
    st.markdown("## Upload Knowledge Base")

    uploaded_file = st.file_uploader("Upload PDF / DOCX")

    if uploaded_file:
        with st.spinner("Training AI..."):
            res = requests.post(
                f"{BASE_URL}/data/upload",
                headers=headers,
                files={
                    "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
                }
            )

        if res.status_code == 200:
            st.success("AI trained successfully!")
        else:
            st.error("Upload failed")

    st.markdown("---")

    # ---------- HEADER ----------
    col1, col2 = st.columns([8, 1])

    with col1:
        st.subheader("Pending Emails (Priority Sorted)")

    with col2:
        if st.button("Refresh"):
            st.rerun()

    # ---------- FETCH EMAILS ----------
    try:
        res = requests.get(f"{BASE_URL}/email/todo", headers=headers)
        emails = res.json() if res.status_code == 200 else []
    except:
        st.error("Failed to fetch emails")
        emails = []

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

                # ---------- CONFIDENCE ----------
                conf = email.get("confidence", 0)

                if conf < 50:
                    st.error(f"🔥 URGENT | Low Confidence: {conf}%")
                elif conf < 80:
                    st.warning(f"⚠️ Medium Confidence: {conf}%")
                else:
                    st.success(f"✅ High Confidence: {conf}%")

                # ---------- THREAD ----------
                if email.get("thread_id"):

                    with st.expander("View Conversation"):

                        try:
                            thread_res = requests.get(
                                f"{BASE_URL}/email/thread/{email['thread_id']}",
                                headers=headers
                            )

                            thread_data = thread_res.json()

                            for t in thread_data:
                                st.markdown(f"🧑 Customer: {t['body']}")

                                if t.get("ai_reply"):
                                    st.markdown(f"🧑‍💻 Support: {t['ai_reply']}")

                        except:
                            st.error("Failed to load thread")

            # ---------- RIGHT PANEL ----------
            with right:
                st.caption(f"Status: {email['status']}")

                # ---------- ASSIGN ----------
                agent_id = st.number_input(
                    "Assign to Agent",
                    min_value=1,
                    step=1,
                    key=f"assign_input_{email['id']}"
                )

                if st.button("Assign", key=f"assign_{email['id']}"):
                    requests.post(
                        f"{BASE_URL}/email/assign",
                        params={
                            "email_id": email["id"],
                            "agent_id": agent_id
                        },
                        headers=headers
                    )
                    st.success("Assigned")
                    st.rerun()

            # ---------- EDIT ----------
            edited_reply = st.text_area(
                "Draft Reply",
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

                    requests.put(
                        f"{BASE_URL}/email/update-reply",
                        params={
                            "email_id": email["id"],
                            "new_reply": edited_reply
                        },
                        headers=headers
                    )

                    requests.post(
                        f"{BASE_URL}/email/send/{email['id']}",
                        headers=headers
                    )

                st.success("Email sent successfully")
                st.rerun()
