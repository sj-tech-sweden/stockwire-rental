import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.domain.customers.models import Company, Customer, Person
from app.domain.integrations.models import TwentySyncLog
from app.domain.integrations.twenty_client import TwentyClient
from app.domain.jobs.models import Job

logger = logging.getLogger(__name__)


class TwentyRecordNotFoundError(Exception):
    """Raised when a Twenty record referenced by external_reference no longer exists."""


def _links_field(url: str | None, label: str = "Stockwire") -> dict[str, str] | None:
    """Format a URL for Twenty LINKS typed fields."""
    if not url:
        return None
    return {"primaryLinkUrl": url, "primaryLinkLabel": label}

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
    "stockwireUrl", "stockwireId", "stockwireNotes", "phoneSecondary",
    "stockwireJobCode", "stockwireStartDate", "stockwireEndDate", "stockwireStatus",
}


async def _safe_update(client: TwentyClient, object_name: str, record_id: str, data: dict) -> None:
    """Update a record, stripping fields that don't exist on the target object.

    Raises TwentyRecordNotFoundError when the target record no longer exists so
    callers can recreate it.
    """
    async def _try_stripped_update(exc: Exception) -> bool:
        err_str = str(exc)
        if "doesn't have any" in err_str or "400" in err_str:
            stripped = {k: v for k, v in data.items() if k not in _STOCKWIRE_FIELDS}
            if stripped != data:
                try:
                    await client.update_object(object_name, record_id, stripped)
                    return True
                except Exception:
                    pass
        return False

    try:
        await client.update_object(object_name, record_id, data)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise TwentyRecordNotFoundError(
                f"{object_name}/{record_id} not found in Twenty"
            ) from exc
        if not await _try_stripped_update(exc):
            raise
    except Exception as exc:
        if not await _try_stripped_update(exc):
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
        payload["stockwireNotes"] = customer.notes
    if customer.id:
        payload["stockwireId"] = customer.id
    frontend = settings.effective_frontend_base_url
    if frontend and customer.id:
        links = _links_field(f"{frontend}/companies/{customer.id}")
        if links:
            payload["stockwireUrl"] = links
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
    from app.config import settings

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
        payload["stockwireId"] = customer.id
    frontend = settings.effective_frontend_base_url
    if frontend and customer.id:
        links = _links_field(f"{frontend}/companies/{customer.id}")
        if links:
            payload["stockwireUrl"] = links
    return payload


def _job_to_opportunity_payload(job: Job) -> dict:
    from app.config import settings

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
        payload["stockwireJobCode"] = job.job_code
    if job.start_date:
        payload["stockwireStartDate"] = job.start_date.isoformat()
    if job.end_date:
        payload["stockwireEndDate"] = job.end_date.isoformat()
    payload["stockwireStatus"] = job.status or ""
    if job.id:
        payload["stockwireId"] = job.id
    frontend = settings.effective_frontend_base_url
    if frontend and job.id:
        links = _links_field(f"{frontend}/job/{job.id}")
        if links:
            payload["stockwireUrl"] = links
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


async def sync_customer_outbound(
    db: Session, client: TwentyClient, customer: Customer, *, force: bool = False
) -> None:
    """Push a Stockwire customer to Twenty CRM.

    By default, records that originated in Twenty (external_origin == "twenty")
    are not pushed back, to avoid overwriting data in Twenty. Use force=True to
    override (e.g. for the one-time stockwire-field write-back after inbound sync).
    """
    if customer.external_origin == "twenty" and not force:
        logger.debug("Skipping outbound sync for Twenty-originated customer %s", customer.id)
        return

    try:
        company_data = _customer_to_company_payload(customer)
        person_data = _customer_to_person_payload(customer)

        twenty_company_id = None

        if customer.external_source == "twenty" and customer.external_reference:
            twenty_company_id = customer.external_reference
            try:
                await _safe_update(client, "companies", twenty_company_id, company_data)
                _log_sync(db, "outbound", "customer", customer.id, twenty_company_id, "update", "success")
            except TwentyRecordNotFoundError:
                logger.warning(
                    "Company %s no longer exists in Twenty; recreating customer %s",
                    twenty_company_id, customer.id,
                )
                customer.external_source = None
                customer.external_reference = None
                twenty_company_id = None

        if not twenty_company_id:
            result = await client.create_object("companies", company_data)
            twenty_company_id = _extract_twenty_id(result, "companies")
            customer.external_source = "twenty"
            customer.external_reference = twenty_company_id
            customer.external_origin = customer.external_origin or "stockwire"
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


