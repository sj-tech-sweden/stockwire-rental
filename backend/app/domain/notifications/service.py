"""Notification dispatch service."""

from __future__ import annotations

import json
import logging
from typing import Any

from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.customers.models import Customer
from app.domain.notifications.models import (
    NotificationLog,
    NotificationTemplate,
    NotificationPreference,
    UserNotificationPreference,
)
from app.domain.auth.models import User

_jinja_env = SandboxedEnvironment()

logger = logging.getLogger(__name__)


def _render_template(value: str | None, context: dict[str, Any]) -> str:
    if not value:
        return ""
    try:
        return _jinja_env.from_string(value).render(**context)
    except Exception:
        logger.exception("Template render failed")
        return value or ""


def _resolve_template(
    db: Session,
    template_key: str,
    locale: str | None = None,
) -> NotificationTemplate | None:
    """Resolve the best matching template by key and locale.

    Priority:
    1. Customer/user preferred language
    2. Company standard language (from settings)
    3. English fallback
    4. Any available locale
    """
    if locale:
        # Try exact match for preferred language
        template = db.scalar(
            select(NotificationTemplate)
            .where(NotificationTemplate.template_key == template_key)
            .where(NotificationTemplate.locale == locale)
            .where(NotificationTemplate.is_enabled.is_(True))
        )
        if template:
            return template

    # Try English fallback
    if locale != "en":
        template = db.scalar(
            select(NotificationTemplate)
            .where(NotificationTemplate.template_key == template_key)
            .where(NotificationTemplate.locale == "en")
            .where(NotificationTemplate.is_enabled.is_(True))
        )
        if template:
            return template

    # Try any available locale (last resort)
    return db.scalar(
        select(NotificationTemplate)
        .where(NotificationTemplate.template_key == template_key)
        .where(NotificationTemplate.is_enabled.is_(True))
        .order_by(NotificationTemplate.locale)
        .limit(1)
    )


def _global_event_channels(db: Session, event_type: str | None) -> tuple[bool, bool]:
    """Return (email_enabled, web_push_enabled) from the global default preference."""
    if not event_type:
        return (True, True)
    pref = db.scalar(
        select(NotificationPreference)
        .where(NotificationPreference.event_type == event_type)
    )
    if pref is None:
        # Default: enabled if no preference record exists
        return (True, True)
    return (pref.email_enabled, pref.web_push_enabled)


def _resolve_event_channels(
    db: Session, user: User | None, event_type: str | None
) -> tuple[bool, bool]:
    """Return (email_enabled, web_push_enabled) for a recipient, applying their
    per-user override on top of the global default (falling back to global when unset)."""
    global_email, global_web = _global_event_channels(db, event_type)
    if user is None:
        return (global_email, global_web)
    up = db.scalar(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user.id,
            UserNotificationPreference.event_type == event_type,
        )
    )
    if up is None:
        return (global_email, global_web)
    return (up.email_enabled, up.web_push_enabled)


def _customer_locale(customer: Customer | None, db: Session) -> str:
    """Get the locale for a customer.

    Priority: customer preferred → company default → English
    """
    if customer and customer.preferred_language:
        return customer.preferred_language
    return _company_default_locale(db)


def _user_locale(user: User | None, db: Session) -> str:
    """Get the locale for a staff user.

    Priority: user preferred → company default → English
    """
    # Users don't have a preferred_language field yet, fall back to company default
    return _company_default_locale(db)


def _company_default_locale(db: Session) -> str:
    """Get the company default language from settings."""
    try:
        from app.domain.settings.models import AppSetting
        from sqlalchemy import select

        row = db.scalar(select(AppSetting).where(AppSetting.key == "company.profile"))
        if row and row.value_json:
            import json
            profile = json.loads(row.value_json) if isinstance(row.value_json, str) else row.value_json
            return profile.get("default_language", "en")
    except Exception:
        # Settings lookup is best-effort; fall back to English if anything fails.
        pass
    return "en"


def _customer_can_receive_email(customer: Customer | None, job: Any | None) -> bool:
    if customer is None or not customer.email:
        return False
    if not customer.email_notifications_enabled:
        return False
    if job is not None and not job.email_notifications_enabled:
        return False
    return True


def _create_log(
    db: Session,
    *,
    job_id: int | None,
    recipient_id: int,
    recipient_type: str,
    channel: str,
    template_key: str,
    locale: str | None,
    status: str,
    error_message: str | None = None,
) -> None:
    log = NotificationLog(
        job_id=job_id,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        channel=channel,
        template_key=template_key,
        locale=locale,
        status=status,
        error_message=error_message,
    )
    db.add(log)
    db.flush()


