import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.email.email_listener import EmailListener

listener = EmailListener(
    host="imap.gmail.com",
    email_user="ibteshamakhtar1@gmail.com",
    password="jttz xupm qlzb ztdv"
)

emails = listener.fetch_unread_emails()

for e in emails:

    print("Subject:", e["subject"])
    print("From:", e["sender"])
    print("Body:", e["body"])
    print("-" * 40)





    