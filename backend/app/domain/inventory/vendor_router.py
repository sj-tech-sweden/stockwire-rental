"""Vendor catalog API: CRUD for vendor_products + pluggable import preview/apply."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user

# Register the web scraper importer plugins so they appear in
# /vendor-catalog/plugins. Importing the plugin classes triggers their
# module-level self-registration; the explicit calls make the dependency
# visible to static analyzers.
from app.domain.inventory.scraper_thomann import ThomannScraperPlugin
from app.domain.inventory.scraper_ui_com import UiComScraperPlugin
from app.domain.inventory.models import VendorProduct
from app.domain.inventory.schemas import (
    BulkDeleteVendorProductsRequest,
    VendorProductClusterRead,
    VendorProductCreate,
    VendorProductRead,
    VendorProductUpdate,
)
from app.domain.inventory.vendor_catalog import (
    IMPORTER_PLUGINS,
    VendorEquipmentRecord,
    cluster_vendor_products,
    get_plugin,
    register_importer_plugin,
    upsert_vendor_products,
)

register_importer_plugin(ThomannScraperPlugin)
register_importer_plugin(UiComScraperPlugin)
from app.domain.settings.models import AppSetting

logger = logging.getLogger(__name__)

# In-memory store for async vendor import job status. A single uvicorn worker
# can use this; multi-worker deployments would need a persistent job queue.
IMPORT_JOBS: dict[str, dict] = {}

router = APIRouter(
    prefix="/vendor-products",
    tags=["vendor-products"],
    dependencies=[Depends(get_current_user)],
)


class ImportPreviewRequest(BaseModel):
    plugin_id: str
    config: dict = {}
    field_map: dict = {}


class ImportApplyRequest(BaseModel):
    vendor_id: int | None = None
    rows: list[dict] = []


# Columns that may be sorted on, to avoid arbitrary attribute reflection.
_SORTABLE = {
    "name", "sku", "unit_cost", "stock_quantity", "brand", "category",
    "vendor_item_number", "supplier_item_number", "last_synced_at", "created_at",
    "weight", "country_of_origin", "intrastat_code", "pieces_per_carton",
    "incoming_quantity", "expected_delivery_date",
}


@router.get("", response_model=list[VendorProductRead])
def list_vendor_products(
    vendor_id: int | None = Query(None),
    search: str | None = Query(None),
    active_only: bool = Query(False),
    category: str | None = Query(None),
    brand: str | None = Query(None),
    ids: str | None = Query(None, description="Comma-separated vendor_product ids"),
    sort_by: str = Query("name"),
    sort_dir: str = Query("asc"),
    limit: int = Query(50, le=200, ge=1),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    response: Response = None,
) -> list[VendorProduct]:
    """List vendor products with server-side filtering, sorting and pagination.

    The total number of matching rows is returned in the ``X-Total-Count``
    header so the UI can paginate without transferring the whole table.
    """
    stmt = select(VendorProduct)
    if vendor_id is not None:
        stmt = stmt.where(VendorProduct.vendor_id == vendor_id)
    if active_only:
        stmt = stmt.where(VendorProduct.is_active.is_(True))
    if category:
        stmt = stmt.where(VendorProduct.category == category)
    if brand:
        stmt = stmt.where(VendorProduct.brand == brand)
    if ids:
        id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            stmt = stmt.where(VendorProduct.id.in_(id_list))
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            (VendorProduct.name.ilike(like))
            | (VendorProduct.sku.ilike(like))
            | (VendorProduct.brand.ilike(like))
            | (VendorProduct.vendor_item_number.ilike(like))
            | (VendorProduct.supplier_item_number.ilike(like))
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    sort_col = getattr(VendorProduct, sort_by, None)
    if sort_col is None or sort_by not in _SORTABLE:
        sort_col = VendorProduct.name
    direction = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    items = db.scalars(stmt.order_by(direction).limit(limit).offset(offset)).all()
    if response is not None:
        response.headers["X-Total-Count"] = str(total or 0)
    return list(items)


@router.get("/clusters", response_model=list[VendorProductClusterRead])
def list_vendor_product_clusters(
    vendor_id: int | None = Query(None),
    search: str | None = Query(None),
    category: str | None = Query(None),
    brand: str | None = Query(None),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Cluster vendor products that represent the same physical item.

    Uses the same reference-key (and fuzzy-name fallback) matching as the
    purchasing comparison engine so cross-supplier duplicates collapse into a
    single card showing every supplier's price/stock/ETA.
    """
    return cluster_vendor_products(
        db,
        vendor_id=vendor_id,
        search=search,
        active_only=active_only,
        category=category,
        brand=brand,
    )


