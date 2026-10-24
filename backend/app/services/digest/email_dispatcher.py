import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple

from app.core.config import settings
from app.core.logging import logger


class EmailDispatcher:
    """Dispatches transactional emails via SMTP or simulates delivery in development/test."""

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> Tuple[bool, str]:
        """Sends multi-part HTML & text email or simulates dispatch when SMTP is unconfigured."""
        if not settings.SMTP_HOST:
            logger.info(
                "SMTP_HOST unconfigured; SIMULATED email delivery to %s | Subject: %s",
                recipient_email,
                subject,
            )
            return True, "SIMULATED_SUCCESS"

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = recipient_email

            part_text = MIMEText(text_content, "plain", "utf-8")
            part_html = MIMEText(html_content, "html", "utf-8")
            msg.attach(part_text)
            msg.attach(part_html)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, [recipient_email], msg.as_string())

            logger.info("Successfully dispatched email via SMTP to %s", recipient_email)
            return True, "SMTP_SENT"
        except Exception as e:
            logger.error("Failed to send email to %s via SMTP: %s", recipient_email, str(e))
            return False, f"SMTP_ERROR: {str(e)}"


email_dispatcher = EmailDispatcher()