async def sync_job_outbound(
    db: Session, client: TwentyClient, job: Job, *, force: bool = False
) -> None:
    """Push a Stockwire job to Twenty CRM as an opportunity.

    By default, records that originated in Twenty (external_origin == "twenty")
    are not pushed back, to avoid overwriting data in Twenty.
    """
    if job.external_origin == "twenty" and not force:
        logger.debug("Skipping outbound sync for Twenty-originated job %s", job.id)
        return

    try:
        opp_data = _job_to_opportunity_payload(job)

        if job.customer_id:
            customer = db.query(Customer).filter(Customer.id == job.customer_id).first()
            if customer and customer.external_source == "twenty" and customer.external_reference:
                opp_data["companyId"] = customer.external_reference

        twenty_opp_id = None

        if job.external_source == "twenty" and job.external_reference:
            twenty_opp_id = job.external_reference
            try:
                await _safe_update(client, "opportunities", twenty_opp_id, opp_data)
                _log_sync(db, "outbound", "job", job.id, twenty_opp_id, "update", "success")
            except TwentyRecordNotFoundError:
                logger.warning(
                    "Opportunity %s no longer exists in Twenty; recreating job %s",
                    twenty_opp_id, job.id,
                )
                job.external_source = None
                job.external_reference = None
                twenty_opp_id = None

        if not twenty_opp_id:
            result = await client.create_object("opportunities", opp_data)
            twenty_opp_id = _extract_twenty_id(result, "opportunities")
            job.external_source = "twenty"
            job.external_reference = twenty_opp_id
            job.external_origin = job.external_origin or "stockwire"
            _log_sync(db, "outbound", "job", job.id, twenty_opp_id, "create", "success")

        db.commit()
    except Exception as e:
        logger.exception("Failed to sync job %s to Twenty", job.id)
        _log_sync(db, "outbound", "job", job.id, None, "update", "failed", str(e))
        db.commit()
        raise


async def sync_customer_inbound(db: Session, client: TwentyClient, twenty_company: dict, twenty_person: dict | None = None) -> bool:
    """Sync a Twenty company into Stockwire.

    Returns True if a new customer was created, False if an existing one was updated.
    """
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
        logger.debug(
            "Inbound company update: customer_id=%s twenty_id=%s name=%r -> %r",
            existing.id, company_id, existing.name, company_name,
        )
        if company_name:
            existing.name = company_name
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
        sw_notes = twenty_company.get("stockwireNotes") or twenty_company.get("notes")
        if sw_notes:
            existing.notes = sw_notes
        _log_sync(db, "inbound", "customer", existing.id, company_id, "update", "success")
        db.commit()
        return False

    full_name = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
    sw_notes = twenty_company.get("stockwireNotes") or twenty_company.get("notes")
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
        external_origin="twenty",
    )
    db.add(new_customer)
    db.flush()
    _log_sync(db, "inbound", "customer", new_customer.id, company_id, "create", "success")
    db.commit()
    return True


async def sync_job_inbound(db: Session, client: TwentyClient, twenty_opp: dict) -> bool:
    """Sync a Twenty opportunity into an existing Stockwire job.

    Jobs are authoritative in Stockwire, so we only update jobs that were
    originally pushed from Stockwire (external_source == "twenty").
    We never create new jobs from Twenty opportunities.

    Returns True if the job was updated, False if no matching job was found.
    """
    opp_id = twenty_opp.get("id")
    opp_name = twenty_opp.get("name", "")

    existing = db.query(Job).filter(
        Job.external_source == "twenty",
        Job.external_reference == opp_id,
    ).first()

    if not existing:
        logger.warning("Ignoring Twenty opportunity %s: no matching Stockwire job", opp_id)
        return False

    reverse_stages = _reverse_stage_map()
    stage = twenty_opp.get("stage", "SCREENING")
    stockwire_status = reverse_stages.get(stage, "draft")

    raw_amount = twenty_opp.get("amount")
    try:
        if isinstance(raw_amount, dict):
            amount_micros = raw_amount.get("amountMicros")
            amount = float(amount_micros) / 1_000_000 if amount_micros else 0
        elif raw_amount:
            amount = float(raw_amount)
        else:
            amount = 0
    except (TypeError, ValueError):
        logger.warning("Could not parse opportunity amount: %r", raw_amount)
        amount = 0

    logger.debug(
        "Inbound job update: job_id=%s opp_id=%s name=%r status=%r amount=%s",
        existing.id, opp_id, opp_name, stockwire_status, amount,
    )
    existing.customer_name = opp_name or existing.customer_name
    existing.status = stockwire_status
    if amount:
        existing.sales_price = amount
    if twenty_opp.get("closeDate"):
        existing.end_date = datetime.fromisoformat(twenty_opp["closeDate"]).date()
    if twenty_opp.get("stockwireStartDate"):
        existing.start_date = datetime.fromisoformat(twenty_opp["stockwireStartDate"]).date()
    if twenty_opp.get("stockwireJobCode") and not existing.job_code:
        existing.job_code = twenty_opp["stockwireJobCode"]
    if twenty_opp.get("description"):
        existing.description = twenty_opp["description"]
    _log_sync(db, "inbound", "job", existing.id, opp_id, "update", "success")
    db.commit()
    return True


