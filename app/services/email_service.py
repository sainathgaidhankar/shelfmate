import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app


def _mail_transport():
    transport = current_app.config.get("MAIL_TRANSPORT", "auto").lower()
    if transport != "auto":
        return transport
    if current_app.config.get("RESEND_API_KEY"):
        return "resend"
    return "smtp"


def _sender_value():
    return current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("SMTP_EMAIL")


def _send_via_resend(to_email, subject, body):
    api_key = current_app.config.get("RESEND_API_KEY")
    api_url = current_app.config.get("RESEND_API_URL")
    sender = _sender_value()

    if not api_key:
        return False, "RESEND_API_KEY is missing."
    if not sender:
        return False, "MAIL_DEFAULT_SENDER is missing."

    payload = json.dumps(
        {
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "text": body,
        }
    ).encode("utf-8")
    request = Request(
        api_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "shelfmate/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=current_app.config.get("SMTP_TIMEOUT", 10)) as response:
            status_code = getattr(response, "status", response.getcode())
            if 200 <= status_code < 300:
                return True, "Email sent."
            body_text = response.read().decode("utf-8", errors="replace")
            current_app.logger.error("Resend API returned non-success status %s: %s", status_code, body_text)
            return False, f"Resend API error: HTTP {status_code}."
    except HTTPError as exc:
        response_text = exc.read().decode("utf-8", errors="replace")
        current_app.logger.exception("Resend API HTTP error for subject %s: %s", subject, response_text)
        try:
            response_json = json.loads(response_text)
            resend_message = response_json.get("message") or response_json.get("error")
        except Exception:
            resend_message = None
        if resend_message:
            return False, f"Resend API rejected the request: {resend_message}"
        return False, f"Resend API rejected the request: HTTP {exc.code}."
    except URLError as exc:
        current_app.logger.exception("Resend API network error for subject %s", subject)
        return False, f"Email API network error: {exc.reason}"
    except Exception as exc:
        current_app.logger.exception("Unexpected Resend API error for subject %s", subject)
        return False, f"Unexpected email API error: {exc}"


def _send_via_smtp(to_email, subject, body):
    smtp_host = current_app.config.get("SMTP_SERVER")
    smtp_port = current_app.config.get("SMTP_PORT")
    smtp_email = current_app.config.get("SMTP_EMAIL")
    smtp_password = current_app.config.get("SMTP_PASSWORD")
    default_sender = _sender_value() or smtp_email

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

    smtp_timeout = current_app.config.get("SMTP_TIMEOUT", 10)
    connection_attempts = [
        {
            "port": smtp_port,
            "use_tls": current_app.config.get("MAIL_USE_TLS"),
            "use_ssl": current_app.config.get("MAIL_USE_SSL"),
        }
    ]
    if smtp_host and "gmail" in smtp_host.lower():
        configured = connection_attempts[0]
        gmail_fallbacks = [
            {"port": 587, "use_tls": True, "use_ssl": False},
            {"port": 465, "use_tls": False, "use_ssl": True},
        ]
        for fallback in gmail_fallbacks:
            if fallback != configured:
                connection_attempts.append(fallback)

    last_error = None
    for attempt in connection_attempts:
        server = None
        try:
            message = MIMEMultipart()
            message["From"] = default_sender
            message["To"] = to_email
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            if attempt["use_ssl"]:
                server = smtplib.SMTP_SSL(
                    smtp_host,
                    attempt["port"],
                    timeout=smtp_timeout,
                    context=ssl.create_default_context(),
                )
            else:
                server = smtplib.SMTP(
                    smtp_host,
                    attempt["port"],
                    timeout=smtp_timeout,
                )

            if attempt["use_tls"] and not attempt["use_ssl"]:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            server.login(smtp_email, smtp_password)
            server.sendmail(
                smtp_email,
                [to_email],
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
        except (OSError, socket.error) as exc:
            last_error = exc
            current_app.logger.warning(
                "SMTP network error on %s:%s for subject %s: %s",
                smtp_host,
                attempt["port"],
                subject,
                exc,
            )
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

    if last_error is not None:
        return False, f"SMTP network error: {last_error}"

    try:
        message = MIMEMultipart()
        message["From"] = default_sender
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))
    except Exception:
        pass
    return False, "SMTP send failed."


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

    transport = _mail_transport()
    if transport == "resend":
        return _send_via_resend(to_email, subject, body)
    if transport == "smtp":
        return _send_via_smtp(to_email, subject, body)

    current_app.logger.error("Unsupported mail transport configured: %s", transport)
    return False, f"Unsupported mail transport: {transport}"


def send_email(to_email, subject, body):
    sent, _message = send_email_with_status(to_email, subject, body)
    return sent
