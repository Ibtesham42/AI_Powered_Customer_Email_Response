import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.email.email_listener import EmailListener
from app.email.email_responder import EmailResponder


EMAIL = "ibteshamakhtar1@gmail.com"
PASSWORD = "jttz xupm qlzb ztdv"

USER_ID = "companyA"


print("Starting AI Email Worker...")


listener = EmailListener(
    host="imap.gmail.com",
    email_user=EMAIL,
    password=PASSWORD
)

# pass user_id here
responder = EmailResponder(user_id=USER_ID)


emails = listener.fetch_unread_emails()


for e in emails:

    customer_email = f"""
Subject: {e['subject']}

{e['body']}
"""

    print("\nCustomer Email Received:\n")
    print(customer_email)

    print("\nGenerating AI response...\n")

    reply = responder.generate_reply(customer_email)

    print("AI Response:\n")

    print(reply)

    print("\n" + "="*50)