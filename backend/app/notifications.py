import logging
import smtplib
import ssl
from email.message import EmailMessage

from sqlalchemy.orm import Session

from .config import settings
from .models import NotificationLog

logger = logging.getLogger(__name__)

EMAIL_TEMPLATES: dict[str, tuple[str, str]] = {
    "employee_onboarding": (
        "Welcome to Big Stack People",
        "Hello {full_name},\n\nYour employee account is ready. Sign in to view your profile and HR information.\n",
    ),
    "leave_application": (
        "New leave request: {employee_name}",
        "{employee_name} submitted a leave request from {start_date} through {end_date}.\n",
    ),
    "leave_decision": (
        "Your leave request was {status}",
        "Your {leave_type} leave request from {start_date} through {end_date} was {status}.\n",
    ),
    "payroll_generated": (
        "Your {period} salary slip is ready",
        "Your salary slip for {period} has been generated.\nNet salary: INR {net_salary}\n",
    ),
    "payroll_credit_simulated": (
        "Salary credit simulated for {period}",
        "A salary credit simulation was recorded for {period}. No funds were transferred.\n",
    ),
    "attendance_alert": (
        "Attendance alert",
        "{message}\n",
    ),
}


def send_notification(db: Session, recipient: str, event_type: str, **context: str) -> None:
    try:
        subject_template, body_template = EMAIL_TEMPLATES[event_type]
    except KeyError as exc:
        raise ValueError(f"No email template is registered for event {event_type!r}") from exc

    subject = subject_template.format_map(context)
    body = body_template.format_map(context)
    status = "logged"
    if settings.smtp_host:
        message = EmailMessage()
        message["From"] = settings.smtp_from_email
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as client:
                if settings.smtp_starttls:
                    client.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password)
                client.send_message(message)
            status = "sent"
        except (OSError, smtplib.SMTPException):
            status = "failed"
            logger.exception("Email delivery failed for event %s to %s", event_type, recipient)

    db.add(NotificationLog(recipient=recipient, event_type=event_type, subject=subject, status=status))
