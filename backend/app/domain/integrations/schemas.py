from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_TWENTY_SYNC_INTERVALS = {0, 15, 30, 60, 120, 240, 480, 1440}


class TwentyConfigBase(BaseModel):
    api_key: str
    base_url: str = "https://api.twenty.com"
    workspace_id: str | None = None
    is_active: bool = True
    sync_interval_minutes: int = Field(default=0, ge=0)

    @field_validator("api_key")
    @classmethod
    def api_key_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("API key must not be empty")
        return v.strip()

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_valid(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v

    @field_validator("sync_interval_minutes")
    @classmethod
    def sync_interval_must_be_valid(cls, v: int) -> int:
        if v not in ALLOWED_TWENTY_SYNC_INTERVALS:
            raise ValueError(
                f"Invalid sync interval. Allowed values: {sorted(ALLOWED_TWENTY_SYNC_INTERVALS)}"
            )
        return v


class TwentyConfigCreate(TwentyConfigBase):
    pass


class TwentyConfigUpdate(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    workspace_id: str | None = None
    is_active: bool | None = None
    sync_interval_minutes: int | None = None
    clear_api_key: bool = False

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v

    @field_validator("sync_interval_minutes")
    @classmethod
    def sync_interval_must_be_valid(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v not in ALLOWED_TWENTY_SYNC_INTERVALS:
            raise ValueError(
                f"Invalid sync interval. Allowed values: {sorted(ALLOWED_TWENTY_SYNC_INTERVALS)}"
            )
        return v


class TwentyConfigRead(BaseModel):
    id: int
    base_url: str = "https://api.twenty.com"
    workspace_id: str | None = None
    is_active: bool = True
    has_api_key: bool = False
    sync_interval_minutes: int = 0
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
    next_sync_at: datetime | None = None
    sync_interval_minutes: int = 0
    total_synced: int = 0
    total_failed: int = 0
    recent_logs: list[TwentySyncLogRead] = []


class TwentySyncTrigger(BaseModel):
    direction: Literal["outbound", "inbound", "both"] = "outbound"
    entity_types: list[str] | None = None  # None = all

    @field_validator("entity_types")
    @classmethod
    def validate_entity_types(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            valid = {"customer", "job"}
            invalid = set(v) - valid
            if invalid:
                raise ValueError(f"Invalid entity types: {', '.join(sorted(invalid))}. Valid: {', '.join(sorted(valid))}")
        return v
