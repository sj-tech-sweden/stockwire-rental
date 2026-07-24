from datetime import datetime

from pydantic import BaseModel


class CustomerBase(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    notes: str | None = None
    external_source: str | None = None
    external_reference: str | None = None
    is_customer: bool = True
    is_product_supplier: bool = False
    is_rental_supplier: bool = False
    is_crew_supplier: bool = False


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    notes: str | None = None
    external_source: str | None = None
    external_reference: str | None = None
    is_customer: bool | None = None
    is_product_supplier: bool | None = None
    is_rental_supplier: bool | None = None
    is_crew_supplier: bool | None = None


class CustomerRead(CustomerBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
