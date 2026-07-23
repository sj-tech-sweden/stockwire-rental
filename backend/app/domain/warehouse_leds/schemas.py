from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LEDControllerBase(BaseModel):
    controller_id: str
    display_name: str | None = None
    mac_address: str | None = None
    led_count: int = 300
    topic_suffix: str | None = None
    is_active: bool = True
    notes: str | None = None


class LEDControllerCreate(LEDControllerBase):
    pass


class LEDControllerUpdate(BaseModel):
    display_name: str | None = None
    mac_address: str | None = None
    ip_address: str | None = None
    hostname: str | None = None
    firmware_version: str | None = None
    led_count: int | None = None
    topic_suffix: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class LEDControllerRead(LEDControllerBase):
    id: int
    ip_address: str | None = None
    hostname: str | None = None
    firmware_version: str | None = None
    status: str = "offline"
    last_seen: datetime | None = None
    wifi_rssi: int | None = None
    uptime_seconds: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LEDControllerZoneBase(BaseModel):
    controller_id: int
    zone_id: int


class LEDControllerZoneRead(LEDControllerZoneBase):
    id: int
    zone_code: str | None = None
    zone_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LEDControllerZoneUpdate(BaseModel):
    zone_ids: list[int] = Field(default_factory=list)


class LEDBinMappingBase(BaseModel):
    controller_id: int
    zone_id: int
    shelf_label: str | None = None
    bin_label: str
    pixel_start: int = 0
    pixel_end: int = 0
    default_color: str = "#FF6600"


class LEDBinMappingCreate(LEDBinMappingBase):
    pass


class LEDBinMappingUpdate(BaseModel):
    zone_id: int | None = None
    shelf_label: str | None = None
    bin_label: str | None = None
    pixel_start: int | None = None
    pixel_end: int | None = None
    default_color: str | None = None


class LEDBinMappingRead(LEDBinMappingBase):
    id: int
    zone_code: str | None = None
    zone_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LEDBinMappingBulkCreateItem(BaseModel):
    controller_id: int
    zone_id: int
    shelf_label: str | None = None
    bin_label: str
    pixel_start: int = 0
    pixel_end: int = 0
    default_color: str = "#FF6600"


class LEDBinMappingBulkCreate(BaseModel):
    items: list[LEDBinMappingBulkCreateItem] = Field(default_factory=list)


class LEDHighlightBin(BaseModel):
    bin_label: str
    color: str = "#FF6600"
    pattern: str = "solid"
    intensity: int = 180


class LEDHighlightShelf(BaseModel):
    shelf_label: str
    bins: list[LEDHighlightBin] = Field(default_factory=list)


class LEDHighlightRequest(BaseModel):
    shelves: list[LEDHighlightShelf] = Field(default_factory=list)
    color: str = "#FF6600"
    pattern: str = "solid"
    intensity: int = 180
    duration_seconds: int | None = None


class LEDIdentifyRequest(BaseModel):
    color: str = "#FFFFFF"
    duration_seconds: int = 3


class LEDStatusResponse(BaseModel):
    controller_id: str
    status: str
    last_seen: datetime | None = None
    ip_address: str | None = None
    led_count: int = 0
    wifi_rssi: int | None = None


class LEDHighlightJobResponse(BaseModel):
    controllers_notified: int
    bins_highlighted: int
    shelves: list[LEDHighlightShelf]


class LEDJobHighlightDetail(BaseModel):
    device_id: int
    asset_tag: str | None = None
    product_name: str | None = None
    zone_id: int | None = None
    zone_code: str | None = None
    controller_id: str | None = None
    bin_label: str | None = None
    pixel_start: int | None = None
    pixel_end: int | None = None
    highlighted: bool = False
