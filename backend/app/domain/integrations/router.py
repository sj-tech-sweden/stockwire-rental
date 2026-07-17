import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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
    sync_customer_outbound,
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

    config = db.query(TwentyConfig).filter(TwentyConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=400, detail="Twenty CRM is not configured")
    return config


def _get_client(db: Session):
    config = _get_config(db)
    return TwentyClient(api_key=config.api_key, base_url=config.base_url)


@router.get("/config", response_model=TwentyConfigRead | None)
def get_config(db: Session = Depends(get_db)):
    from app.domain.integrations.models import TwentyConfig

    config = db.query(TwentyConfig).filter(TwentyConfig.is_active == True).first()
    if not config:
        return None
    return TwentyConfigRead(
        id=config.id,
        base_url=config.base_url,
        workspace_id=config.workspace_id,
        is_active=config.is_active,
        has_api_key=bool(config.api_key),
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("/config", response_model=TwentyConfigRead)
def create_config(payload: TwentyConfigCreate, db: Session = Depends(get_db)):
    from app.domain.integrations.models import TwentyConfig

    existing = db.query(TwentyConfig).filter(TwentyConfig.is_active == True).first()
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
        has_api_key=bool(config.api_key),
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.put("/config", response_model=TwentyConfigRead)
def update_config(payload: TwentyConfigUpdate, db: Session = Depends(get_db)):
    from app.domain.integrations.models import TwentyConfig

    config = db.query(TwentyConfig).filter(TwentyConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="Twenty CRM is not configured")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    return TwentyConfigRead(
        id=config.id,
        base_url=config.base_url,
        workspace_id=config.workspace_id,
        is_active=config.is_active,
        has_api_key=bool(config.api_key),
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
    return {"ok": True}


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


@router.post("/sync")
async def trigger_sync(payload: TwentySyncTrigger, db: Session = Depends(get_db)):
    client = _get_client(db)
    synced = 0
    failed = 0

    entity_types = payload.entity_types or ["customer", "job"]

    if payload.direction in ("outbound", "both"):
        if "customer" in entity_types:
            customers = db.query(Customer).filter(
                (Customer.external_source != "twenty") | (Customer.external_source.is_(None))
            ).all()
            for customer in customers:
                try:
                    await sync_customer_outbound(db, client, customer)
                    synced += 1
                except Exception:
                    failed += 1

        if "job" in entity_types:
            jobs = db.query(Job).filter(
                (Job.external_source != "twenty") | (Job.external_source.is_(None))
            ).all()
            for job in jobs:
                try:
                    await sync_job_outbound(db, client, job)
                    synced += 1
                except Exception:
                    failed += 1

    return {"synced": synced, "failed": failed}


@router.get("/status", response_model=TwentySyncStatus)
def get_sync_status(db: Session = Depends(get_db)):
    from app.domain.integrations.models import TwentyConfig, TwentySyncLog

    config = db.query(TwentyConfig).filter(TwentyConfig.is_active == True).first()
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

    return TwentySyncStatus(
        is_configured=True,
        last_sync_at=last_log.created_at if last_log else None,
        total_synced=total_synced,
        total_failed=total_failed,
        recent_logs=[TwentySyncLogRead.model_validate(log) for log in recent_logs],
    )
