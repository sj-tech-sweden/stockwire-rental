from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


# ── Letterhead Schemas ──────────────────────────────────────────────────────


class LetterheadBase(BaseModel):
    name: str
    is_default: bool = False
    margin_top_mm: Decimal = Decimal("20.0")
    margin_bottom_mm: Decimal = Decimal("20.0")
    margin_left_mm: Decimal = Decimal("20.0")
    margin_right_mm: Decimal = Decimal("20.0")


class LetterheadCreate(LetterheadBase):
    asset_file_id: int | None = None
    page_count: int = 1


class LetterheadUpdate(BaseModel):
    name: str | None = None
    is_default: bool | None = None
    asset_file_id: int | None = None
    page_count: int | None = None
    margin_top_mm: Decimal | None = None
    margin_bottom_mm: Decimal | None = None
    margin_left_mm: Decimal | None = None
    margin_right_mm: Decimal | None = None


class LetterheadRead(LetterheadBase):
    id: int
    asset_file_id: int | None = None
    page_count: int = 1
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Report Template Schemas ─────────────────────────────────────────────────


class ReportTemplateBase(BaseModel):
    name: str
    category: str
    description: str | None = None
    letterhead_id: int | None = None
    body_json: str = "{}"
    translations_json: str | None = None
    data_source_type: str = "job"
    is_enabled: bool = True


class ReportTemplateCreate(ReportTemplateBase):
    pass


class ReportTemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    letterhead_id: int | None = None
    body_json: str | None = None
    translations_json: str | None = None
    data_source_type: str | None = None
    is_enabled: bool | None = None


class ReportTemplateRead(ReportTemplateBase):
    id: int
    is_builtin: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportTemplateListRead(BaseModel):
    id: int
    name: str
    category: str
    description: str | None = None
    data_source_type: str
    is_builtin: bool = False
    is_enabled: bool = True
    translations_json: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Generation Schemas ──────────────────────────────────────────────────────


class ReportGenerateRequest(BaseModel):
    template_id: int
    entity_type: str
    entity_id: int
    format: str = "pdf"
    language: str = "en"

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        allowed = {"pdf", "html", "csv"}
        if v not in allowed:
            raise ValueError(f"Format must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        value = str(v or "en").strip().lower()
        if not value or len(value) > 10:
            raise ValueError("Language must be a short locale code such as 'en' or 'sv'")
        return value


class GeneratedReportLogRead(BaseModel):
    id: int
    template_id: int | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    asset_file_id: int | None = None
    generated_by_user_id: int | None = None
    format: str = "pdf"
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Data Source Schema ──────────────────────────────────────────────────────


class DataSourceField(BaseModel):
    key: str
    label: str
    type: str = "string"


class DataSourceSchemaResponse(BaseModel):
    entity_type: str
    fields: list[DataSourceField] = Field(default_factory=list)
