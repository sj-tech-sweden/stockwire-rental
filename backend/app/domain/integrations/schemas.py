from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class TwentyConfigBase(BaseModel):
    api_key: str
    base_url: str = "https://api.twenty.com"
    workspace_id: str | None = None
    is_active: bool = True

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


class TwentyConfigCreate(TwentyConfigBase):
    pass


class TwentyConfigUpdate(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    workspace_id: str | None = None
    is_active: bool | None = None
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
