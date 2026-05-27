from datetime import datetime

from pydantic import BaseModel


class VenueBase(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    notes: str | None = None


class VenueCreate(VenueBase):
    pass


class VenueUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    notes: str | None = None


class VenueRead(VenueBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}