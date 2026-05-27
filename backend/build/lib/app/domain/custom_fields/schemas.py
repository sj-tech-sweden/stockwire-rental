from datetime import datetime

from pydantic import BaseModel, Field


class CustomFieldEntityTypes:
    PRODUCT = "product"
    JOB = "job"
    CUSTOMER = "customer"
    VENUE = "venue"

    ALL = {PRODUCT, JOB, CUSTOMER, VENUE}


class CustomFieldValueTypes:
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    SELECT = "select"

    ALL = {TEXT, NUMBER, BOOLEAN, DATE, SELECT}


class CustomFieldDefinitionBase(BaseModel):
    entity_type: str = Field(..., examples=["product"])
    key: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=255)
    value_type: str = Field(default=CustomFieldValueTypes.TEXT)
    options: list[str] = Field(default_factory=list)
    is_required: bool = False
    is_active: bool = True


class CustomFieldDefinitionCreate(CustomFieldDefinitionBase):
    pass


class CustomFieldDefinitionUpdate(BaseModel):
    key: str | None = Field(default=None, min_length=1, max_length=64)
    label: str | None = Field(default=None, min_length=1, max_length=255)
    value_type: str | None = None
    options: list[str] | None = None
    is_required: bool | None = None
    is_active: bool | None = None


class CustomFieldDefinitionRead(CustomFieldDefinitionBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomFieldValueUpsert(BaseModel):
    field_definition_id: int
    value: str | None = None


class CustomFieldValuesUpsertRequest(BaseModel):
    values: list[CustomFieldValueUpsert]


class CustomFieldValueRead(BaseModel):
    id: int | None = None
    field_definition_id: int
    key: str
    label: str
    value_type: str
    options: list[str] = Field(default_factory=list)
    value: str | None = None


class CustomFieldValuesRead(BaseModel):
    entity_type: str
    entity_id: int
    values: list[CustomFieldValueRead]
