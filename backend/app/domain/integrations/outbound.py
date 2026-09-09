"""Outbound real-time sync for the Twenty CRM integration.

These helpers push Stockwire changes to Twenty CRM immediately (webhook-style)
instead of waiting for the next scheduled auto-sync. They are intended to be run
as FastAPI background tasks so the API response is not blocked by the outbound
HTTP call to Twenty.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def push_person_to_twenty(person_id: int) -> None:
    """Push a single Person to Twenty CRM if the integration is active.

    Mirrors the inbound webhook receiver (``twenty_webhook.py``) but in the
    opposite direction: when a Person is created or edited in Stockwire we
    forward the change to Twenty right away. Records that originated in Twenty
    (``external_origin == "twenty"``) are skipped by ``sync_person_outbound`` to
    avoid clobbering data owned by Twenty.
    """
    from app.db.session import SessionLocal
    from app.domain.customers.models import Person
    from app.domain.integrations.models import TwentyConfig
    from app.domain.integrations.sync_engine import sync_person_outbound
    from app.domain.integrations.twenty_client import TwentyClient

    db = SessionLocal()
    try:
        config = db.query(TwentyConfig).first()
        if not config or not config.is_active or not config.api_key:
            return

        person = db.get(Person, person_id)
        if person is None:
            return

        client = TwentyClient(api_key=config.api_key, base_url=config.base_url)
        try:
            await sync_person_outbound(db, client, person)
        except Exception:
            logger.exception(
                "Outbound webhook: failed to push person %s to Twenty", person_id
            )
    finally:
        db.close()
