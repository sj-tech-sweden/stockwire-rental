import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user
from app.domain.customers.models import Customer
from app.domain.integrations.schemas import (
    TwentyConfigCreate,
    TwentyConfigRead,
    TwentyConfigUpdate,
    TwentySyncLogRead,
    TwentySyncStatus,
    TwentySyncTrigger,
    TwentyTestResult,
)
from app.domain.integrations.sync_engine import (
    SYNC_PAGE_SIZE,
    sync_customer_inbound,
    sync_customer_outbound,
    sync_job_inbound,
    sync_job_outbound,
)
from app.domain.integrations.twenty_client import TwentyClient
from app.domain.jobs.models import Job

router = APIRouter(
    prefix="/integrations/twenty",
    tags=["integrations"],
    dependencies=[Depends(get_current_user)],
)


def _get_config(db: Session):
    from app.domain.integrations.models import TwentyConfig

    config = db.query(TwentyConfig).first()
    if not config:
        raise HTTPException(status_code=400, detail="Twenty CRM is not configured")
    return config


def _get_client(db: Session):
    config = _get_config(db)
    return TwentyClient(api_key=config.api_key, base_url=config.base_url)


@router.get("/config", response_model=TwentyConfigRead | None)
def get_config(db: Session = Depends(get_db)):
    from app.domain.integrations.models import TwentyConfig

    config = db.query(TwentyConfig).first()
    if not config:
        return None
    return TwentyConfigRead(
        id=config.id,
        base_url=config.base_url,
        workspace_id=config.workspace_id,
        is_active=config.is_active,
        has_api_key=config.api_key is not None and config.api_key != "",
        sync_interval_minutes=config.sync_interval_minutes or 0,
        has_webhook_secret=config.webhook_secret is not None and config.webhook_secret != "",
        schema_provisioned=config.schema_provisioned,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("/config", response_model=TwentyConfigRead)
def create_config(payload: TwentyConfigCreate, db: Session = Depends(get_db)):
    from app.domain.integrations.models import TwentyConfig

    existing = db.query(TwentyConfig).first()
    if existing:
        raise HTTPException(status_code=400, detail="Twenty CRM is already configured. Use PUT to update.")

    config = TwentyConfig(**payload.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return TwentyConfigRead(
        id=config.id,
        base_url=config.base_url,
        workspace_id=config.workspace_id,
        is_active=config.is_active,
        has_api_key=config.api_key is not None and config.api_key != "",
        sync_interval_minutes=config.sync_interval_minutes or 0,
        has_webhook_secret=config.webhook_secret is not None and config.webhook_secret != "",
        schema_provisioned=config.schema_provisioned,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.put("/config", response_model=TwentyConfigRead)
def update_config(payload: TwentyConfigUpdate, db: Session = Depends(get_db)):
    from app.domain.integrations.models import TwentyConfig

    config = db.query(TwentyConfig).first()
    if not config:
        raise HTTPException(status_code=404, detail="Twenty CRM is not configured")

    update_data = payload.model_dump(exclude_unset=True)
    update_data.pop("clear_api_key", None)
    if payload.clear_api_key:
        config.api_key = ""
    elif "api_key" in update_data and not update_data["api_key"]:
        del update_data["api_key"]
    for field, value in update_data.items():
        setattr(config, field, value)
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return TwentyConfigRead(
        id=config.id,
        base_url=config.base_url,
        workspace_id=config.workspace_id,
        is_active=config.is_active,
        has_api_key=config.api_key is not None and config.api_key != "",
        sync_interval_minutes=config.sync_interval_minutes or 0,
        has_webhook_secret=config.webhook_secret is not None and config.webhook_secret != "",
        schema_provisioned=config.schema_provisioned,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.delete("/config")
def delete_config(db: Session = Depends(get_db)):
    from app.domain.integrations.models import TwentyConfig

    config = db.query(TwentyConfig).filter(TwentyConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Twenty CRM is not configured")

    db.delete(config)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test", response_model=TwentyTestResult)
async def test_connection(db: Session = Depends(get_db)):
    try:
        client = _get_client(db)
        metadata = await client.test_connection()
        workspace_name = None
        if isinstance(metadata, dict):
            workspace_name = metadata.get("workspace", {}).get("displayName")
        return TwentyTestResult(success=True, message="Connected successfully", workspace_name=workspace_name)
    except Exception as e:
        return TwentyTestResult(success=False, message=str(e))


@router.post("/provision-schema")
async def provision_schema(db: Session = Depends(get_db)):
    """Provision custom fields and objects in Twenty CRM via Metadata API."""
    client = _get_client(db)
    try:
        result = await client.provision_schema()
        config = db.query(TwentyConfig).filter(TwentyConfig.is_active == True).first()
        if config:
            config.schema_provisioned = True
            config.updated_at = datetime.now(timezone.utc)
            db.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema provisioning failed: {e}")


@router.post("/sync")
async def trigger_sync(payload: TwentySyncTrigger, db: Session = Depends(get_db)):
    client = _get_client(db)
    synced = 0
    failed = 0

    entity_types = payload.entity_types or ["customer", "job"]

    if payload.direction in ("outbound", "both"):
        if "customer" in entity_types:
            offset = 0
            while True:
                customers = db.query(Customer).offset(offset).limit(SYNC_PAGE_SIZE).all()
                if not customers:
                    break
                for customer in customers:
                    try:
                        await sync_customer_outbound(db, client, customer)
                        synced += 1
                    except Exception:
                        failed += 1
                if len(customers) < SYNC_PAGE_SIZE:
                    break
                offset += SYNC_PAGE_SIZE

        if "job" in entity_types:
            offset = 0
            while True:
                jobs = db.query(Job).offset(offset).limit(SYNC_PAGE_SIZE).all()
                if not jobs:
                    break
                for job in jobs:
                    try:
                        await sync_job_outbound(db, client, job)
                        synced += 1
                    except Exception:
                        failed += 1
                if len(jobs) < SYNC_PAGE_SIZE:
                    break
                offset += SYNC_PAGE_SIZE

    if payload.direction in ("inbound", "both"):
        if "customer" in entity_types:
            # Pre-fetch all people once and build a company_id → person lookup to
            # avoid one API call per company during the loop below.
            people_by_company: dict[str, dict] = {}
            try:
                all_people = await client.search_people(email=None)
                for p_edge in all_people:
                    p_node = p_edge.get("node", p_edge)
                    comp = p_node.get("company") or {}
                    if isinstance(comp, dict) and comp.get("id"):
                        people_by_company.setdefault(comp["id"], p_node)
            except Exception:
                logger.warning("trigger_sync: could not pre-fetch people; person matching will be skipped")

            offset = 0
            while True:
                companies_data = await client.list_objects("companies", limit=SYNC_PAGE_SIZE, offset=offset)
                data_val = companies_data.get("data", [])
                if isinstance(data_val, list):
                    companies = data_val
                else:
                    companies = data_val.get("companies", {}).get("edges", [])
                if not companies:
                    break
                for edge in companies:
                    company = edge.get("node", edge)
                    try:
                        matched_person = people_by_company.get(company.get("id") or "")
                        await sync_customer_inbound(db, client, company, matched_person)
                        synced += 1
                    except Exception:
                        failed += 1
                if len(companies) < SYNC_PAGE_SIZE:
                    break
                offset += SYNC_PAGE_SIZE

        if "job" in entity_types:
            offset = 0
            while True:
                opps_data = await client.list_objects("opportunities", limit=SYNC_PAGE_SIZE, offset=offset)
                data_val = opps_data.get("data", [])
                if isinstance(data_val, list):
                    opps = data_val
                else:
                    opps = data_val.get("opportunities", {}).get("edges", [])
                if not opps:
                    break
                for edge in opps:
                    opp = edge.get("node", edge)
                    try:
                        await sync_job_inbound(db, client, opp)
                        synced += 1
                    except Exception:
                        failed += 1
                if len(opps) < SYNC_PAGE_SIZE:
                    break
                offset += SYNC_PAGE_SIZE

    return {"synced": synced, "failed": failed}


@router.get("/status", response_model=TwentySyncStatus)
def get_sync_status(db: Session = Depends(get_db)):
    from datetime import timedelta

    from app.domain.integrations.models import TwentyConfig, TwentySyncLog

    config = db.query(TwentyConfig).first()
    if not config:
        return TwentySyncStatus(is_configured=False)

    last_log = (
        db.query(TwentySyncLog)
        .filter(TwentySyncLog.status == "success")
        .order_by(TwentySyncLog.created_at.desc())
        .first()
    )

    total_synced = db.query(TwentySyncLog).filter(TwentySyncLog.status == "success").count()
    total_failed = db.query(TwentySyncLog).filter(TwentySyncLog.status == "failed").count()

    recent_logs = (
        db.query(TwentySyncLog)
        .order_by(TwentySyncLog.created_at.desc())
        .limit(20)
        .all()
    )

    interval = config.sync_interval_minutes or 0
    next_sync_at = None
    if interval > 0 and config.is_active:
        if last_log:
            next_sync_at = last_log.created_at + timedelta(minutes=interval)
        else:
            next_sync_at = config.created_at + timedelta(minutes=interval)

    return TwentySyncStatus(
        is_configured=True,
        last_sync_at=last_log.created_at if last_log else None,
        next_sync_at=next_sync_at,
        sync_interval_minutes=interval,
        total_synced=total_synced,
        total_failed=total_failed,
        recent_logs=[TwentySyncLogRead.model_validate(log) for log in recent_logs],
    )
