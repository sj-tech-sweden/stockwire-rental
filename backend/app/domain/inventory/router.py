import json
import re
from typing import Any
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import UploadFile, File, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError

from app.db.session import get_db
from app.config import settings
from app.domain.auth.deps import get_current_user, require_admin, require_editor
from app.domain.auth.models import User
from app.domain.audit.service import record_activity
from app.domain.inventory.models import (
    DefectComment,
    DefectReport,
    Device,
    DeviceMaintenance,
    DeviceMaintenanceSchedule,
    InventoryAuditLog,
    InventoryCategory,
    MaintenanceComment,
    Product,
    ProductAccessory,
    ProductComponent,
    Zone,
)
from app.domain.jobs.models import Job, JobRequirement
from app.domain.settings.models import AppSetting
from app.domain.settings.schemas import DEFAULT_CATEGORY_PREFILL_PATHS
from app.domain.realtime.events import emit_realtime_event
from app.domain.inventory.schemas import (
    DeviceCreate,
    DeviceMaintenanceComplete,
    DeviceMaintenanceCreate,
    DeviceMaintenanceBulkUpdateRequest,
    MaintenanceBulkScheduleRequest,
    MaintenanceScheduleBulkUpdateRequest,
    MaintenanceScheduleRead,
    MaintenanceScheduleUpdate,
    BulkDeleteRequest,
    BulkOperationResult,
    DeviceBulkUpdateRequest,
    DefectCommentCreate,
    DefectCommentRead,
    DefectCommentUpdate,
    DefectReportCreate,
    DefectReportRead,
    DefectReportUpdate,
    DefectTimelineEntry,
    MaintenanceCommentCreate,
    MaintenanceCommentRead,
    MaintenanceCommentUpdate,
    DeviceMaintenanceRead,
    DeviceMaintenanceUpdate,
    DeviceRead,
    DeviceUpdate,
    InventoryCategoryCreate,
    InventoryCategoryMove,
    InventoryCategoryRead,
    InventoryCategoryTreeRead,
    InventoryCategoryUpdate,
    InventoryScanRequest,
    InventoryScanResponse,
    InventoryCheckedOutDeviceRead,
    ProductAccessoryRead,
    ProductAccessoryUpsertRequest,
    ProductComponentRead,
    ProductComponentUpsertRequest,
    InventoryAuditRead,
    ProductCreate,
    ProductDevicesBulkCreate,
    ProductBulkUpdateRequest,
    ProductRead,
    ProductUpdate,
    MAINTENANCE_STATUSES,
    DEFECT_SEVERITIES,
    DEFECT_STATUSES,
    MAINTENANCE_INTERVAL_MODES,
    MAINTENANCE_TYPES,
    ZoneCreate,
    ZoneMove,
    ZoneRead,
    ZoneTreeRead,
    ZoneUpdate,
)
 

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(get_current_user)])


def _coerce_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        quantized = Decimal(text).quantize(Decimal("0.01"))
        if not quantized.is_finite():
            return None
        return quantized
    except (InvalidOperation, ValueError):
        return None


@router.get('/import/presets/hirehop')
def get_hirehop_import_preset() -> dict:
    """Return the default HireHop import mapping as a preset for frontend import UI."""
    try:
        import json
        from app.domain.imports.hirehop import DEFAULT_MAPPING_PATH

        if not DEFAULT_MAPPING_PATH.exists():
            return {}
        with open(DEFAULT_MAPPING_PATH, 'r', encoding='utf8') as fh:
            return json.load(fh)
    except Exception:
        return {}



