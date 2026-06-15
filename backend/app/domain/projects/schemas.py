from datetime import date, datetime

from pydantic import BaseModel


class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    customer_id: int | None = None
    venue_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    status: str = "active"


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    customer_id: int | None = None
    venue_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    status: str | None = None


class ProjectRead(ProjectBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
