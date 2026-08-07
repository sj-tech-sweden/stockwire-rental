from __future__ import annotations

from datetime import datetime

from jinja2.sandbox import SandboxedEnvironment
from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.auth.models import PushSubscription, User
from app.domain.customers.models import Customer
from app.domain.jobs.models import Job
from app.domain.notifications.models import NotificationLog, NotificationTemplate
from app.domain.notifications.schemas import NotificationDispatchRequest
from app.services.email import EmailMessage, send_email


_SANDBOXED_ENV = SandboxedEnvironment()


def _render_template(value: str | None, context: dict) -> str:
    if not value:
        return ""
    return _SANDBOXED_ENV.from_string(value).render(**context)


def _create_log(
    db: Session,
    *,
    job_id: int | None,
    recipient_id: int,
    recipient_type: str,
    channel: str,
    template_key: str,
    status: str,
    error_message: str | None = None,
) -> NotificationLog:
    log = NotificationLog(
        job_id=job_id,
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        channel=channel,
        template_key=template_key,
        status=status,
        error_message=error_message,
        sent_at=datetime.utcnow(),
    )
    db.add(log)
    db.flush()
    return log


def _customer_can_receive_email(customer: Customer | None, job: Job | None) -> bool:
    return bool(
        customer
        and customer.email
        and customer.email_notifications_enabled
        and (job is None or job.email_notifications_enabled)
    )


def _user_allows_channel(user: User, channel: str) -> bool:
    preference = str(user.notification_channel or "both")
    if preference == "both":
        return channel in {"email", "web_push"}
    if preference == "none":
        return False
    return preference == channel


def send_notification(db: Session, payload: NotificationDispatchRequest) -> list[NotificationLog]:
    template = db.scalar(
        select(NotificationTemplate).where(NotificationTemplate.template_key == payload.template_key)
    )
    context = dict(payload.context or {})
    channels = ["email", "web_push"] if payload.channel == "both" else [payload.channel]
    logs: list[NotificationLog] = []
    job = db.get(Job, payload.job_id) if payload.job_id is not None else None

    if payload.recipient_type == "customer":
        customer = db.get(Customer, payload.recipient_id)
        if customer is None:
            raise ValueError("Customer not found")
        for channel in channels:
            if channel != "email" or not _customer_can_receive_email(customer, job):
                logs.append(
                    _create_log(
                        db,
                        job_id=payload.job_id,
                        recipient_id=payload.recipient_id,
                        recipient_type="customer",
                        channel="email",
                        template_key=payload.template_key,
                        status="skipped_by_preference",
                    )
                )
                continue
            error = send_email(
                EmailMessage(
                    to=customer.email,
                    subject=_render_template(template.subject_template if template else payload.template_key, context),
                    text_body=_render_template(template.text_template if template else payload.template_key, context),
                    html_body=_render_template(template.html_template if template else None, context) or None,
                ),
                db=db,
            )
            logs.append(
                _create_log(
                    db,
                    job_id=payload.job_id,
                    recipient_id=payload.recipient_id,
                    recipient_type="customer",
                    channel="email",
                    template_key=payload.template_key,
                    status="failed" if error else "sent",
                    error_message=error,
                )
            )
        db.commit()
        return logs

    user = db.get(User, payload.recipient_id)
    if user is None:
        raise ValueError("User not found")

    for channel in channels:
        if not _user_allows_channel(user, channel):
            logs.append(
                _create_log(
                    db,
                    job_id=payload.job_id,
                    recipient_id=payload.recipient_id,
                    recipient_type="staff",
                    channel=channel,
                    template_key=payload.template_key,
                    status="skipped_by_preference",
                )
            )
            continue
        if channel == "email":
            error = send_email(
                EmailMessage(
                    to=user.email,
                    subject=_render_template(template.subject_template if template else payload.template_key, context),
                    text_body=_render_template(template.text_template if template else payload.template_key, context),
                    html_body=_render_template(template.html_template if template else None, context) or None,
                ),
                db=db,
            )
            logs.append(
                _create_log(
                    db,
                    job_id=payload.job_id,
                    recipient_id=payload.recipient_id,
                    recipient_type="staff",
                    channel="email",
                    template_key=payload.template_key,
                    status="failed" if error else "sent",
                    error_message=error,
                )
            )
            continue

        subscriptions = list(
            db.scalars(select(PushSubscription).where(PushSubscription.user_id == user.id)).all()
        )
        if not subscriptions or not settings.web_push_vapid_private_key:
            logs.append(
                _create_log(
                    db,
                    job_id=payload.job_id,
                    recipient_id=payload.recipient_id,
                    recipient_type="staff",
                    channel="web_push",
                    template_key=payload.template_key,
                    status="skipped_by_preference",
                )
            )
            continue
        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh_key, "auth": subscription.auth_key},
                    },
                    data=_render_template(template.text_template if template else payload.template_key, context),
                    vapid_private_key=settings.web_push_vapid_private_key,
                    vapid_claims={"sub": settings.web_push_vapid_subject},
                )
                logs.append(
                    _create_log(
                        db,
                        job_id=payload.job_id,
                        recipient_id=payload.recipient_id,
                        recipient_type="staff",
                        channel="web_push",
                        template_key=payload.template_key,
                        status="sent",
                    )
                )
            except (WebPushException, ValueError) as exc:
                logs.append(
                    _create_log(
                        db,
                        job_id=payload.job_id,
                        recipient_id=payload.recipient_id,
                        recipient_type="staff",
                        channel="web_push",
                        template_key=payload.template_key,
                        status="failed",
                        error_message=str(exc),
                    )
                )
    db.commit()
    return logs