@router.get("/facets")
def vendor_product_facets(
    q: str | None = Query(None, description="Optional substring filter for brand/category"),
    db: Session = Depends(get_db),
) -> dict:
    """Distinct, non-empty categories and brands for filter dropdowns.

    When ``q`` is supplied the lists are filtered by that substring so the
    UI can offer type-ahead search across all values (not just the first N).
    """

    def distinct(column):
        stmt = (
            select(column)
            .where(column.isnot(None))
            .where(column != "")
        )
        if q:
            stmt = stmt.where(column.ilike(f"%{q}%"))
            stmt = stmt.group_by(column).order_by(column).limit(200)
        else:
            stmt = stmt.group_by(column).order_by(column)
        rows = db.scalars(stmt).all()
        return [r for r in rows if r]

    return {
        "categories": distinct(VendorProduct.category),
        "brands": distinct(VendorProduct.brand),
    }


@router.post("", response_model=VendorProductRead, status_code=201)
def create_vendor_product(
    payload: VendorProductCreate, db: Session = Depends(get_db)
) -> VendorProduct:
    vp = VendorProduct(**payload.model_dump())
    db.add(vp)
    db.commit()
    db.refresh(vp)
    return vp


@router.get("/{product_id}", response_model=VendorProductRead)
def get_vendor_product(product_id: int, db: Session = Depends(get_db)) -> VendorProduct:
    vp = db.get(VendorProduct, product_id)
    if vp is None:
        raise HTTPException(status_code=404, detail="Vendor product not found")
    return vp


