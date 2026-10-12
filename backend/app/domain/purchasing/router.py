"""API endpoints for best-purchase comparison and purchase-draft persistence."""

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        try:
            return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
        except (ValueError, TypeError):
            return None

from app.db.session import get_db
from app.domain.auth.deps import get_current_user
from app.domain.auth.models import User
from app.domain.inventory.models import Product
from app.domain.inventory.schemas import ProductRead
from app.domain.purchasing import service as purchasing
from app.domain.purchasing.models import (
    PurchaseDraft,
    PurchaseOrder,
    PurchaseOrderLine,
)
from app.domain.purchasing.pdf import generate_purchase_order_pdf
from app.domain.reports.models import ReportTemplate
from app.services.pdf_service import PDFService
from app.domain.purchasing.schemas import (
    AddToPORequest,
    BestPurchaseRequest,
    BestPurchaseResponse,
    BuildPORequest,
    CombinedPORequest,
    POLineUpdateRequest,
    POUpdateRequest,
    PreviewPORequest,
    PurchaseDraftRead,
    PurchaseOrderLineRead,
    PurchaseOrderRead,
    ReceivePORequest,
    ReceivingLineRead,
    ReceivingLookupRead,
)

router = APIRouter(prefix="/purchasing", tags=["purchasing"])


@router.post(
    "/jobs/{job_id}/best-purchase",
    response_model=BestPurchaseResponse,
)
def best_purchase(
    job_id: int,
    req: BestPurchaseRequest | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> BestPurchaseResponse:
    """Compare suppliers for the job's vendor-linked requirements and persist a
    purchase draft with the recommended basket."""
    if req is not None and req.strategy not in ("multi", "single"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="strategy must be 'multi' or 'single'",
        )
    report_currency = req.report_currency if req else None
    strategy = req.strategy if req else "multi"
    try:
        result = purchasing.compute_best_purchase(db, job_id, report_currency=report_currency)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    draft = purchasing.create_purchase_draft(db, job_id, result, strategy=strategy)
    return BestPurchaseResponse(draft_id=draft.id, **result)


@router.get(
    "/jobs/{job_id}/purchase-drafts",
    response_model=list[PurchaseDraftRead],
)
def list_purchase_drafts(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PurchaseDraft]:
    return list(
        db.scalars(
            select(PurchaseDraft)
            .where(PurchaseDraft.job_id == job_id)
            .order_by(PurchaseDraft.created_at.desc())
        ).all()
    )


@router.get(
    "/drafts/{draft_id}",
    response_model=PurchaseDraftRead,
)
def get_purchase_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PurchaseDraft:
    draft = db.get(PurchaseDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase draft not found")
    return draft


@router.delete(
    "/drafts/{draft_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_purchase_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    draft = db.get(PurchaseDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase draft not found")
    db.delete(draft)
    db.commit()


# --------------------------------------------------------------------------- #
# Purchase orders
# --------------------------------------------------------------------------- #


@router.post(
    "/purchase-orders/from-draft/{draft_id}",
    response_model=list[PurchaseOrderRead],
)
def create_pos_from_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PurchaseOrder]:
    """Turn a purchase draft into one purchase order per supplier."""
    try:
        return purchasing.create_pos_from_draft(db, draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/purchase-orders/combined",
    response_model=list[PurchaseOrderRead],
)
def create_combined_pos(
    req: CombinedPORequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PurchaseOrder]:
    """Create one PO per supplier from multiple jobs, optional restock and manual items."""
    try:
        return purchasing.create_combined_pos(
            db,
            job_ids=req.job_ids,
            include_restock=req.include_restock,
            extra_items=req.extra_items,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/purchase-orders",
    response_model=list[PurchaseOrderRead],
)
def list_purchase_orders(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PurchaseOrder]:
    return list(
        db.scalars(
            select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc())
        ).all()
    )


