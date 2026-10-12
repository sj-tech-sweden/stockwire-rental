"""Pydantic schemas for the best-purchase / supplier-comparison feature."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class PurchaseDraftLineRead(BaseModel):
    id: int
    draft_id: int
    vendor_id: int | None = None
    vendor_name: str | None = None
    vendor_product_id: int | None = None
    requirement_id: int | None = None
    product_id: int | None = None
    product_name: str | None = None
    qty: int
    unit_cost: float | None = None
    currency: str | None = None
    converted_unit_cost: float | None = None
    line_total: float | None = None
    is_selected_cheapest: bool

    model_config = {"from_attributes": True}


class PurchaseDraftRead(BaseModel):
    id: int
    job_id: int
    status: str
    report_currency: str
    total_base: float | None = None
    supplier_count: int
    meta_json: str | None = None
    lines: list[PurchaseDraftLineRead]

    model_config = {"from_attributes": True}


class BestPurchaseRequest(BaseModel):
    report_currency: str | None = None
    strategy: str = "multi"  # "multi" (cheapest across vendors) or "single" (one vendor)


class BestPurchaseResponse(BaseModel):
    draft_id: int
    job_id: int
    report_currency: str
    fx_base: str
    lines: list[dict[str, Any]]
    single_supplier: dict[str, Any] | None = None
    multi_supplier: dict[str, Any]


class PurchaseOrderLineRead(BaseModel):
    id: int
    po_id: int
    vendor_id: int | None = None
    vendor_product_id: int | None = None
    product_id: int | None = None
    requirement_id: int | None = None
    job_id: int | None = None
    description: str | None = None
    sku: str | None = None
    name: str | None = None
    qty: int
    received_qty: int = 0
    unit_cost: float | None = None
    currency: str | None = None
    converted_unit_cost: float | None = None
    line_total: float | None = None
    is_manual: bool = False
    is_restock: bool = False
    creates_device: bool = True

    model_config = {"from_attributes": True}


class POLineUpdateRequest(BaseModel):
    qty: int | None = None
    unit_cost: float | None = None
    currency: str | None = None
    name: str | None = None
    description: str | None = None
    sku: str | None = None


class PurchaseOrderRead(BaseModel):
    id: int
    po_number: str
    supplier_company_id: int | None = None
    supplier_name: str | None = None
    status: str
    order_date: datetime | None = None
    expected_delivery_date: datetime | None = None
    report_currency: str
    total_base: float | None = None
    freight_cost: float | None = None
    freight_currency: str | None = None
    freight_base: float | None = None
    grand_total_base: float | None = None
    meta_json: str | None = None
    created_at: datetime | None = None
    lines: list[PurchaseOrderLineRead]

    model_config = {"from_attributes": True}


class CombinedPORequest(BaseModel):
    job_ids: list[int] = []
    include_restock: bool = False
    extra_items: list["ManualPOItem"] = []


class BuildPOSelection(BaseModel):
    requirement_id: int
    vendor_product_id: int
    qty: int | None = None


class BuildPORequest(BaseModel):
    lines: list[BuildPOSelection] = []
    extra_items: list["ManualPOItem"] = []
    include_restock: bool = False
    freight: dict[int, float] | None = None


class PreviewPORequest(BaseModel):
    job_ids: list[int] = []
    include_restock: bool = False


class AddToPORequest(BaseModel):
    lines: list[BuildPOSelection] = []
    extra_items: list["ManualPOItem"] = []
    freight: dict[int, float] | None = None


class ManualPOItem(BaseModel):
    name: str
    description: str | None = None
    qty: int = 1
    unit_cost: float | None = None
    currency: str | None = None
    vendor_company_id: int | None = None
    vendor_product_id: int | None = None
    product_id: int | None = None
    sku: str | None = None
    supplier_name: str | None = None
    is_restock: bool = False


class ReceiveDeviceFields(BaseModel):
    """Per-unit device details captured at receipt (scan or manual entry)."""

    serial_number: str | None = None
    asset_tag: str | None = None
    barcode: str | None = None
    condition: str = "new"
    status: str = "available"
    location_zone_id: int | None = None
    purchase_price: Decimal | None = None
    notes: str | None = None


class ReceivePOLineItem(BaseModel):
    line_id: int
    received_qty: int
    devices: list[ReceiveDeviceFields] | None = None
    default_condition: str = "new"
    default_status: str = "available"
    default_location_zone_id: int | None = None
    purchase_date: date | None = None
    notes: str | None = None
    serials: list[str] | None = None


class ReceivePORequest(BaseModel):
    lines: list[ReceivePOLineItem]


class ReceivingLineRead(BaseModel):
    po_id: int
    po_number: str
    line_id: int
    product_id: int | None = None
    name: str | None = None
    sku: str | None = None
    qty: int
    received_qty: int
    remaining: int
    unit_cost: Decimal | None = None
    currency: str | None = None
    creates_device: bool = True

    model_config = {"from_attributes": True}


class ReceivingLookupRead(BaseModel):
    product: "dict | None" = None
    lines: list[ReceivingLineRead] = []


class POUpdateRequest(BaseModel):
    status: str | None = None
    order_date: str | None = None
    expected_delivery_date: str | None = None
    supplier_company_id: int | None = None


# Re-evaluate forward refs now that ManualPOItem is defined.
CombinedPORequest.model_rebuild()
