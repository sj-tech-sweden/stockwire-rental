"""Automatic FX rate synchronisation.

Keeps the ``fx_rates`` app setting current by periodically fetching from a free
provider (frankfurter.app) and writing the result back. The provider returns
rates as "amount of CUR per 1 base"; the app's convention is the inverse
("value of 1 CUR in base"), so fetched rates are inverted before storing.

A lightweight daemon thread (mirroring the Twenty CRM auto-sync scheduler)
runs the periodic refresh; a manual refresh is also exposed via the settings
API.
"""

import json
import logging
import threading
import time
from typing import Any

import httpx
from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.settings.accessors import get_company_profile_currency
from app.domain.settings.models import AppSetting

logger = logging.getLogger(__name__)

FX_RATES_KEY = "fx_rates"
FX_PROVIDER_URL = "https://api.frankfurter.dev/v1/latest"
FX_SYNC_INTERVAL_SECONDS = 24 * 60 * 60  # daily
FX_AUTO_SYNC_DEFAULT = True

_lock = threading.Lock()
_stop_event = threading.Event()
_thread: threading.Thread | None = None


def fetch_fx_rates(base: str = "EUR") -> dict[str, Any] | None:
    """Fetch latest rates for ``base`` and convert to the app's convention.

    Returns ``{"base": base, "rates": {CUR: base_per_1_cur}}`` or ``None`` on
    failure.
    """
    base = (base or "EUR").strip().upper()
    try:
        resp = httpx.get(
            FX_PROVIDER_URL,
            params={"from": base},
            timeout=10.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # network/provider errors must not crash the scheduler
        logger.warning(f"FX fetch failed: {exc}")
        return None
    frank = (payload or {}).get("rates") or {}
    if not frank:
        return None
    rates: dict[str, float] = {}
    for cur, val in frank.items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if v == 0:
            continue
        # Provider gives CUR per 1 base; invert to base per 1 CUR.
        rates[cur.upper()] = round(1.0 / v, 6)
    return {"base": base, "rates": rates}


def refresh_fx_rates(db: Any | None = None) -> dict[str, Any] | None:
    """Fetch fresh rates and persist them, preserving any manually-added
    currencies the provider does not cover. Returns the stored data or None.
    """
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        existing = db.scalar(select(AppSetting).where(AppSetting.key == FX_RATES_KEY))
        # The FX base is the company's reporting currency, not a hard-coded
        # EUR. This keeps converted PO totals in the user's own currency.
        company_currency = "SEK"
        try:
            company_currency = (get_company_profile_currency(db) or "SEK").strip().upper() or "SEK"
        except Exception:
            # Fall back to the default reporting currency if the profile lookup fails.
            pass
        base = company_currency

        fetched = fetch_fx_rates(base)
        if not fetched:
            return None

        # Keep manually-entered currencies the provider doesn't return, but
        # only when the base did not change (rates are relative to the base).
        if existing and existing.value_json:
            try:
                prev = json.loads(existing.value_json) or {}
                if str(prev.get("base", "")).upper() == base:
                    for k, v in (prev.get("rates") or {}).items():
                        k = str(k).upper()
                        if k not in fetched["rates"]:
                            try:
                                fetched["rates"][k] = float(v)
                            except (TypeError, ValueError):
                                # Skip manual currency entries whose stored value is not numeric.
                                pass
            except Exception:
                # Ignore corrupt/unparseable persisted rates; refresh from scratch.
                pass

        data = {"base": base, "rates": fetched["rates"]}
        if existing is None:
            existing = AppSetting(key=FX_RATES_KEY, value_json="{}")
            db.add(existing)
        existing.value_json = json.dumps(data)
        db.commit()
        logger.info(f"FX rates refreshed (base {base}, {len(data['rates'])} currencies)")
        return data
    finally:
        if own_session:
            db.close()


def _fx_loop() -> None:
    while not _stop_event.is_set():
        # Sleep in small increments so shutdown is prompt.
        for _ in range(0, FX_SYNC_INTERVAL_SECONDS, 30):
            if _stop_event.is_set():
                return
            time.sleep(30)
        try:
            refresh_fx_rates()
        except Exception as exc:  # never let the scheduler die
            logger.warning(f"FX auto-sync error: {exc}")


def start_fx_auto_sync() -> None:
    """Start the background periodic FX-refresh thread."""
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _stop_event.clear()
        _thread = threading.Thread(target=_fx_loop, name="fx-auto-sync", daemon=True)
        _thread.start()


def stop_fx_auto_sync() -> None:
    """Stop the background thread and wait for it to finish."""
    global _thread
    with _lock:
        _stop_event.set()
        thread = _thread
        _thread = None
    if thread is not None:
        thread.join(timeout=5)
