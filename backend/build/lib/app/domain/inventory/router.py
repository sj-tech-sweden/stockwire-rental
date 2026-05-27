import json
from typing import Any
from datetime import date, timedelta

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_admin, require_editor
from app.domain.auth.models import User
from app.domain.audit.service import record_activity
from app.domain.inventory.models import Device, DeviceMaintenance, DeviceMaintenanceSchedule, InventoryAuditLog, InventoryCategory, Product, ProductAccessory, Zone
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
    InventoryAuditRead,
    ProductCreate,
    ProductDevicesBulkCreate,
    ProductBulkUpdateRequest,
    ProductRead,
    ProductUpdate,
    MAINTENANCE_STATUSES,
    MAINTENANCE_INTERVAL_MODES,
    MAINTENANCE_TYPES,
    ZoneCreate,
    ZoneMove,
    ZoneRead,
    ZoneTreeRead,
    ZoneUpdate,
)

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(get_current_user)])


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


@router.get("/products", response_model=list[ProductRead])
def list_products(db: Session = Depends(get_db)) -> list[ProductRead]:
    products = list(db.scalars(select(Product).order_by(Product.id)).all())
    return [_to_product_read(db, product) for product in products]


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
        message=f"Created product {product.sku} - {product.name}",
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
        message=f"Updated product {product.sku} - {product.name}",
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
            skipped += 1
            continue
        db.delete(row)
        deleted += 1

    db.commit()
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

        if action in {"job_out", "job_in"}:
            if action == "job_out":
                job = _resolve_job_for_scan(db, payload.job_code)
            else:
                candidate_job_code = (payload.job_code or "").strip()
                job = _resolve_job_for_scan(db, candidate_job_code) if candidate_job_code else None

            target_devices = [device]
            if product and product.product_type == "case":
                target_devices = _collect_case_devices(db, device)

            if action == "job_out":
                picked_by_product: dict[int, int] = defaultdict(int)
                for target in target_devices:
                    _ensure_job_requirement(db, job.id, target.product_id)
                    picked_by_product[target.product_id] += 1
                    target.status = "in_use"

                for product_id, increment in picked_by_product.items():
                    req = db.scalar(
                        select(JobRequirement)
                        .where(JobRequirement.job_id == job.id)
                        .where(JobRequirement.product_id == product_id)
                    )
                    if req is not None:
                        req.quantity_picked = int(req.quantity_picked or 0) + int(increment)

                db.commit()
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
                db.commit()
                return response

            if job is not None:
                decremented_by_product: dict[int, int] = defaultdict(int)
                for target in target_devices:
                    decremented_by_product[target.product_id] += 1
                for product_id, decrement in decremented_by_product.items():
                    req = db.scalar(
                        select(JobRequirement)
                        .where(JobRequirement.job_id == job.id)
                        .where(JobRequirement.product_id == product_id)
                    )
                    if req is not None and req.quantity_picked > 0:
                        req.quantity_picked = max(int(req.quantity_picked or 0) - int(decrement), 0)

            for target in target_devices:
                target.status = "available"
            db.commit()
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
    allowed = {"equipment", "accessory", "consumable", "case", "rental"}
    if product_type not in allowed:
        raise HTTPException(status_code=400, detail="product_type must be one of: equipment, accessory, consumable, case, rental")


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


def _ensure_job_requirement(db: Session, job_id: int, product_id: int) -> None:
    existing = db.scalar(
        select(JobRequirement)
        .where(JobRequirement.job_id == job_id)
        .where(JobRequirement.product_id == product_id)
    )
    if existing is None:
        db.add(JobRequirement(job_id=job_id, product_id=product_id, quantity_required=1, quantity_picked=0))
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
            "status": device.status,
            "condition": device.condition,
            "purchase_date": device.purchase_date,
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
            "eventory_available_qty": product.eventory_available_qty,
            "created_at": product.created_at,
            "total_devices": int(total_devices),
            "in_store_devices": int(in_store_devices),
            "on_site_devices": int(on_site_devices),
            "damaged_devices": int(damaged_devices),
            "eventory_packlists": eventory_packlists,
            "accessories": [_to_product_accessory_read(db, row) for row in accessories],
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
