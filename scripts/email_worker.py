
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time

from app.email.email_queue import get_queue, clear_queue
from backend.database import SessionLocal
from backend.models.email import Email
from backend.services.ai_service import generate_email_reply
from app.email.email_listener import EmailListener
from app.utils.config import Config
from app.email.email_queue import add_to_queue


print("Starting AI Worker...")


# ---------------- FETCH EMAILS ----------------
def fetch_emails(db):

    listener = EmailListener(
        host="imap.gmail.com",
        email_user=Config.EMAIL_USER,
        password=Config.EMAIL_PASS
    )

    emails = listener.fetch_unread_emails()

    for e in emails:

        new_email = Email(
            subject=e["subject"],
            body=e["body"],
            company_id=1,
            status="NEW",
            message_id=e.get("message_id"),
            thread_id=e.get("message_id")
        )

        db.add(new_email)
        db.commit()
        db.refresh(new_email)

        add_to_queue(new_email.id, 1)

        print("New email fetched:", e["subject"])


# ---------------- PROCESS QUEUE ----------------
def process_queue():

    db = SessionLocal()

    queue = get_queue()

    if not queue:
        return

    print("Processing:", len(queue))

    for item in queue:

        email = db.query(Email).filter(
            Email.id == item["email_id"]
        ).first()

        if not email:
            continue

        # ✅ FIXED HERE
        result = generate_email_reply(
            email.body,
            item["company_id"],
            db=db,
            thread_id=email.thread_id
        )

        email.ai_reply = result["reply"]          # string only
        email.confidence = result["confidence"]   # int
        email.status = "AI_GENERATED"

        db.commit()

    clear_queue()
    db.close()


# ---------------- RUN LOOP ----------------
if __name__ == "__main__":

    while True:

        db = SessionLocal()

        # fetch new emails
        fetch_emails(db)

        db.close()

        # process AI replies
        process_queue()

        time.sleep(10)

