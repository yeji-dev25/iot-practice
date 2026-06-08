# notifier.py

import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header

from config import (
    EMAIL_ENABLED,
    SMTP_SERVER,
    SMTP_PORT,
    EMAIL_SENDER,
    EMAIL_APP_PASSWORD,
    EMAIL_RECEIVER,
    NOTIFICATION_COOLDOWN_SECONDS
)

last_notification_time = {}


def send_email(subject: str, message: str):
    if not EMAIL_ENABLED:
        print("[EMAIL OFF]", subject, message)
        return

    if not EMAIL_SENDER or not EMAIL_APP_PASSWORD or not EMAIL_RECEIVER:
        print("[EMAIL ERROR] 이메일 설정값이 없습니다.")
        return

    try:
        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.send_message(msg)

        print("[EMAIL SENT]", subject)

    except Exception as e:
        print("[EMAIL ERROR]", e)


def send_notification_once(key: str, subject: str, message: str):
    now = time.time()
    last_time = last_notification_time.get(key, 0)

    if now - last_time < NOTIFICATION_COOLDOWN_SECONDS:
        return

    send_email(subject, message)
    last_notification_time[key] = now