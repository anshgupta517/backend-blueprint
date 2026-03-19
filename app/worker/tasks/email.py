# app/worker/tasks/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.worker.celery_app import celery_app
from app.core.config import settings
from app.core.logging import logger


@celery_app.task(
    bind=True,  # 'self' gives access to task instance (for retries)
    max_retries=3,  # retry up to 3 times on failure
    default_retry_delay=60,  # wait 60 seconds between retries
    name="tasks.send_welcome_email",
)
def send_welcome_email(self, user_email: str, user_name: str) -> dict:
    """
    Sends a welcome email to a newly registered user.

    This runs in the Celery worker process, completely separate
    from the FastAPI app. The user's HTTP request has already
    returned by the time this executes.

    bind=True means 'self' is the task instance — we use it
    to call self.retry() on failure.
    """
    logger.info(f"Sending welcome email to {user_email}")

    try:
        # Build the email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Welcome to {settings.app_name}!"
        msg["From"] = settings.email_from
        msg["To"] = user_email

        # Plain text version
        text_body = f"""
Hi {user_name},

Welcome to {settings.app_name}! Your account has been created.

Get started by visiting our app.

Cheers,
The {settings.app_name} team
        """

        # HTML version
        html_body = f"""
<html><body>
<h2>Welcome to {settings.app_name}, {user_name}!</h2>
<p>Your account has been created successfully.</p>
<p>Get started by visiting our app.</p>
<br>
<p>Cheers,<br>The {settings.app_name} team</p>
</body></html>
        """

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send via SMTP
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.email_from, user_email, msg.as_string())

        logger.info(f"Welcome email sent to {user_email}")
        return {"status": "sent", "email": user_email}

    except Exception as exc:
        logger.error(f"Failed to send welcome email to {user_email}: {exc}")
        # Retry with exponential backoff
        # countdown doubles each retry: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
