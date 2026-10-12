"""Render a purchase order as a PDF using ReportLab."""

import json
from collections import defaultdict
from decimal import Decimal
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select

from app.domain.customers.models import Company
from app.domain.purchasing.models import PurchaseOrder
from app.domain.settings.models import AppSetting

COMPANY_PROFILE_KEY = "company.profile"


def _style() -> ParagraphStyle:
    return ParagraphStyle("cell", fontSize=9, leading=12, alignment=TA_LEFT)


def _company_profile(db: Any) -> dict:
    setting = db.scalar(select(AppSetting).where(AppSetting.key == COMPANY_PROFILE_KEY))
    if setting and setting.value_json:
        try:
            return json.loads(setting.value_json) or {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def generate_purchase_order_pdf(db: Any, po: PurchaseOrder) -> bytes:
    """Build a one-page purchase-order PDF and return its bytes."""
    profile = _company_profile(db)
    supplier: Company | None = (
        db.get(Company, po.supplier_company_id) if po.supplier_company_id else None
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Purchase Order {po.po_number}",
    )
    styles = getSampleStyleSheet()
    cell = _style()
    elements: list[Any] = []

    seller_name = profile.get("name") or "Stockwire Rental"
    seller_lines = [seller_name]
    if profile.get("org_number"):
        seller_lines.append(f"Org.nr: {profile['org_number']}")
    if profile.get("address"):
        seller_lines.append(profile["address"])
    if profile.get("email"):
        seller_lines.append(profile["email"])

    seller = "<br/>".join(seller_lines)
    buyer_lines = [supplier.name if supplier else "—"]
    if supplier and supplier.address:
        buyer_lines.append(supplier.address)
        if supplier.postal_code or supplier.city:
            buyer_lines.append(f"{supplier.postal_code or ''} {supplier.city or ''}".strip())
        if supplier.country:
            buyer_lines.append(supplier.country)
    buyer = "<br/>".join(buyer_lines)

    header = Table(
        [[Paragraph("<b>Purchase Order</b>", styles["Title"]), Paragraph(seller, cell)]],
        colWidths=[90 * mm, 84 * mm],
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(header)
    elements.append(Spacer(1, 6 * mm))

    meta = Table(
        [
            [Paragraph("<b>PO number</b>", cell), Paragraph(po.po_number, cell)],
            [Paragraph("<b>Supplier</b>", cell), Paragraph(buyer, cell)],
            [Paragraph("<b>Status</b>", cell), Paragraph(po.status, cell)],
            [
                Paragraph("<b>Order date</b>", cell),
                Paragraph(str(po.order_date.date()) if po.order_date else "—", cell),
            ],
            [
                Paragraph("<b>Expected delivery</b>", cell),
                Paragraph(
                    str(po.expected_delivery_date.date()) if po.expected_delivery_date else "—",
                    cell,
                ),
            ],
        ],
        colWidths=[35 * mm, 139 * mm],
    )
    meta.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elements.append(meta)
    elements.append(Spacer(1, 8 * mm))

    data = [[Paragraph("<b>#</b>", cell), Paragraph("<b>Item</b>", cell),
             Paragraph("<b>SKU</b>", cell), Paragraph("<b>Qty</b>", cell),
             Paragraph("<b>Unit</b>", cell), Paragraph("<b>Total</b>", cell)]]
    for idx, line in enumerate(po.lines, start=1):
        unit = f"{line.converted_unit_cost:.2f}" if line.converted_unit_cost is not None else (
            f"{line.unit_cost:.2f}" if line.unit_cost is not None else "—"
        )
        if line.currency:
            unit = f"{unit} {line.currency}"
        if line.line_total is not None:
            total = f"{line.line_total:.2f} {po.report_currency or ''}".strip()
        elif line.unit_cost is not None:
            total = f"{line.unit_cost * line.qty:.2f} {line.currency or ''}".strip()
        else:
            total = "—"
        tag = " (restock)" if line.is_restock else (" (manual)" if line.is_manual else "")
        data.append(
            [
                Paragraph(str(idx), cell),
                Paragraph(f"{(line.name or '')}{tag}", cell),
                Paragraph(line.sku or "—", cell),
                Paragraph(str(line.qty), cell),
                Paragraph(unit, cell),
                Paragraph(total, cell),
            ]
        )
    table = Table(data, colWidths=[10 * mm, 79 * mm, 28 * mm, 14 * mm, 28 * mm, 25 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))

    # Totals are summed per currency: converted lines contribute to the report
    # currency, unconverted lines keep their original currency, and freight is
    # added in its own currency. This avoids mislabelling an unconverted amount
    # as the report currency.
    totals_by_currency: dict[str, Any] = defaultdict(lambda: Decimal(0))
    for line in po.lines:
        if line.line_total is not None and line.converted_unit_cost is not None:
            totals_by_currency[po.report_currency or ""] += line.line_total
        elif line.unit_cost is not None:
            totals_by_currency[line.currency or ""] += Decimal(str(line.unit_cost)) * Decimal(
                str(line.qty)
            )
    freight_cur = po.freight_currency or po.report_currency or ""
    if po.freight_base:
        totals_by_currency[freight_cur] += po.freight_base

    currency = po.report_currency or ""
    totals_rows: list[list[Any]] = []
    for cur, amt in sorted(totals_by_currency.items()):
        label = "Total" if cur == currency else f"Total ({cur})"
        totals_rows.append([Paragraph(f"<b>{label}</b>", cell), Paragraph(f"{amt:.2f} {cur}", cell)])
    if not totals_rows:
        totals_rows.append([Paragraph("<b>Total</b>", cell), Paragraph("—", cell)])
    totals = Table(totals_rows, colWidths=[139 * mm, 35 * mm])
    totals.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(totals)

    doc.build(elements)
    return buffer.getvalue()
