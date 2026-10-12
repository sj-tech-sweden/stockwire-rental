"""Quotes subsystem: settings accessor and shared helpers."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from app.domain.settings.models import AppSetting

QUOTES_KEY = "quotes"
DEFAULT_QUOTES: dict[str, Any] = {
    "default_markup_pct": 30.0,
    "vat_rate": 0.25,
}


def get_quotes_settings(db) -> dict[str, Any]:
    """Return the effective quotes settings, merging stored values over defaults."""
    setting = db.scalar(select(AppSetting).where(AppSetting.key == QUOTES_KEY))
    data = dict(DEFAULT_QUOTES)
    if setting and setting.value_json:
        try:
            parsed = json.loads(setting.value_json) or {}
        except Exception:
            parsed = {}
        for key in DEFAULT_QUOTES:
            if key in parsed and parsed[key] is not None:
                data[key] = parsed[key]
    return data
