import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app


def send_email(to_email, subject, body):
    if not current_app.config.get("ENABLE_MAILER"):
        current_app.logger.warning("Email skipped because mailer is disabled: %s", subject)
        return False

    try:
        message = MIMEMultipart()
        message["From"] = current_app.config["SMTP_EMAIL"]
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        smtp_host = current_app.config["SMTP_SERVER"]
        smtp_port = current_app.config["SMTP_PORT"]
        smtp_timeout = current_app.config.get("SMTP_TIMEOUT", 10)

        if current_app.config.get("MAIL_USE_SSL"):
            server = smtplib.SMTP_SSL(
                smtp_host,
                smtp_port,
                timeout=smtp_timeout,
            )
        else:
            server = smtplib.SMTP(
                smtp_host,
                smtp_port,
                timeout=smtp_timeout,
            )

        if current_app.config.get("MAIL_USE_TLS") and not current_app.config.get("MAIL_USE_SSL"):
            server.starttls()
        server.login(
            current_app.config["SMTP_EMAIL"],
            current_app.config["SMTP_PASSWORD"],
        )
        server.sendmail(
            current_app.config["SMTP_EMAIL"],
            to_email,
            message.as_string(),
        )
        server.quit()
        return True
    except Exception:
        current_app.logger.exception("Error sending email to %s with subject %s", to_email, subject)
        return False