# ============================================================================
# New Company/Person Sync Functions
# ============================================================================


def _company_to_company_payload(company: Company) -> dict:
    """Convert a Stockwire Company to a Twenty Company payload."""
    from app.config import settings

    payload: dict = {"name": company.name or ""}
    if company.address or company.city or company.postal_code or company.country:
        payload["address"] = {
            "addressStreet1": company.address or "",
            "addressCity": company.city or "",
            "addressPostcode": company.postal_code or "",
            "addressCountry": company.country or "",
        }
    if company.notes:
        payload["stockwireNotes"] = company.notes
    if company.id:
        payload["stockwireId"] = company.id
    frontend = settings.effective_frontend_base_url
    if frontend and company.id:
        links = _links_field(f"{frontend}/companies/{company.id}")
        if links:
            payload["stockwireUrl"] = links
    return payload


def _person_to_person_payload(person: Person) -> dict:
    """Convert a Stockwire Person to a Twenty Person payload."""
    from app.config import settings

    payload: dict = {}
    if person.first_name or person.last_name:
        payload["name"] = {"firstName": person.first_name or "", "lastName": person.last_name or ""}
    if person.email:
        payload["emails"] = {"primaryEmail": person.email}
    if person.phone:
        payload["phones"] = {"primaryPhoneNumber": _sanitize_phone(person.phone)}
    if person.id:
        payload["stockwireId"] = person.id
    frontend = settings.effective_frontend_base_url
    if frontend and person.id:
        links = _links_field(f"{frontend}/persons/{person.id}")
        if links:
            payload["stockwireUrl"] = links
    return payload


async def sync_company_outbound(
    db: Session, client: TwentyClient, company: Company, *, force: bool = False
) -> None:
    """Push a Stockwire Company to Twenty CRM.

    By default, records that originated in Twenty (external_origin == "twenty")
    are not pushed back, to avoid overwriting data in Twenty. Use force=True to
    override (e.g. for the one-time stockwire-field write-back after inbound sync).
    """
    if company.external_origin == "twenty" and not force:
        logger.debug("Skipping outbound sync for Twenty-originated company %s", company.id)
        return

    try:
        company_data = _company_to_company_payload(company)

        twenty_company_id = None

        if company.external_source == "twenty" and company.external_reference:
            twenty_company_id = company.external_reference
            try:
                await _safe_update(client, "companies", twenty_company_id, company_data)
                _log_sync(db, "outbound", "company", company.id, twenty_company_id, "update", "success")
            except TwentyRecordNotFoundError:
                logger.warning(
                    "Company %s no longer exists in Twenty; recreating company %s",
                    twenty_company_id, company.id,
                )
                company.external_source = None
                company.external_reference = None
                twenty_company_id = None

        if not twenty_company_id:
            result = await client.create_object("companies", company_data)
            twenty_company_id = _extract_twenty_id(result, "companies")
            company.external_source = "twenty"
            company.external_reference = twenty_company_id
            company.external_origin = company.external_origin or "stockwire"
            _log_sync(db, "outbound", "company", company.id, twenty_company_id, "create", "success")

        db.commit()
    except Exception as e:
        logger.exception("Failed to sync company %s to Twenty", company.id)
        _log_sync(db, "outbound", "company", company.id, None, "update", "failed", str(e))
        db.commit()
        raise


