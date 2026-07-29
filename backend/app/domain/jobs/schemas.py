from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class JobBase(BaseModel):
    job_code: str
    project_id: int | None = None
    location_in_venue: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None
    venue_id: int | None = None
    venue_name: str | None = None
    description: str | None = None
    status: str = "draft"
    start_date: date | None = None
    end_date: date | None = None
    sales_price: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    invoice_paid: bool = False
    invoice_paid_at: date | None = None
    notes: str | None = None


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    job_code: str | None = None
    project_id: int | None = None
    location_in_venue: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None
    venue_id: int | None = None
    venue_name: str | None = None
    description: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    sales_price: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    invoice_paid: bool | None = None
    invoice_paid_at: date | None = None
    notes: str | None = None


class JobRead(JobBase):
    id: int
    created_at: datetime
    productionplanner_project_id: str | None = None
    external_source: str | None = None
    external_reference: str | None = None
    eventory_job_ids: str | None = None

    model_config = {"from_attributes": True}


class JobRequirementBase(BaseModel):
    job_id: int
    product_id: int
    quantity_required: int = 1
    quantity_picked: int = 0
    notes: str | None = None


class JobRequirementCreate(JobRequirementBase):
    pass


class JobRequirementUpdate(BaseModel):
    job_id: int | None = None
    product_id: int | None = None
    quantity_required: int | None = None
    quantity_picked: int | None = None
    notes: str | None = None


class JobRequirementRead(JobRequirementBase):
    id: int

    model_config = {"from_attributes": True}


class JobRequirementBulkItem(BaseModel):
    product_id: int
    quantity_required: int = 1
    quantity_picked: int = 0
    notes: str | None = None


class JobRequirementBulkUpsert(BaseModel):
    items: list[JobRequirementBulkItem]
