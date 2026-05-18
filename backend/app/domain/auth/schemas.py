from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

VALID_ROLES = {"admin", "manager", "viewer"}


class UserSummary(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    is_active: bool = True
    role: Literal["admin", "manager", "viewer"] = "viewer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary
