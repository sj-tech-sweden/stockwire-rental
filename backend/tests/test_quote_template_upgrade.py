"""Verify an existing old-style Quote template is upgraded in place."""
import json

from app.domain.quotes.templates import ensure_default_quote_template
from app.domain.reports.models import ReportTemplate


OLD_BODY = {
    "page_size": "A4",
    "margin_top_mm": 20,
    "margin_bottom_mm": 20,
    "margin_left_mm": 20,
    "margin_right_mm": 20,
    "flowables": [
        {"type": "heading", "level": 1, "text": "Quote {{ quote.quote_no }}"},
        {"type": "paragraph", "text": "Date: {{ quote.quote_date }}"},
        {"type": "paragraph", "text": "{{ customer.name if customer else (job.customer_name or '') }}"},
        {
            "type": "heading",
            "level": 2,
            "text": "Equipment & Items",
        },
        {
            "type": "table",
            "source": "quote_lines",
            "columns": [
                {"key": "name", "label": "Item", "width_mm": 70},
                {"key": "sku", "label": "SKU", "width_mm": 35},
                {"key": "quantity", "label": "Qty", "width_mm": 18},
                {"key": "unit_price", "label": "Unit Price", "width_mm": 30},
                {"key": "line_total", "label": "Total", "width_mm": 30},
            ],
        },
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


def test_upgrade_existing_old_quote_template(db_session):
    old = ReportTemplate(
        name="Quote",
        category="custom",
        description="old",
        body_json=json.dumps(OLD_BODY),
        data_source_type="job",
        is_builtin=True,
        is_enabled=True,
        use_letterhead=False,
    )
    db_session.add(old)
    db_session.commit()

    tpl = ensure_default_quote_template(db_session)
    body = json.loads(tpl.body_json)

    # standalone currency row removed from totals
    quote_kv = next(
        f for f in body["flowables"] if f.get("type") == "key_value" and f.get("source") == "quote"
    )
    assert not any(f["key"] == "currency" for f in quote_kv["fields"])

    # equipment table has Type + Days
    equip = next(
        f for f in body["flowables"] if f.get("type") == "table" and f.get("source") == "quote_lines"
    )
    keys = {c["key"] for c in equip["columns"]}
    assert "source_type" in keys and "days" in keys

    # swedish translation still exists
    assert "sv" in (json.loads(tpl.translations_json) if tpl.translations_json else {})