@router.put("/{product_id}", response_model=VendorProductRead)
def update_vendor_product(
    product_id: int, payload: VendorProductUpdate, db: Session = Depends(get_db)
) -> VendorProduct:
    vp = db.get(VendorProduct, product_id)
    if vp is None:
        raise HTTPException(status_code=404, detail="Vendor product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vp, field, value)
    db.commit()
    db.refresh(vp)
    return vp


@router.delete("/{product_id}", status_code=204)
def delete_vendor_product(product_id: int, db: Session = Depends(get_db)) -> None:
    vp = db.get(VendorProduct, product_id)
    if vp is None:
        raise HTTPException(status_code=404, detail="Vendor product not found")
    db.delete(vp)
    db.commit()


@router.post("/bulk-delete", status_code=200)
def bulk_delete_vendor_products(
    req: BulkDeleteVendorProductsRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Delete many vendor products (e.g. everything a removed integration imported)."""
    stmt = select(VendorProduct)
    if req.ids:
        stmt = stmt.where(VendorProduct.id.in_(req.ids))
    else:
        clauses = []
        if req.vendor_id is not None:
            clauses.append(VendorProduct.vendor_id == req.vendor_id)
        if req.source_plugin is not None:
            clauses.append(VendorProduct.source_plugin == req.source_plugin)
        if req.name_contains:
            clauses.append(VendorProduct.name.ilike(f"%{req.name_contains}%"))
        if not clauses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide at least one filter (ids, vendor_id, source_plugin or name_contains)",
            )
        stmt = stmt.where(*clauses)
    products = db.scalars(stmt).all()
    count = len(products)
    for vp in products:
        db.delete(vp)
    db.commit()
    return {"deleted": count}


# ── Import plugin endpoints ───────────────────────────────────────────────────

plugin_router = APIRouter(
    prefix="/vendor-catalog",
    tags=["vendor-catalog"],
    dependencies=[Depends(get_current_user)],
)


@plugin_router.get("/plugins")
def list_importer_plugins() -> list[dict]:
    return [
        {
            "id": cls.id,
            "label": cls.label,
            "source_type": cls.source_type,
            "config_schema": cls.config_schema,
            "default_field_map": cls.default_field_map,
        }
        for cls in IMPORTER_PLUGINS.values()
    ]


@plugin_router.post("/preview")
def preview_import(payload: ImportPreviewRequest, db: Session = Depends(get_db)) -> dict:
    try:
        plugin = get_plugin(payload.plugin_id, payload.field_map, payload.config)
        records = plugin.run()
    except Exception as exc:
        logger.exception("Vendor catalog preview failed")
        raise HTTPException(status_code=400, detail=f"Preview failed: {exc}")
    return {"count": len(records), "records": [r.to_dict() for r in records]}


class DiscoverCategoriesRequest(BaseModel):
    plugin_id: str
    url: str = ""
    config: dict = {}


@plugin_router.post("/discover")
def discover_categories(payload: DiscoverCategoriesRequest) -> dict:
    cls = IMPORTER_PLUGINS.get(payload.plugin_id)
    if cls is None:
        raise HTTPException(status_code=400, detail="Unknown importer plugin")
    try:
        categories = cls.discover_categories(payload.url or "", config=payload.config)
    except Exception as exc:  # discovery is best-effort
        logger.exception("Category discovery failed")
        raise HTTPException(status_code=400, detail=f"Discovery failed: {exc}")
    return {"categories": categories}


@plugin_router.post("/apply")
def apply_import(payload: ImportApplyRequest, db: Session = Depends(get_db)) -> dict:
    records: list[VendorEquipmentRecord] = []
    valid_fields = VendorEquipmentRecord.__dataclass_fields__.keys()
    for row in payload.rows:
        try:
            cleaned = {k: v for k, v in row.items() if k in valid_fields}
            records.append(VendorEquipmentRecord(**cleaned))
        except Exception:
            continue
    if not records:
        raise HTTPException(status_code=400, detail="No valid rows to import")
    result = upsert_vendor_products(db, records, payload.vendor_id, source_plugin=None)
    return result


# ── Persisted import sources ──────────────────────────────────────────────────

VENDOR_SOURCES_KEY = "vendor_catalog.sources"


class VendorSourceBase(BaseModel):
    name: str
    plugin_id: str
    enabled: bool = True
    vendor_id: int | None = None
    config: dict = {}
    field_map: dict = {}
    auto_sync_interval: int = 0


class VendorSourceCreate(VendorSourceBase):
    pass


class VendorSourceUpdate(BaseModel):
    name: str | None = None
    plugin_id: str | None = None
    enabled: bool | None = None
    vendor_id: int | None = None
    config: dict | None = None
    field_map: dict | None = None
    auto_sync_interval: int | None = None


class VendorSourceRead(VendorSourceBase):
    id: str
    last_synced_at: str | None = None


def _read_sources(db: Session) -> list[dict]:
    setting = db.scalar(select(AppSetting).where(AppSetting.key == VENDOR_SOURCES_KEY))
    if not setting or not setting.value_json:
        return []
    try:
        return json.loads(setting.value_json) or []
    except Exception:
        return []


def _write_sources(db: Session, sources: list[dict]) -> None:
    setting = db.scalar(select(AppSetting).where(AppSetting.key == VENDOR_SOURCES_KEY))
    if setting is None:
        setting = AppSetting(key=VENDOR_SOURCES_KEY, value_json=json.dumps(sources))
        db.add(setting)
    else:
        setting.value_json = json.dumps(sources)
    db.commit()


def _find_source(sources: list[dict], source_id: str) -> dict | None:
    return next((s for s in sources if s.get("id") == source_id), None)


sources_router = APIRouter(
    prefix="/vendor-catalog",
    tags=["vendor-catalog"],
    dependencies=[Depends(get_current_user)],
)


@sources_router.get("/sources", response_model=list[VendorSourceRead])
def list_vendor_sources(db: Session = Depends(get_db)) -> list[dict]:
    sources = _read_sources(db)
    for source in sources:
        job_id = source.get("last_import_job_id")
        if job_id:
            job = IMPORT_JOBS.get(job_id)
            if job:
                source["last_import_status"] = job["status"]
                source["last_import_stage"] = job["stage"]
                source["last_import_processed"] = job["processed"]
                source["last_import_total"] = job["total"]
                source["last_import_error"] = job["error"]
            else:
                source["last_import_status"] = "unknown"
    return sources


@sources_router.post("/sources", response_model=VendorSourceRead, status_code=201)
def create_vendor_source(payload: VendorSourceCreate, db: Session = Depends(get_db)) -> dict:
    sources = _read_sources(db)
    source = payload.model_dump()
    source["id"] = uuid.uuid4().hex
    source["last_synced_at"] = None
    sources.append(source)
    _write_sources(db, sources)
    return source


@sources_router.put("/sources/{source_id}", response_model=VendorSourceRead)
def update_vendor_source(
    source_id: str, payload: VendorSourceUpdate, db: Session = Depends(get_db)
) -> dict:
    sources = _read_sources(db)
    source = _find_source(sources, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Vendor source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        source[field] = value
    _write_sources(db, sources)
    return source


@sources_router.delete("/sources/{source_id}", status_code=204)
def delete_vendor_source(
    source_id: str,
    delete_products: bool = Query(False),
    db: Session = Depends(get_db),
) -> None:
    sources = _read_sources(db)
    source = _find_source(sources, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Vendor source not found")
    new_sources = [s for s in sources if s.get("id") != source_id]
    _write_sources(db, new_sources)
    # Cascade: also remove the vendor products this source imported (matched by
    # plugin + vendor). Without this, deleting an integration leaves orphan rows.
    if delete_products:
        clauses = [VendorProduct.source_plugin == source.get("plugin_id")]
        if source.get("vendor_id") is not None:
            clauses.append(VendorProduct.vendor_id == source["vendor_id"])
        for vp in db.scalars(select(VendorProduct).where(*clauses)).all():
            db.delete(vp)
        db.commit()


@sources_router.post("/sources/{source_id}/preview")
def preview_vendor_source(source_id: str, db: Session = Depends(get_db)) -> dict:
    source = _find_source(_read_sources(db), source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Vendor source not found")
    if source.get("plugin_id") not in IMPORTER_PLUGINS:
        raise HTTPException(status_code=400, detail="Unknown importer plugin")
    try:
        plugin = get_plugin(source["plugin_id"], source.get("field_map", {}), source.get("config", {}))
        records = plugin.run()
    except Exception as exc:
        logger.exception("Vendor source preview failed")
        raise HTTPException(status_code=400, detail=f"Preview failed: {exc}")
    return {"count": len(records), "records": [r.to_dict() for r in records]}


@sources_router.post("/sources/{source_id}/run")
def run_vendor_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    sources = _read_sources(db)
    source = _find_source(sources, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Vendor source not found")
    if source.get("plugin_id") not in IMPORTER_PLUGINS:
        raise HTTPException(status_code=400, detail="Unknown importer plugin")

    job_id = uuid.uuid4().hex
    IMPORT_JOBS[job_id] = {
        "job_id": job_id,
        "source_id": source_id,
        "status": "pending",
        "stage": "queued",
        "processed": 0,
        "total": None,
        "created": 0,
        "updated": 0,
        "error": None,
    }
    source["last_import_job_id"] = job_id
    _write_sources(db, sources)
    background_tasks.add_task(_run_vendor_import_job, job_id, source_id, source)
    logger.info("Queued vendor import job %s for source %s", job_id, source_id)
    return {"job_id": job_id, "status": "pending"}


@sources_router.get("/vendor-import-jobs/{job_id}")
def get_vendor_import_job(job_id: str) -> dict:
    job = IMPORT_JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found")
    return dict(job)


def _run_vendor_import_job(job_id: str, source_id: str, source: dict) -> None:
    """Fetch and upsert vendor products in the background, updating IMPORT_JOBS."""
    from app.db.session import SessionLocal

    def _update(**kwargs):
        IMPORT_JOBS[job_id].update(kwargs)

    _update(status="running", stage="fetching")
    db = SessionLocal()
    try:
        plugin = get_plugin(source["plugin_id"], source.get("field_map", {}), source.get("config", {}))
        records = plugin.run()
        total = len(records)
        _update(total=total, stage="upserting", processed=0)

        def progress_callback(processed, total, created, updated):
            _update(processed=processed, total=total, created=created, updated=updated)

        result = upsert_vendor_products(
            db,
            records,
            source.get("vendor_id"),
            source_plugin=source.get("plugin_id"),
            progress_callback=progress_callback,
        )
        _update(
            status="completed",
            stage="finished",
            processed=total,
            created=result["created"],
            updated=result["updated"],
        )
        _update_source_synced_at(db, source_id, records=result)
    except Exception as exc:
        logger.exception("Vendor import job %s failed", job_id)
        _update(status="failed", stage="finished", error=str(exc))
    finally:
        db.close()


def _update_source_synced_at(db: Session, source_id: str, records: dict | None = None) -> None:
    sources = _read_sources(db)
    source = _find_source(sources, source_id)
    if source is None:
        return
    from datetime import datetime

    source["last_synced_at"] = datetime.now(UTC).isoformat()
    source.pop("last_auto_sync_error", None)
    source.pop("last_auto_sync_failed_at", None)
    if records:
        source.setdefault("last_result", {}).update(records)
    _write_sources(db, sources)
