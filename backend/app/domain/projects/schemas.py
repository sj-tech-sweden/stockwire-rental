from datetime import date, datetime

from pydantic import BaseModel

from app.domain.shared_schemas import ProductionPlannerSyncResponse  # noqa: F401


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
    productionplanner_project_id: str | None = None

    model_config = {"from_attributes": True}
