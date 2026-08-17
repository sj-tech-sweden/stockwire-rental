"""Seed predefined report templates."""

from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.domain.reports.models import ReportTemplate
from app.services.report_i18n import translate_flowables

logger = logging.getLogger(__name__)

_DEFAULT_TEMPLATES = [
    # ── Warehouse & Case Documents ──────────────────────────────────────────
    {
        "name": "Case Lid / Insert Manifest",
        "category": "warehouse",
        "description": "Compact 1-page breakdown showing contents, cables, accessories, and serial numbers packed inside a flight case.",
        "data_source_type": "device",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "CASE MANIFEST", "level": 1},
                {"type": "spacer", "height_mm": 3},
                {"type": "key_value", "source": "device", "fields": [
                    {"key": "asset_tag", "label": "Case ID"},
                    {"key": "serial_number", "label": "Serial Number"},
                    {"key": "status", "label": "Status"},
                ]},
                {"type": "key_value", "source": "product", "fields": [
                    {"key": "name", "label": "Product"},
                    {"key": "sku", "label": "SKU"},
                    {"key": "category", "label": "Category"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "heading", "text": "Contents", "level": 2},
                {"type": "table", "source": "device.case_contents", "columns": [
                    {"key": "product.sku", "label": "SKU"},
                    {"key": "product.name", "label": "Product"},
                    {"key": "serial_number", "label": "Serial Number"},
                    {"key": "condition", "label": "Condition"},
                ]},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
    {
        "name": "Case Contents Summary (No Serials)",
        "category": "warehouse",
        "description": "Compact 1-page breakdown showing product counts only (no serial numbers) for quick verification.",
        "data_source_type": "device",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "CASE CONTENTS", "level": 1},
                {"type": "spacer", "height_mm": 3},
                {"type": "key_value", "source": "device", "fields": [
                    {"key": "asset_tag", "label": "Case ID"},
                    {"key": "status", "label": "Status"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "heading", "text": "Contents", "level": 2},
                {"type": "table", "source": "device.case_contents_grouped", "columns": [
                    {"key": "sku", "label": "SKU"},
                    {"key": "name", "label": "Product"},
                    {"key": "count", "label": "Qty"},
                ]},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
    {
        "name": "Kit Component Breakdown",
        "category": "warehouse",
        "description": "Expands grouped bundle SKUs into granular parts lists (e.g., tent poles, sidewalls, pegs, joints).",
        "data_source_type": "product",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "KIT COMPONENT BREAKDOWN", "level": 1},
                {"type": "key_value", "source": "product", "fields": [
                    {"key": "name", "label": "Kit Name"},
                    {"key": "sku", "label": "SKU"},
                    {"key": "category", "label": "Category"},
                    {"key": "brand", "label": "Brand"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "heading", "text": "Components", "level": 2},
                {"type": "table", "source": "product.components", "columns": [
                    {"key": "product.sku", "label": "SKU"},
                    {"key": "product.name", "label": "Component"},
                    {"key": "quantity", "label": "Qty"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "heading", "text": "Accessories", "level": 2},
                {"type": "table", "source": "product.accessories", "columns": [
                    {"key": "product.sku", "label": "SKU"},
                    {"key": "product.name", "label": "Accessory"},
                    {"key": "quantity", "label": "Qty"},
                    {"key": "required", "label": "Required"},
                ]},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
    {
        "name": "Zone-Based Pick List",
        "category": "warehouse",
        "description": "Grouped and ordered by warehouse shelf/rack location for efficient pick paths.",
        "data_source_type": "inventory",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "ZONE-BASED PICK LIST", "level": 1},
                {"type": "paragraph", "text": "Items grouped by warehouse zone for efficient picking.", "style": "small"},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "table", "source": "products", "columns": [
                    {"key": "sku", "label": "SKU"},
                    {"key": "name", "label": "Product"},
                    {"key": "category", "label": "Category"},
                ]},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
    {
        "name": "Return Check-In & Missing Items Audit",
        "category": "warehouse",
        "description": "Scan sheet used during check-in to mark returned items and record missing accessories.",
        "data_source_type": "job",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "RETURN CHECK-IN AUDIT", "level": 1},
                {"type": "key_value", "source": "job", "fields": [
                    {"key": "job_code", "label": "Job Code"},
                    {"key": "customer_name", "label": "Customer"},
                    {"key": "start_date", "label": "Rental Start"},
                    {"key": "end_date", "label": "Rental End"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "paragraph", "text": "Mark each item as: OK / Missing / Damaged", "style": "bold"},
                {"type": "spacer", "height_mm": 2},
                {"type": "table", "source": "job.requirements", "columns": [
                    {"key": "product.sku", "label": "SKU"},
                    {"key": "product.name", "label": "Product"},
                    {"key": "quantity_required", "label": "Qty"},
                    {"key": "quantity_picked", "label": "Returned"},
                ]},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
    {
        "name": "Vehicle Load & Weight Summary",
        "category": "warehouse",
        "description": "Aggregated weight, volume, and case count calculations for transport compliance.",
        "data_source_type": "job",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "VEHICLE LOAD SUMMARY", "level": 1},
                {"type": "key_value", "source": "job", "fields": [
                    {"key": "job_code", "label": "Job Code"},
                    {"key": "customer_name", "label": "Customer"},
                    {"key": "venue_name", "label": "Venue"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "heading", "text": "Required Gear", "level": 2},
                {"type": "table", "source": "job.requirements", "columns": [
                    {"key": "product.sku", "label": "SKU"},
                    {"key": "product.name", "label": "Product"},
                    {"key": "quantity_required", "label": "Qty"},
                    {"key": "product.weight_kg", "label": "Unit Weight (kg)"},
                ]},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
    # ── Asset Management & Operations ───────────────────────────────────────
    {
        "name": "Asset Utilization & Idle Stock",
        "category": "asset",
        "description": "Analysis of gear usage ratios over time to highlight high-performing items vs. dead stock.",
        "data_source_type": "inventory",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "ASSET UTILIZATION REPORT", "level": 1},
                {"type": "paragraph", "text": "Gear usage analysis comparing active vs. idle stock.", "style": "small"},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "table", "source": "devices", "columns": [
                    {"key": "asset_tag", "label": "Asset Tag"},
                    {"key": "status", "label": "Status"},
                    {"key": "condition", "label": "Condition"},
                ]},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
    {
        "name": "Overdue & Unreturned Items",
        "category": "asset",
        "description": "Active list of unreturned gear grouped by customer and job, showing days overdue.",
        "data_source_type": "inventory",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "OVERDUE & UNRETURNED ITEMS", "level": 1},
                {"type": "paragraph", "text": "Items currently outstanding, grouped by customer.", "style": "small"},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "table", "source": "devices", "columns": [
                    {"key": "asset_tag", "label": "Asset Tag"},
                    {"key": "status", "label": "Status"},
                    {"key": "condition", "label": "Condition"},
                ]},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
    {
        "name": "Damage & Maintenance Log",
        "category": "asset",
        "description": "Historical report of gear returned broken, repair costs, and safety inspection schedules.",
        "data_source_type": "device",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "DAMAGE & MAINTENANCE LOG", "level": 1},
                {"type": "key_value", "source": "device", "fields": [
                    {"key": "asset_tag", "label": "Asset Tag"},
                    {"key": "serial_number", "label": "Serial Number"},
                    {"key": "status", "label": "Status"},
                    {"key": "condition", "label": "Condition"},
                ]},
                {"type": "key_value", "source": "product", "fields": [
                    {"key": "name", "label": "Product"},
                    {"key": "sku", "label": "SKU"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "heading", "text": "Maintenance Records", "level": 2},
                {"type": "table", "source": "device.maintenance_records", "columns": [
                    {"key": "maintenance_type", "label": "Type"},
                    {"key": "status", "label": "Status"},
                    {"key": "scheduled_date", "label": "Scheduled"},
                    {"key": "completed_date", "label": "Completed"},
                    {"key": "notes", "label": "Notes"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "heading", "text": "Defect Reports", "level": 2},
                {"type": "table", "source": "device.defect_reports", "columns": [
                    {"key": "title", "label": "Title"},
                    {"key": "status", "label": "Status"},
                    {"key": "severity", "label": "Severity"},
                    {"key": "created_at", "label": "Reported"},
                ]},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
    # ── Logistics & Customer Handover ───────────────────────────────────────
    {
        "name": "On-Site Handover & Delivery Sign-Off",
        "category": "logistics",
        "description": "Delivery receipt with site condition notes and customer signature line.",
        "data_source_type": "job",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "DELIVERY HANDOVER", "level": 1},
                {"type": "key_value", "source": "job", "fields": [
                    {"key": "job_code", "label": "Job Code"},
                    {"key": "customer_name", "label": "Customer"},
                    {"key": "venue_name", "label": "Venue"},
                    {"key": "start_date", "label": "Delivery Date"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "heading", "text": "Items Delivered", "level": 2},
                {"type": "table", "source": "job.requirements", "columns": [
                    {"key": "product.sku", "label": "SKU"},
                    {"key": "product.name", "label": "Product"},
                    {"key": "quantity_required", "label": "Qty"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "heading", "text": "Signature", "level": 2},
                {"type": "paragraph", "text": "Received by: ________________________   Date: ____________"},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
    {
        "name": "Job Summary Card",
        "category": "logistics",
        "description": "Compact job overview using side-by-side columns and centered headings.",
        "data_source_type": "job",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "JOB SUMMARY", "level": 1, "align": "center"},
                {"type": "spacer", "height_mm": 2},
                {
                    "type": "columns",
                    "widths": ["50%", "50%"],
                    "columns": [
                        [
                            {"type": "heading", "text": "Customer", "level": 2},
                            {"type": "paragraph", "text": "{{ job.customer_name }}", "style": "body"},
                            {"type": "paragraph", "text": "{{ job.venue_name }}", "style": "small"},
                        ],
                        [
                            {"type": "heading", "text": "Dates", "level": 2, "align": "right"},
                            {"type": "paragraph", "text": "Start: {{ job.start_date }}", "style": "body", "align": "right"},
                            {"type": "paragraph", "text": "End: {{ job.end_date }}", "style": "body", "align": "right"},
                        ],
                    ],
                },
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small", "align": "center"},
            ],
        }),
    },
    {
        "name": "Venue Compliance & Safety Packet",
        "category": "logistics",
        "description": "Aggregated packet bundling safety certificates and inspection records attached to booked equipment.",
        "data_source_type": "job",
        "body_json": json.dumps({
            "page_size": "A4",
            "flowables": [
                {"type": "heading", "text": "VENUE COMPLIANCE & SAFETY PACKET", "level": 1},
                {"type": "key_value", "source": "job", "fields": [
                    {"key": "job_code", "label": "Job Code"},
                    {"key": "customer_name", "label": "Customer"},
                    {"key": "venue_name", "label": "Venue"},
                    {"key": "start_date", "label": "Event Date"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "line"},
                {"type": "heading", "text": "Booked Equipment", "level": 2},
                {"type": "table", "source": "job.requirements", "columns": [
                    {"key": "product.sku", "label": "SKU"},
                    {"key": "product.name", "label": "Product"},
                    {"key": "quantity_required", "label": "Qty"},
                ]},
                {"type": "spacer", "height_mm": 3},
                {"type": "paragraph", "text": "This packet includes safety certificates and inspection records for all equipment at this venue.", "style": "small"},
                {"type": "spacer", "height_mm": 5},
                {"type": "paragraph", "text": "Generated: {{ now }}", "style": "small"},
            ],
        }),
    },
]


def _build_translations(body_json: str) -> str:
    """Generate a Swedish translation of the template flowables.

    The base body_json is treated as English. We store a full Swedish variant so
    the same template can render in either language.
    """
    try:
        body = json.loads(body_json) if body_json else {}
    except Exception:
        return "{}"
    flowables = body.get("flowables", [])
    if not flowables:
        return "{}"
    translated = translate_flowables(flowables, "sv")
    return json.dumps({"sv": {"flowables": translated}}, ensure_ascii=False)


def seed_report_templates(db: Session) -> int:
    """Insert or update default report templates. Returns count of changed rows."""
    existing = {
        row.name: row
        for row in db.query(ReportTemplate).all()
    }
    changed = 0
    for tmpl in _DEFAULT_TEMPLATES:
        existing_tmpl = existing.get(tmpl["name"])
        translations_json = tmpl.get("translations_json") or _build_translations(tmpl.get("body_json", "{}"))
        if existing_tmpl:
            # Update builtin templates so seeded improvements are rolled out
            if existing_tmpl.is_builtin:
                existing_tmpl.category = tmpl["category"]
                existing_tmpl.description = tmpl.get("description")
                existing_tmpl.body_json = tmpl["body_json"]
                existing_tmpl.translations_json = translations_json
                existing_tmpl.data_source_type = tmpl["data_source_type"]
                changed += 1
            continue
        db.add(ReportTemplate(
            name=tmpl["name"],
            category=tmpl["category"],
            description=tmpl.get("description"),
            body_json=tmpl["body_json"],
            translations_json=translations_json,
            data_source_type=tmpl["data_source_type"],
            is_builtin=True,
            is_enabled=True,
        ))
        changed += 1
    if changed:
        db.commit()
    return changed
