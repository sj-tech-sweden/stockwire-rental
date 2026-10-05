"""Default, editable Quote report template and idempotent seeding helper."""
from __future__ import annotations

import json

from sqlalchemy import select

from app.domain.reports.models import ReportTemplate
from app.services.report_i18n import translate_flowables

DEFAULT_QUOTE_TEMPLATE_NAME = "Quote"

# Equipment table on the quote template. Includes a Type (Rental/Purchase) column
# and a Days column so rental pricing (per-day x days x quantity) is explicit.
QUOTE_EQUIPMENT_COLUMNS = [
    {"key": "source_type", "label": "Type", "width_mm": 18, "translate_value": True},
    {"key": "name", "label": "Item", "width_mm": 54},
    {"key": "sku", "label": "SKU", "width_mm": 24},
    {"key": "quantity", "label": "Qty", "width_mm": 12},
    {"key": "days", "label": "Days", "width_mm": 12},
    {"key": "unit_price", "label": "Unit Price", "width_mm": 24},
    {"key": "line_total", "label": "Total", "width_mm": 24},
]


DEFAULT_QUOTE_TEMPLATE_BODY: dict = {
    "page_size": "A4",
    "margin_top_mm": 20,
    "margin_bottom_mm": 20,
    "margin_left_mm": 20,
    "margin_right_mm": 20,
    "flowables": [
        {
            "type": "heading",
            "level": 1,
            "text": "Quote {{ quote.quote_no }}",
        },
        {
            "type": "paragraph",
            "text": "Date: {{ quote.quote_date }}",
        },
        {
            "type": "paragraph",
            "text": "Customer: {{ customer.name if customer else (job.customer_name or '') }}{% if customer and customer.email %} — {{ customer.email }}{% endif %}{% if customer and customer.phone %} — {{ customer.phone }}{% endif %}",
        },
        {
            "type": "paragraph",
            "text": "{% if venue %}Venue: {{ venue.name }}{% if venue.address %}, {{ venue.address }}{% endif %}{% endif %}",
        },
        {
            "type": "paragraph",
            "text": "Period: {{ job.start_date }} – {{ job.end_date }} ({{ job.rental_days }} days)",
        },
        {
            "type": "paragraph",
            "text": "{% if job.description %}Description: {{ job.description }}{% endif %}",
        },
        {
            "type": "paragraph",
            "text": "{% if job.notes %}Notes: {{ job.notes }}{% endif %}",
        },
        {
            "type": "heading",
            "level": 2,
            "text": "Equipment & Items",
        },
        {
            "type": "paragraph",
            "text": "Rental equipment is priced per day for the rental period above (Total = Rate/day x Days x Quantity). Purchased items are priced per unit.",
        },
        {
            "type": "table",
            "source": "quote_lines",
            "columns": QUOTE_EQUIPMENT_COLUMNS,
        },
        {
            "type": "heading",
            "level": 2,
            "text": "Labour",
        },
        {
            "type": "table",
            "source": "crew_lines",
            "columns": [
                {"key": "role_name", "label": "Role", "width_mm": 55},
                {"key": "quantity", "label": "Qty", "width_mm": 15},
                {"key": "days", "label": "Days", "width_mm": 18},
                {"key": "hours", "label": "Hours", "width_mm": 20},
                {"key": "rate", "label": "Rate", "width_mm": 30},
                {"key": "line_total", "label": "Total", "width_mm": 30},
            ],
        },
        {"type": "spacer", "height_mm": 6},
        {
            "type": "key_value",
            "source": "quote",
            "fields": [
                {"key": "subtotal", "label": "Subtotal"},
                {"key": "vat_rate", "label": "VAT Rate"},
                {"key": "vat_amount", "label": "VAT"},
                {"key": "total", "label": "Total"},
            ],
        },
    ],
}


