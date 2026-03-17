import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.email.email_responder import EmailResponder


print("Loading AI Customer Support System...")

responder = EmailResponder()

query = input("\nCustomer Email:\n")

response = responder.generate_reply(query)

print("\nGenerated Email Response:\n")

print(response)