@router.post(
    "/purchase-orders/preview",
)
def preview_purchase_orders(
    req: PreviewPORequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Show proposed lines with alternative suppliers before building POs."""
    return purchasing.preview_purchase_lines(
        db, req.job_ids, include_restock=req.include_restock
    )


@router.post(
    "/purchase-orders/build",
    response_model=list[PurchaseOrderRead],
)
def build_purchase_orders(
    req: BuildPORequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PurchaseOrder]:
    """Create POs (one per supplier) from explicit per-line supplier selections."""
    try:
        return purchasing.build_purchase_orders(
            db,
            [s.model_dump() for s in req.lines],
            extra_items=req.extra_items,
            include_restock=req.include_restock,
            freight=req.freight,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/purchase-orders/from-job/{job_id}",
    response_model=list[PurchaseOrderRead],
)
def create_pos_from_job(
    job_id: int,
    selections: list[dict] | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PurchaseOrder]:
    """Create PO(s) directly from a job's vendor-linked requirements."""
    try:
        return purchasing.create_pos_from_job(db, job_id, selections=selections)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/purchase-orders/{po_id}/add-lines",
    response_model=PurchaseOrderRead,
)
def add_lines_to_po(
    po_id: int,
    req: AddToPORequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PurchaseOrder:
    """Append lines (and manual items) to an existing draft/partial PO."""
    try:
        return purchasing.add_lines_to_po(
            db,
            po_id,
            [s.model_dump() for s in req.lines],
            extra_items=req.extra_items,
            freight=req.freight,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/purchase-orders/{po_id}",
    response_model=PurchaseOrderRead,
)
def get_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    data = PurchaseOrderRead.model_validate(po)
    for orm_line, read_line in zip(po.lines, data.lines):
        read_line.creates_device = purchasing._line_creates_device(db, orm_line)
    return data


@router.patch(
    "/purchase-orders/{po_id}",
    response_model=PurchaseOrderRead,
)
def update_purchase_order(
    po_id: int,
    req: POUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    if req.status is not None:
        po.status = req.status
    if req.order_date is not None:
        po.order_date = _parse_dt(req.order_date)
    if req.expected_delivery_date is not None:
        po.expected_delivery_date = _parse_dt(req.expected_delivery_date)
    if req.supplier_company_id is not None:
        po.supplier_company_id = req.supplier_company_id
    db.commit()
    db.refresh(po)
    return po


@router.post(
    "/purchase-orders/{po_id}/receive",
    response_model=PurchaseOrderRead,
)
def receive_purchase_order(
    po_id: int,
    req: ReceivePORequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PurchaseOrder:
    """Receive ordered items: increments stock and creates device records."""
    try:
        return purchasing.receive_po(db, po_id, req.lines)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/receiving/lookup",
    response_model=ReceivingLookupRead,
)
def receiving_lookup(
    code: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReceivingLookupRead:
    """Resolve a scanned product (barcode or SKU) and list its open purchase-order
    lines so the operator can receive against them."""
    product = db.scalar(
        select(Product).where(or_(Product.barcode == code, Product.sku == code))
    )
    lines = []
    if product:
        rows = db.scalars(
            select(PurchaseOrderLine)
            .join(PurchaseOrder, PurchaseOrderLine.po_id == PurchaseOrder.id)
            .where(
                PurchaseOrderLine.product_id == product.id,
                PurchaseOrder.status.in_(purchasing.OPEN_PO_STATUSES),
            )
        ).all()
        for ln in rows:
            lines.append(
                ReceivingLineRead(
                    po_id=ln.po_id,
                    po_number=ln.po.po_number,
                    line_id=ln.id,
                    product_id=ln.product_id,
                    name=ln.name,
                    sku=ln.sku,
                    qty=ln.qty,
                    received_qty=ln.received_qty,
                    remaining=max(0, ln.qty - ln.received_qty),
                    unit_cost=ln.unit_cost,
                    currency=ln.currency,
                    creates_device=purchasing._line_creates_device(db, ln),
                )
            )
    return ReceivingLookupRead(
        product=ProductRead.model_validate(product).model_dump() if product else None,
        lines=lines,
    )


@router.delete(
    "/purchase-orders/{po_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    """Delete a purchase order and its lines."""
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    # Received stock is represented by Device records with no foreign key back to
    # the PO, so deleting a (partially) received PO would silently orphan
    # inventory. Block it; reverse the receipt first if needed.
    if po.status == "received" or any((line.received_qty or 0) > 0 for line in po.lines):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a purchase order that has been (partially) received",
        )
    db.delete(po)
    db.commit()


@router.put(
    "/purchase-orders/{po_id}/lines/{line_id}",
    response_model=PurchaseOrderLineRead,
)
def update_purchase_order_line(
    po_id: int,
    line_id: int,
    req: POLineUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PurchaseOrderLine:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    line = db.get(PurchaseOrderLine, line_id)
    if line is None or line.po_id != po.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order line not found")
    try:
        return purchasing.update_po_line(db, po_id, line_id, req)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete(
    "/purchase-orders/{po_id}/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_purchase_order_line(
    po_id: int,
    line_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")
    line = db.get(PurchaseOrderLine, line_id)
    if line is None or line.po_id != po.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order line not found")
    try:
        purchasing.delete_po_line(db, po_id, line_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/purchase-orders/{po_id}/pdf",
)
def purchase_order_pdf(
    po_id: int,
    language: str = "en",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Response:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found")

    # Prefer the seeded, editable "Purchase Order" report template so the PO
    # honours the default letterhead (and any user customisations) unless the
    # report settings pick a specific letterhead. Falls back to the legacy
    # generator if the template is unavailable.
    template = db.scalars(
        select(ReportTemplate)
        .where(ReportTemplate.data_source_type == "purchase_order")
        .where(ReportTemplate.is_enabled.is_(True))
        .order_by(ReportTemplate.is_builtin.desc(), ReportTemplate.id)
    ).first()
    if template is not None:
        try:
            pdf_bytes = PDFService(db).generate_pdf(
                template_id=template.id,
                entity_type="purchase_order",
                entity_id=po_id,
                language=language,
            )
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'inline; filename="{po.po_number}.pdf"'},
            )
        except Exception:
            logger.warning("Template PDF generation failed for PO %s; using legacy generator", po_id)

    pdf_bytes = generate_purchase_order_pdf(db, po)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{po.po_number}.pdf"'},
    )
