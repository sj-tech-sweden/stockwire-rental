from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.reports.models import Letterhead, ReportTemplate, GeneratedReportLog
from app.domain.reports.schemas import (
    LetterheadCreate,
    LetterheadRead,
    LetterheadUpdate,
    ReportTemplateCreate,
    ReportTemplateListRead,
    ReportTemplateRead,
    ReportTemplateUpdate,
    ReportGenerateRequest,
    GeneratedReportLogRead,
    DataSourceSchemaResponse,
    DataSourceField,
)
from app.domain.storage.models import AssetFile
from app.domain.storage.service import StorageService
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(get_current_user)])


# ── Letterheads ─────────────────────────────────────────────────────────────


@router.get("/letterheads", response_model=list[LetterheadRead])
def list_letterheads(db: Session = Depends(get_db)) -> list[LetterheadRead]:
    rows = list(db.scalars(select(Letterhead).order_by(Letterhead.name)).all())
    return [LetterheadRead.model_validate(r) for r in rows]


@router.post("/letterheads", response_model=LetterheadRead, status_code=status.HTTP_201_CREATED)
def create_letterhead(
    payload: LetterheadCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> LetterheadRead:
    existing = db.scalar(select(Letterhead).where(Letterhead.name == payload.name.strip()))
    if existing:
        raise HTTPException(status_code=409, detail="Letterhead with this name already exists")
    if payload.is_default:
        db.query(Letterhead).update({"is_default": False})
    letterhead = Letterhead(
        name=payload.name.strip(),
        is_default=payload.is_default,
        asset_file_id=payload.asset_file_id,
        page_count=payload.page_count,
        margin_top_mm=payload.margin_top_mm,
        margin_bottom_mm=payload.margin_bottom_mm,
        margin_left_mm=payload.margin_left_mm,
        margin_right_mm=payload.margin_right_mm,
    )
    db.add(letterhead)
    db.commit()
    db.refresh(letterhead)
    return LetterheadRead.model_validate(letterhead)


@router.put("/letterheads/{letterhead_id}", response_model=LetterheadRead)
def update_letterhead(
    letterhead_id: int,
    payload: LetterheadUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> LetterheadRead:
    letterhead = db.get(Letterhead, letterhead_id)
    if not letterhead:
        raise HTTPException(status_code=404, detail="Letterhead not found")
    if payload.name is not None:
        letterhead.name = payload.name.strip()
    if payload.is_default is not None:
        if payload.is_default:
            db.query(Letterhead).update({"is_default": False})
        letterhead.is_default = payload.is_default
    if payload.asset_file_id is not None:
        letterhead.asset_file_id = payload.asset_file_id
    if payload.page_count is not None:
        letterhead.page_count = payload.page_count
    if payload.margin_top_mm is not None:
        letterhead.margin_top_mm = payload.margin_top_mm
    if payload.margin_bottom_mm is not None:
        letterhead.margin_bottom_mm = payload.margin_bottom_mm
    if payload.margin_left_mm is not None:
        letterhead.margin_left_mm = payload.margin_left_mm
    if payload.margin_right_mm is not None:
        letterhead.margin_right_mm = payload.margin_right_mm
    db.commit()
    db.refresh(letterhead)
    return LetterheadRead.model_validate(letterhead)


@router.delete("/letterheads/{letterhead_id}")
def delete_letterhead(
    letterhead_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> dict:
    letterhead = db.get(Letterhead, letterhead_id)
    if not letterhead:
        raise HTTPException(status_code=404, detail="Letterhead not found")
    in_use = db.scalar(
        select(ReportTemplate).where(ReportTemplate.letterhead_id == letterhead_id)
    )
    if in_use:
        raise HTTPException(status_code=409, detail="Letterhead is used by templates. Unlink first.")
    db.delete(letterhead)
    db.commit()
    return {"status": "ok"}


@router.post("/letterheads/upload", response_model=LetterheadRead, status_code=status.HTTP_201_CREATED)
async def upload_letterhead_pdf(
    file: UploadFile = File(...),
    name: str = Form(...),
    is_default: bool = Form(default=False),
    margin_top_mm: float = Form(default=20.0),
    margin_bottom_mm: float = Form(default=20.0),
    margin_left_mm: float = Form(default=20.0),
    margin_right_mm: float = Form(default=20.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> LetterheadRead:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    storage = StorageService()
    payload = await file.read()
    if len(payload) > storage.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    storage_key, stored_filename = storage.make_storage_key(
        entity_type="letterhead", category="background", original_filename=file.filename
    )
    storage.save_bytes(storage_key=storage_key, payload=payload, content_type="application/pdf")

    page_count = 1
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(payload))
        page_count = len(reader.pages)
    except Exception:
        pass

    asset = AssetFile(
        entity_type="letterhead",
        entity_id=None,
        category="background",
        original_filename=file.filename,
        stored_filename=stored_filename,
        content_type="application/pdf",
        size_bytes=len(payload),
        storage_backend=storage.backend,
        storage_key=storage_key,
        created_by_user_id=current_user.id if current_user.id else None,
    )
    db.add(asset)
    db.flush()

    if is_default:
        db.query(Letterhead).update({"is_default": False})

    letterhead = Letterhead(
        name=name.strip(),
        is_default=is_default,
        asset_file_id=asset.id,
        page_count=page_count,
        margin_top_mm=margin_top_mm,
        margin_bottom_mm=margin_bottom_mm,
        margin_left_mm=margin_left_mm,
        margin_right_mm=margin_right_mm,
    )
    db.add(letterhead)
    db.commit()
    db.refresh(letterhead)
    return LetterheadRead.model_validate(letterhead)


# ── Report Templates ────────────────────────────────────────────────────────


@router.get("/templates", response_model=list[ReportTemplateListRead])
def list_templates(
    category: str | None = None,
    data_source_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[ReportTemplateListRead]:
    query = select(ReportTemplate).order_by(ReportTemplate.category, ReportTemplate.name)
    if category:
        query = query.where(ReportTemplate.category == category)
    if data_source_type:
        query = query.where(ReportTemplate.data_source_type == data_source_type)
    rows = list(db.scalars(query).all())
    return [ReportTemplateListRead.model_validate(r) for r in rows]


@router.get("/templates/{template_id}", response_model=ReportTemplateRead)
def get_template(template_id: int, db: Session = Depends(get_db)) -> ReportTemplateRead:
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return ReportTemplateRead.model_validate(template)


@router.post("/templates", response_model=ReportTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: ReportTemplateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> ReportTemplateRead:
    template = ReportTemplate(
        name=payload.name.strip(),
        category=payload.category,
        description=payload.description,
        letterhead_id=payload.letterhead_id,
        body_json=payload.body_json,
        translations_json=payload.translations_json,
        data_source_type=payload.data_source_type,
        is_enabled=payload.is_enabled,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return ReportTemplateRead.model_validate(template)


@router.put("/templates/{template_id}", response_model=ReportTemplateRead)
def update_template(
    template_id: int,
    payload: ReportTemplateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> ReportTemplateRead:
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot modify built-in templates")
    if payload.name is not None:
        template.name = payload.name.strip()
    if payload.category is not None:
        template.category = payload.category
    if payload.description is not None:
        template.description = payload.description
    if payload.letterhead_id is not None:
        template.letterhead_id = payload.letterhead_id
    if payload.body_json is not None:
        template.body_json = payload.body_json
        logger.info("Template %d body_json updated, length=%d", template_id, len(payload.body_json))
    if payload.translations_json is not None:
        template.translations_json = payload.translations_json
    if payload.data_source_type is not None:
        template.data_source_type = payload.data_source_type
    if payload.is_enabled is not None:
        template.is_enabled = payload.is_enabled
    db.commit()
    db.refresh(template)
    logger.info("Template %d saved, body_json length=%d", template_id, len(template.body_json or ""))
    return ReportTemplateRead.model_validate(template)


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> dict:
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot delete built-in templates")
    db.delete(template)
    db.commit()
    return {"status": "ok"}


@router.post("/templates/{template_id}/duplicate", response_model=ReportTemplateRead, status_code=status.HTTP_201_CREATED)
def duplicate_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> ReportTemplateRead:
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    new_template = ReportTemplate(
        name=f"{template.name} (Copy)",
        category=template.category,
        description=template.description,
        letterhead_id=template.letterhead_id,
        body_json=template.body_json,
        data_source_type=template.data_source_type,
        is_builtin=False,
        is_enabled=True,
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    return ReportTemplateRead.model_validate(new_template)


@router.get("/templates/{template_id}/preview")
def preview_template(
    template_id: int,
    entity_type: str = "job",
    entity_id: int | None = None,
    language: str = "en",
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Render template preview (returns the flowable JSON with resolved context)."""
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    pdf_service = PDFService(db)
    context = pdf_service.resolve_context(entity_type, entity_id or 1)
    context["now"] = date.today().isoformat()

    body_json = pdf_service._resolve_body(template, language)
    return {
        "template_id": template_id,
        "body_json": body_json,
        "context": context,
    }


# ── Report Generation ───────────────────────────────────────────────────────


@router.post("/generate")
def generate_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    template = db.get(ReportTemplate, payload.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    pdf_service = PDFService(db)
    fmt = payload.format or "pdf"

    try:
        if fmt == "csv":
            content_bytes, content_type, ext = pdf_service.generate_csv(
                template_id=payload.template_id,
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
                language=payload.language,
            )
        elif fmt == "html":
            content_bytes, content_type, ext = pdf_service.generate_html(
                template_id=payload.template_id,
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
                language=payload.language,
            )
        else:
            content_bytes = pdf_service.generate_pdf(
                template_id=payload.template_id,
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
                language=payload.language,
            )
            content_type = "application/pdf"
            ext = "pdf"
    except Exception as exc:
        logger.exception("Report generation failed for template %d", payload.template_id)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}")

    if not content_bytes or len(content_bytes) < 10:
        logger.error("Generated report is empty")
        raise HTTPException(status_code=500, detail="Generated report is empty.")

    storage = StorageService()
    storage_key, stored_filename = storage.make_storage_key(
        entity_type="report",
        category=payload.entity_type,
        original_filename=f"report_{payload.entity_type}_{payload.entity_id}.{ext}",
    )
    storage.save_bytes(storage_key=storage_key, payload=content_bytes, content_type=content_type)

    asset = AssetFile(
        entity_type="report",
        entity_id=payload.entity_id,
        category=payload.entity_type,
        original_filename=f"report_{payload.entity_type}_{payload.entity_id}.{ext}",
        stored_filename=stored_filename,
        content_type=content_type,
        size_bytes=len(content_bytes),
        storage_backend=storage.backend,
        storage_key=storage_key,
        created_by_user_id=current_user.id if current_user.id else None,
    )
    db.add(asset)
    db.flush()

    log = GeneratedReportLog(
        template_id=payload.template_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        asset_file_id=asset.id,
        generated_by_user_id=current_user.id if current_user.id else None,
        format=fmt,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "log_id": log.id,
        "asset_file_id": asset.id,
        "download_url": f"/api/v1/storage/files/{asset.id}/download",
        "size_bytes": len(content_bytes),
        "format": fmt,
        "filename": f"report_{payload.entity_type}_{payload.entity_id}.{ext}",
    }


@router.post("/preview")
def preview_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Response:
    """Generate a report preview without persisting it. Returns the file bytes directly."""
    template = db.get(ReportTemplate, payload.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    pdf_service = PDFService(db)
    fmt = payload.format or "pdf"

    try:
        if fmt == "html":
            content_bytes, content_type, ext = pdf_service.generate_html(
                template_id=payload.template_id,
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
                language=payload.language,
            )
        else:
            content_bytes = pdf_service.generate_pdf(
                template_id=payload.template_id,
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
                language=payload.language,
            )
            content_type = "application/pdf"
            ext = "pdf"
    except Exception as exc:
        logger.exception("Report preview failed for template %d", payload.template_id)
        raise HTTPException(status_code=500, detail=f"Report preview failed: {exc}")

    if not content_bytes or len(content_bytes) < 10:
        logger.error("Generated preview is empty")
        raise HTTPException(status_code=500, detail="Generated preview is empty.")

    return Response(
        content=content_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f"inline; filename=preview_{payload.entity_type}_{payload.entity_id}.{ext}",
        },
    )


@router.get("/logs", response_model=list[GeneratedReportLogRead])
def list_report_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[GeneratedReportLogRead]:
    query = select(GeneratedReportLog).order_by(GeneratedReportLog.created_at.desc())
    if entity_type:
        query = query.where(GeneratedReportLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(GeneratedReportLog.entity_id == entity_id)
    rows = list(db.scalars(query.limit(100)).all())
    return [GeneratedReportLogRead.model_validate(r) for r in rows]


# ── Data Source Schema ──────────────────────────────────────────────────────


_DATA_SOURCE_SCHEMAS: dict[str, list[DataSourceField]] = {
    "job": [
        DataSourceField(key="job.job_code", label="Job Code"),
        DataSourceField(key="job.description", label="Description"),
        DataSourceField(key="job.status", label="Status"),
        DataSourceField(key="job.start_date", label="Start Date"),
        DataSourceField(key="job.end_date", label="End Date"),
        DataSourceField(key="job.sales_price", label="Sales Price", type="number"),
        DataSourceField(key="job.notes", label="Notes", type="text"),
        DataSourceField(key="job.customer_name", label="Customer Name"),
        DataSourceField(key="job.venue_name", label="Venue Name"),
        DataSourceField(key="customer.name", label="Customer"),
        DataSourceField(key="customer.email", label="Customer Email"),
        DataSourceField(key="customer.phone", label="Customer Phone"),
        DataSourceField(key="venue.name", label="Venue"),
        DataSourceField(key="venue.address", label="Venue Address"),
        DataSourceField(key="job.requirements", label="Job Requirements (list)", type="array"),
        DataSourceField(key="job.requirements[0].quantity_required", label="Req. Qty", type="number"),
        DataSourceField(key="job.requirements[0].quantity_picked", label="Req. Picked", type="number"),
        DataSourceField(key="job.requirements[0].product.name", label="Req. Product Name"),
        DataSourceField(key="job.requirements[0].product.sku", label="Req. Product SKU"),
        DataSourceField(key="now", label="Today's Date"),
    ],
    "device": [
        DataSourceField(key="device.asset_tag", label="Asset Tag"),
        DataSourceField(key="device.serial_number", label="Serial Number"),
        DataSourceField(key="device.status", label="Status"),
        DataSourceField(key="device.condition", label="Condition"),
        DataSourceField(key="device.barcode", label="Barcode"),
        DataSourceField(key="product.name", label="Product Name"),
        DataSourceField(key="product.sku", label="SKU"),
        DataSourceField(key="product.category", label="Category"),
        DataSourceField(key="product.weight_kg", label="Weight (kg)", type="number"),
        DataSourceField(key="device.case_device.asset_tag", label="Parent Case Asset Tag"),
        DataSourceField(key="device.case_contents", label="Case Contents (list)", type="array"),
        DataSourceField(key="device.case_contents_grouped", label="Case Contents Grouped (list)", type="array"),
        DataSourceField(key="device.case_contents_grouped[0].sku", label="Grouped SKU"),
        DataSourceField(key="device.case_contents_grouped[0].name", label="Grouped Product Name"),
        DataSourceField(key="device.case_contents_grouped[0].count", label="Grouped Count", type="number"),
        DataSourceField(key="device.case_contents[0].asset_tag", label="Content Asset Tag"),
        DataSourceField(key="device.case_contents[0].serial_number", label="Content Serial Number"),
        DataSourceField(key="device.case_contents[0].product.name", label="Content Product Name"),
        DataSourceField(key="device.case_contents[0].product.sku", label="Content Product SKU"),
        DataSourceField(key="device.maintenance_records", label="Maintenance Records (list)", type="array"),
        DataSourceField(key="device.maintenance_records[0].maintenance_type", label="Maint. Type"),
        DataSourceField(key="device.maintenance_records[0].status", label="Maint. Status"),
        DataSourceField(key="device.maintenance_records[0].scheduled_date", label="Maint. Scheduled"),
        DataSourceField(key="device.maintenance_records[0].completed_date", label="Maint. Completed"),
        DataSourceField(key="device.maintenance_records[0].notes", label="Maint. Notes"),
        DataSourceField(key="device.defect_reports", label="Defect Reports (list)", type="array"),
        DataSourceField(key="device.defect_reports[0].title", label="Defect Title"),
        DataSourceField(key="device.defect_reports[0].status", label="Defect Status"),
        DataSourceField(key="device.defect_reports[0].severity", label="Defect Severity"),
    ],
    "product": [
        DataSourceField(key="product.name", label="Product Name"),
        DataSourceField(key="product.sku", label="SKU"),
        DataSourceField(key="product.category", label="Category"),
        DataSourceField(key="product.brand", label="Brand"),
        DataSourceField(key="product.daily_rate", label="Daily Rate", type="number"),
        DataSourceField(key="product.weight_kg", label="Weight (kg)", type="number"),
        DataSourceField(key="product.devices", label="Devices (list)", type="array"),
        DataSourceField(key="product.devices[0].asset_tag", label="Device Asset Tag"),
        DataSourceField(key="product.devices[0].serial_number", label="Device Serial Number"),
        DataSourceField(key="product.devices[0].status", label="Device Status"),
        DataSourceField(key="product.devices[0].condition", label="Device Condition"),
        DataSourceField(key="product.components", label="Components (list)", type="array"),
        DataSourceField(key="product.components[0].quantity", label="Component Qty", type="number"),
        DataSourceField(key="product.components[0].product.name", label="Component Name"),
        DataSourceField(key="product.components[0].product.sku", label="Component SKU"),
        DataSourceField(key="product.accessories", label="Accessories (list)", type="array"),
        DataSourceField(key="product.accessories[0].quantity", label="Accessory Qty", type="number"),
        DataSourceField(key="product.accessories[0].product.name", label="Accessory Name"),
        DataSourceField(key="product.accessories[0].product.sku", label="Accessory SKU"),
    ],
    "inventory": [
        DataSourceField(key="products", label="Products List", type="array"),
        DataSourceField(key="products[0].name", label="Product Name"),
        DataSourceField(key="products[0].sku", label="Product SKU"),
        DataSourceField(key="products[0].category", label="Product Category"),
        DataSourceField(key="products[0].daily_rate", label="Product Daily Rate", type="number"),
        DataSourceField(key="devices", label="Devices List", type="array"),
        DataSourceField(key="devices[0].asset_tag", label="Device Asset Tag"),
        DataSourceField(key="devices[0].serial_number", label="Device Serial Number"),
        DataSourceField(key="devices[0].status", label="Device Status"),
        DataSourceField(key="devices[0].condition", label="Device Condition"),
    ],
}


@router.get("/data-source/{source_type}/schema", response_model=DataSourceSchemaResponse)
def get_data_source_schema(source_type: str) -> DataSourceSchemaResponse:
    fields = _DATA_SOURCE_SCHEMAS.get(source_type, [])
    return DataSourceSchemaResponse(entity_type=source_type, fields=fields)


@router.get("/debug/template/{template_id}")
def debug_template(template_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Debug endpoint: returns raw template data including body_json."""
    template = db.get(ReportTemplate, template_id)
    if not template:
        return {"error": "not found"}
    body = template.body_json or ""
    parsed = {}
    try:
        parsed = json.loads(body)
    except Exception as e:
        parsed = {"_parse_error": str(e)}
    return {
        "id": template.id,
        "name": template.name,
        "body_json_raw_length": len(body),
        "body_json_raw_preview": body[:200] if body else "(empty)",
        "body_json_parsed_keys": list(parsed.keys()) if isinstance(parsed, dict) else "not a dict",
        "flowables_count": len(parsed.get("flowables", [])) if isinstance(parsed, dict) else 0,
    }
