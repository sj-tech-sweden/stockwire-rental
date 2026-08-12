from datetime import date, datetime

from pydantic import BaseModel


class CustomerBase(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    notes: str | None = None
    external_source: str | None = None
    external_reference: str | None = None
    is_customer: bool = True
    is_product_supplier: bool = False
    is_rental_supplier: bool = False
    is_crew_supplier: bool = False
    email_notifications_enabled: bool = True
    preferred_language: str | None = "en"


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    notes: str | None = None
    external_source: str | None = None
    external_reference: str | None = None
    is_customer: bool | None = None
    is_product_supplier: bool | None = None
    is_rental_supplier: bool | None = None
    is_crew_supplier: bool | None = None
    email_notifications_enabled: bool | None = None
    preferred_language: str | None = None


class CustomerRead(CustomerBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerJobSummary(BaseModel):
    id: int
    job_code: str
    status: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    venue_name: str | None = None


class CustomerProductSummary(BaseModel):
    id: int
    sku: str
    name: str
    product_type: str | None = None
    is_rental_product: bool = False
    rental_price: float = 0
    daily_rate: float = 0
    category: str | None = None


class CustomerCrewMemberSummary(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    user_id: int | None = None
    supplier_id: int | None = None
    hourly_rate: float | None = None
    daily_rate: float | None = None
    is_active: bool = True
    skills: list[str] = []
    certifications: list[dict] = []
    preferred_role_ids: list[int] = []
    preferred_role_names: list[str] = []
    notes: str | None = None


class CustomerInfoRead(CustomerRead):
    jobs: list[CustomerJobSummary] = []
    supplied_products: list[CustomerProductSummary] = []
    crew_members: list[CustomerCrewMemberSummary] = []
