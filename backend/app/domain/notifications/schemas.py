"""Notification Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
    user_agent: str | None = None


class NotificationTemplateCreate(BaseModel):
    template_key: str
    locale: str = "en"
    recipient_type: str = "both"  # "customer" | "staff" | "both"
    subject_template: str | None = None
    html_template: str | None = None
    text_template: str | None = None
    is_enabled: bool = True


class NotificationTemplateUpdate(BaseModel):
    recipient_type: str | None = None
    subject_template: str | None = None
    html_template: str | None = None
    text_template: str | None = None
    is_enabled: bool | None = None


class NotificationTemplateRead(BaseModel):
    id: int
    template_key: str
    locale: str
    recipient_type: str
    subject_template: str | None = None
    html_template: str | None = None
    text_template: str | None = None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class NotificationPreferenceRead(BaseModel):
    id: int
    event_type: str
    label: str
    description: str | None = None
    email_enabled: bool
    web_push_enabled: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: bool | None = None
    web_push_enabled: bool | None = None


class MyNotificationPreferenceRead(BaseModel):
    """A user's effective preference for one event type.

    `is_override` is True when the user has set their own override; otherwise the
    values reflect the global default.
    """

    event_type: str
    label: str
    description: str | None = None
    email_enabled: bool
    web_push_enabled: bool
    is_override: bool

    model_config = {"from_attributes": True}


class MyNotificationPreferenceUpdate(BaseModel):
    email_enabled: bool
    web_push_enabled: bool


class NotificationLogRead(BaseModel):
    id: int
    job_id: int | None = None
    recipient_id: int
    recipient_type: str
    channel: str
    template_key: str
    locale: str | None = None
    status: str
    error_message: str | None = None
    sent_at: datetime

    model_config = {"from_attributes": True}


class NotificationDispatchRequest(BaseModel):
    template_key: str
    recipient_id: int
    recipient_type: str  # "customer" | "staff"
    channel: str  # "email" | "web_push" | "both"
    job_id: int | None = None
    context: dict = {}
    event_type: str | None = None
