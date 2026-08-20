"""Background scheduler for periodic Twenty CRM auto-sync."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_scheduler_thread: threading.Thread | None = None
_stop_event: threading.Event = threading.Event()
_lock = threading.Lock()

# How often the scheduler wakes up to check whether a sync is due (seconds)
_CHECK_INTERVAL_SECONDS = 60


def _run_twenty_sync_now() -> None:
    """Execute a full Two-way Twenty CRM sync in the current thread."""
    from app.db.session import SessionLocal
    from app.domain.integrations.models import TwentyConfig
    from app.domain.integrations.twenty_client import TwentyClient

    db = SessionLocal()
    try:
        config = db.query(TwentyConfig).first()
        if not config or not config.is_active or not config.api_key:
            return

        client = TwentyClient(api_key=config.api_key, base_url=config.base_url)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_do_sync(db, client))
        finally:
            loop.close()
    except Exception:
        logger.exception("Twenty auto-sync failed")
    finally:
        db.close()


async def _do_sync(db, client) -> None:
    from app.domain.customers.models import Customer
    from app.domain.integrations.sync_engine import (
        SYNC_PAGE_SIZE,
        sync_customer_inbound,
        sync_customer_outbound,
        sync_job_inbound,
        sync_job_outbound,
    )
    from app.domain.jobs.models import Job

    # Outbound: customers
    logger.info("Auto-sync stage: outbound customers")
    offset = 0
    processed = 0
    while True:
        customers = db.query(Customer).offset(offset).limit(SYNC_PAGE_SIZE).all()
        if not customers:
            break
        for customer in customers:
            processed += 1
            try:
                await sync_customer_outbound(db, client, customer)
                if processed % 10 == 0:
                    logger.info("Auto-sync outbound-customer: %d processed", processed)
            except Exception:
                logger.exception("Auto-sync: failed to sync customer %s", getattr(customer, "id", "?"))
        if len(customers) < SYNC_PAGE_SIZE:
            break
        offset += SYNC_PAGE_SIZE
    logger.info("Auto-sync stage complete: outbound customers (%d processed)", processed)

    # Outbound: jobs
    logger.info("Auto-sync stage: outbound jobs")
    offset = 0
    processed = 0
    while True:
        jobs = db.query(Job).offset(offset).limit(SYNC_PAGE_SIZE).all()
        if not jobs:
            break
        for job in jobs:
            processed += 1
            try:
                await sync_job_outbound(db, client, job)
                if processed % 10 == 0:
                    logger.info("Auto-sync outbound-job: %d processed", processed)
            except Exception:
                logger.exception("Auto-sync: failed to sync job %s", getattr(job, "id", "?"))
        if len(jobs) < SYNC_PAGE_SIZE:
            break
        offset += SYNC_PAGE_SIZE
    logger.info("Auto-sync stage complete: outbound jobs (%d processed)", processed)

    # Inbound: companies → customers
    logger.info("Auto-sync stage: inbound customers")
    # Pre-fetch all people once and build a company_id → person lookup to avoid
    # one API call per company during the loop below.
    people_by_company: dict[str, dict] = {}
    try:
        all_people = await client.search_people(email=None)
        for p_edge in all_people:
            p_node = p_edge.get("node", p_edge)
            comp = p_node.get("company") or {}
            if isinstance(comp, dict) and comp.get("id"):
                people_by_company.setdefault(comp["id"], p_node)
        logger.info("Auto-sync pre-fetched %d people", len(people_by_company))
    except Exception:
        logger.warning("Auto-sync: could not pre-fetch people; person matching will be skipped")

    offset = 0
    processed = 0
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
            processed += 1
            try:
                matched_person = people_by_company.get(company.get("id") or "")
                created = await sync_customer_inbound(db, client, company, matched_person)
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
                            "Auto-sync: failed to write back stockwire fields for company %s",
                            company.get("id"),
                        )
                if processed % 10 == 0:
                    logger.info("Auto-sync inbound-customer: %d processed", processed)
            except Exception:
                logger.exception("Auto-sync: failed inbound company %s", company.get("id"))
        if len(companies) < SYNC_PAGE_SIZE:
            break
        offset += SYNC_PAGE_SIZE
    logger.info("Auto-sync stage complete: inbound customers (%d processed)", processed)

    # Inbound: opportunities → jobs (only update existing Stockwire jobs)
    logger.info("Auto-sync stage: inbound jobs")
    offset = 0
    processed = 0
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
            processed += 1
            try:
                updated = await sync_job_inbound(db, client, opp)
                if processed % 10 == 0:
                    logger.info("Auto-sync inbound-job: %d processed (updated=%s)", processed, updated)
            except Exception:
                logger.exception("Auto-sync: failed inbound opportunity %s", opp.get("id"))
        if len(opps) < SYNC_PAGE_SIZE:
            break
        offset += SYNC_PAGE_SIZE
    logger.info("Auto-sync stage complete: inbound jobs (%d processed)", processed)


def _scheduler_loop() -> None:
    logger.info("Twenty CRM auto-sync scheduler started")
    while not _stop_event.is_set():
        try:
            _check_and_sync()
        except Exception:
            logger.exception("Twenty auto-sync scheduler encountered an error")
        _stop_event.wait(timeout=_CHECK_INTERVAL_SECONDS)
    logger.info("Twenty CRM auto-sync scheduler stopped")


def _check_and_sync() -> None:
    """Check whether a periodic sync is due and run it if so."""
    from app.db.session import SessionLocal
    from app.domain.integrations.models import TwentyConfig, TwentySyncLog

    db = SessionLocal()
    try:
        config = db.query(TwentyConfig).first()
        if not config or not config.is_active:
            return
        interval = config.sync_interval_minutes or 0
        if interval <= 0:
            return

        last_log = (
            db.query(TwentySyncLog)
            .filter(TwentySyncLog.status == "success")
            .order_by(TwentySyncLog.created_at.desc())
            .first()
        )

        now = datetime.now(timezone.utc)
        if last_log is None:
            # No successful sync yet – use config creation time as reference
            reference = config.created_at
        else:
            reference = last_log.created_at

        # Ensure reference is timezone-aware
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)

        next_sync = reference + timedelta(minutes=interval)
        if now >= next_sync:
            logger.info("Twenty CRM auto-sync: interval elapsed, running sync now")
            _run_twenty_sync_now()
    finally:
        db.close()


def start_twenty_auto_sync() -> None:
    """Start the background periodic-sync scheduler thread."""
    global _scheduler_thread

    with _lock:
        if _scheduler_thread is not None and _scheduler_thread.is_alive():
            return
        _stop_event.clear()
        _scheduler_thread = threading.Thread(
            target=_scheduler_loop,
            name="twenty-auto-sync",
            daemon=True,
        )
        _scheduler_thread.start()


def stop_twenty_auto_sync() -> None:
    """Signal the scheduler to stop and wait for it to finish."""
    global _scheduler_thread

    with _lock:
        _stop_event.set()
        thread = _scheduler_thread
        _scheduler_thread = None

    if thread is not None:
        thread.join(timeout=5)
