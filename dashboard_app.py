import requests
import streamlit as st

BASE_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(page_title="Customer Support Panel", layout="wide")

# ---------- SESSION ----------
if "token" not in st.session_state:
    st.session_state.token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

# ---------- STYLE ----------
st.markdown(
    """
    <style>
    .card {
        padding: 20px;
        border-radius: 12px;
        background-color: #1e1e1e;
        color: white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Customer Support Panel")

# ---------- LOGIN ----------
if not st.session_state.token:

    st.subheader("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            res = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": email, "password": password},
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state.token = data["access_token"]
                st.session_state.refresh_token = data.get("refresh_token")
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")
        except Exception:
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
    except Exception:
        st.error("Backend not reachable")
        stats = {}

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(
        f"<div class='card'>Tickets<br><h2>{stats.get('tickets_total', 0)}</h2></div>",
        unsafe_allow_html=True,
    )
    c2.markdown(
        f"<div class='card'>Open<br><h2>{stats.get('tickets_open', 0)}</h2></div>",
        unsafe_allow_html=True,
    )
    c3.markdown(
        f"<div class='card'>Review Queue<br><h2>{stats.get('review_queue', 0)}</h2></div>",
        unsafe_allow_html=True,
    )
    c4.markdown(
        f"<div class='card'>Escalated<br><h2>{stats.get('tickets_escalated', 0)}</h2></div>",
        unsafe_allow_html=True,
    )
    c5.markdown(
        f"<div class='card'>Resolved<br><h2>{stats.get('tickets_resolved', 0)}</h2></div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ---------- UPLOAD KNOWLEDGE BASE ----------
    st.markdown("## Upload Knowledge Base")

    uploaded_file = st.file_uploader("Upload PDF / DOCX")

    if uploaded_file:
        with st.spinner("Training AI..."):
            res = requests.post(
                f"{BASE_URL}/data/upload",
                headers=headers,
                files={
                    "file": (
                        uploaded_file.name,
                        uploaded_file,
                        uploaded_file.type,
                    )
                },
            )
        if res.status_code == 200:
            st.success("AI trained successfully!")
        else:
            st.error("Upload failed")

    st.markdown("---")

    # ---------- HEADER ----------
    col1, col2 = st.columns([8, 1])
    with col1:
        st.subheader("Review Queue (Priority Sorted)")
    with col2:
        if st.button("Refresh"):
            st.rerun()

    # ---------- FETCH REVIEW QUEUE ----------
    try:
        res = requests.get(f"{BASE_URL}/tickets/queue", headers=headers)
        items = res.json() if res.status_code == 200 else []
    except Exception:
        st.error("Failed to fetch the review queue")
        items = []

    if not items:
        st.success("No drafts awaiting review")

    # ---------- QUEUE ITEMS ----------
    for item in items:
        message_id = item["id"]
        ticket_id = item["ticket_id"]

        with st.container():
            st.markdown("----")
            st.markdown(f"### {item.get('ticket_subject') or '(no subject)'}")
            st.caption(f"From: {item.get('customer_email', 'Customer')}")
            st.write((item.get("body") or "")[:300] + "...")

            # ---------- CONFIDENCE ----------
            conf = item.get("confidence") or 0
            if conf < 50:
                st.error(f"URGENT | Low confidence: {conf}%")
            elif conf < 80:
                st.warning(f"Medium confidence: {conf}%")
            else:
                st.success(f"High confidence: {conf}%")

            # ---------- CONVERSATION ----------
            with st.expander("View Conversation"):
                try:
                    tres = requests.get(
                        f"{BASE_URL}/tickets/{ticket_id}", headers=headers
                    )
                    if tres.status_code == 200:
                        for m in tres.json().get("messages", []):
                            who = (
                                "Customer"
                                if m["direction"] == "inbound"
                                else "Support"
                            )
                            st.markdown(f"**{who}:** {m.get('body', '')}")
                    else:
                        st.error("Failed to load conversation")
                except Exception:
                    st.error("Failed to load conversation")

            # ---------- DRAFT ----------
            edited = st.text_area(
                "Draft Reply",
                value=item.get("ai_draft") or "",
                key=f"draft_{message_id}",
            )

            b1, b2, b3 = st.columns(3)

            # Send: save the (possibly edited) draft, then send.
            if b1.button("Send", key=f"send_{message_id}"):
                with st.spinner("Sending..."):
                    requests.put(
                        f"{BASE_URL}/messages/{message_id}/draft",
                        headers=headers,
                        json={"text": edited},
                    )
                    sres = requests.post(
                        f"{BASE_URL}/messages/{message_id}/send",
                        headers=headers,
                    )
                if sres.status_code == 200:
                    st.success("Reply sent")
                else:
                    st.error("Send failed")
                st.rerun()

            # Regenerate the AI draft.
            if b2.button("Regenerate", key=f"regen_{message_id}"):
                with st.spinner("Regenerating..."):
                    requests.post(
                        f"{BASE_URL}/messages/{message_id}/regenerate",
                        headers=headers,
                    )
                st.rerun()

            # Reject -> escalate the ticket.
            if b3.button("Reject", key=f"reject_{message_id}"):
                requests.post(
                    f"{BASE_URL}/messages/{message_id}/reject",
                    headers=headers,
                    json={"reason": "agent_rejected"},
                )
                st.warning("Draft rejected; ticket escalated")
                st.rerun()
