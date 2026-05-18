from datetime import date, datetime

from pydantic import BaseModel


class JobBase(BaseModel):
    job_code: str
    customer_name: str
    status: str = "draft"
    start_date: date | None = None
    end_date: date | None = None


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    job_code: str | None = None
    customer_name: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class JobRead(JobBase):
    id: int
    created_at: datetime

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
