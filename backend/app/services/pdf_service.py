"""PDF report generation engine using ReportLab + pypdf."""

from __future__ import annotations

import io
import json
import logging
from datetime import date
from typing import Any

from jinja2.sandbox import SandboxedEnvironment
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, A3, LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from app.config import settings
from app.services.report_i18n import get_translator, translate_flowables

logger = logging.getLogger(__name__)

_jinja_env = SandboxedEnvironment()

MM_TO_PT = 2.83465

PAGE_SIZES = {
    "A4": A4,
    "A3": A3,
    "LETTER": LETTER,
}

CATEGORY_LABELS = {
    "warehouse": "Warehouse & Case Documents",
    "asset": "Asset Management & Operations",
    "logistics": "Logistics & Customer Handover",
    "custom": "Custom Templates",
}


def _resolve_value(obj: Any, path: str) -> Any:
    """Resolve a dotted path like 'product.name' against an object or dict."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    return current


def _render_jinja(text: str, context: dict) -> str:
    """Render a Jinja2 template string with the given context."""
    if not text:
        return ""
    try:
        return _jinja_env.from_string(text).render(**context)
    except Exception as exc:
        logger.warning("Jinja render error: %s", exc)
        return text


def _alignment_value(align: str | None) -> int:
    """Map alignment name to ReportLab alignment constant."""
    align_map = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT}
    return align_map.get(str(align).lower().strip(), TA_LEFT)


def _halign(align: str | None) -> str:
    """Map alignment name to ReportLab table hAlign value."""
    value = str(align).lower().strip() if align else "left"
    return {"left": "LEFT", "center": "CENTER", "right": "RIGHT"}.get(value, "LEFT")


def _style_with_alignment(base_style: ParagraphStyle, align: str | None) -> ParagraphStyle:
    """Return a style variant with the requested alignment."""
    if not align:
        return base_style
    target = _alignment_value(align)
    if base_style.alignment == target:
        return base_style
    name = f"{base_style.name}_align_{align}"
    return ParagraphStyle(name, parent=base_style, alignment=target)


def _build_styles(custom_styles: dict | None = None) -> dict[str, ParagraphStyle]:
    """Build ReportLab paragraph styles from JSON definition."""
    base = getSampleStyleSheet()
    styles = {
        "heading1": ParagraphStyle(
            "Heading1Custom", parent=base["Heading1"],
            fontSize=16, leading=20, spaceAfter=4 * mm, spaceBefore=2 * mm,
        ),
        "heading2": ParagraphStyle(
            "Heading2Custom", parent=base["Heading2"],
            fontSize=13, leading=16, spaceAfter=3 * mm, spaceBefore=1.5 * mm,
        ),
        "heading3": ParagraphStyle(
            "Heading3Custom", parent=base["Heading3"],
            fontSize=11, leading=14, spaceAfter=2 * mm, spaceBefore=1 * mm,
        ),
        "body": ParagraphStyle(
            "BodyCustom", parent=base["Normal"],
            fontSize=10, leading=13, spaceAfter=2 * mm,
        ),
        "bold": ParagraphStyle(
            "BoldCustom", parent=base["Normal"],
            fontSize=10, leading=13, spaceAfter=2 * mm,
            fontName="Helvetica-Bold",
        ),
        "small": ParagraphStyle(
            "SmallCustom", parent=base["Normal"],
            fontSize=8, leading=10, spaceAfter=1 * mm,
            textColor=colors.HexColor("#666666"),
        ),
        "center": ParagraphStyle(
            "CenterCustom", parent=base["Normal"],
            fontSize=10, leading=13, alignment=TA_CENTER,
        ),
    }
    if custom_styles:
        for name, props in custom_styles.items():
            if name in styles:
                for key, value in props.items():
                    if key == "font_size":
                        styles[name].fontSize = value
                    elif key == "bold":
                        styles[name].fontName = "Helvetica-Bold" if value else "Helvetica"
                    elif key == "text_color":
                        styles[name].setTextColor(colors.HexColor(value))
                    elif key == "space_after_mm":
                        styles[name].spaceAfter = value * mm
                    elif key == "space_before_mm":
                        styles[name].spaceBefore = value * mm
                    elif key == "alignment":
                        styles[name].alignment = _alignment_value(value)
    return styles


def _build_table(flowable_def: dict, context: dict, styles: dict, align: str | None = None, language: str | None = None) -> list:
    """Build a ReportLab Table from a flowable definition."""
    source_path = flowable_def.get("source", "")
    data = _resolve_value(context, source_path)
    _ = get_translator(language)
    if not isinstance(data, list) or not data:
        return [Paragraph(f"<i>{_('no_data')}</i>", styles["small"])]

    columns = flowable_def.get("columns", [])
    if not columns:
        return []

    # Build header row
    header = [_render_jinja(col.get("label", col.get("key", "")), context) for col in columns]

    # Build data rows
    rows = [header]
    for item in data:
        row = []
        for col in columns:
            val = _resolve_value(item, col.get("key", ""))
            cell_text = _render_jinja(str(col.get("format", "{{ value }}")), {"value": val})
            if not cell_text or cell_text == "None":
                cell_text = "—"
            row.append(cell_text)
        rows.append(row)

    # Calculate column widths
    page_width = A4[0]
    available_width = page_width - 40 * mm
    col_widths = []
    remaining = available_width
    defined_count = 0
    for col in columns:
        w = col.get("width_mm")
        if w:
            col_widths.append(w * mm)
            remaining -= w * mm
            defined_count += 1
    if defined_count < len(columns):
        auto_width = remaining / (len(columns) - defined_count) if (len(columns) - defined_count) > 0 else remaining
        final_widths = []
        ci = 0
        for col in columns:
            if col.get("width_mm"):
                final_widths.append(col_widths[ci])
                ci += 1
            else:
                final_widths.append(auto_width)
        col_widths = final_widths

    # Convert strings to Paragraphs for word wrapping
    table_data = []
    for ri, row in enumerate(rows):
        table_row = []
        for ci, cell in enumerate(row):
            if ri == 0:
                table_row.append(Paragraph(f"<b>{cell}</b>", styles["body"]))
            else:
                table_row.append(Paragraph(str(cell), styles["body"]))
        table_data.append(table_row)

    table = Table(table_data, colWidths=col_widths if col_widths else None, repeatRows=1, hAlign=_halign(align))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
    ]))
    return [table]


def _build_key_value_table(flowable_def: dict, context: dict, styles: dict, align: str | None = None, language: str | None = None) -> list:
    """Build a key-value grid (2-column label:value table)."""
    source_path = flowable_def.get("source", "")
    source_data = _resolve_value(context, source_path) or context
    fields = flowable_def.get("fields", [])

    rows = []
    for field in fields:
        label = field.get("label", field.get("key", ""))
        key = field.get("key", "")
        val = _resolve_value(source_data, key) if isinstance(source_data, dict) else None
        if val is None:
            val = "—"
        rows.append([
            Paragraph(f"<b>{label}</b>", styles["body"]),
            Paragraph(str(val), styles["body"]),
        ])

    if not rows:
        return []

    table = Table(rows, colWidths=[50 * mm, None], hAlign=_halign(align))
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e0e0e0")),
    ]))
    return [table]


class PDFService:
    def __init__(self, db):
        self.db = db

    def _translator(self, language: str | None):
        return get_translator(language)

    def _translate_flowables(self, flowables: list[dict], language: str | None) -> list[dict]:
        """Translate fixed labels/headings in builtin templates while leaving custom text untouched."""
        return translate_flowables(flowables, language)

    def generate_report(
        self,
        template_id: int,
        entity_type: str,
        entity_id: int,
        fmt: str = "pdf",
        language: str | None = None,
    ) -> bytes:
        """Legacy method — use generate_pdf/generate_csv/generate_html instead."""
        return self.generate_pdf(template_id, entity_type, entity_id, language=language)

    def _resolve_body(self, template, language: str | None = None) -> dict:
        """Return the effective body JSON for the requested language.

        The base body_json is treated as the default (English) version. If
        translations_json contains an entry for the requested language, its
        flowables are used instead. This lets a single template produce fully
        translated reports without duplicating templates.
        """
        body = json.loads(template.body_json) if template.body_json else {}
        if not language or language.lower().startswith("en"):
            return body
        translations = {}
        if template.translations_json:
            try:
                translations = json.loads(template.translations_json)
            except Exception as exc:
                logger.warning("Failed to parse translations_json for template %s: %s", template.id, exc)
        lang_key = None
        for key in translations:
            if str(key).lower().startswith(language.lower()):
                lang_key = key
                break
        if lang_key and isinstance(translations[lang_key], dict):
            translated = translations[lang_key]
            if "flowables" in translated:
                body = {**body, "flowables": translated["flowables"]}
        return body

    def generate_pdf(
        self,
        template_id: int,
        entity_type: str,
        entity_id: int,
        language: str | None = None,
    ) -> bytes:
        """Generate a PDF report."""
        from app.domain.reports.models import ReportTemplate, Letterhead

        template = self.db.get(ReportTemplate, template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        body_json = self._resolve_body(template, language)
        logger.info("generate_report template=%d body_json_keys=%s body_json_len=%d language=%s",
                     template_id, list(body_json.keys()), len(template.body_json or ""), language)

        context = self.resolve_context(entity_type, entity_id)
        _ = self._translator(language)
        context["now"] = date.today().isoformat()
        context["generated_at"] = f"{_('generated')}: {date.today().isoformat()}"
        context["entity_type"] = entity_type
        context["entity_id"] = entity_id

        flowable_defs = self._translate_flowables(body_json.get("flowables", []), language)
        translated_body = {**body_json, "flowables": flowable_defs}
        flowables = self._render_flowables(translated_body, context, language)
        logger.info("generate_report flowables_count=%d", len(flowables))

        if not flowables:
            logger.warning("Template %s produced no flowables for %s/%s", template_id, entity_type, entity_id)

        # Determine the effective letterhead first so its margins can be used as defaults.
        letterhead_id = template.letterhead_id
        if not letterhead_id:
            letterhead = self.db.query(Letterhead).filter(Letterhead.is_default.is_(True)).first()
            if letterhead:
                letterhead_id = letterhead.id

        letterhead = self.db.get(Letterhead, letterhead_id) if letterhead_id else None
        default_margins = {
            "top": float(letterhead.margin_top_mm) if letterhead else settings.pdf_default_margin_top_mm,
            "bottom": float(letterhead.margin_bottom_mm) if letterhead else settings.pdf_default_margin_bottom_mm,
            "left": float(letterhead.margin_left_mm) if letterhead else settings.pdf_default_margin_left_mm,
            "right": float(letterhead.margin_right_mm) if letterhead else settings.pdf_default_margin_right_mm,
        }

        margins_mm = {
            "top": float(body_json.get("margin_top_mm", default_margins["top"])),
            "bottom": float(body_json.get("margin_bottom_mm", default_margins["bottom"])),
            "left": float(body_json.get("margin_left_mm", default_margins["left"])),
            "right": float(body_json.get("margin_right_mm", default_margins["right"])),
        }

        content_pdf = self._build_pdf(flowables, body_json.get("page_size", "A4"), margins_mm)

        if letterhead_id:
            try:
                content_pdf = self._overlay_letterhead(content_pdf, letterhead_id)
            except Exception as exc:
                logger.error("Letterhead overlay failed, returning content PDF: %s", exc)

        return content_pdf

    def resolve_context(self, entity_type: str, entity_id: int) -> dict:
        """Build template context from the entity. Public API for preview endpoints."""
        context: dict[str, Any] = {}

        if entity_type == "job":
            from app.domain.jobs.models import Job
            from app.domain.customers.models import Customer
            from app.domain.venues.models import Venue

            job = self.db.get(Job, entity_id)
            if job:
                context["job"] = {
                    "job_code": job.job_code,
                    "description": job.description,
                    "status": job.status,
                    "start_date": str(job.start_date) if job.start_date else None,
                    "end_date": str(job.end_date) if job.end_date else None,
                    "sales_price": float(job.sales_price) if job.sales_price else 0,
                    "notes": job.notes,
                    "customer_name": job.customer_name,
                    "venue_name": job.venue_name,
                }
                if job.customer_id:
                    customer = self.db.get(Customer, job.customer_id)
                    if customer:
                        context["customer"] = {
                            "name": customer.name,
                            "email": customer.email,
                            "phone": customer.phone,
                        }
                if job.venue_id:
                    venue = self.db.get(Venue, job.venue_id)
                    if venue:
                        context["venue"] = {
                            "name": venue.name,
                            "address": getattr(venue, "address", None),
                        }
                if job.requirements:
                    context["job"]["requirements"] = [
                        {
                            "quantity_required": req.quantity_required,
                            "quantity_picked": req.quantity_picked,
                            "is_scannable": req.is_scannable,
                            "notes": req.notes,
                            "product": {
                                "name": req.product.name,
                                "sku": req.product.sku,
                                "category": req.product.category,
                                "brand": req.product.brand,
                                "weight_kg": float(req.product.weight_kg) if req.product.weight_kg else None,
                            } if req.product else None,
                        }
                        for req in job.requirements
                    ]

        elif entity_type == "device":
            from app.domain.inventory.models import Device, Product

            device = self.db.get(Device, entity_id)
            if device:
                context["device"] = {
                    "asset_tag": device.asset_tag,
                    "serial_number": device.serial_number,
                    "status": device.status,
                    "condition": device.condition,
                    "barcode": device.barcode,
                }
                if device.product_id:
                    product = self.db.get(Product, device.product_id)
                    if product:
                        context["product"] = {
                            "name": product.name,
                            "sku": product.sku,
                            "category": product.category,
                            "weight_kg": float(product.weight_kg) if product.weight_kg else None,
                        }

                # Case contents: devices contained in this case
                if device.contained_devices:
                    contents = []
                    grouped = {}
                    for item in device.contained_devices:
                        item_product = self.db.get(Product, item.product_id) if item.product_id else None
                        contents.append({
                            "id": item.id,
                            "asset_tag": item.asset_tag,
                            "serial_number": item.serial_number,
                            "status": item.status,
                            "condition": item.condition,
                            "barcode": item.barcode,
                            "product": {
                                "name": item_product.name if item_product else None,
                                "sku": item_product.sku if item_product else None,
                                "category": item_product.category if item_product else None,
                            } if item_product else None,
                        })
                        # Build grouped counts by SKU for convenient packlist tables
                        sku = item_product.sku if item_product else (item.asset_tag or "unknown")
                        name = item_product.name if item_product else "Unknown"
                        key = (sku, name)
                        if key not in grouped:
                            grouped[key] = {"sku": sku, "name": name, "count": 0, "conditions": set()}
                        grouped[key]["count"] += 1
                        if item.condition:
                            grouped[key]["conditions"].add(item.condition)
                    context["device"]["case_contents"] = contents
                    context["device"]["case_contents_grouped"] = [
                        {
                            "sku": g["sku"],
                            "name": g["name"],
                            "count": g["count"],
                            "conditions": sorted(g["conditions"]),
                        }
                        for g in grouped.values()
                    ]

                # If this device is inside a case, expose the parent case
                if device.case_device:
                    context["device"]["case_device"] = {
                        "id": device.case_device.id,
                        "asset_tag": device.case_device.asset_tag,
                        "serial_number": device.case_device.serial_number,
                        "barcode": device.case_device.barcode,
                    }

                # Maintenance history
                if device.maintenance_records:
                    context["device"]["maintenance_records"] = [
                        {
                            "id": rec.id,
                            "maintenance_type": rec.maintenance_type,
                            "status": rec.status,
                            "scheduled_date": str(rec.scheduled_date) if rec.scheduled_date else None,
                            "completed_date": str(rec.completed_date) if rec.completed_date else None,
                            "notes": rec.notes,
                        }
                        for rec in device.maintenance_records
                    ]

                # Defect reports
                if device.defect_reports:
                    context["device"]["defect_reports"] = [
                        {
                            "id": report.id,
                            "title": report.title,
                            "description": report.description,
                            "status": report.status,
                            "severity": report.severity,
                            "created_at": str(report.created_at) if report.created_at else None,
                        }
                        for report in device.defect_reports
                    ]

        elif entity_type == "inventory":
            from app.domain.inventory.models import Product, Device

            products = self.db.query(Product).all()
            context["products"] = [
                {
                    "id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "category": p.category,
                    "brand": p.brand,
                    "daily_rate": float(p.daily_rate) if p.daily_rate else 0,
                    "weight_kg": float(p.weight_kg) if p.weight_kg else None,
                }
                for p in products
            ]
            devices = self.db.query(Device).all()
            context["devices"] = [
                {
                    "id": d.id,
                    "asset_tag": d.asset_tag,
                    "serial_number": d.serial_number,
                    "status": d.status,
                    "condition": d.condition,
                    "barcode": d.barcode,
                }
                for d in devices
            ]

        elif entity_type == "product":
            from app.domain.inventory.models import Product

            product = self.db.get(Product, entity_id)
            if product:
                context["product"] = {
                    "name": product.name,
                    "sku": product.sku,
                    "category": product.category,
                    "brand": product.brand,
                    "daily_rate": float(product.daily_rate) if product.daily_rate else 0,
                    "weight_kg": float(product.weight_kg) if product.weight_kg else None,
                }
                if product.devices:
                    context["product"]["devices"] = [
                        {
                            "id": d.id,
                            "asset_tag": d.asset_tag,
                            "serial_number": d.serial_number,
                            "status": d.status,
                            "condition": d.condition,
                            "barcode": d.barcode,
                        }
                        for d in product.devices
                    ]

                if product.components_as_parent:
                    context["product"]["components"] = [
                        {
                            "quantity": comp.quantity,
                            "is_scannable": comp.is_scannable,
                            "product": {
                                "name": comp.component_product.name,
                                "sku": comp.component_product.sku,
                                "category": comp.component_product.category,
                                "brand": comp.component_product.brand,
                                "weight_kg": float(comp.component_product.weight_kg) if comp.component_product.weight_kg else None,
                            } if comp.component_product else None,
                        }
                        for comp in product.components_as_parent
                    ]

                if product.accessories_as_parent:
                    context["product"]["accessories"] = [
                        {
                            "quantity": acc.quantity,
                            "required": acc.required,
                            "is_scannable": acc.is_scannable,
                            "product": {
                                "name": acc.accessory_product.name,
                                "sku": acc.accessory_product.sku,
                                "category": acc.accessory_product.category,
                                "brand": acc.accessory_product.brand,
                                "weight_kg": float(acc.accessory_product.weight_kg) if acc.accessory_product.weight_kg else None,
                            } if acc.accessory_product else None,
                        }
                        for acc in product.accessories_as_parent
                    ]

        return context

    def _render_flowables(self, body_json: dict, context: dict, language: str | None = None) -> list:
        """Interpret JSON flowable definitions into ReportLab flowable objects."""
        flowable_defs = body_json.get("flowables", [])
        logger.info("_render_flowables: %d flowable definitions, context keys=%s", len(flowable_defs), list(context.keys()))
        custom_styles = body_json.get("styles", {})
        styles = _build_styles(custom_styles)
        elements = []

        for fdef in flowable_defs:
            ftype = fdef.get("type", "")
            align = fdef.get("align")

            if ftype == "heading":
                level = fdef.get("level", 1)
                style_key = f"heading{min(level, 3)}"
                text = _render_jinja(fdef.get("text", ""), context)
                style = _style_with_alignment(styles.get(style_key, styles["heading1"]), align)
                elements.append(Paragraph(text, style))

            elif ftype == "paragraph":
                text = _render_jinja(fdef.get("text", ""), context)
                style_key = fdef.get("style", "body")
                style = _style_with_alignment(styles.get(style_key, styles["body"]), align)
                elements.append(Paragraph(text, style))

            elif ftype == "table":
                elements.extend(_build_table(fdef, context, styles, align, language))

            elif ftype == "key_value":
                elements.extend(_build_key_value_table(fdef, context, styles, align, language))

            elif ftype == "spacer":
                height = fdef.get("height_mm", 5)
                elements.append(Spacer(1, height * mm))

            elif ftype == "line":
                width_pct = fdef.get("width_percent", 100)
                line = HRFlowable(
                    width=f"{width_pct}%", thickness=0.5,
                    color=colors.HexColor("#cccccc"), spaceAfter=2 * mm, spaceBefore=2 * mm,
                )
                elements.append(self._apply_alignment(line, align))

            elif ftype == "barcode":
                try:
                    value = _render_jinja(fdef.get("value", ""), context)
                    if value:
                        barcode_type = str(fdef.get("barcode_type", "code128")).lower().strip()
                        if barcode_type == "qr":
                            from reportlab.graphics.barcode.qr import QrCodeWidget
                            from reportlab.graphics.shapes import Drawing
                            qr = QrCodeWidget(value)
                            bounds = qr.getBounds()
                            qr_width = bounds[2] - bounds[0]
                            qr_height = bounds[3] - bounds[1]
                            size = 30 * mm
                            drawing = Drawing(size, size, transform=[size / qr_width, 0, 0, size / qr_height, 0, 0])
                            drawing.add(qr)
                            barcode = drawing
                        else:
                            from reportlab.graphics.barcode import code128
                            barcode = code128.Code128(value, barWidth=0.4 * mm, barHeight=10 * mm)
                        elements.append(self._apply_alignment(barcode, align))
                except Exception as exc:
                    logger.warning("Barcode render error: %s", exc)
                    elements.append(Paragraph(f"[Barcode: {fdef.get('value', '')}]", styles["small"]))

            elif ftype == "columns":
                elements.extend(self._build_columns(fdef, context, styles, language))

            elif ftype == "page_break":
                from reportlab.platypus import PageBreak
                elements.append(PageBreak())

        logger.info("_render_flowables: produced %d elements from %d definitions", len(elements), len(flowable_defs))
        return elements

    def _apply_alignment(self, flowable, align: str | None):
        """Wrap a flowable so it respects center/right alignment.

        Left alignment is the default flowable behaviour, so we avoid wrapping
        in a Table. Nesting Tables (e.g. columns containing aligned blocks) can
        trigger ReportLab layout errors.
        """
        if not align or str(align).lower().strip() == "left":
            return flowable
        table = Table([[flowable]], colWidths=[A4[0] - 40 * mm], hAlign=_halign(align))
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), str(align).upper()),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return table

    def _build_columns(self, fdef: dict, context: dict, styles: dict, language: str | None = None) -> list:
        """Build a side-by-side column layout using an invisible table."""
        column_defs = fdef.get("columns", [])
        if not column_defs:
            return []
        # Render child flowables for each column. A list of flowables in a
        # Table cell is rendered sequentially. Avoid KeepTogether because it
        # can report an enormous height when the column content does not fit
        # in the available page space.
        col_flowables = []
        for col_def in column_defs:
            col_body = {"flowables": col_def if isinstance(col_def, list) else []}
            col_elements = self._render_flowables(col_body, context, language)
            if col_elements:
                col_flowables.append(col_elements)
            else:
                col_flowables.append([Spacer(1, 1)])

        if not col_flowables:
            return []

        # Determine column widths
        page_width = A4[0]
        available_width = page_width - 40 * mm
        widths = fdef.get("widths", [])
        col_widths = []
        defined = 0
        for i, _ in enumerate(col_flowables):
            w = widths[i] if i < len(widths) else None
            if w:
                if isinstance(w, str) and w.endswith("%"):
                    col_widths.append(available_width * (float(w[:-1]) / 100))
                    defined += available_width * (float(w[:-1]) / 100)
                else:
                    col_widths.append(float(w) * mm)
                    defined += float(w) * mm
            else:
                col_widths.append(None)
        remaining = available_width - defined
        undefined = sum(1 for w in col_widths if w is None)
        if undefined:
            auto = remaining / undefined
            col_widths = [w if w is not None else auto for w in col_widths]

        table = Table([col_flowables], colWidths=col_widths)
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return [table]

    def _build_pdf(self, flowables: list, page_size_name: str, margins_mm: dict) -> bytes:
        """Use ReportLab Platypus to build PDF from flowables."""
        from reportlab.lib.styles import getSampleStyleSheet
        page_size = PAGE_SIZES.get(page_size_name.upper(), A4)
        buf = io.BytesIO()

        doc = SimpleDocTemplate(
            buf,
            pagesize=page_size,
            topMargin=margins_mm["top"] * MM_TO_PT,
            bottomMargin=margins_mm["bottom"] * MM_TO_PT,
            leftMargin=margins_mm["left"] * MM_TO_PT,
            rightMargin=margins_mm["right"] * MM_TO_PT,
        )

        if not flowables:
            # Fallback: create a minimal valid PDF with a placeholder message
            styles = getSampleStyleSheet()
            flowables = [
                Paragraph("Report", styles["Heading1"]),
                Spacer(1, 4 * mm),
                Paragraph("This report was generated but contains no renderable content.", styles["Normal"]),
                Spacer(1, 4 * mm),
                Paragraph("The template may have empty flowables or missing data context.", styles["Normal"]),
            ]

        try:
            doc.build(flowables)
        except Exception as exc:
            logger.error("ReportLab build failed: %s", exc, exc_info=True)
            # Last resort: discard any partial output and build a simple one-page PDF
            buf.seek(0)
            buf.truncate()
            from reportlab.pdfgen import canvas as pdf_canvas
            c = pdf_canvas.Canvas(buf, pagesize=page_size)
            c.setFont("Helvetica", 12)
            c.drawString(margins_mm["left"] * MM_TO_PT, page_size[1] - margins_mm["top"] * MM_TO_PT, "Report Generation Error")
            c.setFont("Helvetica", 10)
            c.drawString(margins_mm["left"] * MM_TO_PT, page_size[1] - margins_mm["top"] * MM_TO_PT - 20, f"Error: {exc}")
            c.save()

        pdf_bytes = buf.getvalue()
        if not pdf_bytes:
            logger.error("_build_pdf produced empty bytes")
        return pdf_bytes

    def _overlay_letterhead(self, content_pdf: bytes, letterhead_id: int) -> bytes:
        """Merge content PDF on top of letterhead background using pypdf."""
        from pypdf import PdfReader, PdfWriter
        from app.domain.reports.models import Letterhead
        from app.domain.storage.service import StorageService
        from app.domain.storage.models import AssetFile

        letterhead = self.db.get(Letterhead, letterhead_id)
        if not letterhead or not letterhead.asset_file_id:
            logger.info("No letterhead or asset_file_id for letterhead %s", letterhead_id)
            return content_pdf

        asset = self.db.get(AssetFile, letterhead.asset_file_id)
        if not asset or asset.is_deleted:
            logger.info("Asset file %s not found or deleted", letterhead.asset_file_id)
            return content_pdf

        storage = StorageService()
        if storage.backend != "local":
            logger.warning("Letterhead overlay only supports local storage, got %s", storage.backend)
            return content_pdf

        bg_path = storage._local_root() / asset.storage_key
        if not bg_path.exists():
            logger.warning("Letterhead PDF file not found at %s", bg_path)
            return content_pdf

        try:
            bg_reader = PdfReader(str(bg_path))
            content_reader = PdfReader(io.BytesIO(content_pdf))

            if not content_reader.pages:
                logger.warning("Content PDF has no pages")
                return content_pdf

            writer = PdfWriter()

            for i, content_page in enumerate(content_reader.pages):
                if i < len(bg_reader.pages):
                    # Put background BEHIND content (background first, content on top)
                    bg_page = bg_reader.pages[i]
                    bg_page.merge_page(content_page)
                    writer.add_page(bg_page)
                else:
                    writer.add_page(content_page)

            out_buf = io.BytesIO()
            writer.write(out_buf)
            result = out_buf.getvalue()
            if not result:
                logger.error("Letterhead overlay produced empty output")
                return content_pdf
            return result
        except Exception as exc:
            logger.error("Letterhead overlay failed: %s", exc, exc_info=True)
            return content_pdf

    def generate_csv(
        self,
        template_id: int,
        entity_type: str,
        entity_id: int,
        language: str | None = None,
    ) -> tuple[bytes, str, str]:
        """Generate a CSV report. Returns (content_bytes, content_type, file_extension)."""
        import csv
        from app.domain.reports.models import ReportTemplate

        template = self.db.get(ReportTemplate, template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        body_json = self._resolve_body(template, language)
        context = self.resolve_context(entity_type, entity_id)
        _ = self._translator(language)
        context["now"] = date.today().isoformat()
        context["generated_at"] = f"{_('generated')}: {date.today().isoformat()}"

        # Find table flowables and extract their data
        flowable_defs = self._translate_flowables(body_json.get("flowables", []), language)
        buf = io.StringIO()
        writer = csv.writer(buf)

        for fdef in flowable_defs:
            if fdef.get("type") == "table":
                source_path = fdef.get("source", "")
                data = _resolve_value(context, source_path)
                columns = fdef.get("columns", [])
                if isinstance(data, list) and columns:
                    # Header row
                    writer.writerow([col.get("label", col.get("key", "")) for col in columns])
                    # Data rows
                    for item in data:
                        row = [_resolve_value(item, col.get("key", "")) or "" for col in columns]
                        writer.writerow(row)
            elif fdef.get("type") == "key_value":
                source_path = fdef.get("source", "")
                source_data = _resolve_value(context, source_path) or context
                fields = fdef.get("fields", [])
                for field in fields:
                    label = field.get("label", field.get("key", ""))
                    val = _resolve_value(source_data, field.get("key", "")) if isinstance(source_data, dict) else ""
                    writer.writerow([label, val or ""])

        csv_bytes = buf.getvalue().encode("utf-8-sig")
        return csv_bytes, "text/csv", "csv"

    def generate_html(
        self,
        template_id: int,
        entity_type: str,
        entity_id: int,
        language: str | None = None,
    ) -> tuple[bytes, str, str]:
        """Generate an HTML report. Returns (content_bytes, content_type, file_extension)."""
        from app.domain.reports.models import ReportTemplate

        template = self.db.get(ReportTemplate, template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        body_json = self._resolve_body(template, language)
        context = self.resolve_context(entity_type, entity_id)
        _ = self._translator(language)
        context["now"] = date.today().isoformat()
        context["generated_at"] = f"{_('generated')}: {date.today().isoformat()}"

        flowable_defs = self._translate_flowables(body_json.get("flowables", []), language)
        parts = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'>",
            "<style>body{font-family:Arial,sans-serif;margin:20px;line-height:1.5}",
            "table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:4px 8px;text-align:left}",
            "th{background:#f5f5f5}h1{font-size:18px}h2{font-size:15px}.small{font-size:11px;color:#666}",
            ".kv{display:grid;grid-template-columns:140px 1fr;gap:2px 8px}.kv dt{font-weight:bold}",
            ".align-left{text-align:left}.align-center{text-align:center}.align-right{text-align:right}",
            ".columns{display:flex;gap:16px}.columns>.col{flex:1;min-width:0}</style>",
            "</head><body>",
        ]

        def render_flowables(defs):
            out = []
            for fdef in defs:
                ftype = fdef.get("type", "")
                align = fdef.get("align", "left")
                align_class = f" align-{align}" if align in ("center", "right") else ""
                if ftype == "heading":
                    level = min(fdef.get("level", 1), 3)
                    text = _render_jinja(fdef.get("text", ""), context)
                    out.append(f'<h{level} class="align-{align}">{text}</h{level}>')
                elif ftype == "paragraph":
                    text = _render_jinja(fdef.get("text", ""), context)
                    out.append(f'<p class="align-{align}">{text}</p>')
                elif ftype == "table":
                    source_path = fdef.get("source", "")
                    data = _resolve_value(context, source_path)
                    columns = fdef.get("columns", [])
                    if isinstance(data, list) and columns:
                        out.append(f'<table class="align-{align}"><thead><tr>')
                        for col in columns:
                            out.append(f"<th>{col.get('label', col.get('key', ''))}</th>")
                        out.append("</tr></thead><tbody>")
                        for item in data:
                            out.append("<tr>")
                            for col in columns:
                                val = _resolve_value(item, col.get("key", "")) or ""
                                out.append(f"<td>{val}</td>")
                            out.append("</tr>")
                        out.append("</tbody></table>")
                elif ftype == "key_value":
                    source_path = fdef.get("source", "")
                    source_data = _resolve_value(context, source_path) or context
                    fields = fdef.get("fields", [])
                    out.append(f'<div class="kv{align_class}">')
                    for field in fields:
                        label = field.get("label", field.get("key", ""))
                        val = _resolve_value(source_data, field.get("key", "")) if isinstance(source_data, dict) else ""
                        out.append(f"<dt>{label}</dt><dd>{val or '—'}</dd>")
                    out.append("</div>")
                elif ftype == "line":
                    out.append("<hr>")
                elif ftype == "spacer":
                    out.append(f"<div style='height:{fdef.get('height_mm', 5)}mm'></div>")
                elif ftype == "barcode":
                    value = _render_jinja(fdef.get("value", ""), context)
                    barcode_type = str(fdef.get("barcode_type", "code128")).lower().strip()
                    label = "QR code" if barcode_type == "qr" else "Barcode"
                    out.append(f'<div class="align-{align}">[{label}: {value}]</div>')
                elif ftype == "columns":
                    column_defs = fdef.get("columns", [])
                    widths = fdef.get("widths", [])
                    out.append('<div class="columns">')
                    for i, col_def in enumerate(column_defs):
                        style = ""
                        if i < len(widths):
                            style = f" style='flex:0 0 {widths[i]}'"
                        out.append(f'<div class="col"{style}>')
                        out.extend(render_flowables(col_def if isinstance(col_def, list) else []))
                        out.append('</div>')
                    out.append('</div>')
            return out

        parts.extend(render_flowables(flowable_defs))
        parts.append("</body></html>")
        html_str = "".join(parts)
        return html_str.encode("utf-8"), "text/html", "html"