def ensure_default_quote_template(db) -> ReportTemplate:
    """Return the default Quote template, creating it if it does not exist."""
    existing = db.scalar(
        select(ReportTemplate).where(
            ReportTemplate.name == DEFAULT_QUOTE_TEMPLATE_NAME,
            ReportTemplate.category == "custom",
        )
    )
    if existing:
        # Keep the quote template explicitly opted out of the system default
        # letterhead (it is configured without one).
        if existing.use_letterhead is not False:
            existing.use_letterhead = False
            db.commit()
            db.refresh(existing)
        # Non-destructively refresh older quote template bodies (labour table,
        # currency field, equipment Type/Days columns). Whenever the body changes,
        # regenerate the Swedish translation so translated quotes stay in sync.
        body_changed = False
        if _upgrade_quote_labour_table(existing):
            body_changed = True
        if _upgrade_quote_currency(existing):
            body_changed = True
        if _upgrade_quote_equipment_columns(existing):
            body_changed = True
        if body_changed:
            db.commit()
            db.refresh(existing)
            existing.translations_json = _build_quote_sv_translations(existing.body_json)
            db.commit()
            db.refresh(existing)
        # Ensure a Swedish translation exists so the template shows as bilingual.
        if not _has_sv_translation(existing.translations_json):
            existing.translations_json = _build_quote_sv_translations(existing.body_json)
            db.commit()
            db.refresh(existing)
        return existing
    template = ReportTemplate(
        name=DEFAULT_QUOTE_TEMPLATE_NAME,
        category="custom",
        description="Default editable quote document (equipment, items and labour).",
        body_json=json.dumps(DEFAULT_QUOTE_TEMPLATE_BODY),
        translations_json=_build_quote_sv_translations(json.dumps(DEFAULT_QUOTE_TEMPLATE_BODY)),
        data_source_type="job",
        is_builtin=True,
        is_enabled=True,
        use_letterhead=False,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def _has_sv_translation(translations_json: str | None) -> bool:
    if not translations_json:
        return False
    try:
        parsed = json.loads(translations_json)
    except (ValueError, TypeError):
        return False
    return isinstance(parsed, dict) and "sv" in parsed


# Layout for the labour table on the quote template, kept here so it can be
# applied both on creation and when upgrading older quote templates.
QUOTE_LABOUR_COLUMNS = [
    {"key": "role_name", "label": "Role", "width_mm": 55},
    {"key": "quantity", "label": "Qty", "width_mm": 15},
    {"key": "days", "label": "Days", "width_mm": 18},
    {"key": "hours", "label": "Hours", "width_mm": 20},
    {"key": "rate", "label": "Rate", "width_mm": 30},
    {"key": "line_total", "label": "Total", "width_mm": 30},
]


def _upgrade_quote_labour_table(template: "ReportTemplate") -> bool:
    """Refresh the crew_lines (labour) table columns without touching the rest
    of the template body, so daily-rate support is reflected on existing quotes.
    Returns True when the body was modified (caller must commit)."""
    if not template.body_json:
        return False
    try:
        body = json.loads(template.body_json)
    except (ValueError, TypeError):
        return False
    changed = False
    flowables = body.get("flowables", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    for flowable in flowables:
        if (
            isinstance(flowable, dict)
            and flowable.get("type") == "table"
            and flowable.get("source") == "crew_lines"
        ):
            columns = flowable.get("columns") or []
            keys = {c.get("key") for c in columns}
            if "days" not in keys or "hourly_rate" in keys:
                flowable["columns"] = QUOTE_LABOUR_COLUMNS
                changed = True
    if changed:
        template.body_json = json.dumps(body)
    return changed


def _upgrade_quote_currency(template: "ReportTemplate") -> bool:
    """Remove the standalone currency row from quote totals.

    Currency is now shown together with each price value, so the separate
    key-value row is redundant. Returns True when the body was modified.
    """
    if not template.body_json:
        return False
    try:
        body = json.loads(template.body_json)
    except (ValueError, TypeError):
        return False
    flowables = body.get("flowables", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    changed = False
    for flowable in flowables:
        if (
            isinstance(flowable, dict)
            and flowable.get("type") == "key_value"
            and flowable.get("source") == "quote"
        ):
            fields = flowable.get("fields") or []
            new_fields = [f for f in fields if f.get("key") != "currency"]
            if len(new_fields) != len(fields):
                flowable["fields"] = new_fields
                changed = True
    if changed:
        template.body_json = json.dumps(body)
    return changed


def _upgrade_quote_equipment_columns(template: "ReportTemplate") -> bool:
    """Ensure the equipment table exposes the Rental/Purchase Type and Days
    columns so per-day rental pricing is explicit on existing quotes.

    Returns True when the body was modified (caller must commit)."""
    if not template.body_json:
        return False
    try:
        body = json.loads(template.body_json)
    except (ValueError, TypeError):
        return False
    flowables = body.get("flowables", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    changed = False
    for flowable in flowables:
        if (
            isinstance(flowable, dict)
            and flowable.get("type") == "table"
            and flowable.get("source") == "quote_lines"
        ):
            columns = flowable.get("columns") or []
            keys = {c.get("key") for c in columns}
            if "source_type" not in keys or "days" not in keys:
                flowable["columns"] = QUOTE_EQUIPMENT_COLUMNS
                changed = True
    if changed:
        template.body_json = json.dumps(body)
    return changed


def _build_quote_sv_translations(body_json_str: str) -> str:
    """Build a Swedish translation variant of the quote body (matching the way
    seeded report templates are made bilingual), so the quote template shows up
    as available in both English and Swedish."""
    try:
        body = json.loads(body_json_str) if body_json_str else {}
    except (ValueError, TypeError):
        return json.dumps({"sv": {"flowables": []}}, ensure_ascii=False)
    flowables = body.get("flowables", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    translated = translate_flowables(flowables, "sv")
    return json.dumps({"sv": {"flowables": translated}}, ensure_ascii=False)
