"""Twenty CRM webhook endpoint for inbound events."""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.integrations.models import TwentyConfig
from app.domain.integrations.sync_engine import (
    _log_sync,
    sync_customer_inbound,
    sync_customer_outbound,
    sync_job_inbound,
)
from app.domain.integrations.twenty_client import TwentyClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations/twenty", tags=["integrations"])


class TwentyWebhookPayload(BaseModel):
    """Payload from Twenty CRM webhook.

    Twenty sends the event name in `eventName` and the changed record in
    `record`. The legacy `type`/`object`/`data` shapes are kept as fallbacks.
    """

    type: str | None = None  # legacy shape
    eventName: str | None = None  # current Twenty shape, e.g. "company.updated"
    object: dict[str, Any] | None = None  # legacy shape
    data: dict[str, Any] | None = None  # legacy shape
    record: dict[str, Any] | None = None  # current Twenty shape
    objectMetadata: dict[str, Any] | None = None  # validation/test ping shape
    targetUrl: str | None = None  # validation/test ping shape
    workspaceId: str | None = None  # validation/test ping shape


def _verify_webhook_signature(payload: bytes, signature: str | None, secret: str, headers: dict[str, str] | None = None) -> bool:
    """Verify webhook signature using Twenty's documented format.

    Twenty signs: HMAC-SHA256(secret, timestamp + ":" + JSON.stringify(body))
    See: https://docs.twenty.com/developers/extend/webhooks#validation-steps
    """
    if not signature or not secret:
        return False

    # Strip any prefix like "sha256=" or "v0="
    clean_sig = signature
    for prefix in ("sha256=", "v1=", "v0="):
        if clean_sig.startswith(prefix):
            clean_sig = clean_sig[len(prefix):]

    ts = (headers or {}).get("x-twenty-webhook-timestamp")

    # Re-serialize the body as compact JSON (same as JSON.stringify in JS)
    try:
        import json as _json
        body_json = _json.loads(payload)
        compact_body = _json.dumps(body_json, separators=(",", ":"), ensure_ascii=False).encode()
    except (ValueError, TypeError):
        compact_body = payload

    # Try both raw secret string and hex-decoded bytes
    secret_bytes_variants = [secret.encode()]
    try:
        secret_bytes_variants.append(bytes.fromhex(secret))
    except ValueError:
        pass  # Not a hex string, use raw bytes only

    for secret_bytes in secret_bytes_variants:
        # Twenty's documented format: timestamp:JSON payload
        if ts:
            string_to_sign = (ts + ":").encode() + compact_body
            expected = hmac.new(secret_bytes, string_to_sign, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, clean_sig):
                logger.warning("Webhook signature matched: HMAC(timestamp:compact_json)")
                return True

            # Also try with original body bytes (some versions may not re-serialize)
            string_to_sign_orig = (ts + ":").encode() + payload
            expected = hmac.new(secret_bytes, string_to_sign_orig, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, clean_sig):
                logger.warning("Webhook signature matched: HMAC(timestamp:raw_body)")
                return True

            # Try with pretty-printed JSON
            try:
                pretty_body = _json.dumps(body_json, ensure_ascii=False).encode()
                string_to_sign_pretty = (ts + ":").encode() + pretty_body
                expected = hmac.new(secret_bytes, string_to_sign_pretty, hashlib.sha256).hexdigest()
                if hmac.compare_digest(expected, clean_sig):
                    logger.warning("Webhook signature matched: HMAC(timestamp:pretty_json)")
                    return True
            except (TypeError, ValueError):
                pass  # pretty-print failed, skip this variant

        # Fallback: plain body (no timestamp prefix)
        expected = hmac.new(secret_bytes, payload, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, clean_sig):
            logger.warning("Webhook signature matched: HMAC(body) plain")
            return True

    logger.warning(
        "No signature format matched. signature=%s secret_length=%d ts=%s compact_len=%d",
        _mask_signature(signature), len(secret), ts, len(compact_body),
    )
    return False


