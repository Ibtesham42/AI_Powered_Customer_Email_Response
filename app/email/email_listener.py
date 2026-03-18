import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup


class EmailListener:

    def __init__(self, host, email_user, password):

        print("Connecting to IMAP server...")

        self.mail = imaplib.IMAP4_SSL(host)

        print("Logging in...")

        self.mail.login(email_user, password)

        print("Login successful")

    def clean_html(self, html):

        soup = BeautifulSoup(html, "html.parser")

        return soup.get_text(separator="\n")

    def fetch_unread_emails(self):

        self.mail.select("INBOX")

        status, messages = self.mail.search(None, '(UNSEEN)')

        email_ids = messages[0].split()

        print("Unread emails found:", len(email_ids))

        emails = []

        

        

        # latest email only
        email_ids = list(reversed(email_ids))

        for e_id in email_ids:

            _, msg_data = self.mail.fetch(e_id, "(RFC822)")

            raw_email = msg_data[0][1]

            msg = email.message_from_bytes(raw_email)

            subject, encoding = decode_header(msg["Subject"])[0]

            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")

            sender = msg.get("From")

            body = ""

            if msg.is_multipart():

                for part in msg.walk():

                    content_type = part.get_content_type()

                    if content_type == "text/plain":

                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break

                    elif content_type == "text/html":

                        html = part.get_payload(decode=True).decode(errors="ignore")
                        body = self.clean_html(html)

            else:

                body = msg.get_payload(decode=True).decode(errors="ignore")

            self.mail.store(e_id, '+FLAGS', '\\Seen')

            emails.append({
                "subject": subject,
                "sender": sender,
                "body": body
            })

        return emails