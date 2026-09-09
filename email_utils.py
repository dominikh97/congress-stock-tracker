import os
import smtplib
from email.mime.text import MIMEText


def load_smtp_config():
    """Read SMTP settings from the environment (set as GitHub secrets)."""

    host = os.environ.get("SMTP_HOST")
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")

    if not (host and username and password):
        return None

    return {
        "host": host,
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "username": username,
        "password": password,
        "from_address": os.environ.get("SMTP_FROM", username),
    }


def send_email(smtp_config, to_address, subject, body):

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_config["from_address"]
    msg["To"] = to_address

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
        server.starttls()
        server.login(smtp_config["username"], smtp_config["password"])
        server.sendmail(
            smtp_config["from_address"],
            [to_address],
            msg.as_string()
        )
