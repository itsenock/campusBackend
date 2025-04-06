import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

smtp_server = os.getenv('SMTP_SERVER')
smtp_port = int(os.getenv('SMTP_PORT', 587))
smtp_username = os.getenv('SMTP_USERNAME')
smtp_password = os.getenv('SMTP_PASSWORD')
smtp_use_tls = os.getenv('SMTP_USE_TLS', 'True') == 'True'
from_email = smtp_username  # Or use os.getenv('FROM_EMAIL')
to_email = 'mutetienock4@gmail.com'  # Replace with your email for testing
subject = 'SMTP Configuration Test'
body = 'This is a test email to verify SMTP configuration.'

message = MIMEText(body)
message['Subject'] = subject
message['From'] = from_email
message['To'] = to_email

try:
    server = smtplib.SMTP(smtp_server, smtp_port)
    if smtp_use_tls:
        server.starttls()
    server.login(smtp_username, smtp_password)
    server.sendmail(from_email, to_email, message.as_string())
    server.quit()
    print('Email sent successfully.')
except Exception as e:
    print(f'Failed to send email: {e}')
