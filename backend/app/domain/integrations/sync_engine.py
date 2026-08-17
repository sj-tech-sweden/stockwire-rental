import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.customers.models import Customer
from app.domain.integrations.models import TwentySyncLog
from app.domain.integrations.twenty_client import TwentyClient
from app.domain.jobs.models import Job

logger = logging.getLogger(__name__)

STAGE_MAP = {
    "draft": "NEW",
    "confirmed": "SCREENING",
    "in_progress": "MEETING",
    "completed": "CUSTOMER",
    "cancelled": "NEW",
}

SYNC_PAGE_SIZE = 50

# Fields that are custom-added via schema provisioning; may not exist on older records
_STOCKWIRE_FIELDS = {
    "stockwire_url", "stockwire_id", "stockwire_notes", "phone_secondary",
    "stockwire_job_code", "stockwire_start_date", "stockwire_end_date", "stockwire_status",
}


async def _safe_update(client: TwentyClient, object_name: str, record_id: str, data: dict) -> None:
    """Update a record, stripping fields that don't exist on the target object."""
    try:
        await client.update_object(object_name, record_id, data)
    except Exception as exc:
        err_str = str(exc)
        # If a field is missing, strip stockwire_* fields and retry
        if "doesn't have any" in err_str or "400" in err_str:
            stripped = {k: v for k, v in data.items() if k not in _STOCKWIRE_FIELDS}
            if stripped != data:
                try:
                    await client.update_object(object_name, record_id, stripped)
                    return
                except Exception:
                    pass
        raise


def _extract_twenty_id(response: dict, object_name: str) -> str | None:
    data = response.get("data", {})
    create_map = {
        "companies": "createCompany",
        "people": "createPerson",
        "opportunities": "createOpportunity",
    }
    wrapper = data.get(create_map.get(object_name, ""), {})
    return wrapper.get("id")


def _reverse_stage_map() -> dict[str, str]:
    return {v: k for k, v in STAGE_MAP.items()}


def _log_sync(
    db: Session,
    direction: str,
    entity_type: str,
    entity_id: int | None,
    twenty_id: str | None,
    operation: str,
    status: str,
    error_message: str | None = None,
    payload: str | None = None,
) -> None:
    log = TwentySyncLog(
        direction=direction,
        entity_type=entity_type,
        entity_id=entity_id,
        twenty_id=twenty_id,
        operation=operation,
        status=status,
        error_message=error_message,
        payload=payload,
    )
    db.add(log)


def _customer_to_company_payload(customer: Customer) -> dict:
    from app.config import settings

    payload: dict = {"name": customer.name or ""}
    if customer.address or customer.city or customer.postal_code or customer.country:
        payload["address"] = {
            "addressStreet1": customer.address or "",
            "addressCity": customer.city or "",
            "addressPostcode": customer.postal_code or "",
            "addressCountry": customer.country or "",
        }
    if customer.notes:
        payload["stockwire_notes"] = customer.notes
    if customer.id:
        payload["stockwire_id"] = customer.id
    frontend = settings.effective_frontend_base_url
    if frontend and customer.id:
        payload["stockwire_url"] = f"{frontend}/customer/{customer.id}"
    return payload


def _sanitize_phone(phone: str) -> str:
    """Return phone in E.164 format that Twenty CRM accepts."""
    # Strip dashes, spaces, parentheses, and leading/trailing whitespace
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+").strip()
    if not cleaned:
        return ""
    # Already E.164
    if cleaned.startswith("+"):
        return cleaned
    # 00 prefix → +
    if cleaned.startswith("00"):
        return "+" + cleaned[2:]
    # Swedish mobile/landline: 10 digits starting with 0 → +46
    if len(cleaned) == 10 and cleaned.startswith("0"):
        return "+46" + cleaned[1:]
    # Return cleaned version as fallback (may still fail validation)
    return cleaned


