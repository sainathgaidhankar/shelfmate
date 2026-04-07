import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl

from flask import current_app


def send_email_with_status(to_email, subject, body):
    if not current_app.config.get("ENABLE_MAILER"):
        message = "Mailer is disabled."
        current_app.logger.warning("Email skipped because mailer is disabled: %s", subject)
        return False, message

    to_email = (to_email or "").strip()
    if not to_email:
        message = "Recipient email address is missing."
        current_app.logger.error("Email skipped because recipient is missing for subject %s", subject)
        return False, message

    smtp_host = current_app.config.get("SMTP_SERVER")
    smtp_port = current_app.config.get("SMTP_PORT")
    smtp_email = current_app.config.get("SMTP_EMAIL")
    smtp_password = current_app.config.get("SMTP_PASSWORD")
    default_sender = current_app.config.get("MAIL_DEFAULT_SENDER") or smtp_email

    if not all([smtp_host, smtp_port, smtp_email, smtp_password, default_sender]):
        missing = [
            name
            for name, value in [
                ("SMTP_SERVER", smtp_host),
                ("SMTP_PORT", smtp_port),
                ("SMTP_EMAIL", smtp_email),
                ("SMTP_PASSWORD", smtp_password),
                ("MAIL_DEFAULT_SENDER", default_sender),
            ]
            if not value
        ]
        message = f"SMTP configuration is incomplete: {', '.join(missing)}."
        current_app.logger.error("Email skipped because SMTP configuration is incomplete for subject %s: %s", subject, message)
        return False, message

    server = None
    try:
        message = MIMEMultipart()
        message["From"] = default_sender
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        smtp_timeout = current_app.config.get("SMTP_TIMEOUT", 10)

        if current_app.config.get("MAIL_USE_SSL"):
            server = smtplib.SMTP_SSL(
                smtp_host,
                smtp_port,
                timeout=smtp_timeout,
                context=ssl.create_default_context(),
            )
        else:
            server = smtplib.SMTP(
                smtp_host,
                smtp_port,
                timeout=smtp_timeout,
            )

        if current_app.config.get("MAIL_USE_TLS") and not current_app.config.get("MAIL_USE_SSL"):
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
        server.login(smtp_email, smtp_password)
        server.sendmail(
            default_sender,
            to_email,
            message.as_string(),
        )
        server.quit()
        return True, "Email sent."
    except smtplib.SMTPAuthenticationError as exc:
        current_app.logger.exception("SMTP authentication failed for subject %s", subject)
        return False, f"SMTP authentication failed: {exc}"
    except smtplib.SMTPRecipientsRefused as exc:
        current_app.logger.exception("Recipient refused for subject %s", subject)
        return False, f"Recipient refused: {exc}"
    except smtplib.SMTPException as exc:
        current_app.logger.exception("SMTP error sending email to %s with subject %s", to_email, subject)
        return False, f"SMTP error: {exc}"
    except Exception as exc:
        current_app.logger.exception("Error sending email to %s with subject %s", to_email, subject)
        return False, f"Unexpected mail error: {exc}"
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass


def send_email(to_email, subject, body):
    sent, _message = send_email_with_status(to_email, subject, body)
    return sent
