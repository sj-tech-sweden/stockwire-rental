from datetime import datetime

from pydantic import BaseModel


class AssetFileRead(BaseModel):
    id: int
    entity_type: str | None = None
    entity_id: int | None = None
    category: str | None = None
    original_filename: str
    content_type: str | None = None
    size_bytes: int
    storage_backend: str
    created_by_user_id: int | None = None
    created_at: datetime
    download_url: str


class CompanyProfileRead(BaseModel):
    company_name: str | None = None
    default_language: str | None = None
    logo_file_id: int | None = None
    logo_url: str | None = None
    logo_light_wide_file_id: int | None = None
    logo_light_wide_url: str | None = None
    logo_light_small_file_id: int | None = None
    logo_light_small_url: str | None = None
    logo_dark_wide_file_id: int | None = None
    logo_dark_wide_url: str | None = None
    logo_dark_small_file_id: int | None = None
    logo_dark_small_url: str | None = None
    currency: str | None = None
    vat_number: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None


class CompanyProfileUpdate(BaseModel):
    company_name: str | None = None
    default_language: str | None = None
    logo_file_id: int | None = None
    logo_light_wide_file_id: int | None = None
    logo_light_small_file_id: int | None = None
    logo_dark_wide_file_id: int | None = None
    logo_dark_small_file_id: int | None = None
    currency: str | None = None
    vat_number: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
