"""Email utility service for sending emails via SMTP."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from src.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    recipient_email: str,
    subject: str,
    body: str,
    is_html: bool = False,
) -> bool:
    """
    Send an email asynchronously.

    Returns:
        True if success, False otherwise.
    """
    message = MIMEMultipart()
    message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    message["To"] = recipient_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "html" if is_html else "plain"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=False,  # Mailpit doesn't need TLS locally
        )
        logger.info(f"Email sent to {recipient_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        return False
