import smtplib
from email.mime.text import MIMEText


class EmailSender:

    def __init__(self, email_user, password):

        self.email_user = email_user
        self.password = password

    def send_email(self, to_email, subject, body):

        msg = MIMEText(body)

        msg["Subject"] = subject
        msg["From"] = self.email_user
        msg["To"] = to_email

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)

        server.login(self.email_user, self.password)

        server.sendmail(
            self.email_user,
            to_email,
            msg.as_string()
        )

        server.quit()