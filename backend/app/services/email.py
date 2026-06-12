import json
import logging
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SmtpConfig:
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = "noreply@stockwire.app"
    from_name: str = "Stockwire Rental"
    use_tls: bool = True
    resend_api_key: str = ""


class EmailMessage:
    def __init__(self, to: str, subject: str, text_body: str, html_body: str | None = None) -> None:
        self.to = to
        self.subject = subject
        self.text_body = text_body
        self.html_body = html_body


class EmailBackend(Protocol):
    def send(self, message: EmailMessage) -> str | None: ...


def _get_env_smtp_config() -> SmtpConfig:
    return SmtpConfig(
        host=settings.smtp_host or "",
        port=settings.smtp_port,
        username=settings.smtp_user or "",
        password=settings.smtp_password or "",
        from_email=settings.smtp_from_email or "",
        from_name=settings.smtp_from_name or "",
        use_tls=settings.smtp_use_tls,
        resend_api_key=settings.resend_api_key or "",
    )


def _get_db_smtp_config(db: Session) -> SmtpConfig:
    from app.domain.settings.models import AppSetting

    setting = db.scalar(select(AppSetting).where(AppSetting.key == "email.smtp"))
    if not setting or not setting.value_json:
        return _get_env_smtp_config()
    try:
        parsed = json.loads(setting.value_json)
    except Exception:
        return _get_env_smtp_config()
    env = _get_env_smtp_config()
    return SmtpConfig(
        host=str(parsed.get("host") or env.host),
        port=int(parsed.get("port") or env.port),
        username=str(parsed.get("username") or env.username),
        password=str(parsed.get("password") or env.password),
        from_email=str(parsed.get("from_email") or env.from_email),
        from_name=str(parsed.get("from_name") or env.from_name),
        use_tls=bool(parsed.get("use_tls", env.use_tls)),
        resend_api_key=str(parsed.get("resend_api_key") or env.resend_api_key),
    )


def resolve_smtp_config(db: Session | None = None) -> SmtpConfig:
    env_host = (settings.smtp_host or "").strip()
    if env_host:
        return _get_env_smtp_config()
    if db is not None:
        return _get_db_smtp_config(db)
    return _get_env_smtp_config()


SMTP_TIMEOUT = 10

class ResendBackend:
    def __init__(self, smtp_cfg: SmtpConfig) -> None:
        self.cfg = smtp_cfg

    def send(self, message: EmailMessage) -> str | None:
        try:
            api_key = settings.resend_api_key or self.cfg.resend_api_key
            if not api_key:
                return "RESEND_API_KEY is not configured"
            body: dict[str, str | list[str]] = {
                "from": f"{self.cfg.from_name} <{self.cfg.from_email}>",
                "to": [message.to],
                "subject": message.subject,
                "text": message.text_body,
            }
            if message.html_body:
                body["html"] = message.html_body
            with httpx.Client(timeout=SMTP_TIMEOUT) as client:
                r = client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=body,
                )
                r.raise_for_status()
            logger.info("Email sent via Resend to %s", message.to)
            return None
        except Exception as e:
            logger.exception("Failed to send email via Resend to %s", message.to)
            return str(e)


class SMTPBackend:
    def __init__(self, cfg: SmtpConfig) -> None:
        self.cfg = cfg

    def send(self, message: EmailMessage) -> str | None:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = f"{self.cfg.from_name} <{self.cfg.from_email}>"
            msg["To"] = message.to
            msg.attach(MIMEText(message.text_body, "plain"))
            if message.html_body:
                msg.attach(MIMEText(message.html_body, "html"))

            if self.cfg.use_tls:
                server = smtplib.SMTP(self.cfg.host, self.cfg.port, timeout=SMTP_TIMEOUT)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.cfg.host, self.cfg.port, timeout=SMTP_TIMEOUT)

            if self.cfg.username and self.cfg.password:
                server.login(self.cfg.username, self.cfg.password)

            server.sendmail(self.cfg.from_email, [message.to], msg.as_string())
            server.quit()
            logger.info("Email sent via SMTP to %s", message.to)
            return None
        except Exception as e:
            logger.exception("Failed to send email via SMTP to %s", message.to)
            return str(e)


def _get_backend(cfg: SmtpConfig) -> EmailBackend:
    api_key = settings.resend_api_key or cfg.resend_api_key
    if api_key:
        return ResendBackend(cfg)
    if cfg.host:
        return SMTPBackend(cfg)
    raise RuntimeError(
        "No email backend configured. Set RESEND_API_KEY or provide an SMTP host."
    )


def send_email(message: EmailMessage, db: Session | None = None) -> str | None:
    cfg = resolve_smtp_config(db)
    try:
        backend = _get_backend(cfg)
    except RuntimeError as e:
        return str(e)
    return backend.send(message)
