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
    notification_channel: str
    auth_source: str
    external_provider: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    is_active: bool = True
    role: Literal["admin", "manager", "viewer"] = "viewer"
    notification_channel: Literal["email", "web_push", "both", "none"] = "both"


class UserLogin(BaseModel):
    email: str
    password: str


class UserSelfUpdate(BaseModel):
    email: EmailStr
    full_name: str
    password: str | None = None
    notification_channel: Literal["email", "web_push", "both", "none"] = "both"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary
    refresh_token: str | None = None


class SSOProviderSummary(BaseModel):
    provider: str
    kind: Literal["oidc", "saml"]
    display_name: str
    enabled: bool
    auto_create_users: bool


class OIDCExchangeRequest(BaseModel):
    provider: str
    code: str
    redirect_uri: str


class SAMLAssertionRequest(BaseModel):
    provider: str
    saml_response: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
