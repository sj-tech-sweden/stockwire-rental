import logging
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user
from app.domain.customers.models import Customer
from app.domain.integrations.schemas import (
    TwentyConfigCreate,
    TwentyConfigRead,
    TwentyConfigUpdate,
    TwentySyncJobStatus,
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
def get_config(request: Request, db: Session = Depends(get_db)):
    from app.config import settings
    from app.domain.integrations.models import TwentyConfig

    config = db.query(TwentyConfig).first()
    if not config:
        return None
    env_url = settings.api_base_url or None
    is_env = bool(env_url)
    default_url = settings.effective_api_base_url or _get_request_base_url(request)
    return TwentyConfigRead(
        id=config.id,
        base_url=config.base_url,
        workspace_id=config.workspace_id,
        is_active=config.is_active,
        has_api_key=config.api_key is not None and config.api_key != "",
        sync_interval_minutes=config.sync_interval_minutes or 0,
        has_webhook_secret=config.webhook_secret is not None and config.webhook_secret != "",
        webhook_base_url=env_url if is_env else config.webhook_base_url,
        webhook_base_url_is_env=is_env,
        default_webhook_base_url=default_url,
        schema_provisioned=config.schema_provisioned,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("/config", response_model=TwentyConfigRead)
def create_config(payload: TwentyConfigCreate, request: Request, db: Session = Depends(get_db)):
    from app.config import settings
    from app.domain.integrations.models import TwentyConfig

    existing = db.query(TwentyConfig).first()
    if existing:
        raise HTTPException(status_code=400, detail="Twenty CRM is already configured. Use PUT to update.")

    config = TwentyConfig(**payload.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    env_url = settings.api_base_url or None
    is_env = bool(env_url)
    return TwentyConfigRead(
        id=config.id,
        base_url=config.base_url,
        workspace_id=config.workspace_id,
        is_active=config.is_active,
        has_api_key=config.api_key is not None and config.api_key != "",
        sync_interval_minutes=config.sync_interval_minutes or 0,
        has_webhook_secret=config.webhook_secret is not None and config.webhook_secret != "",
        webhook_base_url=env_url if is_env else config.webhook_base_url,
        webhook_base_url_is_env=is_env,
        default_webhook_base_url=settings.effective_api_base_url or _get_request_base_url(request),
        schema_provisioned=config.schema_provisioned,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.put("/config", response_model=TwentyConfigRead)
def update_config(payload: TwentyConfigUpdate, request: Request, db: Session = Depends(get_db)):
    from app.config import settings
    from app.domain.integrations.models import TwentyConfig

    config = db.query(TwentyConfig).first()
    if not config:
        raise HTTPException(status_code=404, detail="Twenty CRM is not configured")

    update_data = payload.model_dump(exclude_unset=True)
    update_data.pop("clear_api_key", None)
    update_data.pop("clear_webhook_secret", None)
    if payload.clear_api_key:
        config.api_key = ""
    elif "api_key" in update_data and not update_data["api_key"]:
        del update_data["api_key"]
    if payload.clear_webhook_secret:
        config.webhook_secret = ""
    elif "webhook_secret" in update_data and not update_data["webhook_secret"]:
        del update_data["webhook_secret"]
    if "webhook_base_url" in update_data and update_data["webhook_base_url"] is not None:
        update_data["webhook_base_url"] = update_data["webhook_base_url"].strip() or None
    env_url = settings.api_base_url or None
    is_env = bool(env_url)
    if is_env and "webhook_base_url" in update_data:
        # API_BASE_URL takes precedence; ignore user value when env controls it.
        del update_data["webhook_base_url"]
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
        webhook_base_url=env_url if is_env else config.webhook_base_url,
        webhook_base_url_is_env=is_env,
        default_webhook_base_url=settings.effective_api_base_url or _get_request_base_url(request),
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


# In-memory store for background integration jobs (sync + schema provision).
INTEGRATION_JOBS: dict[str, dict] = {}


def _update_job(job_id: str, **kwargs) -> None:
    job = INTEGRATION_JOBS.get(job_id)
    if job is None:
        return
    job.update(kwargs)
    try:
        from app.domain.realtime.events import emit_realtime_event
        emit_realtime_event(
            f"twenty.job.{job_id}",
            {"job_id": job_id, **job},
        )
    except Exception:
        logger.debug("Failed to broadcast Twenty job update for %s", job_id, exc_info=True)


def _get_request_base_url(request: Request) -> str:
    """Build the public backend base URL from request headers."""
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or f"{request.url.hostname}:{request.url.port}"
    return f"{scheme}://{host}"


async def _run_provision_schema_job(job_id: str, db_session_factory, request_base_url: str | None = None) -> None:
    """Run schema provisioning in the background and update INTEGRATION_JOBS."""
    from app.domain.integrations.models import TwentyConfig

    _update_job(job_id, status="running")
    db = db_session_factory()
    try:
        config = db.query(TwentyConfig).filter(TwentyConfig.is_active.is_(True)).first()
        client = _get_client(db)
        webhook_url = None
        webhook_secret = None
        if config:
            from app.config import settings
            api_base = (
                config.webhook_base_url
                or settings.effective_api_base_url
                or request_base_url
            )
            if not config.webhook_base_url and not settings.api_base_url and request_base_url:
                logger.warning(
                    "Neither webhook_base_url nor API_BASE_URL is configured; falling back to request base URL %s for Twenty webhooks. "
                    "Set webhook_base_url in Twenty settings or API_BASE_URL in the backend environment for a stable URL.",
                    request_base_url,
                )
            if api_base:
                webhook_url = f"{api_base}/api/v1/integrations/twenty/webhook"
            webhook_secret = config.webhook_secret or None

        result = await client.provision_schema(
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            job_id=job_id,
        )
        result["webhook_url"] = webhook_url
        if config:
            config.schema_provisioned = True
            config.updated_at = datetime.now(timezone.utc)
            db.commit()

        _update_job(
            job_id,
            status="completed",
            result=result,
            fields_created=len(result.get("custom_fields_created", [])),
            objects_created=len(result.get("custom_objects_created", [])),
            webhooks_created=len(result.get("webhooks_created", [])),
            errors=result.get("errors", []),
        )
        logger.info(
            "Background schema provision (job=%s) complete: %d fields, %d objects, %d webhooks, %d errors",
            job_id,
            len(result.get("custom_fields_created", [])),
            len(result.get("custom_objects_created", [])),
            len(result.get("webhooks_created", [])),
            len(result.get("errors", [])),
        )
    except Exception as exc:
        logger.exception("Background schema provision (job=%s) failed", job_id)
        _update_job(job_id, status="failed", error=str(exc))
    finally:
        db.close()


@router.post("/provision-schema")
async def provision_schema(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start schema provisioning as a background job.

    Returns immediately with a job_id that can be polled via GET /sync/{job_id}.
    """
    from app.db.session import SessionLocal
    from app.domain.integrations.models import TwentyConfig

    # Validate configuration before accepting the job.
    _get_client(db)
    if not db.query(TwentyConfig).filter(TwentyConfig.is_active.is_(True)).first():
        raise HTTPException(status_code=400, detail="Twenty CRM is not configured")

    request_base_url = _get_request_base_url(request)
    job_id = str(uuid4())
    INTEGRATION_JOBS[job_id] = {
        "job_id": job_id,
        "type": "provision-schema",
        "status": "pending",
        "stage": "schema provisioning",
        "processed": 0,
        "total": None,
        "synced": 0,
        "failed": 0,
        "result": None,
        "error": None,
    }
    background_tasks.add_task(_run_provision_schema_job, job_id, SessionLocal, request_base_url)
    logger.info("Queued Twenty schema provision job %s", job_id)
    return {"job_id": job_id, "status": "pending"}


async def _run_sync_job(job_id: str, payload: TwentySyncTrigger) -> None:
    """Run a sync job in the background and update INTEGRATION_JOBS with progress."""
    from app.db.session import SessionLocal

    _update_job(job_id, status="running")
    db = SessionLocal()
    try:
        client = _get_client(db)
        synced = 0
        failed = 0

        entity_types = payload.entity_types or ["customer", "job"]
        logger.info(
            "Starting background Twenty sync (job=%s): direction=%s, entities=%s",
            job_id, payload.direction, entity_types,
        )

        if payload.direction in ("outbound", "both"):
            if "customer" in entity_types:
                _update_job(job_id, stage="outbound customers")
                offset = 0
                processed = 0
                total_customers = db.query(Customer).count()
                _update_job(job_id, total=total_customers)
                while True:
                    customers = db.query(Customer).offset(offset).limit(SYNC_PAGE_SIZE).all()
                    if not customers:
                        break
                    for customer in customers:
                        processed += 1
                        try:
                            await sync_customer_outbound(db, client, customer)
                            synced += 1
                        except Exception as exc:
                            failed += 1
                            logger.exception("Sync failed for customer %s: %s", customer.id, exc)
                        _update_job(job_id, processed=processed, synced=synced, failed=failed)
                    if len(customers) < SYNC_PAGE_SIZE:
                        break
                    offset += SYNC_PAGE_SIZE
                logger.info(
                    "Background sync (job=%s) outbound customers complete: synced=%d, failed=%d",
                    job_id, synced, failed,
                )

            if "job" in entity_types:
                _update_job(job_id, stage="outbound jobs")
                offset = 0
                processed = 0
                total_jobs = db.query(Job).count()
                _update_job(job_id, total=total_jobs)
                while True:
                    jobs = db.query(Job).offset(offset).limit(SYNC_PAGE_SIZE).all()
                    if not jobs:
                        break
                    for job in jobs:
                        processed += 1
                        try:
                            await sync_job_outbound(db, client, job)
                            synced += 1
                        except Exception as exc:
                            failed += 1
                            logger.exception("Sync failed for job %s: %s", job.id, exc)
                        _update_job(job_id, processed=processed, synced=synced, failed=failed)
                    if len(jobs) < SYNC_PAGE_SIZE:
                        break
                    offset += SYNC_PAGE_SIZE
                logger.info(
                    "Background sync (job=%s) outbound jobs complete: synced=%d, failed=%d",
                    job_id, synced, failed,
                )

        if payload.direction in ("inbound", "both"):
            if "customer" in entity_types:
                _update_job(job_id, stage="inbound customers")
                # Pre-fetch all people once and build a company_id → person lookup.
                people_by_company: dict[str, dict] = {}
                try:
                    all_people = await client.search_people(email=None)
                    for p_edge in all_people:
                        p_node = p_edge.get("node", p_edge)
                        comp = p_node.get("company") or {}
                        if isinstance(comp, dict) and comp.get("id"):
                            people_by_company.setdefault(comp["id"], p_node)
                    logger.info(
                        "Background sync (job=%s) pre-fetched %d people",
                        job_id, len(people_by_company),
                    )
                except Exception:
                    logger.warning("Background sync (job=%s): could not pre-fetch people", job_id)

                offset = 0
                processed = 0
                while True:
                    companies_data = await client.list_objects("companies", limit=SYNC_PAGE_SIZE, offset=offset)
                    data_val = companies_data.get("data", [])
                    if isinstance(data_val, list):
                        companies = data_val
                    elif isinstance(data_val, dict):
                        inner = data_val.get("companies", data_val)
                        companies = inner.get("edges", inner) if isinstance(inner, dict) else inner if isinstance(inner, list) else []
                    else:
                        companies = []
                    if not companies:
                        break
                    for edge in companies:
                        company = edge.get("node", edge)
                        processed += 1
                        try:
                            matched_person = people_by_company.get(company.get("id") or "")
                            created = await sync_customer_inbound(db, client, company, matched_person)
                            synced += 1
                            if created:
                                try:
                                    customer = db.query(Customer).filter(
                                        Customer.external_source == "twenty",
                                        Customer.external_reference == str(company.get("id")),
                                    ).first()
                                    if customer:
                                        await sync_customer_outbound(db, client, customer, force=True)
                                except Exception:
                                    logger.exception(
                                        "Failed to write back stockwire fields for customer %s",
                                        company.get("id"),
                                    )
                                    failed += 1
                        except Exception as exc:
                            failed += 1
                            logger.exception("Sync failed for inbound company %s: %s", company.get("id"), exc)
                        _update_job(job_id, processed=processed, synced=synced, failed=failed)
                    if len(companies) < SYNC_PAGE_SIZE:
                        break
                    offset += SYNC_PAGE_SIZE
                logger.info(
                    "Background sync (job=%s) inbound customers complete: synced=%d, failed=%d",
                    job_id, synced, failed,
                )

            if "job" in entity_types:
                _update_job(job_id, stage="inbound jobs")
                offset = 0
                processed = 0
                while True:
                    opps_data = await client.list_objects("opportunities", limit=SYNC_PAGE_SIZE, offset=offset)
                    data_val = opps_data.get("data", [])
                    if isinstance(data_val, list):
                        opps = data_val
                    elif isinstance(data_val, dict):
                        inner = data_val.get("opportunities", data_val)
                        opps = inner.get("edges", inner) if isinstance(inner, dict) else inner if isinstance(inner, list) else []
                    else:
                        opps = []
                    if not opps:
                        break
                    for edge in opps:
                        opp = edge.get("node", edge)
                        processed += 1
                        try:
                            updated = await sync_job_inbound(db, client, opp)
                            if updated:
                                synced += 1
                        except Exception as exc:
                            failed += 1
                            logger.exception("Sync failed for inbound opportunity %s: %s", opp.get("id"), exc)
                        _update_job(job_id, processed=processed, synced=synced, failed=failed)
                    if len(opps) < SYNC_PAGE_SIZE:
                        break
                    offset += SYNC_PAGE_SIZE
                logger.info(
                    "Background sync (job=%s) inbound jobs complete: synced=%d, failed=%d",
                    job_id, synced, failed,
                )

        _update_job(job_id, status="completed")
        logger.info("Background Twenty sync (job=%s) complete: synced=%d, failed=%d", job_id, synced, failed)
    except Exception as exc:
        logger.exception("Background Twenty sync (job=%s) failed", job_id)
        _update_job(job_id, status="failed", error=str(exc))
    finally:
        db.close()


@router.post("/sync")
async def trigger_sync(
    payload: TwentySyncTrigger,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start a Twenty CRM sync as a background job.

    Returns immediately with a job_id that can be polled via GET /sync/{job_id}.
    """
    # Validate configuration before accepting the job.
    _get_client(db)

    job_id = str(uuid4())
    entity_types = payload.entity_types or ["customer", "job"]
    INTEGRATION_JOBS[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "direction": payload.direction,
        "entity_types": entity_types,
        "synced": 0,
        "failed": 0,
        "stage": None,
        "processed": 0,
        "total": None,
        "error": None,
    }
    background_tasks.add_task(_run_sync_job, job_id, payload)
    logger.info("Queued Twenty sync job %s", job_id)
    return {"job_id": job_id, "status": "pending"}


@router.get("/sync/{job_id}", response_model=TwentySyncJobStatus)
async def get_sync_job(job_id: str) -> dict:
    """Get the status of a background sync job."""
    job = INTEGRATION_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Sync job not found")
    return job


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
