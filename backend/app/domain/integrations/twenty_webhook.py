"""Twenty CRM webhook endpoint for inbound events."""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.domain.integrations.models import TwentyConfig, TwentySyncLog
from app.domain.integrations.twenty_client import TwentyClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations/twenty", tags=["integrations"])


class TwentyWebhookPayload(BaseModel):
    """Payload from Twenty CRM webhook."""
    type: str  # e.g. "company.created", "company.updated", "opportunity.updated"
    object: dict[str, Any] | None = None
    data: dict[str, Any] | None = None


def _verify_webhook_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    """Verify HMAC-SHA256 webhook signature."""
    if not signature or not secret:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _get_config(db: Session) -> TwentyConfig | None:
    return db.query(TwentyConfig).filter(TwentyConfig.is_active.is_(True)).first()


@router.post("/webhook")
async def twenty_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Handle inbound webhooks from Twenty CRM.

    Verifies the webhook signature against the configured secret,
    then processes the event (company sync, opportunity → job creation, etc.).
    """
    config = _get_config(db)
    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Twenty integration not configured")

    body = await request.body()
    signature = request.headers.get("x-twenty-signature") or request.headers.get("x-webhook-signature")

    webhook_secret = settings.twenty_webhook_secret
    if webhook_secret and not _verify_webhook_signature(body, signature, webhook_secret):
        logger.warning("Twenty webhook signature verification failed")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature")

    try:
        payload = TwentyWebhookPayload.model_validate_json(body)
    except Exception as exc:
        logger.error("Invalid webhook payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")

    event_type = payload.type
    logger.info("Twenty webhook received: %s", event_type)

    try:
        if event_type in ("company.created", "company.updated"):
            _handle_company_event(db, config, payload)
        elif event_type == "opportunity.updated":
            _handle_opportunity_event(db, config, payload)
        else:
            logger.info("Unhandled Twenty webhook event: %s", event_type)
    except Exception as exc:
        logger.exception("Error processing Twenty webhook %s", event_type)
        _log_sync(db, "inbound", event_type.split(".")[0], None, None, "webhook", "failed", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook processing failed")

    db.commit()
    return {"status": "ok"}


def _handle_company_event(db: Session, config: TwentyConfig, payload: TwentyWebhookPayload) -> None:
    """Sync a Twenty company to a Stockwire customer."""
    obj = payload.object or payload.data or {}
    twenty_id = obj.get("id")
    if not twenty_id:
        return

    name = obj.get("name") or "Untitled Company"
    email = None
    if obj.get("emails"):
        email = obj["emails"].get("primaryEmail")

    existing = db.query(Customer).filter(
        Customer.external_source == "twenty",
        Customer.external_reference == str(twenty_id),
    ).first()

    if existing:
        existing.name = name
        if email:
            existing.email = email
        _log_sync(db, "inbound", "customer", existing.id, str(twenty_id), "update", "success")
    else:
        customer = Customer(
            name=name,
            email=email,
            external_source="twenty",
            external_reference=str(twenty_id),
        )
        db.add(customer)
        db.flush()
        _log_sync(db, "inbound", "customer", customer.id, str(twenty_id), "create", "success")


def _handle_opportunity_event(db: Session, config: TwentyConfig, payload: TwentyWebhookPayload) -> None:
    """When an opportunity is CLOSED_WON, auto-create a draft job in Stockwire."""
    obj = payload.object or payload.data or {}
    stage = obj.get("stage", "").upper()
    twenty_opp_id = obj.get("id")
    if not twenty_opp_id or stage != "CLOSED_WON":
        return

    # Check if a job already exists for this opportunity
    existing = db.query(Job).filter(
        Job.external_source == "twenty",
        Job.external_reference == str(twenty_opp_id),
    ).first()
    if existing:
        _log_sync(db, "inbound", "job", existing.id, str(twenty_opp_id), "update", "success")
        return

    # Resolve customer from the opportunity's company
    company_id = obj.get("companyId")
    customer = None
    if company_id:
        customer = db.query(Customer).filter(
            Customer.external_source == "twenty",
            Customer.external_reference == str(company_id),
        ).first()

    opp_name = obj.get("name") or "Twenty Opportunity"
    job = Job(
        job_code=f"TWENTY-{str(twenty_opp_id)[:8]}",
        customer_id=customer.id if customer else None,
        customer_name=customer.name if customer else opp_name,
        description=opp_name,
        status="draft",
        external_source="twenty",
        external_reference=str(twenty_opp_id),
    )
    db.add(job)
    db.flush()
    _log_sync(db, "inbound", "job", job.id, str(twenty_opp_id), "create", "success")


def _log_sync(
    db: Session,
    direction: str,
    entity_type: str,
    entity_id: int | None,
    twenty_id: str | None,
    operation: str,
    status_val: str,
    error_message: str | None = None,
) -> None:
    log = TwentySyncLog(
        direction=direction,
        entity_type=entity_type,
        entity_id=entity_id,
        twenty_id=twenty_id,
        operation=operation,
        status=status_val,
        error_message=error_message,
    )
    db.add(log)
