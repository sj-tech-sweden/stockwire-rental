"""Read-only accessors for application settings (no router imports)."""
from __future__ import annotations

import json

from sqlalchemy import select

from app.domain.settings.models import AppSetting

COMPANY_PROFILE_KEY = "company.profile"


def get_company_profile_default_language(db) -> str:
    """Return the server's default language (from the company profile setting).

    Falls back to ``en`` when unset or unreadable.
    """
    setting = db.scalar(select(AppSetting).where(AppSetting.key == COMPANY_PROFILE_KEY))
    if setting and setting.value_json:
        try:
            return (json.loads(setting.value_json) or {}).get("default_language") or "en"
        except Exception:
            return "en"
    return "en"


def get_company_profile_currency(db) -> str:
    """Return the company's default currency (from the company profile setting).

    Falls back to ``SEK`` when unset or unreadable.
    """
    setting = db.scalar(select(AppSetting).where(AppSetting.key == COMPANY_PROFILE_KEY))
    if setting and setting.value_json:
        try:
            return (json.loads(setting.value_json) or {}).get("currency") or "SEK"
        except Exception:
            return "SEK"
    return "SEK"
