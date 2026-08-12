"""Notification management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_admin
from app.domain.auth.models import PushSubscription, User
from app.domain.notifications.models import (
    NotificationLog,
    NotificationPreference,
    NotificationTemplate,
    UserNotificationPreference,
)
from app.domain.notifications.seed import seed_notification_defaults
from app.domain.notifications.schemas import (
    NotificationDispatchRequest,
    NotificationLogRead,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    MyNotificationPreferenceRead,
    MyNotificationPreferenceUpdate,
    NotificationTemplateCreate,
    NotificationTemplateRead,
    NotificationTemplateUpdate,
    PushSubscriptionCreate,
)
from app.domain.notifications.service import send_notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ── Push Subscriptions ──────────────────────────────────────────────────────


@router.get("/vapid-public-key")
def vapid_public_key() -> dict[str, str]:
    from app.config import settings
    return {"public_key": settings.web_push_vapid_public_key}


@router.get("/subscriptions")
def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    subs = db.scalars(
        select(PushSubscription).where(PushSubscription.user_id == current_user.id)
    ).all()
    return [{"id": s.id, "endpoint": s.endpoint, "created_at": s.created_at.isoformat()} for s in subs]


@router.post("/subscriptions")
def create_subscription(
    payload: PushSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    existing = db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint)
    )
    if existing:
        existing.p256dh_key = payload.keys.p256dh
        existing.auth_key = payload.keys.auth
        existing.user_id = current_user.id
    else:
        sub = PushSubscription(
            user_id=current_user.id,
            endpoint=payload.endpoint,
            p256dh_key=payload.keys.p256dh,
            auth_key=payload.keys.auth,
        )
        db.add(sub)
    db.commit()
    return Response(
        content='{"ok": true}',
        status_code=status.HTTP_201_CREATED,
        media_type="application/json",
    )


@router.delete("/subscriptions/{subscription_id}")
def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    sub = db.get(PushSubscription, subscription_id)
    if not sub or sub.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.delete(sub)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Templates ───────────────────────────────────────────────────────────────


@router.get("/templates", response_model=list[NotificationTemplateRead])
def list_templates(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[NotificationTemplate]:
    return list(db.scalars(select(NotificationTemplate).order_by(NotificationTemplate.template_key, NotificationTemplate.locale)).all())


@router.post("/templates", response_model=NotificationTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(payload: NotificationTemplateCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> NotificationTemplate:
    existing = db.scalar(
        select(NotificationTemplate)
        .where(NotificationTemplate.template_key == payload.template_key)
        .where(NotificationTemplate.locale == payload.locale)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Template for this key and locale already exists")
    template = NotificationTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/templates/{template_id}", response_model=NotificationTemplateRead)
def update_template(
    template_id: int,
    payload: NotificationTemplateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> NotificationTemplate:
    template = db.get(NotificationTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Response:
    template = db.get(NotificationTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Preferences ─────────────────────────────────────────────────────────────


@router.get("/preferences", response_model=list[NotificationPreferenceRead])
def list_preferences(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[NotificationPreference]:
    return list(db.scalars(select(NotificationPreference).order_by(NotificationPreference.event_type)).all())


@router.put("/preferences/{preference_id}", response_model=NotificationPreferenceRead)
def update_preference(
    preference_id: int,
    payload: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> NotificationPreference:
    pref = db.get(NotificationPreference, preference_id)
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pref, field, value)
    db.commit()
    db.refresh(pref)
    return pref


# ── Per-user preferences (start from global defaults) ─────────────────────────


def _event_labels(db: Session) -> dict[str, tuple[str, str | None]]:
    """Map event_type -> (label, description) from the global preferences table."""
    labels: dict[str, tuple[str, str | None]] = {}
    for pref in db.scalars(select(NotificationPreference).order_by(NotificationPreference.event_type)).all():
        labels[pref.event_type] = (pref.label, pref.description)
    return labels


@router.get("/my-preferences", response_model=list[MyNotificationPreferenceRead])
def list_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MyNotificationPreferenceRead]:
    """List the current user's effective notification preferences.

    Values reflect the user's own override when set, otherwise the global default.
    """
    labels = _event_labels(db)
    overrides = {
        up.event_type: up
        for up in db.scalars(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == current_user.id
            )
        ).all()
    }
    # Ensure every globally-defined event type is represented.
    result: list[MyNotificationPreferenceRead] = []
    for event_type, (label, description) in labels.items():
        override = overrides.get(event_type)
        if override is not None:
            result.append(
                MyNotificationPreferenceRead(
                    event_type=event_type,
                    label=label,
                    description=description,
                    email_enabled=override.email_enabled,
                    web_push_enabled=override.web_push_enabled,
                    is_override=True,
                )
            )
        else:
            global_pref = db.scalar(
                select(NotificationPreference).where(NotificationPreference.event_type == event_type)
            )
            result.append(
                MyNotificationPreferenceRead(
                    event_type=event_type,
                    label=label,
                    description=description,
                    email_enabled=global_pref.email_enabled if global_pref else True,
                    web_push_enabled=global_pref.web_push_enabled if global_pref else True,
                    is_override=False,
                )
            )
    return result


@router.put("/my-preferences/{event_type}", response_model=MyNotificationPreferenceRead)
def update_my_preference(
    event_type: str,
    payload: MyNotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MyNotificationPreferenceRead:
    """Set (or update) the current user's override for a single event type."""
    override = db.scalar(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == current_user.id,
            UserNotificationPreference.event_type == event_type,
        )
    )
    if override is None:
        override = UserNotificationPreference(
            user_id=current_user.id,
            event_type=event_type,
            email_enabled=payload.email_enabled,
            web_push_enabled=payload.web_push_enabled,
        )
        db.add(override)
    else:
        override.email_enabled = payload.email_enabled
        override.web_push_enabled = payload.web_push_enabled
    db.commit()
    db.refresh(override)

    label_row = db.scalar(
        select(NotificationPreference).where(NotificationPreference.event_type == event_type)
    )
    return MyNotificationPreferenceRead(
        event_type=event_type,
        label=label_row.label if label_row else event_type,
        description=label_row.description if label_row else None,
        email_enabled=override.email_enabled,
        web_push_enabled=override.web_push_enabled,
        is_override=True,
    )


