from datetime import datetime

from pydantic import BaseModel


class CalendarFeedCreate(BaseModel):
    name: str
    feed_type: str  # "crew" or "jobs"
    crew_member_id: int | None = None


class CalendarFeedUpdate(BaseModel):
    name: str | None = None
    feed_type: str | None = None
    crew_member_id: int | None = None
    is_active: bool | None = None


class CalendarFeedRead(BaseModel):
    id: int
    name: str
    token: str
    feed_type: str
    crew_member_id: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