@router.post('/import')
async def import_inventory(
    file: UploadFile = File(...),
    preset: str | None = Query('hirehop'),
    dry_run: bool | None = Query(True),
    update_existing: bool | None = Query(False),
    limit: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> dict:
    """Upload an inventory file and import it. Supports `preset=hirehop`.

    If `dry_run=true` (default) returns counts and samples without persisting.
    """
    import json
    from app.domain.imports.hirehop import DEFAULT_MAPPING_PATH, process_hirehop_data, load_mapping

    max_upload_bytes = max(1, int(settings.storage_max_upload_mb or 25)) * 1024 * 1024
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds {max_upload_bytes // (1024 * 1024)}MB limit",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    try:
        data = json.loads(content.decode('utf8'))
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid JSON file')

    if preset != 'hirehop':
        raise HTTPException(status_code=400, detail='Unsupported preset')

    # load default mapping from the app package resource
    try:
        mapping = load_mapping(str(DEFAULT_MAPPING_PATH)) if DEFAULT_MAPPING_PATH.exists() else None
    except Exception:
        mapping = None

    products_out, devices_out = process_hirehop_data(data, mapping=mapping, limit=limit)

    if dry_run:
        return {
            'products': len(products_out),
            'devices': len(devices_out),
            'sample_products': products_out[:10],
            'sample_devices': devices_out[:10],
        }

    # persist products
    created_products = []
    updated_products = []
    source_to_product_id: dict = {}
    for p in products_out:
        src_id = p.get('source_id')
        ext_ref = str(src_id) if src_id is not None else None

        existing = None
        if ext_ref:
            try:
                existing = db.scalar(
                    select(Product).where(Product.external_source == 'hirehop').where(Product.external_reference == ext_ref)
                )
            except Exception:
                existing = None

        if existing:
            # update a few useful fields to keep import idempotent
            if p.get('sku'):
                existing.sku = p.get('sku')
            if p.get('title') or p.get('name'):
                existing.name = p.get('title') or p.get('name')
            if str(p.get('is_box') or '').strip().lower() in {'1', 'true', 'yes'}:
                existing.product_type = 'case'
            if p.get('brand') is not None:
                existing.brand = p.get('brand')
            if p.get('manufacturer') is not None:
                existing.manufacturer = p.get('manufacturer')
            if p.get('daily_rate') is not None:
                existing.daily_rate = p.get('daily_rate')
            if p.get('rental_price') is not None:
                existing.rental_price = p.get('rental_price')
            replace_cost = _coerce_decimal(p.get('replace_cost'))
            if replace_cost is not None:
                existing.replace_cost = replace_cost
            if p.get('weight') is not None:
                existing.weight_kg = p.get('weight')
            if p.get('height_cm') is not None:
                existing.height_cm = p.get('height_cm')
            if p.get('width_cm') is not None:
                existing.width_cm = p.get('width_cm')
            if p.get('depth_cm') is not None:
                existing.depth_cm = p.get('depth_cm')
            matched_category = _resolve_hirehop_category(db, p)
            if matched_category is not None:
                existing.category_id = matched_category.id
                existing.category = matched_category.name
            try:
                db.commit()
                db.refresh(existing)
                record_activity(
                    db,
                    user_id=current_user.id,
                    entity_type='product',
                    entity_id=existing.id,
                    action='update',
                    message_format='product_updated',
                    message_params={'sku': existing.sku, 'name': existing.name},
                    details={'sku': existing.sku, 'name': existing.name},
                )
                emit_realtime_event('inventory.updated', {'entity': 'product', 'action': 'update', 'id': existing.id})
                updated_products.append(_to_product_read(db, existing))
                if src_id is not None:
                    source_to_product_id[src_id] = existing.id
            except Exception:
                db.rollback()
        else:
            prod_data = {}
            prod_data['sku'] = p.get('sku') or (f"HH-{src_id}" if src_id is not None else None)
            prod_data['name'] = p.get('title') or p.get('name') or 'Imported product'
            if str(p.get('is_box') or '').strip().lower() in {'1', 'true', 'yes'}:
                prod_data['product_type'] = 'case'
            prod_data['brand'] = p.get('brand')
            prod_data['manufacturer'] = p.get('manufacturer')
            matched_category = _resolve_hirehop_category(db, p)
            if matched_category is not None:
                prod_data['category_id'] = matched_category.id
                prod_data['category'] = matched_category.name
            prod_data['daily_rate'] = p.get('daily_rate') or 0
            prod_data['rental_price'] = p.get('rental_price') or 0
            prod_data['replace_cost'] = _coerce_decimal(p.get('replace_cost'))
            weight = p.get('weight') if p.get('weight') is not None else p.get('weight_kg')
            prod_data['weight_kg'] = weight
            prod_data['height_cm'] = p.get('height_cm')
            prod_data['width_cm'] = p.get('width_cm')
            prod_data['depth_cm'] = p.get('depth_cm')
            prod_data['external_source'] = 'hirehop'
            prod_data['external_reference'] = ext_ref

            product = Product(**{k: v for k, v in prod_data.items() if v is not None})
            db.add(product)
            try:
                db.commit()
                db.refresh(product)
                record_activity(
                    db,
                    user_id=current_user.id,
                    entity_type='product',
                    entity_id=product.id,
                    action='create',
                    message_format='product_imported',
                    message_params={'sku': product.sku, 'name': product.name},
                    details={'sku': product.sku, 'name': product.name},
                )
                emit_realtime_event('inventory.updated', {'entity': 'product', 'action': 'create', 'id': product.id})
                created_products.append(_to_product_read(db, product))
                if src_id is not None:
                    source_to_product_id[src_id] = product.id
            except Exception:
                db.rollback()

    # persist devices
    created_devices = []
    updated_devices = []
    skipped_devices = 0
    for d in devices_out:
        prod_src = d.get('product_source_id')
        product_id = source_to_product_id.get(prod_src)
        if not product_id:
            skipped_devices += 1
            continue

        # avoid duplicates by HireHop source_serial_id, then serial_number or barcode (scoped to the same product)
        source_serial = d.get('source_serial_id')
        serial = d.get('serial') or d.get('serial_number')
        barcode = d.get('barcode')
        exists_dev = None
        try:
            if source_serial:
                exists_dev = db.scalar(select(Device).where(Device.source_serial_id == str(source_serial), Device.product_id == product_id))
            if not exists_dev and serial:
                exists_dev = db.scalar(select(Device).where(Device.serial_number == serial, Device.product_id == product_id))
            if not exists_dev and barcode:
                exists_dev = db.scalar(select(Device).where(Device.barcode == barcode, Device.product_id == product_id))
        except Exception:
            exists_dev = None

        if exists_dev:
            if update_existing:
                # update fields on existing device
                if serial:
                    exists_dev.serial_number = serial
                if barcode:
                    exists_dev.barcode = barcode
                if source_serial:
                    exists_dev.source_serial_id = str(source_serial)
                if d.get('purchase_date'):
                    try:
                        from datetime import datetime

                        exists_dev.purchase_date = datetime.strptime(str(d.get('purchase_date')), '%Y-%m-%d').date()
                    except Exception:
                        pass
                purchase_price = _coerce_decimal(d.get('purchase_price'))
                if purchase_price is not None:
                    exists_dev.purchase_price = purchase_price
                purchased_from = str(d.get('purchased_from') or '').strip()
                if purchased_from:
                    exists_dev.purchased_from = purchased_from
                sold_price = _coerce_decimal(d.get('sold_price'))
                if sold_price is not None:
                    exists_dev.sold_price = sold_price
                finance_upto = str(d.get('finance_upto') or '').strip()
                if finance_upto:
                    exists_dev.finance_upto = finance_upto
                finance_company = str(d.get('finance_company') or '').strip()
                if finance_company:
                    exists_dev.finance_company = finance_company
                finance_ref = str(d.get('finance_ref') or '').strip()
                if finance_ref:
                    exists_dev.finance_ref = finance_ref
                pre_prep = str(d.get('pre_prep') or '').strip()
                if pre_prep:
                    exists_dev.pre_prep = pre_prep
                if d.get('retire_date'):
                    try:
                        from datetime import datetime

                        exists_dev.retire_date = datetime.strptime(str(d.get('retire_date')), '%Y-%m-%d').date()
                    except Exception:
                        pass
                depot = d.get('depot')
                if depot:
                    zone = db.scalar(select(Zone).where(Zone.code == depot))
                    if zone is None:
                        zone = db.scalar(select(Zone).where(Zone.name == depot))
                    if zone:
                        exists_dev.location_zone_id = zone.id
                try:
                    db.commit()
                    db.refresh(exists_dev)
                    updated_devices.append(_to_device_read(db, exists_dev))
                except Exception:
                    db.rollback()
                    skipped_devices += 1
                continue
            else:
                skipped_devices += 1
                continue

        device_data = {}
        device_data['product_id'] = product_id
        # map fields
        if serial:
            device_data['serial_number'] = serial
        if barcode:
            device_data['barcode'] = barcode
        if d.get('source_serial_id'):
            device_data['source_serial_id'] = str(d.get('source_serial_id'))
        if d.get('purchase_date'):
            try:
                from datetime import datetime

                device_data['purchase_date'] = datetime.strptime(str(d.get('purchase_date')), '%Y-%m-%d').date()
            except Exception:
                pass
        purchase_price = _coerce_decimal(d.get('purchase_price'))
        if purchase_price is not None:
            device_data['purchase_price'] = purchase_price
        if d.get('purchased_from') is not None:
            purchased_from = str(d.get('purchased_from') or '').strip()
            if purchased_from:
                device_data['purchased_from'] = purchased_from
        sold_price = _coerce_decimal(d.get('sold_price'))
        if sold_price is not None:
            device_data['sold_price'] = sold_price
        if d.get('finance_upto') is not None:
            finance_upto = str(d.get('finance_upto') or '').strip()
            if finance_upto:
                device_data['finance_upto'] = finance_upto
        if d.get('finance_company') is not None:
            finance_company = str(d.get('finance_company') or '').strip()
            if finance_company:
                device_data['finance_company'] = finance_company
        if d.get('finance_ref') is not None:
            finance_ref = str(d.get('finance_ref') or '').strip()
            if finance_ref:
                device_data['finance_ref'] = finance_ref
        if d.get('pre_prep') is not None:
            pre_prep = str(d.get('pre_prep') or '').strip()
            if pre_prep:
                device_data['pre_prep'] = pre_prep
        if d.get('retire_date'):
            try:
                from datetime import datetime

                device_data['retire_date'] = datetime.strptime(str(d.get('retire_date')), '%Y-%m-%d').date()
            except Exception:
                pass
        # attempt to resolve depot -> zone id
        depot = d.get('depot')
        if depot:
            zone = db.scalar(select(Zone).where(Zone.code == depot))
            if zone is None:
                zone = db.scalar(select(Zone).where(Zone.name == depot))
            if zone:
                device_data['location_zone_id'] = zone.id

        # ensure asset_tag
        if not device_data.get('asset_tag'):
            product_obj = db.get(Product, product_id)
            device_data['asset_tag'] = _generate_asset_tag(db, product=product_obj)

        device = Device(**device_data)
        db.add(device)
        try:
            db.commit()
            db.refresh(device)
            emit_realtime_event('inventory.updated', {'entity': 'device', 'action': 'create', 'id': device.id})
            created_devices.append(_to_device_read(db, device))
        except Exception:
            db.rollback()
            skipped_devices += 1
            continue

    return {
        'created_products': len(created_products),
        'created_devices': len(created_devices),
        'updated_devices': len(updated_devices),
        'skipped_devices': skipped_devices,
        'products': created_products[:20],
        'devices': created_devices[:20],
        'updated_devices_rows': updated_devices[:20],
    }



@router.post("/locations/bulk-delete", response_model=BulkOperationResult)
def bulk_delete_locations(payload: BulkDeleteRequest, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> BulkOperationResult:
    ids = sorted(set(payload.ids))
    rows = list(db.scalars(select(Zone).where(Zone.id.in_(ids))).all())
    rows_by_id = {row.id: row for row in rows}
    row_ids = [row.id for row in rows]

    linked_device_zone_ids = (
        set(
            db.scalars(
                select(Device.location_zone_id)
                .where(Device.location_zone_id.in_(row_ids))
                .group_by(Device.location_zone_id)
            ).all()
        )
        if row_ids
        else set()
    )
    child_parent_ids = (
        set(
            db.scalars(
                select(Zone.parent_id)
                .where(Zone.parent_id.in_(row_ids))
                .where(Zone.id.not_in(row_ids))
                .group_by(Zone.parent_id)
            ).all()
        )
        if row_ids
        else set()
    )

    def _depth(zone: Zone) -> int:
        depth = 0
        parent_id = zone.parent_id
        seen: set[int] = set()
        while parent_id is not None and parent_id in rows_by_id and parent_id not in seen:
            seen.add(parent_id)
            depth += 1
            parent_id = rows_by_id[parent_id].parent_id
        return depth

    rows.sort(key=_depth, reverse=True)

    deleted = 0
    skipped = max(len(ids) - len(rows), 0)
    for row in rows:
        if row.id in linked_device_zone_ids:
            skipped += 1
            continue
        if row.id in child_parent_ids:
            skipped += 1
            continue
        db.delete(row)
        deleted += 1

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to bulk delete locations due to linked records") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to bulk delete locations") from exc
    if deleted:
        emit_realtime_event("inventory.updated", {"entity": "zone", "action": "bulk_delete", "count": deleted})
    return BulkOperationResult(deleted=deleted, skipped=skipped)


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "inventory", "status": "scaffolded"}


@router.get("/categories", response_model=list[InventoryCategoryRead])
def list_categories(db: Session = Depends(get_db)) -> list[InventoryCategory]:
    return list(
        db.scalars(
            select(InventoryCategory).order_by(
                InventoryCategory.parent_id,
                InventoryCategory.sort_order,
                InventoryCategory.name,
            )
        ).all()
    )


@router.get("/categories/tree", response_model=list[InventoryCategoryTreeRead])
def list_categories_tree(db: Session = Depends(get_db)) -> list[InventoryCategoryTreeRead]:
    categories = list(
        db.scalars(
            select(InventoryCategory).order_by(
                InventoryCategory.parent_id,
                InventoryCategory.sort_order,
                InventoryCategory.name,
            )
        ).all()
    )
    return _build_category_tree(categories)


@router.post("/categories", response_model=InventoryCategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: InventoryCategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> InventoryCategory:
    if payload.parent_id is not None:
        parent = db.get(InventoryCategory, payload.parent_id)
        if parent is None:
            raise HTTPException(status_code=404, detail="Parent category not found")

    category = InventoryCategory(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/categories/{category_id}", response_model=InventoryCategoryRead)
def update_category(
    category_id: int,
    payload: InventoryCategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> InventoryCategory:
    category = db.get(InventoryCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    updates = payload.model_dump(exclude_unset=True)

    if "parent_id" in updates:
        parent_id = updates["parent_id"]
        _validate_parent_assignment(db, category, parent_id)

    for key, value in updates.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category


@router.post("/categories/{category_id}/move", response_model=InventoryCategoryRead)
def move_category(
    category_id: int,
    payload: InventoryCategoryMove,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> InventoryCategory:
    category = db.get(InventoryCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    target_parent_id = payload.parent_id
    _validate_parent_assignment(db, category, target_parent_id)

    before_category = None
    if payload.before_id is not None:
        before_category = db.get(InventoryCategory, payload.before_id)
        if before_category is None:
            raise HTTPException(status_code=404, detail="before_id category not found")
        if before_category.parent_id != target_parent_id:
            raise HTTPException(status_code=400, detail="before_id must have the same parent as move target")

    old_parent_id = category.parent_id
    category.parent_id = target_parent_id

    sibling_query = (
        select(InventoryCategory)
        .where(InventoryCategory.parent_id == target_parent_id)
        .where(InventoryCategory.id != category.id)
        .order_by(InventoryCategory.sort_order, InventoryCategory.id)
    )
    siblings = list(db.scalars(sibling_query).all())

    insert_index = len(siblings)
    if before_category is not None:
        for i, sibling in enumerate(siblings):
            if sibling.id == before_category.id:
                insert_index = i
                break
    siblings.insert(insert_index, category)

    for idx, sibling in enumerate(siblings):
        sibling.sort_order = idx

    _normalize_sibling_sort_orders(db, old_parent_id)
    if old_parent_id != target_parent_id:
        _normalize_sibling_sort_orders(db, target_parent_id)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    category = db.get(InventoryCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    has_children = db.scalar(
        select(func.count()).select_from(InventoryCategory).where(InventoryCategory.parent_id == category_id)
    )
    if has_children and has_children > 0:
        raise HTTPException(status_code=409, detail="Category has children and cannot be deleted")

    products_using = db.scalar(
        select(func.count()).select_from(Product).where(Product.category_id == category_id)
    )
    if products_using and products_using > 0:
        raise HTTPException(status_code=409, detail="Category is used by products")

    db.delete(category)
    db.commit()
    return None


@router.post("/categories/prefill", response_model=list[InventoryCategoryRead])
def prefill_categories(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[InventoryCategory]:
    defaults = _get_category_prefill_paths(db)

    for path in defaults:
        parent_id: int | None = None
        for depth, name in enumerate(path):
            existing = db.scalar(
                select(InventoryCategory)
                .where(InventoryCategory.parent_id == parent_id)
                .where(func.lower(InventoryCategory.name) == name.lower())
            )
            if existing is None:
                existing = InventoryCategory(name=name, parent_id=parent_id, sort_order=depth)
                db.add(existing)
                db.flush()
            parent_id = existing.id

    db.commit()
    return list_categories(db)


def _get_category_prefill_paths(db: Session) -> list[list[str]]:
    setting = db.scalar(select(AppSetting).where(AppSetting.key == "inventory.category_prefill_paths"))
    if setting is None or not setting.value_json:
        return [path[:] for path in DEFAULT_CATEGORY_PREFILL_PATHS]

    try:
        raw = json.loads(setting.value_json)
    except Exception:
        return [path[:] for path in DEFAULT_CATEGORY_PREFILL_PATHS]

    if not isinstance(raw, list):
        return [path[:] for path in DEFAULT_CATEGORY_PREFILL_PATHS]

    paths: list[list[str]] = []
    for item in raw:
        if not isinstance(item, list):
            continue
        parts = [str(part or "").strip() for part in item]
        parts = [part for part in parts if part]
        if parts:
            paths.append(parts)
    return paths or [path[:] for path in DEFAULT_CATEGORY_PREFILL_PATHS]


def _find_category_by_path(db: Session, path: list[str] | None) -> InventoryCategory | None:
    if not path:
        return None

    parent_id: int | None = None
    current: InventoryCategory | None = None
    for name in path:
        part = str(name or '').strip()
        if not part:
            return None
        current = db.scalar(
            select(InventoryCategory)
            .where(InventoryCategory.parent_id == parent_id)
            .where(func.lower(InventoryCategory.name) == part.lower())
        )
        if current is None:
            return None
        parent_id = current.id
    return current


def _resolve_hirehop_category(db: Session, product_data: dict[str, Any]) -> InventoryCategory | None:
    # Cases are the one safe special-case mapping worth applying automatically.
    is_box = str(product_data.get('is_box') or '').strip().lower() in {'1', 'true', 'yes'}
    if is_box:
        return _find_category_by_path(db, ['Accessories', 'Cases']) or _find_category_by_path(db, ['Cases'])

    category_path = product_data.get('category_path')
    if isinstance(category_path, list):
        return _find_category_by_path(db, [str(part) for part in category_path])

    return None


@router.get("/products", response_model=list[ProductRead])
def list_products(db: Session = Depends(get_db)) -> list[ProductRead]:
    products = list(db.scalars(select(Product).order_by(Product.id)).all())
    return [_to_product_read(db, product) for product in products]


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductRead:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_product_read(db, product)


@router.get("/products/generate-sku")
def generate_product_sku(db: Session = Depends(get_db), prefix: str = "PRD-") -> dict[str, str]:
    cleaned_prefix = (prefix or "PRD-").strip()
    if not cleaned_prefix:
        cleaned_prefix = "PRD-"
    if len(cleaned_prefix) > 20:
        raise HTTPException(status_code=400, detail="Prefix is too long")
    return {"sku": _generate_next_product_sku(db, cleaned_prefix)}


@router.post("/products", response_model=ProductRead)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> ProductRead:
    data = payload.model_dump()
    _validate_product_type(data.get("product_type"))

    if data.get("category_id") is not None:
        category = db.get(InventoryCategory, data["category_id"])
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        data["category"] = category.name
    product = Product(**data)
    db.add(product)
    db.commit()
    db.refresh(product)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="product",
        entity_id=product.id,
        action="create",
        message_format="product_created",
        message_params={"sku": product.sku, "name": product.name},
        details={"sku": product.sku, "name": product.name},
    )
    emit_realtime_event("inventory.updated", {"entity": "product", "action": "create", "id": product.id})
    db.commit()
    return _to_product_read(db, product)


@router.put("/products/{product_id}", response_model=ProductRead)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> ProductRead:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    updates = payload.model_dump(exclude_unset=True)
    if "product_type" in updates:
        _validate_product_type(updates.get("product_type"))

    if "category_id" in updates and updates["category_id"] is not None:
        category = db.get(InventoryCategory, updates["category_id"])
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        updates["category"] = category.name

    for key, value in updates.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="product",
        entity_id=product.id,
        action="update",
        message_format="product_updated",
        message_params={"sku": product.sku, "name": product.name},
        details={"sku": product.sku, "name": product.name},
    )
    emit_realtime_event("inventory.updated", {"entity": "product", "action": "update", "id": product.id})
    db.commit()
    return _to_product_read(db, product)


@router.post("/products/bulk-update", response_model=BulkOperationResult)
def bulk_update_products(
    payload: ProductBulkUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> BulkOperationResult:
    updates = payload.patch.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No patch fields provided")

    if "product_type" in updates:
        _validate_product_type(updates.get("product_type"))

    if "category_id" in updates and updates["category_id"] is not None:
        category = db.get(InventoryCategory, updates["category_id"])
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        updates["category"] = category.name

    ids = sorted(set(payload.ids))
    rows = list(db.scalars(select(Product).where(Product.id.in_(ids))).all())
    for row in rows:
        for key, value in updates.items():
            setattr(row, key, value)

    db.commit()
    if rows:
        emit_realtime_event("inventory.updated", {"entity": "product", "action": "bulk_update", "count": len(rows)})
    return BulkOperationResult(updated=len(rows), skipped=max(len(ids) - len(rows), 0))


@router.post("/products/bulk-delete", response_model=BulkOperationResult)
def bulk_delete_products(
    payload: BulkDeleteRequest,
    delete_linked_devices: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> BulkOperationResult:
    ids = sorted(set(payload.ids))
    rows = list(db.scalars(select(Product).where(Product.id.in_(ids))).all())

    deleted = 0
    skipped = max(len(ids) - len(rows), 0)
    for row in rows:
        linked_devices = db.scalar(select(func.count()).select_from(Device).where(Device.product_id == row.id)) or 0
        if linked_devices > 0:
            if not delete_linked_devices:
                skipped += 1
                continue
            linked_rows = list(db.scalars(select(Device).where(Device.product_id == row.id)).all())
            linked_ids = [linked.id for linked in linked_rows]
            # Clear case_device_id references pointing at these devices to avoid FK constraint violations
            if linked_ids:
                db.execute(
                    Device.__table__.update()
                    .where(Device.case_device_id.in_(linked_ids))
                    .values(case_device_id=None)
                )
            for linked in linked_rows:
                db.delete(linked)
        linked_requirements = list(
            db.scalars(select(JobRequirement).where(JobRequirement.product_id == row.id)).all()
        )
        for requirement in linked_requirements:
            db.delete(requirement)
        db.delete(row)
        deleted += 1

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to bulk delete products due to linked records") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to bulk delete products") from exc
    if deleted:
        emit_realtime_event("inventory.updated", {"entity": "product", "action": "bulk_delete", "count": deleted})
    return BulkOperationResult(deleted=deleted, skipped=skipped)


@router.get("/products/{product_id}/accessories", response_model=list[ProductAccessoryRead])
def list_product_accessories(product_id: int, db: Session = Depends(get_db)) -> list[ProductAccessoryRead]:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    links = list(
        db.scalars(
            select(ProductAccessory)
            .where(ProductAccessory.parent_product_id == product_id)
            .order_by(ProductAccessory.required.desc(), ProductAccessory.id)
        ).all()
    )
    return [_to_product_accessory_read(db, link) for link in links]


@router.put("/products/{product_id}/accessories", response_model=list[ProductAccessoryRead])
def upsert_product_accessories(
    product_id: int,
    payload: ProductAccessoryUpsertRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> list[ProductAccessoryRead]:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    incoming_by_accessory: dict[int, tuple[int, bool]] = {}
    for item in payload.items:
        accessory_id = int(item.accessory_product_id)
        if accessory_id == product_id:
            raise HTTPException(status_code=400, detail="Product cannot reference itself as accessory")
        accessory = db.get(Product, accessory_id)
        if accessory is None:
            raise HTTPException(status_code=404, detail=f"Accessory product not found: {accessory_id}")
        incoming_by_accessory[accessory_id] = (max(int(item.quantity or 1), 1), bool(item.required))

    existing = list(
        db.scalars(select(ProductAccessory).where(ProductAccessory.parent_product_id == product_id)).all()
    )
    existing_by_accessory = {row.accessory_product_id: row for row in existing}

    for accessory_id, (quantity, required) in incoming_by_accessory.items():
        current = existing_by_accessory.get(accessory_id)
        if current is None:
            db.add(
                ProductAccessory(
                    parent_product_id=product_id,
                    accessory_product_id=accessory_id,
                    quantity=quantity,
                    required=required,
                )
            )
            continue
        current.quantity = quantity
        current.required = required

    for row in existing:
        if row.accessory_product_id not in incoming_by_accessory:
            db.delete(row)

    db.commit()
    links = list(
        db.scalars(
            select(ProductAccessory)
            .where(ProductAccessory.parent_product_id == product_id)
            .order_by(ProductAccessory.required.desc(), ProductAccessory.id)
        ).all()
    )
    emit_realtime_event("inventory.updated", {"entity": "product_accessory", "action": "upsert", "product_id": product_id})
    return [_to_product_accessory_read(db, link) for link in links]


@router.get("/products/{product_id}/components", response_model=list[ProductComponentRead])
def list_product_components(product_id: int, db: Session = Depends(get_db)) -> list[ProductComponentRead]:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    links = list(
        db.scalars(
            select(ProductComponent)
            .where(ProductComponent.parent_product_id == product_id)
            .order_by(ProductComponent.id)
        ).all()
    )
    return [_to_product_component_read(db, link) for link in links]


@router.put("/products/{product_id}/components", response_model=list[ProductComponentRead])
def upsert_product_components(
    product_id: int,
    payload: ProductComponentUpsertRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> list[ProductComponentRead]:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    incoming_by_component: dict[int, int] = {}
    for item in payload.items:
        component_id = int(item.component_product_id)
        if component_id == product_id:
            raise HTTPException(status_code=400, detail="Product cannot reference itself as component")
        component = db.get(Product, component_id)
        if component is None:
            raise HTTPException(status_code=404, detail=f"Component product not found: {component_id}")
        incoming_by_component[component_id] = max(int(item.quantity or 1), 1)

    existing = list(
        db.scalars(select(ProductComponent).where(ProductComponent.parent_product_id == product_id)).all()
    )
    existing_by_component = {row.component_product_id: row for row in existing}

    for component_id, quantity in incoming_by_component.items():
        current = existing_by_component.get(component_id)
        if current is None:
            db.add(
                ProductComponent(
                    parent_product_id=product_id,
                    component_product_id=component_id,
                    quantity=quantity,
                )
            )
            continue
        current.quantity = quantity

    for row in existing:
        if row.component_product_id not in incoming_by_component:
            db.delete(row)

    db.commit()
    links = list(
        db.scalars(
            select(ProductComponent)
            .where(ProductComponent.parent_product_id == product_id)
            .order_by(ProductComponent.id)
        ).all()
    )
    emit_realtime_event("inventory.updated", {"entity": "product_component", "action": "upsert", "product_id": product_id})
    return [_to_product_component_read(db, link) for link in links]


@router.post("/products/{product_id}/devices", response_model=list[DeviceRead])
def create_devices_for_product(
    product_id: int,
    payload: ProductDevicesBulkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> list[Device]:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload.quantity > 1 and not payload.auto_generate and not payload.asset_tag:
        raise HTTPException(status_code=400, detail="asset_tag is required when auto_generate is false")

    if payload.location_zone_id is not None:
        zone = db.get(Zone, payload.location_zone_id)
        if zone is None:
            raise HTTPException(status_code=404, detail="Location not found")

    created: list[Device] = []
    for _ in range(payload.quantity):
        if payload.auto_generate:
            asset_tag = _generate_asset_tag(db, product=product, preferred_prefix=payload.asset_tag_prefix)
        else:
            asset_tag = payload.asset_tag

        if not asset_tag:
            raise HTTPException(status_code=400, detail="Asset tag could not be determined")

        if db.scalar(select(Device).where(Device.asset_tag == asset_tag)) is not None:
            raise HTTPException(status_code=409, detail=f"Device asset_tag already exists: {asset_tag}")

        device = Device(
            product_id=product_id,
            asset_tag=asset_tag,
            location_zone_id=payload.location_zone_id,
            status=payload.status,
            condition=payload.condition,
            notes=payload.notes,
        )
        db.add(device)
        db.flush()
        created.append(device)

    db.commit()
    for device in created:
        db.refresh(device)
    emit_realtime_event(
        "inventory.updated",
        {"entity": "device", "action": "bulk_create", "product_id": product_id, "count": len(created)},
    )
    return created


@router.get("/devices", response_model=list[DeviceRead])
def list_devices(db: Session = Depends(get_db)) -> list[DeviceRead]:
    rows = list(db.scalars(select(Device).order_by(Device.id)).all())
    return [_to_device_read(db, row) for row in rows]


@router.get("/devices/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)) -> DeviceRead:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return _to_device_read(db, device)


@router.get("/devices/generate-asset-tag")
def generate_device_asset_tag(
    db: Session = Depends(get_db),
    product_id: int | None = None,
    prefix: str | None = None,
) -> dict[str, str]:
    product: Product | None = None
    if product_id is not None:
        product = db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

    cleaned_prefix = (prefix or "").strip() or None
    if cleaned_prefix is not None and len(cleaned_prefix) > 32:
        raise HTTPException(status_code=400, detail="Prefix is too long")

    return {"asset_tag": _generate_asset_tag(db, product=product, preferred_prefix=cleaned_prefix)}


@router.get("/checked-out-devices", response_model=list[InventoryCheckedOutDeviceRead])
def list_checked_out_devices(
    job_code: str | None = None,
    db: Session = Depends(get_db),
) -> list[InventoryCheckedOutDeviceRead]:
    base_rows = list(
        db.execute(
            select(Device, Product, Zone)
            .join(Product, Product.id == Device.product_id)
            .outerjoin(Zone, Zone.id == Device.location_zone_id)
            .where(Device.status == "in_use")
            .order_by(Device.product_id, Device.id)
        ).all()
    )

    candidate = (job_code or "").strip()
    if not candidate:
        return [
            InventoryCheckedOutDeviceRead(
                device_id=device.id,
                asset_tag=device.asset_tag,
                serial_number=device.serial_number,
                barcode=device.barcode,
                qr_code=device.qr_code,
                rfid=device.rfid,
                product_id=device.product_id,
                product_name=product.name if product else None,
                location_zone_id=device.location_zone_id,
                location_name=zone.name if zone else None,
                condition=device.condition,
                status=device.status,
            )
            for device, product, zone in base_rows
        ]

    job = db.scalar(select(Job).where(Job.job_code == candidate))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    picked_by_product: dict[int, int] = {}
    requirement_rows = list(
        db.scalars(
            select(JobRequirement)
            .where(JobRequirement.job_id == job.id)
            .where(JobRequirement.quantity_picked > 0)
            .order_by(JobRequirement.product_id, JobRequirement.id)
        ).all()
    )
    for req in requirement_rows:
        picked_by_product[req.product_id] = int(req.quantity_picked or 0)

    remaining_by_product = dict(picked_by_product)
    filtered_rows: list[InventoryCheckedOutDeviceRead] = []
    for device, product, zone in base_rows:
        remaining = int(remaining_by_product.get(device.product_id, 0))
        if remaining <= 0:
            continue
        remaining_by_product[device.product_id] = remaining - 1
        filtered_rows.append(
            InventoryCheckedOutDeviceRead(
                device_id=device.id,
                asset_tag=device.asset_tag,
                serial_number=device.serial_number,
                barcode=device.barcode,
                qr_code=device.qr_code,
                rfid=device.rfid,
                product_id=device.product_id,
                product_name=product.name if product else None,
                location_zone_id=device.location_zone_id,
                location_name=zone.name if zone else None,
                condition=device.condition,
                status=device.status,
                job_id=job.id,
                job_code=job.job_code,
            )
        )

    return filtered_rows


@router.post("/devices", response_model=DeviceRead)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> DeviceRead:
    data = payload.model_dump()
    _validate_device_product_and_location(db, data)

    if not data.get("asset_tag"):
        product = db.get(Product, data["product_id"])
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        data["asset_tag"] = _generate_asset_tag(db, product=product)

    device = Device(**data)
    db.add(device)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(device)
    emit_realtime_event("inventory.updated", {"entity": "device", "action": "create", "id": device.id})
    return _to_device_read(db, device)


@router.put("/devices/{device_id}", response_model=DeviceRead)
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> DeviceRead:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    updates = payload.model_dump(exclude_unset=True)
    _validate_device_product_and_location(db, updates)

    for key, value in updates.items():
        setattr(device, key, value)
    db.commit()
    db.refresh(device)
    emit_realtime_event("inventory.updated", {"entity": "device", "action": "update", "id": device.id})
    return _to_device_read(db, device)


@router.put("/devices/{device_id}/component-devices", response_model=list[DeviceRead])
def update_device_component_devices(
    device_id: int,
    payload: list[int],
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> list[DeviceRead]:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    incoming = set(payload)
    if device_id in incoming:
        raise HTTPException(status_code=400, detail="Device cannot be a component of itself")

    existing = list(
        db.scalars(select(Device).where(Device.parent_component_device_id == device_id)).all()
    )
    existing_by_id = {row.id: row for row in existing}

    for comp_id in incoming:
        if comp_id in existing_by_id:
            del existing_by_id[comp_id]
            continue
        comp_device = db.get(Device, comp_id)
        if comp_device is None:
            raise HTTPException(status_code=404, detail=f"Component device not found: {comp_id}")
        comp_device.parent_component_device_id = device_id

    for stale in existing_by_id.values():
        stale.parent_component_device_id = None

    db.commit()
    result = list(
        db.scalars(
            select(Device).where(Device.parent_component_device_id == device_id).order_by(Device.id)
        ).all()
    )
    emit_realtime_event("inventory.updated", {"entity": "device_component", "action": "update", "device_id": device_id})
    return [_to_device_read(db, d) for d in result]


@router.get("/devices/{device_id}/component-devices", response_model=list[DeviceRead])
def list_device_component_devices(
    device_id: int,
    db: Session = Depends(get_db),
) -> list[DeviceRead]:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    result = list(
        db.scalars(
            select(Device).where(Device.parent_component_device_id == device_id).order_by(Device.id)
        ).all()
    )
    return [_to_device_read(db, d) for d in result]


@router.post("/devices/bulk-update", response_model=BulkOperationResult)
def bulk_update_devices(
    payload: DeviceBulkUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> BulkOperationResult:
    updates = payload.patch.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No patch fields provided")

    _validate_device_product_and_location(db, updates)

    ids = sorted(set(payload.ids))
    rows = list(db.scalars(select(Device).where(Device.id.in_(ids))).all())
    for row in rows:
        for key, value in updates.items():
            setattr(row, key, value)

    db.commit()
    if rows:
        emit_realtime_event("inventory.updated", {"entity": "device", "action": "bulk_update", "count": len(rows)})
    return BulkOperationResult(updated=len(rows), skipped=max(len(ids) - len(rows), 0))


@router.post("/devices/bulk-delete", response_model=BulkOperationResult)
def bulk_delete_devices(
    payload: BulkDeleteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> BulkOperationResult:
    ids = sorted(set(payload.ids))
    rows = list(db.scalars(select(Device).where(Device.id.in_(ids))).all())

    deleted = 0
    skipped = max(len(ids) - len(rows), 0)
    for row in rows:
        db.delete(row)
        deleted += 1

    db.commit()
    if deleted:
        emit_realtime_event("inventory.updated", {"entity": "device", "action": "bulk_delete", "count": deleted})
    return BulkOperationResult(deleted=deleted, skipped=skipped)


@router.get("/maintenance", response_model=list[DeviceMaintenanceRead])
def list_maintenance(status: str | None = None, db: Session = Depends(get_db)) -> list[DeviceMaintenanceRead]:
    query = select(DeviceMaintenance).order_by(DeviceMaintenance.scheduled_date, DeviceMaintenance.id)
    if status:
        _validate_maintenance_status(status)
        query = query.where(DeviceMaintenance.status == status)
    records = list(db.scalars(query).all())
    return [_to_maintenance_read(db, record) for record in records]


@router.get("/maintenance/device/{device_id}", response_model=list[DeviceMaintenanceRead])
def list_maintenance_for_device(device_id: int, db: Session = Depends(get_db)) -> list[DeviceMaintenanceRead]:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    records = list(
        db.scalars(
            select(DeviceMaintenance)
            .where(DeviceMaintenance.device_id == device_id)
            .order_by(DeviceMaintenance.scheduled_date, DeviceMaintenance.id)
        ).all()
    )
    return [_to_maintenance_read(db, record) for record in records]


@router.post("/maintenance", response_model=DeviceMaintenanceRead)
def create_maintenance(payload: DeviceMaintenanceCreate, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> DeviceMaintenanceRead:
    data = payload.model_dump()
    _validate_maintenance_payload(db, data)

    if data.get("status") == "completed" and data.get("completed_date") is None:
        data["completed_date"] = date.today()

    record = DeviceMaintenance(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    emit_realtime_event("inventory.updated", {"entity": "maintenance", "action": "create", "id": record.id})
    return _to_maintenance_read(db, record)


@router.put("/maintenance/{maintenance_id}", response_model=DeviceMaintenanceRead)
def update_maintenance(
    maintenance_id: int,
    payload: DeviceMaintenanceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> DeviceMaintenanceRead:
    record = db.get(DeviceMaintenance, maintenance_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Maintenance record not found")

    updates = payload.model_dump(exclude_unset=True)
    _validate_maintenance_payload(db, updates)

    if updates.get("status") == "completed" and "completed_date" not in updates:
        updates["completed_date"] = date.today()

    for key, value in updates.items():
        setattr(record, key, value)

    db.commit()
    db.refresh(record)
    emit_realtime_event("inventory.updated", {"entity": "maintenance", "action": "update", "id": record.id})
    return _to_maintenance_read(db, record)


@router.post("/maintenance/{maintenance_id}/complete", response_model=DeviceMaintenanceRead)
def complete_maintenance(
    maintenance_id: int,
    payload: DeviceMaintenanceComplete,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> DeviceMaintenanceRead:
    record = db.get(DeviceMaintenance, maintenance_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Maintenance record not found")

    record.status = "completed"
    record.completed_date = payload.completed_date or date.today()
    if payload.notes is not None:
        record.notes = payload.notes

    db.commit()
    db.refresh(record)
    emit_realtime_event("inventory.updated", {"entity": "maintenance", "action": "complete", "id": record.id})
    return _to_maintenance_read(db, record)


@router.post("/maintenance/bulk-update", response_model=BulkOperationResult)
def bulk_update_maintenance(
    payload: DeviceMaintenanceBulkUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> BulkOperationResult:
    updates = payload.patch.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No patch fields provided")

    _validate_maintenance_payload(db, updates)
    if updates.get("status") == "completed" and "completed_date" not in updates:
        updates["completed_date"] = date.today()

    ids = sorted(set(payload.ids))
    rows = list(db.scalars(select(DeviceMaintenance).where(DeviceMaintenance.id.in_(ids))).all())
    for row in rows:
        for key, value in updates.items():
            setattr(row, key, value)

    db.commit()
    if rows:
        emit_realtime_event("inventory.updated", {"entity": "maintenance", "action": "bulk_update", "count": len(rows)})
    return BulkOperationResult(updated=len(rows), skipped=max(len(ids) - len(rows), 0))


@router.post("/maintenance/bulk-delete", response_model=BulkOperationResult)
def bulk_delete_maintenance(
    payload: BulkDeleteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> BulkOperationResult:
    ids = sorted(set(payload.ids))
    rows = list(db.scalars(select(DeviceMaintenance).where(DeviceMaintenance.id.in_(ids))).all())

    deleted = 0
    skipped = max(len(ids) - len(rows), 0)
    for row in rows:
        db.delete(row)
        deleted += 1

    db.commit()
    if deleted:
        emit_realtime_event("inventory.updated", {"entity": "maintenance", "action": "bulk_delete", "count": deleted})
    return BulkOperationResult(deleted=deleted, skipped=skipped)


@router.post("/maintenance/bulk-schedule", response_model=list[DeviceMaintenanceRead])
def bulk_schedule_maintenance(
    payload: MaintenanceBulkScheduleRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> list[DeviceMaintenanceRead]:
    _validate_maintenance_type(payload.maintenance_type)
    _validate_maintenance_interval_mode(payload.interval_mode)

    device_ids = set(payload.device_ids)
    if payload.product_ids:
        products = list(db.scalars(select(Product).where(Product.id.in_(payload.product_ids))).all())
        found_product_ids = {product.id for product in products}
        missing_product_ids = sorted(set(payload.product_ids) - found_product_ids)
        if missing_product_ids:
            raise HTTPException(status_code=404, detail=f"Product not found: {missing_product_ids[0]}")

        product_devices = list(
            db.scalars(select(Device).where(Device.product_id.in_(payload.product_ids)).order_by(Device.id)).all()
        )
        for device in product_devices:
            device_ids.add(device.id)

    if not device_ids:
        raise HTTPException(status_code=400, detail="No devices found for selected schedule targets")

    schedule = DeviceMaintenanceSchedule(
        maintenance_type=payload.maintenance_type,
        interval_mode=payload.interval_mode,
        interval_value=payload.interval_value,
        scheduled_date=payload.scheduled_date,
        notes=payload.notes,
    )
    db.add(schedule)
    db.flush()

    created: list[DeviceMaintenance] = []
    for device_id in sorted(device_ids):
        device = db.get(Device, device_id)
        if device is None:
            raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

        record = DeviceMaintenance(
            device_id=device_id,
            schedule_id=schedule.id,
            status="scheduled",
            notes=payload.notes,
        )
        _apply_schedule_values_to_task(db, record, schedule)
        db.add(record)
        db.flush()
        created.append(record)

    db.commit()
    for record in created:
        db.refresh(record)
    emit_realtime_event(
        "inventory.updated",
        {"entity": "maintenance", "action": "bulk_schedule", "count": len(created)},
    )
    return [_to_maintenance_read(db, record) for record in created]


@router.get("/maintenance-schedules", response_model=list[MaintenanceScheduleRead])
def list_maintenance_schedules(db: Session = Depends(get_db)) -> list[MaintenanceScheduleRead]:
    rows = list(
        db.scalars(
            select(DeviceMaintenanceSchedule).order_by(DeviceMaintenanceSchedule.updated_at.desc(), DeviceMaintenanceSchedule.id.desc())
        ).all()
    )
    return [_to_schedule_read(row) for row in rows]


@router.post("/maintenance-schedules/bulk-update", response_model=BulkOperationResult)
def bulk_update_maintenance_schedules(
    payload: MaintenanceScheduleBulkUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> BulkOperationResult:
    updates = payload.patch.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No patch fields provided")

    if updates.get("maintenance_type") is not None:
        _validate_maintenance_type(updates["maintenance_type"])
    if updates.get("interval_mode") is not None:
        _validate_maintenance_interval_mode(updates["interval_mode"])

    ids = sorted(set(payload.ids))
    rows = list(db.scalars(select(DeviceMaintenanceSchedule).where(DeviceMaintenanceSchedule.id.in_(ids))).all())
    for row in rows:
        _apply_schedule_updates(db, row, updates)

    db.commit()
    if rows:
        emit_realtime_event("inventory.updated", {"entity": "maintenance", "action": "bulk_schedule_update", "count": len(rows)})
    return BulkOperationResult(updated=len(rows), skipped=max(len(ids) - len(rows), 0))


@router.post("/maintenance-schedules/bulk-delete", response_model=BulkOperationResult)
def bulk_delete_maintenance_schedules(
    payload: BulkDeleteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> BulkOperationResult:
    ids = sorted(set(payload.ids))
    rows = list(db.scalars(select(DeviceMaintenanceSchedule).where(DeviceMaintenanceSchedule.id.in_(ids))).all())

    deleted = 0
    skipped = max(len(ids) - len(rows), 0)
    for row in rows:
        db.delete(row)
        deleted += 1

    db.commit()
    if deleted:
        emit_realtime_event("inventory.updated", {"entity": "maintenance", "action": "bulk_schedule_delete", "count": deleted})
    return BulkOperationResult(deleted=deleted, skipped=skipped)


@router.get("/maintenance-schedules/{schedule_id}", response_model=MaintenanceScheduleRead)
def get_maintenance_schedule(schedule_id: int, db: Session = Depends(get_db)) -> MaintenanceScheduleRead:
    schedule = db.get(DeviceMaintenanceSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")
    return _to_schedule_read(schedule)


@router.put("/maintenance-schedules/{schedule_id}", response_model=MaintenanceScheduleRead)
def update_maintenance_schedule(
    schedule_id: int,
    payload: MaintenanceScheduleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> MaintenanceScheduleRead:
    schedule = db.get(DeviceMaintenanceSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")

    updates = payload.model_dump(exclude_unset=True)
    _apply_schedule_updates(db, schedule, updates)

    db.commit()
    db.refresh(schedule)
    emit_realtime_event(
        "inventory.updated",
        {
            "entity": "maintenance",
            "action": "schedule_update",
            "schedule_id": schedule.id,
            "updated_tasks": _pending_schedule_task_count(db, schedule.id),
        },
    )
    return _to_schedule_read(schedule)


# ---------------------------------------------------------------------------
# Maintenance comments
# ---------------------------------------------------------------------------

@router.get("/maintenance/{maintenance_id}/comments", response_model=list[MaintenanceCommentRead])
def list_maintenance_comments(maintenance_id: int, db: Session = Depends(get_db)) -> list[MaintenanceCommentRead]:
    record = db.get(DeviceMaintenance, maintenance_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    rows = db.scalars(
        select(MaintenanceComment)
        .where(MaintenanceComment.maintenance_id == maintenance_id)
        .order_by(MaintenanceComment.created_at.asc())
    ).all()
    return [MaintenanceCommentRead.model_validate(r) for r in rows]


@router.post("/maintenance/{maintenance_id}/comments", response_model=MaintenanceCommentRead)
def create_maintenance_comment(
    maintenance_id: int,
    payload: MaintenanceCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> MaintenanceCommentRead:
    record = db.get(DeviceMaintenance, maintenance_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    if not (payload.comment or "").strip():
        raise HTTPException(status_code=400, detail="comment is required")
    comment = MaintenanceComment(
        maintenance_id=maintenance_id,
        comment=payload.comment.strip(),
        created_by_user_id=current_user.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    emit_realtime_event("inventory.updated", {"entity": "maintenance_comment", "action": "create", "id": comment.id})
    return MaintenanceCommentRead.model_validate(comment)


@router.put("/maintenance-comments/{comment_id}", response_model=MaintenanceCommentRead)
def update_maintenance_comment(
    comment_id: int,
    payload: MaintenanceCommentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> MaintenanceCommentRead:
    row = db.get(MaintenanceComment, comment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Maintenance comment not found")
    new_text = payload.comment
    if new_text is not None:
        if not new_text.strip():
            raise HTTPException(status_code=400, detail="comment is required")
        row.comment = new_text.strip()
    db.commit()
    db.refresh(row)
    emit_realtime_event("inventory.updated", {"entity": "maintenance_comment", "action": "update", "id": row.id})
    return MaintenanceCommentRead.model_validate(row)


@router.delete("/maintenance-comments/{comment_id}")
def delete_maintenance_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> dict:
    row = db.get(MaintenanceComment, comment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Maintenance comment not found")
    db.delete(row)
    db.commit()
    emit_realtime_event("inventory.updated", {"entity": "maintenance_comment", "action": "delete", "id": comment_id})
    return {"ok": True}


@router.get("/defect-reports", response_model=list[DefectReportRead])
def list_defect_reports(
    device_id: int | None = None,
    maintenance_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[DefectReportRead]:
    query = select(DefectReport).order_by(DefectReport.updated_at.desc(), DefectReport.id.desc())
    if device_id is not None:
        query = query.where(DefectReport.device_id == device_id)
    if maintenance_id is not None:
        query = query.where(DefectReport.maintenance_id == maintenance_id)
    if status is not None:
        _validate_defect_status(status)
        query = query.where(DefectReport.status == status)
    rows = list(db.scalars(query).all())

    # Batch-load related entities to avoid N+1 queries
    device_ids = list({row.device_id for row in rows if row.device_id is not None})
    maintenance_ids = list({row.maintenance_id for row in rows if row.maintenance_id is not None})
    devices_by_id: dict[int, Device] = (
        {d.id: d for d in db.scalars(select(Device).where(Device.id.in_(device_ids))).all()}
        if device_ids
        else {}
    )
    product_ids = list({d.product_id for d in devices_by_id.values() if d.product_id is not None})
    products_by_id: dict[int, Product] = (
        {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()}
        if product_ids
        else {}
    )
    maintenance_by_id: dict[int, DeviceMaintenance] = (
        {m.id: m for m in db.scalars(select(DeviceMaintenance).where(DeviceMaintenance.id.in_(maintenance_ids))).all()}
        if maintenance_ids
        else {}
    )

    result = []
    for row in rows:
        device = devices_by_id.get(row.device_id)
        product = products_by_id.get(device.product_id) if device is not None and device.product_id is not None else None
        maintenance = maintenance_by_id.get(row.maintenance_id) if row.maintenance_id is not None else None
        result.append(_hydrate_defect_report_read(row, device, product, maintenance))
    return result


@router.post("/defect-reports", response_model=DefectReportRead)
def create_defect_report(
    payload: DefectReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> DefectReportRead:
    data = payload.model_dump()
    _normalize_defect_report_text_fields(data)
    _validate_defect_report_payload(db, data)
    report = DefectReport(
        **data,
        created_by_user_id=current_user.id,
    )
    db.add(report)
    _update_device_on_defect_change(db, data["device_id"])
    db.commit()
    db.refresh(report)
    emit_realtime_event("inventory.updated", {"entity": "defect_report", "action": "create", "id": report.id})
    return _to_defect_report_read(db, report)


@router.get("/defect-reports/{report_id}", response_model=DefectReportRead)
def get_defect_report(report_id: int, db: Session = Depends(get_db)) -> DefectReportRead:
    report = db.get(DefectReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Defect report not found")
    return _to_defect_report_read(db, report)


@router.put("/defect-reports/{report_id}", response_model=DefectReportRead)
def update_defect_report(
    report_id: int,
    payload: DefectReportUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> DefectReportRead:
    report = db.get(DefectReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Defect report not found")

    updates = payload.model_dump(exclude_unset=True)
    for required_field in ("device_id", "title", "status", "severity"):
        if required_field in updates and updates[required_field] is None:
            raise HTTPException(status_code=400, detail=f"{required_field} cannot be null")
    _normalize_defect_report_text_fields(updates)
    _validate_defect_report_payload(
        db,
        {
            "device_id": updates.get("device_id", report.device_id),
            "maintenance_id": updates.get("maintenance_id", report.maintenance_id),
            "status": updates.get("status"),
            "severity": updates.get("severity"),
            "title": updates.get("title"),
        },
    )
    for key, value in updates.items():
        setattr(report, key, value)
    _update_device_on_defect_change(db, report.device_id)
    db.commit()
    db.refresh(report)
    emit_realtime_event("inventory.updated", {"entity": "defect_report", "action": "update", "id": report.id})
    return _to_defect_report_read(db, report)


@router.delete("/defect-reports/{report_id}")
def delete_defect_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> dict[str, bool]:
    report = db.get(DefectReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Defect report not found")
    device_id = report.device_id
    db.delete(report)
    _update_device_on_defect_change(db, device_id)
    db.commit()
    emit_realtime_event("inventory.updated", {"entity": "defect_report", "action": "delete", "id": report_id})
    return {"ok": True}


@router.get("/defect-reports/{report_id}/comments", response_model=list[DefectCommentRead])
def list_defect_comments(report_id: int, db: Session = Depends(get_db)) -> list[DefectCommentRead]:
    _get_defect_report_or_404(db, report_id)
    rows = list(
        db.scalars(
            select(DefectComment)
            .where(DefectComment.defect_report_id == report_id)
            .order_by(DefectComment.created_at.asc(), DefectComment.id.asc())
        ).all()
    )
    return [DefectCommentRead.model_validate(row) for row in rows]


@router.post("/defect-reports/{report_id}/comments", response_model=DefectCommentRead)
def create_defect_comment(
    report_id: int,
    payload: DefectCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> DefectCommentRead:
    _get_defect_report_or_404(db, report_id)
    comment_text = payload.comment.strip()
    if not comment_text:
        raise HTTPException(status_code=400, detail="comment is required")
    comment = DefectComment(
        defect_report_id=report_id,
        comment=comment_text,
        created_by_user_id=current_user.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    emit_realtime_event("inventory.updated", {"entity": "defect_comment", "action": "create", "id": comment.id})
    return DefectCommentRead.model_validate(comment)


@router.put("/defect-comments/{comment_id}", response_model=DefectCommentRead)
def update_defect_comment(
    comment_id: int,
    payload: DefectCommentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> DefectCommentRead:
    row = db.get(DefectComment, comment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Defect comment not found")
    updates = payload.model_dump(exclude_unset=True)
    if "comment" in updates:
        if updates["comment"] is None:
            raise HTTPException(status_code=400, detail="comment is required")
        comment_text = str(updates["comment"]).strip()
        if not comment_text:
            raise HTTPException(status_code=400, detail="comment is required")
        updates["comment"] = comment_text
    for key, value in updates.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    emit_realtime_event("inventory.updated", {"entity": "defect_comment", "action": "update", "id": row.id})
    return DefectCommentRead.model_validate(row)


@router.delete("/defect-comments/{comment_id}")
def delete_defect_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> dict[str, bool]:
    row = db.get(DefectComment, comment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Defect comment not found")
    db.delete(row)
    db.commit()
    emit_realtime_event("inventory.updated", {"entity": "defect_comment", "action": "delete", "id": comment_id})
    return {"ok": True}


@router.get("/defect-timeline", response_model=list[DefectTimelineEntry])
def list_defect_timeline(
    device_id: int | None = None,
    maintenance_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[DefectTimelineEntry]:
    if device_id is None and maintenance_id is None:
        raise HTTPException(status_code=400, detail="Either device_id or maintenance_id is required")

    reports_query = select(DefectReport)
    if device_id is not None:
        reports_query = reports_query.where(DefectReport.device_id == device_id)
    if maintenance_id is not None:
        reports_query = reports_query.where(DefectReport.maintenance_id == maintenance_id)
    reports = list(db.scalars(reports_query).all())
    report_ids = [row.id for row in reports]

    comments: list[DefectComment] = []
    if report_ids:
        comments = list(
            db.scalars(
                select(DefectComment).where(DefectComment.defect_report_id.in_(report_ids))
            ).all()
        )

    timeline: list[DefectTimelineEntry] = []
    report_by_id = {row.id: row for row in reports}
    for row in reports:
        timeline.append(
            DefectTimelineEntry(
                id=f"report:{row.id}",
                entry_type="defect_report",
                created_at=row.created_at,
                updated_at=row.updated_at,
                defect_report_id=row.id,
                device_id=row.device_id,
                maintenance_id=row.maintenance_id,
                status=row.status,
                severity=row.severity,
                title=row.title,
                description=row.description,
                created_by_user_id=row.created_by_user_id,
            )
        )
    for row in comments:
        report = report_by_id.get(row.defect_report_id)
        if report is None:
            continue
        timeline.append(
            DefectTimelineEntry(
                id=f"comment:{row.id}",
                entry_type="defect_comment",
                created_at=row.created_at,
                updated_at=row.updated_at,
                defect_report_id=row.defect_report_id,
                device_id=report.device_id,
                maintenance_id=report.maintenance_id,
                status=report.status,
                severity=report.severity,
                title=report.title,
                comment=row.comment,
                created_by_user_id=row.created_by_user_id,
            )
        )
    timeline.sort(key=lambda item: (
        item.created_at,
        0 if item.entry_type == "defect_report" else 1,
        item.defect_report_id,
        int(item.id.split(":")[1]) if ":" in item.id else 0,
    ))
    return timeline


@router.post("/scan/process", response_model=InventoryScanResponse)
def process_scan(
    payload: InventoryScanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor),
) -> InventoryScanResponse:
    action = (payload.action or "lookup").strip().lower()
    scan_code = (payload.scan_code or "").strip()
    if not scan_code:
        raise HTTPException(status_code=400, detail="scan_code is required")

    device: Device | None = None
    product: Product | None = None
    zone: Zone | None = None
    job: Job | None = None
    rental_scan_actions = {"rental_receive", "rental_job_out", "rental_job_in", "rental_return_supplier"}

    try:
        if action in rental_scan_actions:
            product = _find_rental_product_by_scan_code(db, scan_code)
            if product is None:
                response = InventoryScanResponse(success=False, message="Rental product not found", action=action)
                _record_scan_audit(
                    db,
                    action=action,
                    scan_code=scan_code,
                    success=False,
                    message=response.message,
                    user_id=current_user.id,
                    details={"payload": payload.model_dump()},
                )
                db.commit()
                return response

            if action in {"rental_job_out", "rental_job_in"}:
                job = _resolve_job_for_scan(db, payload.job_code)
                _ensure_job_requirement(db, job.id, product.id)

            balance_before = _rental_scan_balance(db, product.id)
            if action in {"rental_job_out", "rental_return_supplier"} and balance_before["on_hand"] <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="No received rental units are available for this product",
                )

            if action == "rental_receive":
                message = "Rental received from supplier"
            elif action == "rental_job_out":
                req = db.scalar(
                    select(JobRequirement)
                    .where(JobRequirement.job_id == job.id)
                    .where(JobRequirement.product_id == product.id)
                )
                if req is not None:
                    req.quantity_picked = int(req.quantity_picked or 0) + 1
                message = f"Rental scanned out to job {job.job_code}"
            elif action == "rental_job_in":
                req = db.scalar(
                    select(JobRequirement)
                    .where(JobRequirement.job_id == job.id)
                    .where(JobRequirement.product_id == product.id)
                )
                if req is not None and int(req.quantity_picked or 0) > 0:
                    req.quantity_picked = max(int(req.quantity_picked or 0) - 1, 0)
                message = f"Rental scanned back from job {job.job_code}"
            else:
                message = "Rental returned to supplier"

            response = InventoryScanResponse(
                success=True,
                message=message,
                action=action,
                asset_tag=scan_code,
                product_id=product.id,
                product_name=product.name,
                job_id=job.id if job else None,
            )
            _record_scan_audit(
                db,
                action=action,
                scan_code=scan_code,
                success=True,
                message=response.message,
                user_id=current_user.id,
                product_id=product.id,
                job_id=job.id if job else None,
                details={
                    "payload": payload.model_dump(),
                    "rental_balance_before": balance_before,
                },
            )
            db.commit()
            return response

        device = _find_device_by_scan_code(db, scan_code)
        if device is None:
            response = InventoryScanResponse(success=False, message="Device not found", action=action)
            _record_scan_audit(
                db,
                action=action,
                scan_code=scan_code,
                success=False,
                message=response.message,
                user_id=current_user.id,
                details={"payload": payload.model_dump()},
            )
            db.commit()
            return response

        product = db.get(Product, device.product_id)

        if action == "lookup":
            response = _scan_response(action, device, product, "Device found", db=db, include_full_details=True)
            _record_scan_audit(
                db,
                action=action,
                scan_code=scan_code,
                success=True,
                message=response.message,
                user_id=current_user.id,
                device_id=device.id,
                product_id=product.id if product else None,
                details={"payload": payload.model_dump()},
            )
            db.commit()
            return response

        if action == "move":
            if payload.zone_id is None and payload.case_device_id is None:
                raise HTTPException(status_code=400, detail="zone_id or case_device_id is required for move action")

            if payload.case_device_id is not None:
                case_device = db.get(Device, payload.case_device_id)
                if case_device is None:
                    raise HTTPException(status_code=404, detail="Case device not found")
                if case_device.id == device.id:
                    raise HTTPException(status_code=400, detail="Device cannot be moved into itself")

                case_product = db.get(Product, case_device.product_id)
                if case_product is None or case_product.product_type != "case":
                    raise HTTPException(status_code=400, detail="Target device is not a case")

                device.case_device_id = case_device.id
                device.location_zone_id = case_device.location_zone_id
                db.commit()
                db.refresh(device)
                response = _scan_response(action, device, product, f"Moved device into case {case_device.asset_tag}")
                _record_scan_audit(
                    db,
                    action=action,
                    scan_code=scan_code,
                    success=True,
                    message=response.message,
                    user_id=current_user.id,
                    device_id=device.id,
                    product_id=product.id if product else None,
                    details={"payload": payload.model_dump(), "case_device_id": case_device.id},
                )
                db.commit()
                return response

            zone = db.get(Zone, payload.zone_id)
            if zone is None:
                raise HTTPException(status_code=404, detail="Location not found")
            device.location_zone_id = zone.id
            device.case_device_id = None
            db.commit()
            db.refresh(device)
            response = _scan_response(action, device, product, f"Moved device to {zone.name}", zone_id=zone.id)
            _record_scan_audit(
                db,
                action=action,
                scan_code=scan_code,
                success=True,
                message=response.message,
                user_id=current_user.id,
                device_id=device.id,
                product_id=product.id if product else None,
                zone_id=zone.id,
                details={"payload": payload.model_dump()},
            )
            db.commit()
            return response

        if action == "assign_component":
            if payload.parent_component_device_id is None:
                raise HTTPException(status_code=400, detail="parent_component_device_id is required for assign_component action")

            parent_device = db.get(Device, payload.parent_component_device_id)
            if parent_device is None:
                raise HTTPException(status_code=404, detail="Parent device not found")
            if parent_device.id == device.id:
                raise HTTPException(status_code=400, detail="Device cannot be a component of itself")

            device.parent_component_device_id = parent_device.id
            db.commit()
            db.refresh(device)
            response = _scan_response(action, device, product, f"Assigned device as component of {parent_device.asset_tag}")
            _record_scan_audit(
                db,
                action=action,
                scan_code=scan_code,
                success=True,
                message=response.message,
                user_id=current_user.id,
                device_id=device.id,
                product_id=product.id if product else None,
                details={"payload": payload.model_dump(), "parent_component_device_id": parent_device.id},
            )
            db.commit()
            return response

        if action == "maintenance":
            maintenance_type = payload.maintenance_type or "inspection"
            interval_mode = payload.interval_mode or "calendar"
            _validate_maintenance_type(maintenance_type)
            _validate_maintenance_interval_mode(interval_mode)
            interval_value = payload.interval_value

            record_data = {
                "device_id": device.id,
                "maintenance_type": maintenance_type,
                "status": "scheduled",
                "interval_mode": interval_mode,
                "interval_value": interval_value,
                "notes": payload.notes,
            }
            if interval_mode == "runtime" and interval_value:
                current_usage = float(device.usage_hours or 0)
                record_data["due_usage_hours"] = current_usage + float(interval_value)
            else:
                record_data["scheduled_date"] = date.today()

            db.add(DeviceMaintenance(**record_data))
            db.commit()
            response = _scan_response(action, device, product, "Maintenance scheduled")
            _record_scan_audit(
                db,
                action=action,
                scan_code=scan_code,
                success=True,
                message=response.message,
                user_id=current_user.id,
                device_id=device.id,
                product_id=product.id if product else None,
                details={"payload": payload.model_dump()},
            )
            db.commit()
            return response

        if action == "report_defect":
            title = (payload.defect_title or "").strip()
            if not title:
                raise HTTPException(status_code=400, detail="defect_title is required for report_defect action")
            severity = (payload.defect_severity or "medium").strip()
            _validate_defect_severity(severity)
            report = DefectReport(
                device_id=device.id,
                title=title,
                description=(payload.defect_description or "").strip() or None,
                severity=severity,
                status="open",
                created_by_user_id=current_user.id,
            )
            db.add(report)
            _update_device_on_defect_change(db, device.id)
            db.commit()
            db.refresh(report)
            emit_realtime_event("inventory.updated", {"entity": "defect_report", "action": "create", "id": report.id})
            response = _scan_response(action, device, product, "Defect reported")
            _record_scan_audit(
                db,
                action=action,
                scan_code=scan_code,
                success=True,
                message=response.message,
                user_id=current_user.id,
                device_id=device.id,
                product_id=product.id if product else None,
                details={"payload": payload.model_dump(), "defect_report_id": report.id},
            )
            db.commit()
            return response

        if action in {"job_out", "job_in"}:
            if action == "job_out":
                job = _resolve_job_for_scan(db, payload.job_code)
            else:
                candidate_job_code = (payload.job_code or "").strip()
                job = _resolve_job_for_scan(db, candidate_job_code) if candidate_job_code else None

            target_devices = [device]
            if product and product.product_type == "case":
                target_devices = _collect_case_devices(db, device)
            target_devices = _lock_devices_for_update(db, target_devices)

            if action == "job_out":
                # Preflight check: verify none of the devices are already checked out to this job
                device_ids = [target.id for target in target_devices]
                checked_out_device_ids = _get_devices_checked_out_to_job(db, device_ids=device_ids, job_id=job.id)
                if checked_out_device_ids:
                    count = len(checked_out_device_ids)
                    device_word = "Devices" if count > 1 else "Device"
                    verb = "are" if count > 1 else "is"
                    raise HTTPException(
                        status_code=409,
                        detail=f"{device_word} {verb} already scanned out to job {job.job_code}",
                    )

                # All devices passed the duplicate check, now proceed with state changes
                picked_by_product: dict[int, int] = defaultdict(int)
                for target in target_devices:
                    _ensure_job_requirement(db, job.id, target.product_id)
                    picked_by_product[target.product_id] += 1
                    target.status = "in_use"

                for product_id in sorted(picked_by_product):
                    increment = picked_by_product[product_id]
                    req = db.scalar(
                        select(JobRequirement)
                        .where(JobRequirement.job_id == job.id)
                        .where(JobRequirement.product_id == product_id)
                        .with_for_update()
                    )
                    if req is not None:
                        req.quantity_picked = int(req.quantity_picked or 0) + int(increment)

                db.flush()
                db.refresh(device)
                affected_count = len(target_devices)
                response = _scan_response(
                    action,
                    device,
                    product,
                    "Scanned case and contained devices out to job" if affected_count > 1 else "Scanned out to job",
                    job_id=job.id,
                )
                _record_scan_audit(
                    db,
                    action=action,
                    scan_code=scan_code,
                    success=True,
                    message=response.message,
                    user_id=current_user.id,
                    device_id=device.id,
                    product_id=product.id if product else None,
                    job_id=job.id,
                    details={"payload": payload.model_dump(), "affected_device_ids": [row.id for row in target_devices]},
                )
                for target in target_devices:
                    if target.id == device.id:
                        continue
                    _record_scan_audit(
                        db,
                        action=action,
                        scan_code=scan_code,
                        success=True,
                        message=response.message,
                        user_id=current_user.id,
                        device_id=target.id,
                        product_id=target.product_id,
                        job_id=job.id,
                        details={
                            "payload": payload.model_dump(),
                            "scanned_case_device_id": device.id,
                        },
                        suppress_event=True,
                    )
                db.commit()
                return response

            return_zone = None
            if payload.zone_id is not None:
                return_zone = db.get(Zone, payload.zone_id)
                if return_zone is None:
                    raise HTTPException(status_code=404, detail="Location not found")

            if job is not None:
                decremented_by_product: dict[int, int] = defaultdict(int)
                for target in target_devices:
                    decremented_by_product[target.product_id] += 1
                for product_id in sorted(decremented_by_product):
                    decrement = decremented_by_product[product_id]
                    req = db.scalar(
                        select(JobRequirement)
                        .where(JobRequirement.job_id == job.id)
                        .where(JobRequirement.product_id == product_id)
                        .with_for_update()
                    )
                    if req is not None and req.quantity_picked > 0:
                        req.quantity_picked = max(int(req.quantity_picked or 0) - int(decrement), 0)

            for target in target_devices:
                target.status = "available"
                if return_zone is not None:
                    target.location_zone_id = return_zone.id
            db.flush()
            db.refresh(device)
            affected_count = len(target_devices)
            response = _scan_response(
                action,
                device,
                product,
                (
                    "Scanned case and contained devices in from job"
                    if affected_count > 1 and job is not None
                    else "Scanned in from job"
                    if job is not None
                    else "Scanned in (global check-in)"
                ),
                job_id=job.id if job is not None else None,
            )
            _record_scan_audit(
                db,
                action=action,
                scan_code=scan_code,
                success=True,
                message=response.message,
                user_id=current_user.id,
                device_id=device.id,
                product_id=product.id if product else None,
                job_id=job.id if job is not None else None,
                details={"payload": payload.model_dump(), "affected_device_ids": [row.id for row in target_devices]},
            )
            for target in target_devices:
                if target.id == device.id:
                    continue
                _record_scan_audit(
                    db,
                    action=action,
                    scan_code=scan_code,
                    success=True,
                    message=response.message,
                    user_id=current_user.id,
                    device_id=target.id,
                    product_id=target.product_id,
                    job_id=job.id if job is not None else None,
                    details={
                        "payload": payload.model_dump(),
                        "scanned_case_device_id": device.id,
                    },
                    suppress_event=True,
                )
            db.commit()
            return response

        raise HTTPException(status_code=400, detail="Unsupported scan action")
    except HTTPException as exc:
        _record_scan_audit(
            db,
            action=action,
            scan_code=scan_code,
            success=False,
            message=str(exc.detail),
            user_id=current_user.id,
            device_id=device.id if device else None,
            product_id=product.id if product else None,
            zone_id=zone.id if zone else None,
            job_id=job.id if job else None,
            details={"payload": payload.model_dump(), "status_code": exc.status_code},
        )
        db.commit()
        raise


@router.get("/audit", response_model=list[InventoryAuditRead])
def list_inventory_audit_logs(
    limit: int = 100,
    device_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[InventoryAuditRead]:
    safe_limit = min(max(limit, 1), 500)
    query = select(InventoryAuditLog).order_by(InventoryAuditLog.created_at.desc(), InventoryAuditLog.id.desc())
    if device_id is not None:
        query = query.where(InventoryAuditLog.device_id == device_id)
    rows = list(
        db.scalars(
            query.limit(safe_limit)
        ).all()
    )
    return [_to_inventory_audit_read(db, row) for row in rows]


@router.get("/zones", response_model=list[ZoneRead])
def list_zones(db: Session = Depends(get_db)) -> list[Zone]:
    return list(db.scalars(select(Zone).order_by(Zone.parent_id, Zone.sort_order, Zone.name)).all())


@router.get("/zones/tree", response_model=list[ZoneTreeRead])
def list_zones_tree(db: Session = Depends(get_db)) -> list[ZoneTreeRead]:
    zones = list(
        db.scalars(
            select(Zone).order_by(
                Zone.parent_id,
                Zone.sort_order,
                Zone.name,
            )
        ).all()
    )
    return _build_zone_tree(zones)


@router.post("/zones", response_model=ZoneRead)
def create_zone(payload: ZoneCreate, db: Session = Depends(get_db)) -> Zone:
    if payload.parent_id is not None:
        parent = db.get(Zone, payload.parent_id)
        if parent is None:
            raise HTTPException(status_code=404, detail="Parent location not found")

    zone = Zone(**payload.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    emit_realtime_event("inventory.updated", {"entity": "zone", "action": "create", "id": zone.id})
    return zone


@router.put("/zones/{zone_id}", response_model=ZoneRead)
def update_zone(zone_id: int, payload: ZoneUpdate, db: Session = Depends(get_db)) -> Zone:
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")

    updates = payload.model_dump(exclude_unset=True)
    if "parent_id" in updates:
        _validate_zone_parent_assignment(db, zone, updates["parent_id"])

    for key, value in updates.items():
        setattr(zone, key, value)
    db.commit()
    db.refresh(zone)
    emit_realtime_event("inventory.updated", {"entity": "zone", "action": "update", "id": zone.id})
    return zone


@router.post("/zones/{zone_id}/move", response_model=ZoneRead)
def move_zone(
    zone_id: int,
    payload: ZoneMove,
    db: Session = Depends(get_db),
) -> Zone:
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Location not found")

    target_parent_id = payload.parent_id
    _validate_zone_parent_assignment(db, zone, target_parent_id)

    before_zone = None
    if payload.before_id is not None:
        before_zone = db.get(Zone, payload.before_id)
        if before_zone is None:
            raise HTTPException(status_code=404, detail="before_id location not found")
        if before_zone.parent_id != target_parent_id:
            raise HTTPException(status_code=400, detail="before_id must have the same parent as move target")

    old_parent_id = zone.parent_id
    zone.parent_id = target_parent_id

    sibling_query = (
        select(Zone)
        .where(Zone.parent_id == target_parent_id)
        .where(Zone.id != zone.id)
        .order_by(Zone.sort_order, Zone.id)
    )
    siblings = list(db.scalars(sibling_query).all())

    insert_index = len(siblings)
    if before_zone is not None:
        for i, sibling in enumerate(siblings):
            if sibling.id == before_zone.id:
                insert_index = i
                break
    siblings.insert(insert_index, zone)

    for idx, sibling in enumerate(siblings):
        sibling.sort_order = idx

    _normalize_zone_sibling_sort_orders(db, old_parent_id)
    if old_parent_id != target_parent_id:
        _normalize_zone_sibling_sort_orders(db, target_parent_id)

    db.commit()
    db.refresh(zone)
    return zone


@router.get("/locations", response_model=list[ZoneRead])
def list_locations(db: Session = Depends(get_db)) -> list[Zone]:
    return list_zones(db)


@router.get("/locations/tree", response_model=list[ZoneTreeRead])
def list_locations_tree(db: Session = Depends(get_db)) -> list[ZoneTreeRead]:
    return list_zones_tree(db)


@router.post("/locations", response_model=ZoneRead)
def create_location(payload: ZoneCreate, db: Session = Depends(get_db)) -> Zone:
    return create_zone(payload=payload, db=db)


@router.put("/locations/{location_id}", response_model=ZoneRead)
def update_location(location_id: int, payload: ZoneUpdate, db: Session = Depends(get_db)) -> Zone:
    return update_zone(zone_id=location_id, payload=payload, db=db)


@router.post("/locations/{location_id}/move", response_model=ZoneRead)
def move_location(location_id: int, payload: ZoneMove, db: Session = Depends(get_db)) -> Zone:
    return move_zone(zone_id=location_id, payload=payload, db=db)


@router.post("/locations/{location_id}/subzones/bulk", response_model=list[ZoneRead])
def create_subzones_bulk(
    location_id: int,
    payload: list[ZoneCreate],
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
) -> list[Zone]:
    parent = db.get(Zone, location_id)
    if parent is None:
        raise HTTPException(status_code=404, detail="Parent location not found")

    max_code_length = Zone.__table__.columns.code.type.length or 50
    created: list[Zone] = []
    # pre-check for conflicting codes to give a friendly 409 response
    requested_codes: list[str] = []
    requested_code_by_lower: dict[str, str] = {}
    duplicate_codes: set[str] = set()
    for item in payload:
        code = (item.code or "").strip()
        if not code:
            raise HTTPException(status_code=422, detail="Zone code is required")
        if len(code) > max_code_length:
            raise HTTPException(status_code=422, detail=f"Zone code must be at most {max_code_length} characters")
        lower_code = code.lower()
        previous = requested_code_by_lower.get(lower_code)
        if previous is not None:
            duplicate_codes.add(previous)
            duplicate_codes.add(code)
        else:
            requested_code_by_lower[lower_code] = code
        requested_codes.append(code)
    if duplicate_codes:
        raise HTTPException(
            status_code=409,
            detail={"message": "Code conflict", "conflicts": sorted(duplicate_codes, key=str.lower)},
        )
    if requested_codes:
        lower_codes = list(requested_code_by_lower.keys())
        existing = list(db.scalars(select(Zone.code).where(func.lower(Zone.code).in_(lower_codes))).all())
        if existing:
            raise HTTPException(status_code=409, detail={"message": "Code conflict", "conflicts": existing})
    for item, code in zip(payload, requested_codes):
        # ensure child uses the provided payload but force the parent assignment
        data = item.model_dump()
        data["code"] = code
        data["parent_id"] = location_id
        zone = Zone(**data)
        db.add(zone)
        created.append(zone)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # attempt to extract conflicting codes if possible (Postgres / SQLite messages)
        conflicts: list[str] = []
        try:
            orig = getattr(exc, 'orig', None) or exc
            text = str(orig)

            # Postgres pattern: Key (code)=(abc) already exists.
            matches = re.findall(r"Key \(code\)=\(([^)]+)\)", text)
            if matches:
                conflicts.extend(matches)
            # SQLite pattern: UNIQUE constraint failed: zones.code: abc
            matches = re.findall(r"UNIQUE constraint failed: [^:]+: (.+)$", text)
            if matches:
                conflicts.extend([m.strip() for m in matches])
        except Exception:
            conflicts = []

        detail = {"message": "Code conflict", "conflicts": conflicts} if conflicts else "One or more zone codes conflict with existing entries"
        raise HTTPException(status_code=409, detail=detail) from exc
    except DataError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="One or more zone values are invalid") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create subzones") from exc

    # refresh created objects so fields like id are populated
    for zone in created:
        db.refresh(zone)

    emit_realtime_event("inventory.updated", {"entity": "zone", "action": "bulk_create", "count": len(created)})
    return created


def _build_category_tree(categories: list[InventoryCategory]) -> list[InventoryCategoryTreeRead]:
    children_by_parent: dict[int | None, list[InventoryCategory]] = defaultdict(list)
    for cat in categories:
        children_by_parent[cat.parent_id].append(cat)

    for bucket in children_by_parent.values():
        bucket.sort(key=lambda item: (item.sort_order, item.name.lower()))

    def build_node(cat: InventoryCategory) -> InventoryCategoryTreeRead:
        return InventoryCategoryTreeRead(
            id=cat.id,
            name=cat.name,
            parent_id=cat.parent_id,
            sort_order=cat.sort_order,
            is_active=cat.is_active,
            children=[build_node(child) for child in children_by_parent.get(cat.id, [])],
        )

    roots = children_by_parent.get(None, [])
    return [build_node(root) for root in roots]


def _build_zone_tree(zones: list[Zone]) -> list[ZoneTreeRead]:
    children_by_parent: dict[int | None, list[Zone]] = defaultdict(list)
    for zone in zones:
        children_by_parent[zone.parent_id].append(zone)

    for bucket in children_by_parent.values():
        bucket.sort(key=lambda item: (item.sort_order, item.name.lower()))

    def build_node(zone: Zone) -> ZoneTreeRead:
        return ZoneTreeRead(
            id=zone.id,
            code=zone.code,
            name=zone.name,
            zone_type=zone.zone_type,
            barcode=zone.barcode,
            qr_code=zone.qr_code,
            rfid=zone.rfid,
            parent_id=zone.parent_id,
            sort_order=zone.sort_order,
            is_active=zone.is_active,
            children=[build_node(child) for child in children_by_parent.get(zone.id, [])],
        )

    roots = children_by_parent.get(None, [])
    return [build_node(root) for root in roots]


def _validate_parent_assignment(db: Session, category: InventoryCategory, parent_id: int | None) -> None:
    if parent_id == category.id:
        raise HTTPException(status_code=400, detail="Category cannot be its own parent")

    if parent_id is None:
        return

    parent = db.get(InventoryCategory, parent_id)
    if parent is None:
        raise HTTPException(status_code=404, detail="Parent category not found")

    current = parent
    while current is not None:
        if current.id == category.id:
            raise HTTPException(status_code=400, detail="Category cannot be moved under its descendant")
        current = current.parent


def _normalize_sibling_sort_orders(db: Session, parent_id: int | None) -> None:
    siblings = list(
        db.scalars(
            select(InventoryCategory)
            .where(InventoryCategory.parent_id == parent_id)
            .order_by(InventoryCategory.sort_order, InventoryCategory.id)
        ).all()
    )
    for idx, sibling in enumerate(siblings):
        sibling.sort_order = idx


def _validate_product_type(product_type: str | None) -> None:
    if product_type is None:
        return
    allowed = {"equipment", "accessory", "consumable", "case", "rental", "bundle"}
    if product_type not in allowed:
        raise HTTPException(status_code=400, detail="product_type must be one of: equipment, accessory, consumable, case, rental, bundle")


def _validate_device_product_and_location(db: Session, payload: dict) -> None:
    if payload.get("product_id") is not None:
        product = db.get(Product, payload["product_id"])
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

    if payload.get("location_zone_id") is not None:
        zone = db.get(Zone, payload["location_zone_id"])
        if zone is None:
            raise HTTPException(status_code=404, detail="Location not found")

    if payload.get("case_device_id") is not None:
        case_device = db.get(Device, payload["case_device_id"])
        if case_device is None:
            raise HTTPException(status_code=404, detail="Case device not found")
        case_product = db.get(Product, case_device.product_id)
        if case_product is None or case_product.product_type != "case":
            raise HTTPException(status_code=400, detail="case_device_id must point to a device whose product_type is case")

    if payload.get("parent_component_device_id") is not None:
        component_device = db.get(Device, payload["parent_component_device_id"])
        if component_device is None:
            raise HTTPException(status_code=404, detail="Component device not found")
        component_product = db.get(Product, component_device.product_id)
        if component_product is None:
            raise HTTPException(status_code=400, detail="Component device has no product")


def _validate_zone_parent_assignment(db: Session, zone: Zone, parent_id: int | None) -> None:
    if parent_id == zone.id:
        raise HTTPException(status_code=400, detail="Location cannot be its own parent")

    if parent_id is None:
        return

    parent = db.get(Zone, parent_id)
    if parent is None:
        raise HTTPException(status_code=404, detail="Parent location not found")

    current = parent
    while current is not None:
        if current.id == zone.id:
            raise HTTPException(status_code=400, detail="Location cannot be moved under its descendant")
        current = current.parent


def _validate_maintenance_status(status: str) -> None:
    if status not in MAINTENANCE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(MAINTENANCE_STATUSES)}")


def _validate_maintenance_type(maintenance_type: str) -> None:
    if maintenance_type not in MAINTENANCE_TYPES:
        raise HTTPException(status_code=400, detail=f"maintenance_type must be one of: {', '.join(MAINTENANCE_TYPES)}")


def _validate_maintenance_interval_mode(interval_mode: str) -> None:
    if interval_mode not in MAINTENANCE_INTERVAL_MODES:
        raise HTTPException(status_code=400, detail=f"interval_mode must be one of: {', '.join(MAINTENANCE_INTERVAL_MODES)}")


def _validate_maintenance_payload(db: Session, payload: dict) -> None:
    if payload.get("device_id") is not None:
        device = db.get(Device, payload["device_id"])
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found")

    if payload.get("status") is not None:
        _validate_maintenance_status(payload["status"])
    if payload.get("maintenance_type") is not None:
        _validate_maintenance_type(payload["maintenance_type"])
    if payload.get("interval_mode") is not None:
        _validate_maintenance_interval_mode(payload["interval_mode"])


def _validate_defect_status(status: str) -> None:
    if status not in DEFECT_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(DEFECT_STATUSES)}")


def _validate_defect_severity(severity: str) -> None:
    if severity not in DEFECT_SEVERITIES:
        raise HTTPException(status_code=400, detail=f"severity must be one of: {', '.join(DEFECT_SEVERITIES)}")


RESOLVED_DEFECT_STATUSES = {"resolved", "closed"}


def _update_device_on_defect_change(db: Session, device_id: int) -> None:
    device = db.get(Device, device_id)
    if device is None:
        return
    db.flush()
    open_count = db.scalar(
        select(func.count()).select_from(DefectReport).where(
            DefectReport.device_id == device_id,
            DefectReport.status.notin_(RESOLVED_DEFECT_STATUSES),
        )
    )
    if open_count and open_count > 0:
        device.status = "maintenance"
        device.condition = "damaged"
    else:
        device.status = "available"
        device.condition = "good"
    db.add(device)


def _validate_defect_report_payload(db: Session, payload: dict) -> None:
    if payload.get("device_id") is not None:
        device = db.get(Device, payload["device_id"])
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found")

    maintenance_id = payload.get("maintenance_id")
    if maintenance_id is not None:
        maintenance = db.get(DeviceMaintenance, maintenance_id)
        if maintenance is None:
            raise HTTPException(status_code=404, detail="Maintenance record not found")
        if payload.get("device_id") is not None and maintenance.device_id != payload["device_id"]:
            raise HTTPException(status_code=400, detail="maintenance_id does not belong to device_id")

    if payload.get("status") is not None:
        _validate_defect_status(payload["status"])
    if payload.get("severity") is not None:
        _validate_defect_severity(payload["severity"])
    if payload.get("title") is not None and not str(payload["title"]).strip():
        raise HTTPException(status_code=400, detail="title is required")


def _normalize_defect_report_text_fields(payload: dict) -> None:
    if "title" in payload and payload["title"] is not None:
        payload["title"] = str(payload["title"]).strip()
    if "description" in payload:
        description = payload["description"]
        payload["description"] = (str(description).strip() or None) if description is not None else None


def _effective_schedule_interval_value(db: Session, device_id: int, schedule: DeviceMaintenanceSchedule) -> int | None:
    if schedule.interval_value is not None:
        return schedule.interval_value

    device = db.get(Device, device_id)
    if device is None:
        return None
    product = db.get(Product, device.product_id)
    if product is None:
        return None
    return product.maintenance_interval_days


def _apply_schedule_values_to_task(db: Session, record: DeviceMaintenance, schedule: DeviceMaintenanceSchedule) -> None:
    record.maintenance_type = schedule.maintenance_type
    record.interval_mode = schedule.interval_mode
    record.notes = schedule.notes

    effective_interval_value = _effective_schedule_interval_value(db, record.device_id, schedule)
    record.interval_value = effective_interval_value

    device = db.get(Device, record.device_id)
    if schedule.interval_mode == "runtime":
        record.scheduled_date = None
        if effective_interval_value is None:
            record.due_usage_hours = None
            return
        current_usage = float(device.usage_hours or 0) if device is not None else 0.0
        record.due_usage_hours = current_usage + float(effective_interval_value)
        return

    record.due_usage_hours = None
    if schedule.scheduled_date is not None:
        record.scheduled_date = schedule.scheduled_date
        return
    if effective_interval_value is not None:
        base_date = device.purchase_date if device is not None else None
        record.scheduled_date = (base_date or date.today()) + timedelta(days=int(effective_interval_value))
    else:
        record.scheduled_date = None


def _pending_schedule_tasks(db: Session, schedule_id: int) -> list[DeviceMaintenance]:
    return list(
        db.scalars(
            select(DeviceMaintenance)
            .where(DeviceMaintenance.schedule_id == schedule_id)
            .where(DeviceMaintenance.status.in_(["scheduled", "in_progress"]))
            .order_by(DeviceMaintenance.id)
        ).all()
    )


def _pending_schedule_task_count(db: Session, schedule_id: int) -> int:
    return len(_pending_schedule_tasks(db, schedule_id))


def _apply_schedule_updates(db: Session, schedule: DeviceMaintenanceSchedule, updates: dict[str, Any]) -> None:
    if updates.get("maintenance_type") is not None:
        _validate_maintenance_type(updates["maintenance_type"])
    if updates.get("interval_mode") is not None:
        _validate_maintenance_interval_mode(updates["interval_mode"])

    for key, value in updates.items():
        setattr(schedule, key, value)

    pending_records = _pending_schedule_tasks(db, schedule.id)
    for record in pending_records:
        _apply_schedule_values_to_task(db, record, schedule)


def _to_schedule_read(schedule: DeviceMaintenanceSchedule) -> MaintenanceScheduleRead:
    return MaintenanceScheduleRead.model_validate(
        {
            "id": schedule.id,
            "maintenance_type": schedule.maintenance_type,
            "interval_mode": schedule.interval_mode,
            "interval_value": schedule.interval_value,
            "scheduled_date": schedule.scheduled_date,
            "notes": schedule.notes,
            "created_at": schedule.created_at,
            "updated_at": schedule.updated_at,
        }
    )


def _to_maintenance_read(db: Session, record: DeviceMaintenance) -> DeviceMaintenanceRead:
    device = db.get(Device, record.device_id)
    product = db.get(Product, device.product_id) if device else None

    return DeviceMaintenanceRead.model_validate(
        {
            "id": record.id,
            "device_id": record.device_id,
            "schedule_id": record.schedule_id,
            "maintenance_type": record.maintenance_type,
            "status": record.status,
            "interval_mode": record.interval_mode,
            "interval_value": record.interval_value,
            "due_usage_hours": record.due_usage_hours,
            "scheduled_date": record.scheduled_date,
            "completed_date": record.completed_date,
            "notes": record.notes,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "product_id": product.id if product else None,
            "product_name": product.name if product else None,
            "asset_tag": device.asset_tag if device else None,
        }
    )


def _hydrate_defect_report_read(
    row: DefectReport,
    device: Device | None,
    product: Product | None,
    maintenance: DeviceMaintenance | None,
) -> DefectReportRead:
    return DefectReportRead.model_validate(
        {
            "id": row.id,
            "device_id": row.device_id,
            "maintenance_id": row.maintenance_id,
            "title": row.title,
            "description": row.description,
            "status": row.status,
            "severity": row.severity,
            "created_by_user_id": row.created_by_user_id,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "asset_tag": device.asset_tag if device is not None else None,
            "product_id": product.id if product is not None else None,
            "product_name": product.name if product is not None else None,
            "maintenance_type": maintenance.maintenance_type if maintenance is not None else None,
        }
    )


def _to_defect_report_read(db: Session, row: DefectReport) -> DefectReportRead:
    device = db.get(Device, row.device_id)
    product = db.get(Product, device.product_id) if device is not None else None
    maintenance = db.get(DeviceMaintenance, row.maintenance_id) if row.maintenance_id is not None else None
    return _hydrate_defect_report_read(row, device, product, maintenance)


def _get_defect_report_or_404(db: Session, report_id: int) -> DefectReport:
    row = db.get(DefectReport, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Defect report not found")
    return row


def _find_device_by_scan_code(db: Session, scan_code: str) -> Device | None:
    code = (scan_code or "").strip()
    if not code:
        return None
    return db.scalar(
        select(Device).where(
            (Device.asset_tag == code)
            | (Device.barcode == code)
            | (Device.qr_code == code)
            | (Device.rfid == code)
            | (Device.serial_number == code)
        )
    )


def _find_rental_product_by_scan_code(db: Session, scan_code: str) -> Product | None:
    code = (scan_code or "").strip()
    if not code:
        return None
    normalized = code.upper()

    return db.scalar(
        select(Product)
        .where(
            (Product.is_rental_product.is_(True))
            | (Product.product_type == "rental")
        )
        .where(
            (func.upper(Product.sku) == normalized)
            | (func.upper(Product.external_reference) == normalized)
        )
    )


def _rental_scan_balance(db: Session, product_id: int) -> dict[str, int]:
    def _count(action: str) -> int:
        return int(
            db.scalar(
                select(func.count())
                .select_from(InventoryAuditLog)
                .where(InventoryAuditLog.success.is_(True))
                .where(InventoryAuditLog.product_id == product_id)
                .where(InventoryAuditLog.action == action)
            )
            or 0
        )

    received = _count("rental_receive")
    job_in = _count("rental_job_in")
    job_out = _count("rental_job_out")
    returned_supplier = _count("rental_return_supplier")
    on_hand = received + job_in - job_out - returned_supplier
    return {
        "received": received,
        "job_in": job_in,
        "job_out": job_out,
        "returned_supplier": returned_supplier,
        "on_hand": max(on_hand, 0),
    }


def _resolve_job_for_scan(db: Session, job_code: str | None) -> Job:
    candidate = (job_code or "").strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="job_code is required for job scan actions")

    job = db.scalar(select(Job).where(Job.job_code == candidate))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _get_devices_checked_out_to_job(db: Session, *, device_ids: list[int], job_id: int) -> set[int]:
    """
    Batch check which devices are already checked out to the given job.
    
    Uses a window function to efficiently retrieve the latest job_out/job_in audit row 
    per device in a single query, avoiding N+1 query patterns for case scans with 
    many contained devices.
    
    Filters audit logs by:
    - source='scan': Only scan-based audit entries
    - success=True: Only successful operations
    - action in ('job_out', 'job_in'): Only job checkout/checkin operations
    
    The latest row is determined by ordering created_at DESC, then id DESC (as a 
    tiebreaker when multiple rows have the same timestamp).
    
    Args:
        db: Database session
        device_ids: List of device IDs to check
        job_id: Job ID to check against
    
    Returns:
        Set of device IDs that are currently checked out to the specified job.
        Returns an empty set if device_ids is empty or no devices are checked out.
    """
    # Early return for empty input - avoids constructing an empty IN clause
    if not device_ids:
        return set()
    
    # Subquery to get the latest audit row per device using window functions
    latest_audits_subq = (
        select(
            InventoryAuditLog.device_id,
            InventoryAuditLog.action,
            InventoryAuditLog.job_id,
            func.row_number()
            .over(
                partition_by=InventoryAuditLog.device_id,
                order_by=(
                    InventoryAuditLog.created_at.desc(),
                    InventoryAuditLog.id.desc(),
                ),
            )
            .label("rn"),
        )
        .where(InventoryAuditLog.source == "scan")
        .where(InventoryAuditLog.success.is_(True))
        .where(InventoryAuditLog.device_id.in_(device_ids))
        .where(InventoryAuditLog.action.in_(("job_out", "job_in")))
        .subquery()
    )
    
    # Select only the latest row (rn = 1) for each device
    latest_audits = db.execute(
        select(latest_audits_subq.c.device_id)
        .where(latest_audits_subq.c.rn == 1)
        .where(latest_audits_subq.c.action == "job_out")
        .where(latest_audits_subq.c.job_id == job_id)
    ).scalars().all()
    
    return set(latest_audits)


def _lock_devices_for_update(db: Session, devices: list[Device]) -> list[Device]:
    if not devices:
        return []
    sorted_device_ids = sorted({row.id for row in devices})
    locked_devices_result = db.scalars(
        select(Device)
        .where(Device.id.in_(sorted_device_ids))
        .order_by(Device.id)
        .with_for_update()
    )
    locked_by_id = {row.id: row for row in locked_devices_result}
    if len(locked_by_id) != len(sorted_device_ids):
        raise HTTPException(status_code=404, detail="One or more target devices were not found for scan")
    return [locked_by_id[row.id] for row in devices]


def _ensure_job_requirement(db: Session, job_id: int, product_id: int) -> None:
    existing = db.scalar(
        select(JobRequirement)
        .where(JobRequirement.job_id == job_id)
        .where(JobRequirement.product_id == product_id)
    )
    if existing is None:
        db.add(JobRequirement(job_id=job_id, product_id=product_id, quantity_required=0, quantity_picked=0))
        db.flush()


def _scan_response(
    action: str,
    device: Device,
    product: Product | None,
    message: str,
    job_id: int | None = None,
    zone_id: int | None = None,
    db: Session | None = None,
    include_full_details: bool = False,
) -> InventoryScanResponse:
    device_details = None
    product_details = None
    location_details = None
    maintenance_details = None

    if include_full_details and db is not None:
        full_details = _build_lookup_details(db, device, product)
        device_details = full_details["device_details"]
        product_details = full_details["product_details"]
        location_details = full_details["location_details"]
        maintenance_details = full_details["maintenance_details"]

    return InventoryScanResponse(
        success=True,
        message=message,
        action=action,
        device_id=device.id,
        asset_tag=device.asset_tag,
        product_id=product.id if product else None,
        product_name=product.name if product else None,
        job_id=job_id,
        zone_id=zone_id,
        device_details=device_details,
        product_details=product_details,
        location_details=location_details,
        maintenance_details=maintenance_details,
    )


def _collect_case_devices(db: Session, case_device: Device) -> list[Device]:
    rows = [case_device]
    direct_children = list(
        db.scalars(
            select(Device)
            .where(Device.case_device_id == case_device.id)
            .order_by(Device.id)
        ).all()
    )
    rows.extend(direct_children)
    return rows


def _to_product_component_read(db: Session, row: ProductComponent) -> ProductComponentRead:
    component = db.get(Product, row.component_product_id)
    return ProductComponentRead(
        id=row.id,
        parent_product_id=row.parent_product_id,
        component_product_id=row.component_product_id,
        component_sku=component.sku if component else None,
        component_name=component.name if component else None,
        quantity=int(row.quantity or 1),
    )


def _to_product_accessory_read(db: Session, row: ProductAccessory) -> ProductAccessoryRead:
    accessory = db.get(Product, row.accessory_product_id)
    return ProductAccessoryRead(
        id=row.id,
        parent_product_id=row.parent_product_id,
        accessory_product_id=row.accessory_product_id,
        accessory_sku=accessory.sku if accessory else None,
        accessory_name=accessory.name if accessory else None,
        quantity=int(row.quantity or 1),
        required=bool(row.required),
    )


def _to_device_read(db: Session, device: Device) -> DeviceRead:
    case_asset_tag = None
    if device.case_device_id:
        case_device = db.get(Device, device.case_device_id)
        case_asset_tag = case_device.asset_tag if case_device else None

    parent_component_asset_tag = None
    if device.parent_component_device_id:
        comp_device = db.get(Device, device.parent_component_device_id)
        parent_component_asset_tag = comp_device.asset_tag if comp_device else None

    current_job_id = None
    current_job_code = None
    if str(device.status or "").lower() == "in_use":
        latest_job_audit = db.scalar(
            select(InventoryAuditLog)
            .where(InventoryAuditLog.device_id == device.id)
            .where(InventoryAuditLog.success.is_(True))
            .where(InventoryAuditLog.job_id.is_not(None))
            .order_by(InventoryAuditLog.created_at.desc(), InventoryAuditLog.id.desc())
        )
        if latest_job_audit and latest_job_audit.action == "job_out":
            current_job_id = latest_job_audit.job_id
            job = db.get(Job, latest_job_audit.job_id)
            current_job_code = job.job_code if job else None

    return DeviceRead.model_validate(
        {
            "id": device.id,
            "product_id": device.product_id,
            "asset_tag": device.asset_tag,
            "serial_number": device.serial_number,
            "barcode": device.barcode,
            "qr_code": device.qr_code,
            "rfid": device.rfid,
            "location_zone_id": device.location_zone_id,
            "case_device_id": device.case_device_id,
            "case_asset_tag": case_asset_tag,
            "parent_component_device_id": device.parent_component_device_id,
            "parent_component_asset_tag": parent_component_asset_tag,
            "status": device.status,
            "condition": device.condition,
            "purchase_date": device.purchase_date,
            "purchase_price": device.purchase_price,
            "purchased_from": device.purchased_from,
            "sold_price": device.sold_price,
            "finance_upto": device.finance_upto,
            "finance_company": device.finance_company,
            "finance_ref": device.finance_ref,
            "pre_prep": device.pre_prep,
            "warranty_end_date": device.warranty_end_date,
            "retire_date": device.retire_date,
            "usage_hours": device.usage_hours,
            "notes": device.notes,
            "created_at": device.created_at,
            "current_job_id": current_job_id,
            "current_job_code": current_job_code,
        }
    )


def _build_lookup_details(db: Session, device: Device, product: Product | None) -> dict[str, Any]:
    zone = db.get(Zone, device.location_zone_id) if device.location_zone_id else None
    case_device = db.get(Device, device.case_device_id) if device.case_device_id else None
    maintenance_records = list(
        db.scalars(
            select(DeviceMaintenance)
            .where(DeviceMaintenance.device_id == device.id)
            .order_by(DeviceMaintenance.created_at.desc(), DeviceMaintenance.id.desc())
        ).all()
    )

    return {
        "device_details": {
            "id": device.id,
            "product_id": device.product_id,
            "asset_tag": device.asset_tag,
            "serial_number": device.serial_number,
            "barcode": device.barcode,
            "qr_code": device.qr_code,
            "rfid": device.rfid,
            "location_zone_id": device.location_zone_id,
            "location_zone_name": zone.name if zone else None,
            "case_device_id": device.case_device_id,
            "case_asset_tag": case_device.asset_tag if case_device else None,
            "status": device.status,
            "condition": device.condition,
            "purchase_date": device.purchase_date,
            "purchase_price": device.purchase_price,
            "purchased_from": device.purchased_from,
            "sold_price": device.sold_price,
            "finance_upto": device.finance_upto,
            "finance_company": device.finance_company,
            "finance_ref": device.finance_ref,
            "pre_prep": device.pre_prep,
            "warranty_end_date": device.warranty_end_date,
            "retire_date": device.retire_date,
            "usage_hours": device.usage_hours,
            "notes": device.notes,
            "created_at": device.created_at,
        },
        "product_details": {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "category": product.category,
            "category_id": product.category_id,
            "brand": product.brand,
            "manufacturer": product.manufacturer,
            "product_type": product.product_type,
            "is_rental_product": product.is_rental_product,
            "supplier_name": product.supplier_name,
            "rental_price": product.rental_price,
            "external_source": product.external_source,
            "external_reference": product.external_reference,
            "eventory_available_qty": product.eventory_available_qty,
            "weight_kg": product.weight_kg,
            "height_cm": product.height_cm,
            "width_cm": product.width_cm,
            "depth_cm": product.depth_cm,
            "maintenance_interval_days": product.maintenance_interval_days,
            "power_consumption_watts": product.power_consumption_watts,
            "daily_rate": product.daily_rate,
        } if product else None,
        "location_details": {
            "id": zone.id,
            "code": zone.code,
            "name": zone.name,
            "zone_type": zone.zone_type,
            "parent_id": zone.parent_id,
            "sort_order": zone.sort_order,
            "is_active": zone.is_active,
        } if zone else None,
        "maintenance_details": [
            {
                "id": row.id,
                "maintenance_type": row.maintenance_type,
                "status": row.status,
                "interval_mode": row.interval_mode,
                "interval_value": row.interval_value,
                "due_usage_hours": row.due_usage_hours,
                "scheduled_date": row.scheduled_date,
                "completed_date": row.completed_date,
                "notes": row.notes,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in maintenance_records
        ],
    }


def _record_scan_audit(
    db: Session,
    *,
    action: str,
    scan_code: str | None,
    success: bool,
    message: str,
    user_id: int | None,
    device_id: int | None = None,
    product_id: int | None = None,
    zone_id: int | None = None,
    job_id: int | None = None,
    details: dict[str, Any] | None = None,
    suppress_event: bool = False,
) -> None:
    db.add(
        InventoryAuditLog(
            source="scan",
            action=action,
            success=success,
            message=message,
            scan_code=scan_code,
            user_id=user_id,
            device_id=device_id,
            product_id=product_id,
            zone_id=zone_id,
            job_id=job_id,
            details_json=json.dumps(details, ensure_ascii=True) if details else None,
        )
    )
    if not suppress_event:
        emit_realtime_event(
            "inventory.scan",
            {
                "action": action,
                "success": success,
                "message": message,
                "device_id": device_id,
                "product_id": product_id,
                "zone_id": zone_id,
                "job_id": job_id,
            },
        )


def _to_inventory_audit_read(db: Session, row: InventoryAuditLog) -> InventoryAuditRead:
    product = db.get(Product, row.product_id) if row.product_id else None
    zone = db.get(Zone, row.zone_id) if row.zone_id else None
    job = db.get(Job, row.job_id) if row.job_id else None

    details = None
    if row.details_json:
        try:
            details = json.loads(row.details_json)
        except json.JSONDecodeError:
            details = {"raw": row.details_json}

    return InventoryAuditRead(
        id=row.id,
        created_at=row.created_at,
        user_id=row.user_id,
        source=row.source,
        action=row.action,
        success=row.success,
        message=row.message,
        scan_code=row.scan_code,
        device_id=row.device_id,
        product_id=row.product_id,
        product_name=product.name if product else None,
        zone_id=row.zone_id,
        zone_name=zone.name if zone else None,
        job_id=row.job_id,
        job_code=job.job_code if job else None,
        details=details,
    )


def _normalize_zone_sibling_sort_orders(db: Session, parent_id: int | None) -> None:
    siblings = list(
        db.scalars(
            select(Zone)
            .where(Zone.parent_id == parent_id)
            .order_by(Zone.sort_order, Zone.id)
        ).all()
    )
    for idx, sibling in enumerate(siblings):
        sibling.sort_order = idx


def _to_product_read(db: Session, product: Product) -> ProductRead:
    total_devices = db.scalar(select(func.count()).select_from(Device).where(Device.product_id == product.id)) or 0
    in_store_devices = db.scalar(
        select(func.count()).select_from(Device)
        .where(Device.product_id == product.id)
        .where(Device.status.in_(["available", "reserved", "maintenance"]))
    ) or 0
    on_site_devices = db.scalar(
        select(func.count()).select_from(Device)
        .where(Device.product_id == product.id)
        .where(Device.status == "in_use")
    ) or 0
    damaged_devices = db.scalar(
        select(func.count()).select_from(Device)
        .where(Device.product_id == product.id)
        .where(Device.condition == "damaged")
    ) or 0
    accessories = list(
        db.scalars(
            select(ProductAccessory)
            .where(ProductAccessory.parent_product_id == product.id)
            .order_by(ProductAccessory.required.desc(), ProductAccessory.id)
        ).all()
    )
    components = list(
        db.scalars(
            select(ProductComponent)
            .where(ProductComponent.parent_product_id == product.id)
            .order_by(ProductComponent.id)
        ).all()
    )
    eventory_packlists: list[dict[str, object]] = []
    if product.eventory_packlists_json:
        try:
            parsed = json.loads(product.eventory_packlists_json)
            if isinstance(parsed, list):
                eventory_packlists = [item for item in parsed if isinstance(item, dict)]
        except Exception:
            eventory_packlists = []

    return ProductRead.model_validate(
        {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "category": product.category,
            "category_id": product.category_id,
            "brand": product.brand,
            "manufacturer": product.manufacturer,
            "product_type": product.product_type,
            "is_rental_product": product.is_rental_product,
            "supplier_name": product.supplier_name,
            "rental_price": product.rental_price,
            "external_source": product.external_source,
            "external_reference": product.external_reference,
            "weight_kg": product.weight_kg,
            "height_cm": product.height_cm,
            "width_cm": product.width_cm,
            "depth_cm": product.depth_cm,
            "maintenance_interval_days": product.maintenance_interval_days,
            "power_consumption_watts": product.power_consumption_watts,
            "daily_rate": product.daily_rate,
            "replace_cost": product.replace_cost,
            "eventory_available_qty": product.eventory_available_qty,
            "created_at": product.created_at,
            "total_devices": int(total_devices),
            "in_store_devices": int(in_store_devices),
            "on_site_devices": int(on_site_devices),
            "damaged_devices": int(damaged_devices),
            "eventory_packlists": eventory_packlists,
            "accessories": [_to_product_accessory_read(db, row) for row in accessories],
            "components": [_to_product_component_read(db, row) for row in components],
        }
    )


def _generate_next_product_sku(db: Session, prefix: str = "PRD-") -> str:
    existing_skus = db.scalars(select(Product.sku).where(Product.sku.like(f"{prefix}%"))).all()
    max_number = 0
    width = 4

    for sku in existing_skus:
        if not sku:
            continue
        suffix = str(sku)[len(prefix):]
        if not suffix.isdigit():
            continue
        max_number = max(max_number, int(suffix))
        width = max(width, len(suffix))

    return f"{prefix}{max_number + 1:0{width}d}"


def _generate_asset_tag(db: Session, product: Product | None = None, preferred_prefix: str | None = None) -> str:
    base_prefix = preferred_prefix or (product.sku if product is not None else None) or "ASSET"
    prefix = base_prefix.strip().upper()
    prefix = prefix.rstrip("-")
    if not prefix:
        prefix = "ASSET"

    existing_tags = list(
        db.scalars(select(Device.asset_tag).where(Device.asset_tag.like(f"{prefix}-%"))).all()
    )

    max_idx = 0
    for tag in existing_tags:
        if not tag:
            continue
        suffix = str(tag).rsplit("-", 1)
        if len(suffix) == 2 and suffix[1].isdigit():
            max_idx = max(max_idx, int(suffix[1]))

    next_idx = max_idx + 1
    while True:
        candidate = f"{prefix}-{next_idx:03d}"
        exists = db.scalar(select(Device.id).where(Device.asset_tag == candidate))
        if not exists:
            return candidate
        next_idx += 1