async def sync_person_outbound(
    db: Session, client: TwentyClient, person: Person, *, force: bool = False
) -> None:
    """Push a Stockwire Person to Twenty CRM.

    By default, records that originated in Twenty (external_origin == "twenty")
    are not pushed back, to avoid overwriting data in Twenty. Use force=True to
    override (e.g. for the one-time stockwire-field write-back after inbound sync).
    """
    if person.external_origin == "twenty" and not force:
        logger.debug("Skipping outbound sync for Twenty-originated person %s", person.id)
        return

    try:
        person_data = _person_to_person_payload(person)

        # Link to company in Twenty if person has company_id
        if person.company_id:
            company = db.get(Company, person.company_id)
            if company and company.external_reference:
                person_data["companyId"] = company.external_reference

        twenty_person_id = None

        if person.external_source == "twenty" and person.external_reference:
            twenty_person_id = person.external_reference
            try:
                await _safe_update(client, "people", twenty_person_id, person_data)
                _log_sync(db, "outbound", "person", person.id, twenty_person_id, "update", "success")
            except TwentyRecordNotFoundError:
                logger.warning(
                    "Person %s no longer exists in Twenty; recreating person %s",
                    twenty_person_id, person.id,
                )
                person.external_source = None
                person.external_reference = None
                twenty_person_id = None

        if not twenty_person_id:
            result = await client.create_object("people", person_data)
            twenty_person_id = _extract_twenty_id(result, "people")
            person.external_source = "twenty"
            person.external_reference = twenty_person_id
            person.external_origin = person.external_origin or "stockwire"
            _log_sync(db, "outbound", "person", person.id, twenty_person_id, "create", "success")

        db.commit()
    except Exception as e:
        logger.exception("Failed to sync person %s to Twenty", person.id)
        _log_sync(db, "outbound", "person", person.id, None, "update", "failed", str(e))
        db.commit()
        raise


async def sync_company_inbound(db: Session, client: TwentyClient, twenty_company: dict) -> bool:
    """Sync a Twenty Company into a Stockwire Company.

    Returns True if a new company was created, False if an existing one was updated.
    """
    company_id = twenty_company.get("id")
    company_name = twenty_company.get("name", "")

    existing = db.query(Company).filter(
        Company.external_source == "twenty",
        Company.external_reference == company_id,
    ).first()

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

    sw_notes = twenty_company.get("stockwireNotes") or twenty_company.get("notes")

    if existing:
        logger.debug(
            "Inbound company update: company_id=%s twenty_id=%s name=%r -> %r",
            existing.id, company_id, existing.name, company_name,
        )
        if company_name:
            existing.name = company_name
        if address:
            existing.address = address
        if city:
            existing.city = city
        if postal_code:
            existing.postal_code = postal_code
        if country:
            existing.country = country
        if sw_notes:
            existing.notes = sw_notes
        _log_sync(db, "inbound", "company", existing.id, company_id, "update", "success")
        db.commit()
        return False

    new_company = Company(
        name=company_name or None,
        address=address or None,
        city=city or None,
        postal_code=postal_code or None,
        country=country or None,
        notes=sw_notes,
        external_source="twenty",
        external_reference=company_id,
        external_origin="twenty",
    )
    db.add(new_company)
    db.flush()
    _log_sync(db, "inbound", "company", new_company.id, company_id, "create", "success")
    db.commit()
    return True


async def sync_person_inbound(db: Session, client: TwentyClient, twenty_person: dict) -> bool:
    """Sync a Twenty Person into a Stockwire Person.

    Returns True if a new person was created, False if an existing one was updated.
    """
    person_id = twenty_person.get("id")
    name_obj = twenty_person.get("name") or {}
    first_name = name_obj.get("firstName", "")
    last_name = name_obj.get("lastName", "")

    # Get company link
    twenty_company_id = twenty_person.get("companyId")
    company_id = None
    if twenty_company_id:
        company = db.query(Company).filter(
            Company.external_source == "twenty",
            Company.external_reference == str(twenty_company_id),
        ).first()
        if company:
            company_id = company.id

    existing = db.query(Person).filter(
        Person.external_source == "twenty",
        Person.external_reference == person_id,
    ).first()

    emails_data = twenty_person.get("emails") or {}
    email = emails_data.get("primaryEmail") if isinstance(emails_data, dict) else None
    phones_data = twenty_person.get("phones") or {}
    phone = phones_data.get("primaryPhoneNumber") if isinstance(phones_data, dict) else None

    if existing:
        logger.debug(
            "Inbound person update: person_id=%s twenty_id=%s name=%r %r",
            existing.id, person_id, first_name, last_name,
        )
        if first_name:
            existing.first_name = first_name
        if last_name:
            existing.last_name = last_name
        if email:
            existing.email = email
        if phone:
            existing.phone = phone
        if company_id is not None:
            existing.company_id = company_id
        _log_sync(db, "inbound", "person", existing.id, person_id, "update", "success")
        db.commit()
        return False

    new_person = Person(
        first_name=first_name or None,
        last_name=last_name or None,
        email=email,
        phone=phone,
        company_id=company_id,
        external_source="twenty",
        external_reference=person_id,
        external_origin="twenty",
    )
    db.add(new_person)
    db.flush()
    _log_sync(db, "inbound", "person", new_person.id, person_id, "create", "success")
    db.commit()
    return True
