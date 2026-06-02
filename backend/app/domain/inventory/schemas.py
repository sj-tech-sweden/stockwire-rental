from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class InventoryCategoryBase(BaseModel):
    name: str
    parent_id: int | None = None
    sort_order: int = 0
    is_active: bool = True


class InventoryCategoryCreate(InventoryCategoryBase):
    pass


class InventoryCategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class InventoryCategoryMove(BaseModel):
    parent_id: int | None = None
    before_id: int | None = None


class InventoryCategoryRead(InventoryCategoryBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryCategoryTreeRead(BaseModel):
    id: int
    name: str
    parent_id: int | None = None
    sort_order: int = 0
    is_active: bool = True
    children: list["InventoryCategoryTreeRead"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProductBase(BaseModel):
    sku: str
    name: str
    category: str = "general"
    category_id: int | None = None
    brand: str | None = None
    manufacturer: str | None = None
    product_type: str = "equipment"
    is_rental_product: bool = False
    supplier_name: str | None = None
    rental_price: Decimal = Decimal("0.00")
    external_source: str | None = None
    external_reference: str | None = None
    eventory_available_qty: int = 0
    weight_kg: Decimal | None = None
    height_cm: Decimal | None = None
    width_cm: Decimal | None = None
    depth_cm: Decimal | None = None
    maintenance_interval_days: int | None = None
    power_consumption_watts: Decimal | None = None
    daily_rate: Decimal = Decimal("0.00")
    replace_cost: Decimal | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    category: str | None = None
    category_id: int | None = None
    brand: str | None = None
    manufacturer: str | None = None
    product_type: str | None = None
    is_rental_product: bool | None = None
    supplier_name: str | None = None
    rental_price: Decimal | None = None
    external_source: str | None = None
    external_reference: str | None = None
    eventory_available_qty: int | None = None
    weight_kg: Decimal | None = None
    height_cm: Decimal | None = None
    width_cm: Decimal | None = None
    depth_cm: Decimal | None = None
    maintenance_interval_days: int | None = None
    power_consumption_watts: Decimal | None = None
    daily_rate: Decimal | None = None
    replace_cost: Decimal | None = None


class ProductBulkUpdateRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
    patch: ProductUpdate

    @model_validator(mode="after")
    def validate_ids(self):
        if not self.ids:
            raise ValueError("At least one id is required")
        return self


class BulkDeleteRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ids(self):
        if not self.ids:
            raise ValueError("At least one id is required")
        return self


class BulkOperationResult(BaseModel):
    updated: int = 0
    deleted: int = 0
    skipped: int = 0


class ProductRead(ProductBase):
    id: int
    created_at: datetime
    total_devices: int = 0
    in_store_devices: int = 0
    on_site_devices: int = 0
    damaged_devices: int = 0
    eventory_packlists: list[dict[str, object]] = Field(default_factory=list)
    accessories: list["ProductAccessoryRead"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class DeviceBase(BaseModel):
    product_id: int
    asset_tag: str | None = None
    serial_number: str | None = None
    barcode: str | None = None
    qr_code: str | None = None
    rfid: str | None = None
    location_zone_id: int | None = None
    case_device_id: int | None = None
    status: str = "available"
    condition: str = "good"
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    purchased_from: str | None = None
    sold_price: Decimal | None = None
    finance_upto: str | None = None
    finance_company: str | None = None
    finance_ref: str | None = None
    pre_prep: str | None = None
    warranty_end_date: date | None = None
    retire_date: date | None = None
    usage_hours: Decimal | None = None
    notes: str | None = None


class DeviceCreate(DeviceBase):
    pass


class ProductDevicesBulkCreate(BaseModel):
    quantity: int = Field(default=1, ge=1, le=500)
    auto_generate: bool = True
    asset_tag: str | None = None
    asset_tag_prefix: str | None = None
    location_zone_id: int | None = None
    status: str = "available"
    condition: str = "good"
    notes: str | None = None


class DeviceUpdate(BaseModel):
    product_id: int | None = None
    asset_tag: str | None = None
    serial_number: str | None = None
    barcode: str | None = None
    qr_code: str | None = None
    rfid: str | None = None
    location_zone_id: int | None = None
    case_device_id: int | None = None
    status: str | None = None
    condition: str | None = None
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    purchased_from: str | None = None
    sold_price: Decimal | None = None
    finance_upto: str | None = None
    finance_company: str | None = None
    finance_ref: str | None = None
    pre_prep: str | None = None
    warranty_end_date: date | None = None
    retire_date: date | None = None
    usage_hours: Decimal | None = None
    notes: str | None = None


class DeviceBulkUpdateRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
    patch: DeviceUpdate

    @model_validator(mode="after")
    def validate_ids(self):
        if not self.ids:
            raise ValueError("At least one id is required")
        return self


class DeviceRead(DeviceBase):
    id: int
    created_at: datetime
    case_asset_tag: str | None = None
    current_job_id: int | None = None
    current_job_code: str | None = None

    model_config = {"from_attributes": True}


class ProductAccessoryRead(BaseModel):
    id: int
    parent_product_id: int
    accessory_product_id: int
    accessory_sku: str | None = None
    accessory_name: str | None = None
    quantity: int = 1
    required: bool = False


class ProductAccessoryUpsertItem(BaseModel):
    accessory_product_id: int
    quantity: int = 1
    required: bool = False


class ProductAccessoryUpsertRequest(BaseModel):
    items: list[ProductAccessoryUpsertItem] = Field(default_factory=list)


MAINTENANCE_STATUSES = ["scheduled", "in_progress", "completed", "canceled"]
MAINTENANCE_INTERVAL_MODES = ["calendar", "runtime"]
MAINTENANCE_TYPES = ["inspection", "cleaning", "repair", "calibration", "pat_test", "scheduled"]
DEFECT_STATUSES = ["open", "in_progress", "resolved", "closed"]
DEFECT_SEVERITIES = ["low", "medium", "high", "critical"]


class DeviceMaintenanceBase(BaseModel):
    device_id: int
    maintenance_type: str = "inspection"
    status: str = "scheduled"
    interval_mode: str = "calendar"
    interval_value: int | None = None
    due_usage_hours: Decimal | None = None
    scheduled_date: date | None = None
    completed_date: date | None = None
    notes: str | None = None


class DeviceMaintenanceCreate(DeviceMaintenanceBase):
    pass


class DeviceMaintenanceUpdate(BaseModel):
    device_id: int | None = None
    maintenance_type: str | None = None
    status: str | None = None
    interval_mode: str | None = None
    interval_value: int | None = None
    due_usage_hours: Decimal | None = None
    scheduled_date: date | None = None
    completed_date: date | None = None
    notes: str | None = None


class DeviceMaintenanceBulkUpdateRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
    patch: DeviceMaintenanceUpdate

    @model_validator(mode="after")
    def validate_ids(self):
        if not self.ids:
            raise ValueError("At least one id is required")
        return self


class DeviceMaintenanceComplete(BaseModel):
    completed_date: date | None = None
    notes: str | None = None


class DeviceMaintenanceRead(DeviceMaintenanceBase):
    id: int
    schedule_id: int | None = None
    created_at: datetime
    updated_at: datetime
    product_id: int | None = None
    product_name: str | None = None
    asset_tag: str | None = None

    model_config = {"from_attributes": True}


class MaintenanceBulkScheduleRequest(BaseModel):
    device_ids: list[int] = Field(default_factory=list)
    product_ids: list[int] = Field(default_factory=list)
    maintenance_type: str = "inspection"
    interval_mode: str = "calendar"
    interval_value: int | None = None
    scheduled_date: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_targets(self):
        if not self.device_ids and not self.product_ids:
            raise ValueError("At least one device or product target is required")
        return self


class MaintenanceScheduleRead(BaseModel):
    id: int
    maintenance_type: str
    interval_mode: str
    interval_value: int | None = None
    scheduled_date: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class MaintenanceScheduleUpdate(BaseModel):
    maintenance_type: str | None = None
    interval_mode: str | None = None
    interval_value: int | None = None
    scheduled_date: date | None = None
    notes: str | None = None


class MaintenanceScheduleBulkUpdateRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
    patch: MaintenanceScheduleUpdate

    @model_validator(mode="after")
    def validate_ids(self):
        if not self.ids:
            raise ValueError("At least one id is required")
        return self


class DefectReportBase(BaseModel):
    device_id: int
    maintenance_id: int | None = None
    title: str
    description: str | None = None
    status: str = "open"
    severity: str = "medium"


class DefectReportCreate(DefectReportBase):
    pass


class DefectReportUpdate(BaseModel):
    device_id: int | None = None
    maintenance_id: int | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    severity: str | None = None


class DefectReportRead(DefectReportBase):
    id: int
    created_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime
    asset_tag: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    maintenance_type: str | None = None

    model_config = {"from_attributes": True}


class DefectCommentBase(BaseModel):
    comment: str


class DefectCommentCreate(DefectCommentBase):
    pass


class DefectCommentUpdate(BaseModel):
    comment: str | None = None


class DefectCommentRead(DefectCommentBase):
    id: int
    defect_report_id: int
    created_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DefectTimelineEntry(BaseModel):
    id: str
    entry_type: str
    created_at: datetime
    updated_at: datetime
    defect_report_id: int
    device_id: int
    maintenance_id: int | None = None
    status: str | None = None
    severity: str | None = None
    title: str | None = None
    description: str | None = None
    comment: str | None = None
    created_by_user_id: int | None = None


class InventoryScanRequest(BaseModel):
    scan_code: str
    action: str = "lookup"
    zone_id: int | None = None
    case_device_id: int | None = None
    job_code: str | None = None
    maintenance_type: str | None = None
    interval_mode: str | None = None
    interval_value: int | None = None
    notes: str | None = None


class InventoryScanResponse(BaseModel):
    success: bool
    message: str
    action: str
    device_id: int | None = None
    asset_tag: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    job_id: int | None = None
    zone_id: int | None = None
    device_details: dict | None = None
    product_details: dict | None = None
    location_details: dict | None = None
    maintenance_details: list[dict] | None = None


class InventoryAuditRead(BaseModel):
    id: int
    created_at: datetime
    user_id: int | None = None
    source: str
    action: str
    success: bool
    message: str
    scan_code: str | None = None
    device_id: int | None = None
    product_id: int | None = None
    product_name: str | None = None
    zone_id: int | None = None
    zone_name: str | None = None
    job_id: int | None = None
    job_code: str | None = None
    details: dict | None = None


class InventoryCheckedOutDeviceRead(BaseModel):
    device_id: int
    asset_tag: str | None = None
    product_id: int
    product_name: str | None = None
    location_zone_id: int | None = None
    location_name: str | None = None
    condition: str | None = None
    status: str
    job_id: int | None = None
    job_code: str | None = None


class InventoryDeviceCheckoutRead(BaseModel):
    device_id: int
    status: str
    job_id: int | None = None
    job_code: str | None = None
    last_action: str | None = None


class ZoneBase(BaseModel):
    code: str
    name: str
    zone_type: str = "rack"
    barcode: str | None = None
    qr_code: str | None = None
    rfid: str | None = None
    parent_id: int | None = None
    sort_order: int = 0
    is_active: bool = True


class ZoneCreate(ZoneBase):
    pass


class ZoneUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    zone_type: str | None = None
    barcode: str | None = None
    qr_code: str | None = None
    rfid: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class ZoneMove(BaseModel):
    parent_id: int | None = None
    before_id: int | None = None


class ZoneRead(ZoneBase):
    id: int

    model_config = {"from_attributes": True}


class ZoneTreeRead(BaseModel):
    id: int
    code: str
    name: str
    zone_type: str = "rack"
    barcode: str | None = None
    qr_code: str | None = None
    rfid: str | None = None
    parent_id: int | None = None
    sort_order: int = 0
    is_active: bool = True
    children: list["ZoneTreeRead"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


ProductRead.model_rebuild()