def _get_config(db: Session) -> TwentyConfig | None:
    return db.query(TwentyConfig).filter(TwentyConfig.is_active.is_(True)).first()


def _mask_signature(signature: str | None) -> str:
    if not signature:
        return "(none)"
    if len(signature) <= 8:
        return signature
    return f"{signature[:4]}...{signature[-4:]}"


@router.post("/webhook")
async def twenty_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Handle inbound webhooks from Twenty CRM.

    Verifies the webhook signature against the configured secret, then processes
    the event using the data already present in the webhook payload. No extra
    API calls to Twenty are needed for the actual sync.
    """
    config = _get_config(db)
    if not config:
        logger.warning("Twenty webhook rejected: integration not configured")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Twenty integration not configured")

    body = await request.body()
    signature_header_names = ["x-twenty-signature", "x-webhook-signature", "x-twenty-webhook-signature", "x-hub-signature-256", "x-signature"]
    signature = None
    for name in signature_header_names:
        signature = request.headers.get(name)
        if signature:
            break
    webhook_secret = config.webhook_secret or ""

    logger.debug(
        "Twenty webhook request received: content-length=%d signature-header=%s configured_secret=%s header_names=%s",
        len(body),
        _mask_signature(signature),
        "yes" if webhook_secret else "no",
        list(request.headers.keys()),
    )

    try:
        payload = TwentyWebhookPayload.model_validate_json(body)
    except Exception as exc:
        logger.error("Invalid webhook payload: %s preview=%s", exc, body[:500].decode("utf-8", errors="replace"))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")

    event_type = payload.eventName or payload.type
    record = payload.record or payload.object or payload.data or {}
    payload_keys = list(payload.model_dump(exclude_none=True).keys())

    logger.debug(
        "Twenty webhook parsed: event=%s record_present=%s record_keys=%s payload_keys=%s",
        event_type,
        bool(payload.record or payload.object or payload.data),
        list(record.keys()) if record else [],
        payload_keys,
    )

    # Twenty sends unsigned validation/test pings (e.g. on webhook creation)
    # that contain targetUrl/objectMetadata but no record. Accept those
    # without signature verification.
    has_event_metadata = bool(payload.objectMetadata or payload.targetUrl)
    is_validation_ping = not record and has_event_metadata
    if is_validation_ping:
        logger.warning("Twenty webhook validation ping accepted: event=%s", event_type)
        return {"status": "ok"}

    if not event_type:
        logger.warning("Twenty webhook missing event name: payload keys=%s", payload_keys)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing event name")

    if webhook_secret and signature and not _verify_webhook_signature(body, signature, webhook_secret, dict(request.headers)):
        logger.warning(
            "Twenty webhook signature verification failed: header=%s ts=%s nonce=%s body_preview=%s",
            _mask_signature(signature),
            request.headers.get("x-twenty-webhook-timestamp"),
            request.headers.get("x-twenty-webhook-nonce"),
            body[:200].decode("utf-8", errors="replace"),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature")

    record_id = record.get("id")
    logger.debug(
        "Twenty webhook processing: event=%s record_id=%s record_keys=%s",
        event_type,
        record_id,
        list(record.keys()),
    )

    client = TwentyClient(api_key=config.api_key, base_url=config.base_url)

    try:
        if event_type in ("company.created", "company.updated"):
            await _handle_company_event(db, client, event_type, record)
        elif event_type in ("person.created", "person.updated"):
            await _handle_person_event(db, client, event_type, record)
        elif event_type in ("opportunity.created", "opportunity.updated"):
            await _handle_opportunity_event(db, client, event_type, record)
        else:
            logger.warning("Unhandled Twenty webhook event: %s", event_type)
    except Exception as exc:
        logger.exception("Error processing Twenty webhook %s for record %s", event_type, record_id)
        entity_type = event_type.split(".")[0] if "." in event_type else "unknown"
        _log_sync(db, "inbound", entity_type, None, record_id, "webhook", "failed", str(exc))
        db.commit()
        # Return 200 so Twenty does not retry and hammer the endpoint.
        # The failure is visible in the sync logs and application logs.
        return {"status": "error", "detail": "An internal error occurred while processing the webhook."}

    db.commit()
    return {"status": "ok"}


async def _handle_company_event(
    db: Session,
    client: TwentyClient,
    event_type: str,
    record: dict[str, Any],
) -> None:
    """Sync a Twenty company to a Stockwire customer using the webhook record."""
    from app.domain.realtime.events import emit_realtime_event

    twenty_id = record.get("id")
    if not twenty_id:
        logger.warning("Twenty company webhook missing record id")
        return

    logger.warning("Syncing Twenty company %s to Stockwire (event=%s)", twenty_id, event_type)
    created = await sync_customer_inbound(db, client, record, twenty_person=None)

    if created:
        logger.warning("Twenty company %s CREATED in Stockwire; writing back stockwire fields", twenty_id)
        from app.domain.customers.models import Customer

        customer = db.query(Customer).filter(
            Customer.external_source == "twenty",
            Customer.external_reference == str(twenty_id),
        ).first()
        if customer:
            await sync_customer_outbound(db, client, customer, force=True)
            emit_realtime_event("customers.updated", {"action": "created", "id": customer.id})
    else:
        logger.warning("Twenty company %s UPDATED in Stockwire", twenty_id)
        from app.domain.customers.models import Customer

        customer = db.query(Customer).filter(
            Customer.external_source == "twenty",
            Customer.external_reference == str(twenty_id),
        ).first()
        if customer:
            emit_realtime_event("customers.updated", {"action": "updated", "id": customer.id})


async def _handle_person_event(
    db: Session,
    client: TwentyClient,
    event_type: str,
    record: dict[str, Any],
) -> None:
    """Sync a Twenty person to the linked Stockwire customer's email/phone."""
    from app.domain.realtime.events import emit_realtime_event

    person_id = record.get("id")
    company_id = record.get("companyId")
    if not company_id:
        logger.warning("Twenty person %s has no companyId; ignoring", person_id)
        return

    from app.domain.customers.models import Customer

    customer = db.query(Customer).filter(
        Customer.external_source == "twenty",
        Customer.external_reference == str(company_id),
    ).first()
    if not customer:
        logger.warning("No Stockwire customer linked to Twenty company %s", company_id)
        return

    name_obj = record.get("name") or {}
    full_name = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
    if full_name:
        customer.name = full_name

    emails = record.get("emails") or {}
    if isinstance(emails, dict) and emails.get("primaryEmail"):
        customer.email = emails["primaryEmail"]

    phones = record.get("phones") or {}
    if isinstance(phones, dict) and phones.get("primaryPhoneNumber"):
        customer.phone = phones["primaryPhoneNumber"]

    db.commit()
    logger.warning("Synced Twenty person %s to Stockwire customer %s", person_id, customer.id)
    emit_realtime_event("customers.updated", {"action": "updated", "id": customer.id})


async def _handle_opportunity_event(
    db: Session,
    client: TwentyClient,
    event_type: str,
    record: dict[str, Any],
) -> None:
    """Sync a Twenty opportunity to a Stockwire job using the webhook record."""
    from app.domain.realtime.events import emit_realtime_event

    opp_id = record.get("id")
    if not opp_id:
        logger.warning("Twenty opportunity webhook missing record id")
        return

    logger.warning("Syncing Twenty opportunity %s to Stockwire (event=%s)", opp_id, event_type)
    updated = await sync_job_inbound(db, client, record)
    if updated:
        logger.warning("Twenty opportunity %s UPDATED in Stockwire", opp_id)
        from app.domain.jobs.models import Job

        job = db.query(Job).filter(
            Job.external_source == "twenty",
            Job.external_reference == opp_id,
        ).first()
        if job:
            emit_realtime_event("jobs.updated", {"action": "updated", "id": job.id})
    else:
        logger.warning("Twenty opportunity %s ignored: no matching Stockwire job", opp_id)