@router.delete("/my-preferences/{event_type}", status_code=status.HTTP_204_NO_CONTENT)
def reset_my_preference(
    event_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Remove the current user's override, reverting to the global default."""
    override = db.scalar(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == current_user.id,
            UserNotificationPreference.event_type == event_type,
        )
    )
    if override is not None:
        db.delete(override)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/seed-defaults")
def seed_defaults(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    """Load default notification templates and preferences."""
    result = seed_notification_defaults(db)
    return {"ok": True, **result}


@router.post("/test")
def test_notification(
    template_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Send a test notification to the current admin user over the staff channel.

    If template_id is provided, that template's key is used; otherwise the default
    job.created template is used.
    """
    recipient_type = "staff"
    channel = "both"
    template_key = "job.created"

    if template_id:
        template = db.get(NotificationTemplate, template_id)
        if template:
            template_key = template.template_key

    send_notification(db, {
        "template_key": template_key,
        "recipient_id": current_user.id,
        "recipient_type": recipient_type,
        "channel": channel,
        "context": {
            "job_code": "TEST-001",
            "customer_name": "Test Customer",
            "description": "This is a test notification",
            "start_date": "2026-08-15",
            "end_date": "2026-08-17",
            "device_name": "Test Device",
            "title": "Test Defect",
            "severity": "Medium",
            "maintenance_type": "Scheduled",
            "due_date": "2026-08-20",
        },
        "event_type": template_key,
    })
    db.commit()
    return {"ok": True, "message": f"Test notification sent using template: {template_key}"}


# ── Logs ────────────────────────────────────────────────────────────────────


@router.get("/logs", response_model=list[NotificationLogRead])
def list_logs(
    job_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[NotificationLog]:
    stmt = select(NotificationLog).order_by(NotificationLog.sent_at.desc())
    if job_id is not None:
        stmt = stmt.where(NotificationLog.job_id == job_id)
    return list(db.scalars(stmt.limit(200)).all())


# ── Dispatch ────────────────────────────────────────────────────────────────


@router.post("/dispatch")
def dispatch_notification(
    payload: NotificationDispatchRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    send_notification(db, payload.model_dump())
    db.commit()
    return {"ok": True}
