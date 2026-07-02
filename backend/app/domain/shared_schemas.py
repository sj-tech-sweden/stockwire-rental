from pydantic import BaseModel


class ProductionPlannerSyncResponse(BaseModel):
    success: bool
    message: str
    productionplanner_project_id: str | None = None
    productionplanner_url: str | None = None
