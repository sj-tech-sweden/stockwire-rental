from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


# ---------- Vehicle ----------

class VehicleBase(BaseModel):
    name: str
    vehicle_type: Literal["truck", "van", "trailer", "car"]
    license_plate: str | None = None
    max_weight_kg: Decimal | None = None
    max_volume_m3: Decimal | None = None
    interior_length_cm: Decimal | None = None
    interior_width_cm: Decimal | None = None
    interior_height_cm: Decimal | None = None
    can_pull_trailer: bool = False
    max_tow_weight_kg: Decimal | None = None
    curb_weight_kg: Decimal | None = None
    max_payload_kg: Decimal | None = None
    notes: str | None = None
    is_active: bool = True


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    name: str | None = None
    vehicle_type: Literal["truck", "van", "trailer", "car"] | None = None
    license_plate: str | None = None
    max_weight_kg: Decimal | None = None
    max_volume_m3: Decimal | None = None
    interior_length_cm: Decimal | None = None
    interior_width_cm: Decimal | None = None
    interior_height_cm: Decimal | None = None
    can_pull_trailer: bool | None = None
    max_tow_weight_kg: Decimal | None = None
    curb_weight_kg: Decimal | None = None
    max_payload_kg: Decimal | None = None
    notes: str | None = None
    is_active: bool | None = None


class VehicleRead(BaseModel):
    id: int
    name: str
    vehicle_type: str
    license_plate: str | None = None
    max_weight_kg: Decimal | None = None
    max_volume_m3: Decimal | None = None
    interior_length_cm: Decimal | None = None
    interior_width_cm: Decimal | None = None
    interior_height_cm: Decimal | None = None
    can_pull_trailer: bool
    max_tow_weight_kg: Decimal | None = None
    curb_weight_kg: Decimal | None = None
    max_payload_kg: Decimal | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Route Vehicle ----------

class RouteVehicleRead(BaseModel):
    vehicle_id: int
    vehicle_name: str | None = None
    vehicle_type: str | None = None
    load_order: int = 0
    notes: str | None = None

    model_config = {"from_attributes": True}


class RouteVehicleAssign(BaseModel):
    vehicle_id: int
    load_order: int = 0
    notes: str | None = None


class RouteVehicleReorder(BaseModel):
    vehicle_ids: list[int]  # ordered list of vehicle IDs


# ---------- Route Stop ----------

class JobStopRead(BaseModel):
    id: int
    job_code: str | None = None
    customer_name: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    venue_city: str | None = None
    venue_country: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    model_config = {"from_attributes": True}


class VehicleStopRead(BaseModel):
    id: int
    name: str | None = None
    vehicle_type: str | None = None
    model_config = {"from_attributes": True}

class RouteStopRead(BaseModel):
    id: int
    route_id: int
    job_id: int
    vehicle_id: int | None = None
    stop_order: int
    notes: str | None = None
    job: JobStopRead | None = None
    vehicle: VehicleStopRead | None = None

    model_config = {"from_attributes": True}


class RouteStopCreate(BaseModel):
    job_id: int
    vehicle_id: int | None = None
    notes: str | None = None


class RouteStopReorder(BaseModel):
    stop_ids: list[int]


# ---------- Route ----------

class RouteBase(BaseModel):
    name: str
    start_date: date
    notes: str | None = None


class RouteCreate(RouteBase):
    stops: list[RouteStopCreate] = []
    vehicle_ids: list[int] = []


class RouteUpdate(BaseModel):
    name: str | None = None
    status: Literal["planned", "in_progress", "completed", "cancelled"] | None = None
    start_date: date | None = None
    notes: str | None = None


class RouteRead(BaseModel):
    id: int
    name: str
    status: str
    start_date: date
    notes: str | None = None
    created_by_id: int | None = None
    created_at: datetime
    updated_at: datetime
    stops: list[RouteStopRead] = []
    vehicles: list[RouteVehicleRead] = []

    model_config = {"from_attributes": True}


# ---------- Planning ----------

class VehicleSuggestion(BaseModel):
    suggestion_id: str  # unique ID for this suggestion
    label: str  # human-readable label e.g. "Truck 1" or "Car 1 + Trailer 1"
    vehicles: list[VehicleRead]
    total_weight_kg: Decimal
    total_volume_m3: Decimal
    total_max_weight_kg: Decimal
    total_max_volume_m3: Decimal | None = None
    fits: bool
    weight_utilization_pct: float | None = None
    volume_utilization_pct: float | None = None
    is_combo: bool = False
    combo_description: str | None = None  # e.g. "Car pulls trailer"


class SuggestVehiclesRequest(BaseModel):
    job_ids: list[int]


class GoogleMapsExportRequest(BaseModel):
    route_id: int
    origin_address: str | None = None


class GoogleMapsExportResponse(BaseModel):
    url: str
    stop_count: int


class PackingListStop(BaseModel):
    stop_order: int
    drop_off_order: int
    job_id: int
    job_code: str | None = None
    customer_name: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    vehicle_name: str | None = None
    products: list["PackingListProduct"] = []
    stop_weight_kg: Decimal = Decimal("0")
    stop_volume_m3: Decimal = Decimal("0")


class PackingListProduct(BaseModel):
    product_id: int
    product_name: str | None = None
    quantity: int
    weight_kg: Decimal | None = None
    volume_m3: Decimal | None = None


class PackingListResponse(BaseModel):
    route_id: int
    route_name: str
    vehicles: list[VehicleRead] = []
    total_weight_kg: Decimal = Decimal("0")
    total_volume_m3: Decimal = Decimal("0")
    stops: list[PackingListStop] = []
