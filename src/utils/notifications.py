"""Notification service for sending alerts."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import requests

from .config import Config

logger = logging.getLogger(__name__)

class NotificationService:
    """Service to handle sending notifications."""

    def __init__(self, config: Config):
        self.config = config

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email notification."""
        # Check if email is explicitly enabled or we are in console mode
        if self.config.notification_provider == "console":
            # Use print as well as logger to ensure it's visible in streamlit logs if configured
            print(f"[MOCK EMAIL] To: {to_email} | Subject: {subject} | Body: {body}")
            logger.info(f"[MOCK EMAIL] To: {to_email} | Subject: {subject} | Body: {body}")
            return True

        if self.config.notification_provider == "email" or (self.config.email_smtp_server and self.config.email_sender_user):
            return self._send_smtp_email(to_email, subject, body)

        logger.warning(f"Email requested but provider configuration is missing or provider is {self.config.notification_provider}")
        return False

    def send_sms(self, to_number: str, message: str) -> bool:
        """Send an SMS notification."""
        if self.config.notification_provider == "console":
            print(f"[MOCK SMS] To: {to_number} | Message: {message}")
            logger.info(f"[MOCK SMS] To: {to_number} | Message: {message}")
            return True

        if self.config.notification_provider == "twilio" or (self.config.twilio_account_sid and self.config.twilio_auth_token):
            return self._send_twilio_sms(to_number, message)

        logger.warning(f"SMS requested but provider configuration is missing or provider is {self.config.notification_provider}")
        return False

    def _send_smtp_email(self, to_email: str, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart()
            sender = self.config.email_from_address or self.config.email_sender_user
            msg['From'] = sender
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port)
            server.starttls()
            server.login(self.config.email_sender_user, self.config.email_sender_password)
            text = msg.as_string()
            server.sendmail(sender, to_email, text)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _send_twilio_sms(self, to_number: str, message: str) -> bool:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.config.twilio_account_sid}/Messages.json"
            data = {
                "To": to_number,
                "From": self.config.twilio_from_number,
                "Body": message
            }
            response = requests.post(
                url,
                data=data,
                auth=(self.config.twilio_account_sid, self.config.twilio_auth_token)
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

_service_instance = None

def get_notification_service(config: Optional[Config] = None) -> NotificationService:
    """Get the singleton instance of the notification service."""
    global _service_instance
    if _service_instance is None:
        if config is None:
            config = Config.from_env()
        _service_instance = NotificationService(config)
    return _service_instance
