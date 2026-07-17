from datetime import date
from decimal import Decimal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.inventory.models import Product
from app.domain.jobs.models import Job, JobRequirement
from app.domain.route_planner.models import DeliveryRoute, RouteStop, RouteVehicle, Vehicle
from app.domain.route_planner.schemas import (
    GoogleMapsExportRequest,
    GoogleMapsExportResponse,
    JobStopRead,
    PackingListProduct,
    PackingListResponse,
    PackingListStop,
    RouteCreate,
    RouteRead,
    RouteStopCreate,
    RouteStopRead,
    RouteStopReorder,
    RouteUpdate,
    RouteVehicleAssign,
    RouteVehicleRead,
    RouteVehicleReorder,
    SuggestVehiclesRequest,
    VehicleCreate,
    VehicleRead,
    VehicleStopRead,
    VehicleSuggestion,
    VehicleUpdate,
)

router = APIRouter(prefix="/route-planner", tags=["route-planner"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_route_or_404(route_id: int, db: Session) -> DeliveryRoute:
    route = db.execute(
        select(DeliveryRoute).where(DeliveryRoute.id == route_id)
    ).scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


def _get_vehicle_or_404(vehicle_id: int, db: Session) -> Vehicle:
    vehicle = db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id)
    ).scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


def _vehicle_effective_volume(v: Vehicle) -> Decimal | None:
    """Return effective volume: explicit max_volume_m3 or calculated from interior dims."""
    if v.max_volume_m3:
        return Decimal(str(v.max_volume_m3))
    if v.interior_length_cm and v.interior_width_cm and v.interior_height_cm:
        return (
            Decimal(str(v.interior_length_cm))
            * Decimal(str(v.interior_width_cm))
            * Decimal(str(v.interior_height_cm))
            / Decimal("1000000")
        )
    return None


def _route_volume_cm3(product: Product) -> Decimal:
    if product.height_cm and product.width_cm and product.depth_cm:
        return Decimal(str(product.height_cm)) * Decimal(str(product.width_cm)) * Decimal(str(product.depth_cm))
    return Decimal("0")


def _build_job_stop_read(job: Job) -> dict:
    venue = job.venue if hasattr(job, "venue") and job.venue else None
    customer = job.customer if hasattr(job, "customer") and job.customer else None
    return {
        "id": job.id,
        "job_code": job.job_code,
        "customer_name": customer.name if customer else (job.customer_name or None),
        "venue_name": venue.name if venue else (job.venue_name or None),
        "venue_address": venue.address if venue else None,
        "venue_city": venue.city if venue else None,
        "venue_country": venue.country if venue else None,
        "status": job.status,
        "start_date": job.start_date,
        "end_date": job.end_date,
    }


def _build_route_read(route: DeliveryRoute) -> RouteRead:
    stops = []
    for s in route.stops:
        job_read = _build_job_stop_read(s.job) if s.job else None
        vehicle_read = VehicleStopRead(id=s.vehicle.id, name=s.vehicle.name, vehicle_type=s.vehicle.vehicle_type) if s.vehicle else None
        stops.append(RouteStopRead(
            id=s.id, route_id=s.route_id, job_id=s.job_id,
            vehicle_id=s.vehicle_id,
            stop_order=s.stop_order, notes=s.notes,
            job=JobStopRead(**job_read) if job_read else None,
            vehicle=vehicle_read,
        ))
    vehicles = []
    for va in route.vehicle_assignments:
        vehicles.append(RouteVehicleRead(
            vehicle_id=va.vehicle_id,
            vehicle_name=va.vehicle.name if va.vehicle else None,
            vehicle_type=va.vehicle.vehicle_type if va.vehicle else None,
            load_order=va.load_order,
            notes=va.notes,
        ))
    return RouteRead(
        id=route.id, name=route.name, status=route.status,
        start_date=route.start_date, notes=route.notes,
        created_by_id=route.created_by_id,
        created_at=route.created_at, updated_at=route.updated_at,
        stops=stops, vehicles=vehicles,
    )


def _load_route_with_joins(route_id: int, db: Session) -> DeliveryRoute | None:
    return db.execute(
        select(DeliveryRoute)
        .options(
            joinedload(DeliveryRoute.stops).joinedload(RouteStop.job).joinedload(Job.venue),
            joinedload(DeliveryRoute.stops).joinedload(RouteStop.job).joinedload(Job.customer),
            joinedload(DeliveryRoute.stops).joinedload(RouteStop.vehicle),
            joinedload(DeliveryRoute.vehicle_assignments).joinedload(RouteVehicle.vehicle),
        )
        .where(DeliveryRoute.id == route_id)
    ).unique().scalar_one_or_none()


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

