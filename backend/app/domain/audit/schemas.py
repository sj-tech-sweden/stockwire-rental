from datetime import datetime

from pydantic import BaseModel


class ActivityLogRead(BaseModel):
    id: int
    created_at: datetime
    user_id: int | None = None
    user_full_name: str | None = None
    entity_type: str
    entity_id: int | None = None
    action: str
    message: str
    message_format: str | None = None
    message_params: dict | None = None
    details: dict | None = None
