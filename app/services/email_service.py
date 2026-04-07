import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl

from flask import current_app


def send_email(to_email, subject, body):
    if not current_app.config.get("ENABLE_MAILER"):
        current_app.logger.warning("Email skipped because mailer is disabled: %s", subject)
        return False

    smtp_host = current_app.config.get("SMTP_SERVER")
    smtp_port = current_app.config.get("SMTP_PORT")
    smtp_email = current_app.config.get("SMTP_EMAIL")
    smtp_password = current_app.config.get("SMTP_PASSWORD")
    default_sender = current_app.config.get("MAIL_DEFAULT_SENDER") or smtp_email

    if not all([smtp_host, smtp_port, smtp_email, smtp_password, default_sender]):
        current_app.logger.error("Email skipped because SMTP configuration is incomplete for subject %s", subject)
        return False

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
        return True
    except Exception:
        current_app.logger.exception("Error sending email to %s with subject %s", to_email, subject)
        return False