@router.get("/vehicles", response_model=list[VehicleRead])
def list_vehicles(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.execute(
        select(Vehicle).where(Vehicle.is_active.is_(True)).order_by(Vehicle.name)
    ).scalars().all()


@router.post("/vehicles", response_model=VehicleRead, status_code=201)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db), _user: User = Depends(require_editor)):
    existing = db.execute(select(Vehicle).where(Vehicle.name == payload.name)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Vehicle name already exists")
    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.put("/vehicles/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(vehicle_id: int, payload: VehicleUpdate, db: Session = Depends(get_db), _user: User = Depends(require_editor)):
    vehicle = _get_vehicle_or_404(vehicle_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != vehicle.name:
        existing = db.execute(select(Vehicle).where(Vehicle.name == data["name"])).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Vehicle name already exists")
    for k, v in data.items():
        setattr(vehicle, k, v)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/vehicles/{vehicle_id}", status_code=204)
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db), _user: User = Depends(require_editor)):
    vehicle = _get_vehicle_or_404(vehicle_id, db)
    vehicle.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/routes", response_model=list[RouteRead])
def list_routes(
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = select(DeliveryRoute).options(
        joinedload(DeliveryRoute.stops).joinedload(RouteStop.job).joinedload(Job.venue),
        joinedload(DeliveryRoute.stops).joinedload(RouteStop.job).joinedload(Job.customer),
        joinedload(DeliveryRoute.stops).joinedload(RouteStop.vehicle),
        joinedload(DeliveryRoute.vehicle_assignments).joinedload(RouteVehicle.vehicle),
    )
    if status:
        q = q.where(DeliveryRoute.status == status)
    if date_from:
        q = q.where(DeliveryRoute.start_date >= date_from)
    if date_to:
        q = q.where(DeliveryRoute.start_date <= date_to)
    q = q.order_by(DeliveryRoute.start_date.desc(), DeliveryRoute.id.desc())
    routes = db.execute(q).unique().scalars().all()
    return [_build_route_read(r) for r in routes]


@router.get("/routes/{route_id}", response_model=RouteRead)
def get_route(route_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    route = _load_route_with_joins(route_id, db)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return _build_route_read(route)


@router.post("/routes", response_model=RouteRead, status_code=201)
def create_route(payload: RouteCreate, db: Session = Depends(get_db), user: User = Depends(require_editor)):
    route = DeliveryRoute(
        name=payload.name,
        start_date=payload.start_date,
        notes=payload.notes,
        created_by_id=user.id,
    )
    db.add(route)
    db.flush()
    for i, stop_in in enumerate(payload.stops, 1):
        job = db.get(Job, stop_in.job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {stop_in.job_id} not found")
        db.add(RouteStop(route_id=route.id, job_id=stop_in.job_id, stop_order=i, notes=stop_in.notes))
    for i, vid in enumerate(payload.vehicle_ids):
        _get_vehicle_or_404(vid, db)
        db.add(RouteVehicle(route_id=route.id, vehicle_id=vid, load_order=i))
    db.commit()
    db.refresh(route)
    loaded = _load_route_with_joins(route.id, db)
    return _build_route_read(loaded)


@router.put("/routes/{route_id}", response_model=RouteRead)
def update_route(route_id: int, payload: RouteUpdate, db: Session = Depends(get_db), user: User = Depends(require_editor)):
    route = _get_route_or_404(route_id, db)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(route, k, v)
    db.commit()
    loaded = _load_route_with_joins(route_id, db)
    return _build_route_read(loaded)


@router.delete("/routes/{route_id}", status_code=204)
def delete_route(route_id: int, db: Session = Depends(get_db), _user: User = Depends(require_editor)):
    route = _get_route_or_404(route_id, db)
    db.delete(route)
    db.commit()


# ---------------------------------------------------------------------------
# Route Vehicles (multi-vehicle assignment)
# ---------------------------------------------------------------------------

@router.post("/routes/{route_id}/vehicles", response_model=RouteRead)
def assign_vehicle(route_id: int, payload: RouteVehicleAssign, db: Session = Depends(get_db), user: User = Depends(require_editor)):
    _get_route_or_404(route_id, db)
    _get_vehicle_or_404(payload.vehicle_id, db)
    existing = db.execute(
        select(RouteVehicle).where(RouteVehicle.route_id == route_id, RouteVehicle.vehicle_id == payload.vehicle_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Vehicle already assigned to this route")
    db.add(RouteVehicle(route_id=route_id, vehicle_id=payload.vehicle_id, load_order=payload.load_order, notes=payload.notes))
    db.commit()
    loaded = _load_route_with_joins(route_id, db)
    return _build_route_read(loaded)


@router.put("/routes/{route_id}/vehicles/reorder", response_model=RouteRead)
def reorder_vehicles(route_id: int, payload: RouteVehicleReorder, db: Session = Depends(get_db), user: User = Depends(require_editor)):
    _get_route_or_404(route_id, db)
    assignments = db.execute(
        select(RouteVehicle).where(RouteVehicle.route_id == route_id)
    ).scalars().all()
    assign_map = {a.vehicle_id: a for a in assignments}
    for idx, vid in enumerate(payload.vehicle_ids):
        if vid not in assign_map:
            raise HTTPException(status_code=400, detail=f"Vehicle {vid} not assigned to route")
        assign_map[vid].load_order = idx
    db.commit()
    loaded = _load_route_with_joins(route_id, db)
    return _build_route_read(loaded)


@router.delete("/routes/{route_id}/vehicles/{vehicle_id}", status_code=204)
def remove_vehicle(route_id: int, vehicle_id: int, db: Session = Depends(get_db), _user: User = Depends(require_editor)):
    assignment = db.execute(
        select(RouteVehicle).where(RouteVehicle.route_id == route_id, RouteVehicle.vehicle_id == vehicle_id)
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Vehicle not assigned to this route")
    db.delete(assignment)
    db.commit()


# ---------------------------------------------------------------------------
# Route Stops
# ---------------------------------------------------------------------------

@router.post("/routes/{route_id}/stops", response_model=RouteRead)
def add_stop(route_id: int, payload: RouteStopCreate, db: Session = Depends(get_db), user: User = Depends(require_editor)):
    route = _get_route_or_404(route_id, db)
    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {payload.job_id} not found")
    existing = db.execute(
        select(RouteStop).where(RouteStop.route_id == route_id, RouteStop.job_id == payload.job_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Job already in route")
    max_order = db.execute(
        select(func.max(RouteStop.stop_order)).where(RouteStop.route_id == route_id)
    ).scalar() or 0
    db.add(RouteStop(route_id=route_id, job_id=payload.job_id, vehicle_id=payload.vehicle_id, stop_order=max_order + 1, notes=payload.notes))
    db.commit()
    loaded = _load_route_with_joins(route_id, db)
    return _build_route_read(loaded)


@router.put("/routes/{route_id}/stops/reorder", response_model=RouteRead)
def reorder_stops(route_id: int, payload: RouteStopReorder, db: Session = Depends(get_db), user: User = Depends(require_editor)):
    route = _get_route_or_404(route_id, db)
    stops = db.execute(
        select(RouteStop).where(RouteStop.route_id == route_id)
    ).scalars().all()
    stop_map = {s.id: s for s in stops}
    for idx, stop_id in enumerate(payload.stop_ids):
        if stop_id not in stop_map:
            raise HTTPException(status_code=400, detail=f"Stop {stop_id} not in route")
        stop_map[stop_id].stop_order = idx
    db.commit()
    loaded = _load_route_with_joins(route_id, db)
    return _build_route_read(loaded)


@router.delete("/routes/{route_id}/stops/{stop_id}", status_code=204)
def remove_stop(route_id: int, stop_id: int, db: Session = Depends(get_db), _user: User = Depends(require_editor)):
    stop = db.execute(
        select(RouteStop).where(RouteStop.id == stop_id, RouteStop.route_id == route_id)
    ).scalar_one_or_none()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    db.delete(stop)
    db.flush()
    remaining = db.execute(
        select(RouteStop).where(RouteStop.route_id == route_id).order_by(RouteStop.stop_order)
    ).scalars().all()
    for idx, s in enumerate(remaining, 1):
        s.stop_order = idx
    db.commit()


@router.put("/routes/{route_id}/stops/{stop_id}/vehicle", response_model=RouteRead)
def assign_stop_vehicle(route_id: int, stop_id: int, vehicle_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_editor)):
    stop = db.execute(
        select(RouteStop).where(RouteStop.id == stop_id, RouteStop.route_id == route_id)
    ).scalar_one_or_none()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    stop.vehicle_id = vehicle_id
    db.commit()
    loaded = _load_route_with_joins(route_id, db)
    return _build_route_read(loaded)


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def _calc_cargo(db: Session, job_ids: list[int]) -> tuple[Decimal, Decimal]:
    """Calculate total weight and volume for a set of jobs."""
    total_weight = Decimal("0")
    total_volume = Decimal("0")
    for jid in job_ids:
        job = db.get(Job, jid)
        if not job:
            continue
        reqs = db.execute(
            select(JobRequirement).where(JobRequirement.job_id == jid)
        ).scalars().all()
        for req in reqs:
            product = db.get(Product, req.product_id)
            if not product:
                continue
            qty = Decimal(str(req.quantity_required))
            if product.weight_kg:
                total_weight += Decimal(str(product.weight_kg)) * qty
            v = _route_volume_cm3(product)
            if v > 0:
                total_volume += v * qty / Decimal("1000000")
    return total_weight, total_volume


def _make_suggestion(
    suggestion_id: str,
    vehicles: list[Vehicle],
    total_weight: Decimal,
    total_volume: Decimal,
    is_combo: bool = False,
    combo_description: str | None = None,
) -> VehicleSuggestion:
    """Build a VehicleSuggestion from a list of 1+ vehicles."""
    # For trailers use max_payload_kg (actual load capacity); for others use max_weight_kg
    combined_max_weight = Decimal("0")
    for v in vehicles:
        if v.vehicle_type == "trailer" and v.max_payload_kg:
            combined_max_weight += Decimal(str(v.max_payload_kg))
        elif v.max_weight_kg:
            combined_max_weight += Decimal(str(v.max_weight_kg))
    combined_max_volume: Decimal | None = None
    volumes = [_vehicle_effective_volume(v) for v in vehicles]
    if any(v is not None for v in volumes):
        combined_max_volume = sum(v for v in volumes if v is not None)

    fits = True
    if combined_max_weight > 0 and total_weight > combined_max_weight:
        fits = False
    if combined_max_volume is not None and total_volume > combined_max_volume:
        fits = False

    w_util = None
    v_util = None
    if combined_max_weight > 0:
        w_util = float(total_weight / combined_max_weight * 100)
    if combined_max_volume and combined_max_volume > 0:
        v_util = float(total_volume / combined_max_volume * 100)

    label = " + ".join(v.name for v in vehicles)
    return VehicleSuggestion(
        suggestion_id=suggestion_id,
        label=label,
        vehicles=[VehicleRead.model_validate(v) for v in vehicles],
        total_weight_kg=total_weight,
        total_volume_m3=total_volume,
        total_max_weight_kg=combined_max_weight,
        total_max_volume_m3=combined_max_volume,
        fits=fits,
        weight_utilization_pct=w_util,
        volume_utilization_pct=v_util,
        is_combo=is_combo,
        combo_description=combo_description,
    )


@router.post("/suggest-vehicles", response_model=list[VehicleSuggestion])
def suggest_vehicles(payload: SuggestVehiclesRequest, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    total_weight, total_volume = _calc_cargo(db, payload.job_ids)
    vehicles = db.execute(
        select(Vehicle).where(Vehicle.is_active.is_(True)).order_by(Vehicle.name)
    ).scalars().all()

    suggestions: list[VehicleSuggestion] = []

    # --- Single vehicle suggestions ---
    for v in vehicles:
        suggestions.append(_make_suggestion(
            suggestion_id=f"single-{v.id}",
            vehicles=[v],
            total_weight=total_weight,
            total_volume=total_volume,
        ))

    # --- Combo suggestions: towing vehicles + trailers ---
    tow_vehicles = [v for v in vehicles if v.can_pull_trailer and v.vehicle_type in ("truck", "van", "car")]
    trailers = [v for v in vehicles if v.vehicle_type == "trailer"]

    for tow_v in tow_vehicles:
        for trailer in trailers:
            # Check if tow vehicle can pull this trailer (curb weight = trailer's own weight)
            trailer_weight = trailer.curb_weight_kg or trailer.max_weight_kg
            if trailer_weight and tow_v.max_tow_weight_kg:
                if Decimal(str(trailer_weight)) > Decimal(str(tow_v.max_tow_weight_kg)):
                    continue  # trailer too heavy to tow
            combo_id = f"combo-{tow_v.id}-{trailer.id}"
            # Build description with weight info
            parts = [f"{tow_v.name} pulls {trailer.name}"]
            if trailer.curb_weight_kg:
                parts.append(f"curb {trailer.curb_weight_kg}kg")
            if trailer.max_payload_kg:
                parts.append(f"payload {trailer.max_payload_kg}kg")
            desc = " · ".join(parts)
            suggestions.append(_make_suggestion(
                suggestion_id=combo_id,
                vehicles=[tow_v, trailer],
                total_weight=total_weight,
                total_volume=total_volume,
                is_combo=True,
                combo_description=desc,
            ))

    # Sort: fitting first, then by weight utilization (ascending = best fit)
    suggestions.sort(key=lambda s: (not s.fits, s.weight_utilization_pct or 9999))
    return suggestions


@router.post("/export-google-maps", response_model=GoogleMapsExportResponse)
def export_google_maps(payload: GoogleMapsExportRequest, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    route = db.execute(
        select(DeliveryRoute)
        .options(
            joinedload(DeliveryRoute.stops).joinedload(RouteStop.job).joinedload(Job.venue),
        )
        .where(DeliveryRoute.id == payload.route_id)
    ).unique().scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    parts: list[str] = []
    if payload.origin_address:
        parts.append(quote(payload.origin_address))
    for stop in sorted(route.stops, key=lambda s: s.stop_order):
        job = stop.job
        if not job:
            continue
        venue = job.venue if hasattr(job, "venue") and job.venue else None
        if venue and venue.address:
            addr_parts = [venue.address]
            if venue.city:
                addr_parts.append(venue.city)
            if venue.country:
                addr_parts.append(venue.country)
            parts.append(quote(", ".join(addr_parts)))
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Route needs at least one stop with a venue address")
    url = "https://www.google.com/maps/dir/" + "/".join(parts)
    return GoogleMapsExportResponse(url=url, stop_count=len(route.stops))


@router.get("/routes/{route_id}/packing-list", response_model=PackingListResponse)
def get_packing_list(route_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    route = _load_route_with_joins(route_id, db)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    sorted_stops = sorted(route.stops, key=lambda s: s.stop_order)
    total_weight = Decimal("0")
    total_volume = Decimal("0")
    packing_stops: list[PackingListStop] = []
    for idx, stop in enumerate(reversed(sorted_stops), 1):
        job = stop.job
        if not job:
            continue
        venue = job.venue if hasattr(job, "venue") and job.venue else None
        customer = job.customer if hasattr(job, "customer") and job.customer else None
        products: list[PackingListProduct] = []
        stop_weight = Decimal("0")
        stop_volume = Decimal("0")
        for req in job.requirements:
            product = req.product
            if not product:
                continue
            qty = Decimal(str(req.quantity_required))
            pw = Decimal(str(product.weight_kg)) * qty if product.weight_kg else Decimal("0")
            pv = _route_volume_cm3(product) * qty / Decimal("1000000") if _route_volume_cm3(product) > 0 else Decimal("0")
            products.append(PackingListProduct(
                product_id=product.id, product_name=product.name,
                quantity=req.quantity_required, weight_kg=pw, volume_m3=pv,
            ))
            stop_weight += pw
            stop_volume += pv
        total_weight += stop_weight
        total_volume += stop_volume
        packing_stops.append(PackingListStop(
            stop_order=idx, drop_off_order=stop.stop_order,
            job_id=job.id, job_code=job.job_code,
            customer_name=customer.name if customer else (job.customer_name or None),
            venue_name=venue.name if venue else (job.venue_name or None),
            venue_address=venue.address if venue else None,
            vehicle_name=stop.vehicle.name if stop.vehicle else None,
            products=products, stop_weight_kg=stop_weight, stop_volume_m3=stop_volume,
        ))
    assigned_vehicles = [va.vehicle for va in route.vehicle_assignments if va.vehicle]
    return PackingListResponse(
        route_id=route.id, route_name=route.name,
        vehicles=[VehicleRead.model_validate(v) for v in assigned_vehicles],
        total_weight_kg=total_weight, total_volume_m3=total_volume,
        stops=packing_stops,
    )
