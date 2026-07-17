from datetime import datetime

from pydantic import BaseModel


class TwentyConfigBase(BaseModel):
    api_key: str
    base_url: str = "https://api.twenty.com"
    workspace_id: str | None = None
    is_active: bool = True


class TwentyConfigCreate(TwentyConfigBase):
    pass


class TwentyConfigUpdate(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    workspace_id: str | None = None
    is_active: bool | None = None


class TwentyConfigRead(BaseModel):
    id: int
    base_url: str = "https://api.twenty.com"
    workspace_id: str | None = None
    is_active: bool = True
    has_api_key: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TwentyTestResult(BaseModel):
    success: bool
    message: str
    workspace_name: str | None = None


class TwentySyncLogRead(BaseModel):
    id: int
    direction: str
    entity_type: str
    entity_id: int | None = None
    twenty_id: str | None = None
    operation: str
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TwentySyncStatus(BaseModel):
    is_configured: bool
    last_sync_at: datetime | None = None
    total_synced: int = 0
    total_failed: int = 0
    recent_logs: list[TwentySyncLogRead] = []


class TwentySyncTrigger(BaseModel):
    direction: str = "outbound"  # "outbound", "inbound", "both"
    entity_types: list[str] | None = None  # None = all
