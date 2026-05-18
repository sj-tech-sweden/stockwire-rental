from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserSummary(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password_hash: str
    full_name: str
    is_active: bool = True
    is_admin: bool = False