def _customer_to_person_payload(customer: Customer) -> dict:
    parts = (customer.name or "").strip().split(None, 1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""
    payload: dict = {}
    if first_name or last_name:
        payload["name"] = {"firstName": first_name, "lastName": last_name}
    if customer.email:
        payload["emails"] = {"primaryEmail": customer.email}
    if customer.phone:
        payload["phones"] = {"primaryPhoneNumber": _sanitize_phone(customer.phone)}
    if customer.id:
        payload["stockwire_id"] = customer.id
    return payload


def _job_to_opportunity_payload(job: Job) -> dict:
    payload: dict = {
        "name": f"{job.job_code} - {job.customer_name or ''}".strip(" -"),
        "stage": STAGE_MAP.get(job.status, "SCREENING"),
    }
    if job.sales_price:
        micros = int(round(float(job.sales_price) * 1_000_000))
        payload["amount"] = {"amountMicros": micros}
    if job.end_date:
        payload["closeDate"] = job.end_date.isoformat()
    if job.job_code:
        payload["stockwire_job_code"] = job.job_code
    if job.start_date:
        payload["stockwire_start_date"] = job.start_date.isoformat()
    if job.end_date:
        payload["stockwire_end_date"] = job.end_date.isoformat()
    payload["stockwire_status"] = job.status or ""
    if job.id:
        payload["stockwire_id"] = job.id
    if job.description:
        payload["description"] = job.description
    return payload


async def _find_existing_person(client: TwentyClient, company_id: str, email: str | None) -> str | None:
    if not email:
        return None
    try:
        people = await client.search_people(email=email)
        for person_edge in people:
            person = person_edge.get("node", person_edge)
            company_rel = person.get("company") or {}
            if company_rel.get("id") == company_id:
                return person.get("id")
    except Exception:
        logger.debug("Could not search for existing person with email %s", email)
    return None


async def sync_customer_outbound(db: Session, client: TwentyClient, customer: Customer) -> None:
    try:
        company_data = _customer_to_company_payload(customer)
        person_data = _customer_to_person_payload(customer)

        twenty_company_id = None

        if customer.external_source == "twenty" and customer.external_reference:
            twenty_company_id = customer.external_reference
            await _safe_update(client, "companies", twenty_company_id, company_data)
            _log_sync(db, "outbound", "customer", customer.id, twenty_company_id, "update", "success")
        else:
            result = await client.create_object("companies", company_data)
            twenty_company_id = _extract_twenty_id(result, "companies")
            customer.external_source = "twenty"
            customer.external_reference = twenty_company_id
            _log_sync(db, "outbound", "customer", customer.id, twenty_company_id, "create", "success")

        if twenty_company_id and person_data.get("name"):
            person_data["companyId"] = twenty_company_id
            existing_person_id = await _find_existing_person(client, twenty_company_id, customer.email)
            if existing_person_id:
                await client.update_object("people", existing_person_id, person_data)
            else:
                try:
                    result = await client.create_object("people", person_data)
                    _extract_twenty_id(result, "people")
                except Exception as create_err:
                    err_str = str(create_err).lower()
                    if "duplicate" in err_str or "400" in err_str or "invalid_phone" in err_str or "phone" in err_str:
                        logger.debug("Person may already exist or has invalid data for customer %s, skipping create: %s", customer.id, create_err)
                    else:
                        raise

        db.commit()
    except Exception as e:
        logger.exception("Failed to sync customer %s to Twenty", customer.id)
        _log_sync(db, "outbound", "customer", customer.id, None, "update", "failed", str(e))
        db.commit()
        raise


async def sync_job_outbound(db: Session, client: TwentyClient, job: Job) -> None:
    try:
        opp_data = _job_to_opportunity_payload(job)

        if job.customer_id:
            customer = db.query(Customer).filter(Customer.id == job.customer_id).first()
            if customer and customer.external_source == "twenty" and customer.external_reference:
                opp_data["companyId"] = customer.external_reference

        twenty_opp_id = None

        if job.external_source == "twenty" and job.external_reference:
            twenty_opp_id = job.external_reference
            await _safe_update(client, "opportunities", twenty_opp_id, opp_data)
            _log_sync(db, "outbound", "job", job.id, twenty_opp_id, "update", "success")
        else:
            result = await client.create_object("opportunities", opp_data)
            twenty_opp_id = _extract_twenty_id(result, "opportunities")
            job.external_source = "twenty"
            job.external_reference = twenty_opp_id
            _log_sync(db, "outbound", "job", job.id, twenty_opp_id, "create", "success")

        db.commit()
    except Exception as e:
        logger.exception("Failed to sync job %s to Twenty", job.id)
        _log_sync(db, "outbound", "job", job.id, None, "update", "failed", str(e))
        db.commit()
        raise


async def sync_customer_inbound(db: Session, client: TwentyClient, twenty_company: dict, twenty_person: dict | None = None) -> None:
    company_id = twenty_company.get("id")
    company_name = twenty_company.get("name", "")

    existing = db.query(Customer).filter(
        Customer.external_source == "twenty",
        Customer.external_reference == company_id,
    ).first()

    person = twenty_person or {}
    name_obj = person.get("name") or {}
    email = None
    phone = None
    emails_data = person.get("emails") or {}
    if isinstance(emails_data, dict):
        email = emails_data.get("primaryEmail")
    phones_data = person.get("phones") or {}
    if isinstance(phones_data, dict):
        phone = phones_data.get("primaryPhoneNumber")

    address_data = twenty_company.get("address") or {}
    if isinstance(address_data, dict):
        address = address_data.get("addressStreet1") or ""
        city = address_data.get("addressCity") or ""
        postal_code = address_data.get("addressPostcode") or ""
        country = address_data.get("addressCountry") or ""
    else:
        address = str(address_data) if address_data else ""
        city = twenty_company.get("city") or ""
        postal_code = twenty_company.get("postalCode") or ""
        country = twenty_company.get("country") or ""

    if existing:
        if name_obj.get("firstName") or name_obj.get("lastName"):
            full_name = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
            if full_name:
                existing.name = full_name
        if email:
            existing.email = email
        if phone:
            existing.phone = phone
        if address:
            existing.address = address
        if city:
            existing.city = city
        if postal_code:
            existing.postal_code = postal_code
        if country:
            existing.country = country
        sw_notes = twenty_company.get("stockwire_notes") or twenty_company.get("notes")
        if sw_notes:
            existing.notes = sw_notes
        _log_sync(db, "inbound", "customer", existing.id, company_id, "update", "success")
    else:
        full_name = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
        sw_notes = twenty_company.get("stockwire_notes") or twenty_company.get("notes")
        new_customer = Customer(
            name=company_name or full_name or None,
            email=email,
            phone=phone,
            address=address or None,
            city=city or None,
            postal_code=postal_code or None,
            country=country or None,
            notes=sw_notes,
            external_source="twenty",
            external_reference=company_id,
        )
        db.add(new_customer)
        db.flush()
        _log_sync(db, "inbound", "customer", new_customer.id, company_id, "create", "success")

    db.commit()


async def sync_job_inbound(db: Session, client: TwentyClient, twenty_opp: dict) -> None:
    opp_id = twenty_opp.get("id")
    opp_name = twenty_opp.get("name", "")

    existing = db.query(Job).filter(
        Job.external_source == "twenty",
        Job.external_reference == opp_id,
    ).first()

    reverse_stages = _reverse_stage_map()
    stage = twenty_opp.get("stage", "SCREENING")
    stockwire_status = reverse_stages.get(stage, "draft")

    raw_amount = twenty_opp.get("amount")
    if isinstance(raw_amount, dict):
        amount_micros = raw_amount.get("amountMicros")
        amount = float(amount_micros) / 1_000_000 if amount_micros else 0
    elif raw_amount:
        amount = float(raw_amount)
    else:
        amount = 0

    if existing:
        existing.customer_name = opp_name or existing.customer_name
        existing.status = stockwire_status
        if amount:
            existing.sales_price = amount
        if twenty_opp.get("closeDate"):
            existing.end_date = datetime.fromisoformat(twenty_opp["closeDate"]).date()
        if twenty_opp.get("stockwire_start_date"):
            existing.start_date = datetime.fromisoformat(twenty_opp["stockwire_start_date"]).date()
        if twenty_opp.get("stockwire_job_code") and not existing.job_code:
            existing.job_code = twenty_opp["stockwire_job_code"]
        if twenty_opp.get("description"):
            existing.description = twenty_opp["description"]
        _log_sync(db, "inbound", "job", existing.id, opp_id, "update", "success")
    else:
        new_job = Job(
            job_code=twenty_opp.get("stockwire_job_code") or (opp_name[:50] if opp_name else f"TWENTY-{opp_id[:8]}"),
            customer_name=opp_name,
            status=stockwire_status,
            sales_price=amount or None,
            start_date=datetime.fromisoformat(twenty_opp["stockwire_start_date"]).date() if twenty_opp.get("stockwire_start_date") else None,
            end_date=datetime.fromisoformat(twenty_opp["closeDate"]).date() if twenty_opp.get("closeDate") else None,
            description=twenty_opp.get("description") or opp_name,
            external_source="twenty",
            external_reference=opp_id,
        )
        db.add(new_job)
        db.flush()
        _log_sync(db, "inbound", "job", new_job.id, opp_id, "create", "success")

    db.commit()
