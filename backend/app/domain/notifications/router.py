from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_admin
from app.domain.auth.models import PushSubscription, User
from app.domain.notifications.models import NotificationLog, NotificationTemplate
from app.domain.notifications.schemas import (
    NotificationDispatchRequest,
    NotificationDispatchResponse,
    NotificationLogRead,
    NotificationTemplateCreate,
    NotificationTemplateRead,
    NotificationTemplateUpdate,
    PushSubscriptionCreate,
    PushSubscriptionRead,
    VapidPublicKeyRead,
)
from app.domain.notifications.service import send_notification

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/vapid-public-key", response_model=VapidPublicKeyRead)
def get_vapid_public_key() -> VapidPublicKeyRead:
    return VapidPublicKeyRead(public_key=settings.web_push_vapid_public_key)


@router.get("/subscriptions", response_model=list[PushSubscriptionRead])
def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PushSubscription]:
    return list(
        db.scalars(select(PushSubscription).where(PushSubscription.user_id == current_user.id)).all()
    )


@router.post("/subscriptions", response_model=PushSubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: PushSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PushSubscription:
    existing = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint))
    if existing:
        existing.user_id = current_user.id
        existing.p256dh_key = payload.keys.p256dh
        existing.auth_key = payload.keys.auth
        existing.user_agent = payload.user_agent
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    subscription = PushSubscription(
        user_id=current_user.id,
        endpoint=payload.endpoint,
        p256dh_key=payload.keys.p256dh,
        auth_key=payload.keys.auth,
        user_agent=payload.user_agent,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    subscription = db.get(PushSubscription, subscription_id)
    if subscription is None or subscription.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.delete(subscription)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/templates", response_model=list[NotificationTemplateRead])
def list_templates(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[NotificationTemplate]:
    return list(db.scalars(select(NotificationTemplate).order_by(NotificationTemplate.template_key)).all())


@router.post("/templates", response_model=NotificationTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: NotificationTemplateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> NotificationTemplate:
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
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, key, value)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/logs", response_model=list[NotificationLogRead])
def list_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    job_id: int | None = None,
) -> list[NotificationLog]:
    stmt = select(NotificationLog).order_by(NotificationLog.sent_at.desc())
    if job_id is not None:
        stmt = stmt.where(NotificationLog.job_id == job_id)
    return list(db.scalars(stmt).all())


@router.post("/dispatch", response_model=NotificationDispatchResponse)
def dispatch_notification(
    payload: NotificationDispatchRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> NotificationDispatchResponse:
    try:
        logs = send_notification(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return NotificationDispatchResponse(
        results=[NotificationLogRead.model_validate(log) for log in logs]
    )
