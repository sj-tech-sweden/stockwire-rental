from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ProductBase(BaseModel):
    sku: str
    name: str
    category: str = "general"
    daily_rate: Decimal = Decimal("0.00")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    category: str | None = None
    daily_rate: Decimal | None = None


class ProductRead(ProductBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceBase(BaseModel):
    product_id: int
    asset_tag: str
    serial_number: str | None = None
    status: str = "available"
    notes: str | None = None


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    product_id: int | None = None
    asset_tag: str | None = None
    serial_number: str | None = None
    status: str | None = None
    notes: str | None = None


class DeviceRead(DeviceBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ZoneBase(BaseModel):
    code: str
    name: str
    zone_type: str = "rack"
    parent_id: int | None = None


class ZoneCreate(ZoneBase):
    pass


class ZoneUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    zone_type: str | None = None
    parent_id: int | None = None


class ZoneRead(ZoneBase):
    id: int

    model_config = {"from_attributes": True}
