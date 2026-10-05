"""Quotes API: settings and quote (PDF) generation."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user
from app.domain.jobs.models import Job
from app.domain.customers.models import Customer
from app.domain.quotes.settings import QUOTES_KEY, DEFAULT_QUOTES, get_quotes_settings
from app.domain.quotes.templates import ensure_default_quote_template
from app.domain.settings.accessors import get_company_profile_default_language
from app.domain.settings.models import AppSetting
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quotes", tags=["quotes"], dependencies=[Depends(get_current_user)])


@router.get("/settings")
def get_quotes_settings_endpoint(db: Session = Depends(get_db)) -> dict:
    """Return the effective quotes settings (markup %, VAT rate)."""
    return get_quotes_settings(db)


@router.put("/settings")
def update_quotes_settings_endpoint(payload: dict, db: Session = Depends(get_db)) -> dict:
    """Persist quotes settings (default_markup_pct, vat_rate)."""
    data = dict(DEFAULT_QUOTES)
    data.update({k: payload[k] for k in DEFAULT_QUOTES if k in payload})
    setting = db.scalar(select(AppSetting).where(AppSetting.key == QUOTES_KEY))
    if setting is None:
        setting = AppSetting(key=QUOTES_KEY, value_json=json.dumps(data))
        db.add(setting)
    else:
        setting.value_json = json.dumps(data)
    db.commit()
    return data


@router.post("/jobs/{job_id}/generate")
def generate_quote(job_id: int, db: Session = Depends(get_db)) -> Response:
    """Generate the quote PDF for a job and mark the job as a quotation."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    template = ensure_default_quote_template(db)
    pdf_service = PDFService(db)

    # Use the linked customer's preferred language for the quote, falling back
    # to the server default language (company profile) when the customer has no
    # language preference.
    language = get_company_profile_default_language(db)
    if job.customer_id:
        customer = db.get(Customer, job.customer_id)
        if customer and customer.preferred_language:
            language = customer.preferred_language

    try:
        pdf_bytes = pdf_service.generate_pdf(
            template_id=template.id,
            entity_type="job",
            entity_id=job_id,
            language=language,
        )
    except Exception as exc:
        logger.exception("Quote generation failed for job %d", job_id)
        raise HTTPException(status_code=500, detail=f"Quote generation failed: {exc}")

    if not pdf_bytes or len(pdf_bytes) < 10:
        raise HTTPException(status_code=500, detail="Generated quote is empty.")

    job.status = "quotation"
    db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=quote_{job.job_code}.pdf",
        },
    )


@router.post("/jobs/{job_id}/sync-twenty")
async def sync_quote_to_twenty_endpoint(job_id: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """Manually push the job's quote PDF + note to its synced Twenty opportunity."""
    from app.domain.integrations.models import TwentyConfig
    from app.domain.integrations.sync_engine import sync_quote_to_twenty
    from app.domain.integrations.twenty_client import TwentyClient

    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    config = db.query(TwentyConfig).first()
    if not config or not config.is_active or not config.api_key:
        raise HTTPException(status_code=400, detail="Twenty CRM integration is not active")

    client = TwentyClient(api_key=config.api_key, base_url=config.base_url)
    public_base_url = str(request.base_url).rstrip("/")
    return await sync_quote_to_twenty(db, client, job, public_base_url=public_base_url)
