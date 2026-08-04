from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
    user_agent: str | None = None


class PushSubscriptionRead(BaseModel):
    id: int
    endpoint: str
    user_agent: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationTemplateBase(BaseModel):
    template_key: str
    subject_template: str | None = None
    html_template: str | None = None
    text_template: str | None = None


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateUpdate(BaseModel):
    subject_template: str | None = None
    html_template: str | None = None
    text_template: str | None = None


class NotificationTemplateRead(NotificationTemplateBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationLogRead(BaseModel):
    id: int
    job_id: int | None = None
    recipient_id: int
    recipient_type: Literal["customer", "staff"]
    channel: Literal["email", "web_push"]
    template_key: str
    status: Literal["sent", "failed", "skipped_by_preference"]
    error_message: str | None = None
    sent_at: datetime

    model_config = {"from_attributes": True}


class NotificationDispatchRequest(BaseModel):
    template_key: str
    recipient_type: Literal["customer", "staff"]
    recipient_id: int
    channel: Literal["email", "web_push", "both"]
    job_id: int | None = None
    context: dict = {}


class NotificationDispatchResponse(BaseModel):
    results: list[NotificationLogRead]


class VapidPublicKeyRead(BaseModel):
    public_key: str