def send_notification(db: Session, payload: dict[str, Any]) -> None:
    """Dispatch a notification to a recipient via the appropriate channel(s).

    payload keys:
        template_key: str
        recipient_id: int
        recipient_type: "customer" | "staff"
        channel: "email" | "web_push" | "both"
        job_id: int | None
        context: dict[str, Any]
        event_type: str | None  -- for preference lookup
    """
    template_key = payload["template_key"]
    recipient_id = payload["recipient_id"]
    recipient_type = payload["recipient_type"]
    channel = payload["channel"]
    job_id = payload.get("job_id")
    context = payload.get("context", {})
    event_type = payload.get("event_type")

    job = None
    if job_id:
        from app.domain.jobs.models import Job

        job = db.get(Job, job_id)

    # Determine recipient + locale
    locale = None
    customer = None
    user = None
    if recipient_type == "customer":
        customer = db.get(Customer, recipient_id)
        locale = _customer_locale(customer, db)
    else:
        user = db.get(User, recipient_id)
        locale = _user_locale(user, db)

    # Resolve which channels are actually enabled for this recipient + event.
    # Priority: per-user override (staff) -> global default -> enabled.
    if recipient_type == "customer":
        pref_email, pref_web = _global_event_channels(db, event_type) if event_type else (True, True)
        coarse = "both"
    else:
        pref_email, pref_web = (
            _resolve_event_channels(db, user, event_type) if event_type else (True, True)
        )
        coarse = (getattr(user, "notification_channel", "both") or "both")

    def _coarse_allows(ch: str) -> bool:
        if coarse == "none":
            return False
        if coarse == "both":
            return True
        return coarse == ch

    # Intersect the requested channel with preferences + the coarse kill-switch
    requested = channel or "both"
    channels: list[str] = []
    if requested in ("email", "both") and pref_email and _coarse_allows("email"):
        channels.append("email")
    if requested in ("web_push", "both") and pref_web and _coarse_allows("web_push"):
        channels.append("web_push")
    if not channels:
        return

    template = _resolve_template(db, template_key, locale)
    if template and template.recipient_type not in ("both", recipient_type):
        _create_log(
            db, job_id=job_id, recipient_id=recipient_id,
            recipient_type=recipient_type, channel=channel or "both",
            template_key=template_key, locale=locale,
            status="skipped_by_preference",
            error_message=f"Template recipient_type '{template.recipient_type}' does not match '{recipient_type}'",
        )
        return
    for ch in channels:
        if ch == "email":
            if recipient_type == "customer":
                if not _customer_can_receive_email(customer, job):
                    _create_log(
                        db, job_id=job_id, recipient_id=recipient_id,
                        recipient_type=recipient_type, channel=ch,
                        template_key=template_key, locale=locale,
                        status="skipped_by_preference",
                    )
                    continue
                to_email = customer.email
            else:
                # user was fetched earlier for locale resolution
                to_email = user.email

            if not to_email:
                _create_log(
                    db, job_id=job_id, recipient_id=recipient_id,
                    recipient_type=recipient_type, channel=ch,
                    template_key=template_key, locale=locale,
                    status="failed", error_message="No email address",
                )
                continue

            subject = _render_template(template.subject_template if template else None, context)
            html = _render_template(template.html_template if template else None, context)
            text = _render_template(template.text_template if template else None, context)

            if not subject and not text:
                subject = template_key
                text = template_key

            from app.services.email import EmailMessage, send_email

            msg = EmailMessage(to=to_email, subject=subject or template_key, text_body=text or template_key, html_body=html or None)
            error = send_email(msg, db=db)
            if error:
                _create_log(
                    db, job_id=job_id, recipient_id=recipient_id,
                    recipient_type=recipient_type, channel=ch,
                    template_key=template_key, locale=locale,
                    status="failed", error_message=error,
                )
            else:
                _create_log(
                    db, job_id=job_id, recipient_id=recipient_id,
                    recipient_type=recipient_type, channel=ch,
                    template_key=template_key, locale=locale,
                    status="sent",
                )

        elif ch == "web_push":
            if recipient_type == "customer":
                _create_log(
                    db, job_id=job_id, recipient_id=recipient_id,
                    recipient_type=recipient_type, channel=ch,
                    template_key=template_key, locale=locale,
                    status="skipped_by_preference",
                )
                continue

            from app.domain.auth.models import PushSubscription
            from pywebpush import webpush, WebPushException

            subs = list(db.scalars(select(PushSubscription).where(PushSubscription.user_id == recipient_id)).all())
            if not subs or not settings.web_push_vapid_private_key:
                _create_log(
                    db, job_id=job_id, recipient_id=recipient_id,
                    recipient_type=recipient_type, channel=ch,
                    template_key=template_key, locale=locale,
                    status="skipped_by_preference",
                )
                continue

            text = _render_template(template.text_template if template else template_key, context)
            payload_data = {"title": template_key, "body": text}

            for sub in subs:
                try:
                    webpush(
                        subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh_key, "auth": sub.auth_key}},
                        data=json.dumps(payload_data),
                        vapid_private_key=settings.web_push_vapid_private_key,
                        vapid_claims={"sub": settings.web_push_vapid_subject},
                    )
                except (WebPushException, ValueError) as exc:
                    logger.warning("Web push failed for user %s: %s", recipient_id, exc)

            _create_log(
                db, job_id=job_id, recipient_id=recipient_id,
                recipient_type=recipient_type, channel=ch,
                template_key=template_key, locale=locale,
                status="sent",
            )

    db.flush()
