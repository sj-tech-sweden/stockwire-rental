"""API routes for warehouse LED controller management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.router import get_current_user
from app.domain.auth.models import User
from app.domain.inventory.models import Device, Zone
from app.domain.jobs.models import Job, JobRequirement
from app.domain.warehouse_leds import mqtt_client
from app.domain.warehouse_leds.esp_home import generate_esphome_yaml, generate_secrets_template
from app.domain.warehouse_leds.models import LEDBinMapping, LEDController, LEDControllerZone
from app.domain.warehouse_leds.schemas import (
    LEDBinMappingBulkCreate,
    LEDBinMappingCreate,
    LEDBinMappingRead,
    LEDBinMappingUpdate,
    LEDControllerCreate,
    LEDControllerRead,
    LEDControllerUpdate,
    LEDControllerZoneRead,
    LEDControllerZoneUpdate,
    LEDHighlightBin,
    LEDHighlightJobResponse,
    LEDHighlightRequest,
    LEDHighlightShelf,
    LEDIdentifyRequest,
    LEDJobHighlightDetail,
    LEDStatusResponse,
)

router = APIRouter(prefix="/warehouse-leds", tags=["warehouse-leds"])


# ---------------------------------------------------------------------------
# Controllers
# ---------------------------------------------------------------------------

@router.get("/controllers", response_model=list[LEDControllerRead])
def list_controllers(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[LEDController]:
    return db.execute(
        select(LEDController).order_by(LEDController.display_name, LEDController.controller_id)
    ).scalars().all()


@router.post("/controllers", response_model=LEDControllerRead, status_code=201)
def create_controller(
    body: LEDControllerCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> LEDController:
    existing = db.execute(
        select(LEDController).where(LEDController.controller_id == body.controller_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(400, f"Controller '{body.controller_id}' already exists")
    ctrl = LEDController(**body.model_dump())
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)
    return ctrl


@router.get("/controllers/{controller_db_id}", response_model=LEDControllerRead)
def get_controller(
    controller_db_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> LEDController:
    ctrl = db.get(LEDController, controller_db_id)
    if not ctrl:
        raise HTTPException(404, "Controller not found")
    return ctrl


@router.patch("/controllers/{controller_db_id}", response_model=LEDControllerRead)
def update_controller(
    controller_db_id: int,
    body: LEDControllerUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> LEDController:
    ctrl = db.get(LEDController, controller_db_id)
    if not ctrl:
        raise HTTPException(404, "Controller not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(ctrl, key, value)
    db.commit()
    db.refresh(ctrl)
    return ctrl


@router.delete("/controllers/{controller_db_id}", status_code=204)
def delete_controller(
    controller_db_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> None:
    ctrl = db.get(LEDController, controller_db_id)
    if not ctrl:
        raise HTTPException(404, "Controller not found")
    db.delete(ctrl)
    db.commit()


# ---------------------------------------------------------------------------
# Controller Zone Assignments
# ---------------------------------------------------------------------------

@router.get("/controllers/{controller_db_id}/zones", response_model=list[LEDControllerZoneRead])
def list_controller_zones(
    controller_db_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[LEDControllerZone]:
    ctrl = db.get(LEDController, controller_db_id)
    if not ctrl:
        raise HTTPException(404, "Controller not found")
    assignments = db.execute(
        select(LEDControllerZone).where(LEDControllerZone.controller_id == controller_db_id)
    ).scalars().all()
    result = []
    for a in assignments:
        zone = db.get(Zone, a.zone_id)
        item = LEDControllerZoneRead(
            id=a.id,
            controller_id=a.controller_id,
            zone_id=a.zone_id,
            zone_code=zone.code if zone else None,
            zone_name=zone.name if zone else None,
            created_at=a.created_at,
        )
        result.append(item)
    return result


@router.put("/controllers/{controller_db_id}/zones", response_model=list[LEDControllerZoneRead])
def set_controller_zones(
    controller_db_id: int,
    body: LEDControllerZoneUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[LEDControllerZone]:
    ctrl = db.get(LEDController, controller_db_id)
    if not ctrl:
        raise HTTPException(404, "Controller not found")

    db.execute(
        LEDControllerZone.__table__.delete().where(LEDControllerZone.controller_id == controller_db_id)
    )

    created = []
    for zone_id in body.zone_ids:
        zone = db.get(Zone, zone_id)
        if not zone:
            continue
        assignment = LEDControllerZone(controller_id=controller_db_id, zone_id=zone_id)
        db.add(assignment)
        created.append(assignment)

    db.commit()
    for a in created:
        db.refresh(a)
    return created


# ---------------------------------------------------------------------------
# Bin Mappings
# ---------------------------------------------------------------------------

@router.get("/mappings", response_model=list[LEDBinMappingRead])
def list_bin_mappings(
    controller_id: int | None = Query(None),
    zone_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[LEDBinMapping]:
    stmt = select(LEDBinMapping)
    if controller_id is not None:
        stmt = stmt.where(LEDBinMapping.controller_id == controller_id)
    if zone_id is not None:
        stmt = stmt.where(LEDBinMapping.zone_id == zone_id)
    stmt = stmt.order_by(LEDBinMapping.bin_label)
    mappings = db.execute(stmt).scalars().all()
    result = []
    for m in mappings:
        zone = db.get(Zone, m.zone_id)
        item = LEDBinMappingRead(
            id=m.id,
            controller_id=m.controller_id,
            zone_id=m.zone_id,
            shelf_label=m.shelf_label,
            bin_label=m.bin_label,
            pixel_start=m.pixel_start,
            pixel_end=m.pixel_end,
            default_color=m.default_color,
            zone_code=zone.code if zone else None,
            zone_name=zone.name if zone else None,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        result.append(item)
    return result


@router.post("/mappings", response_model=LEDBinMappingRead, status_code=201)
def create_bin_mapping(
    body: LEDBinMappingCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> LEDBinMapping:
    ctrl = db.get(LEDController, body.controller_id)
    if not ctrl:
        raise HTTPException(400, "Controller not found")
    zone = db.get(Zone, body.zone_id)
    if not zone:
        raise HTTPException(400, "Zone not found")

    existing = db.execute(
        select(LEDBinMapping).where(LEDBinMapping.bin_label == body.bin_label)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(400, f"Mapping for bin '{body.bin_label}' already exists")

    mapping = LEDBinMapping(**body.model_dump())
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.put("/mappings/{mapping_id}", response_model=LEDBinMappingRead)
def update_bin_mapping(
    mapping_id: int,
    body: LEDBinMappingUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> LEDBinMapping:
    mapping = db.get(LEDBinMapping, mapping_id)
    if not mapping:
        raise HTTPException(404, "Mapping not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(mapping, key, value)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.delete("/mappings/{mapping_id}", status_code=204)
def delete_bin_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> None:
    mapping = db.get(LEDBinMapping, mapping_id)
    if not mapping:
        raise HTTPException(404, "Mapping not found")
    db.delete(mapping)
    db.commit()


@router.post("/mappings/bulk", status_code=201)
def bulk_create_bin_mappings(
    body: LEDBinMappingBulkCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    created = 0
    skipped = 0
    for item in body.items:
        existing = db.execute(
            select(LEDBinMapping).where(LEDBinMapping.bin_label == item.bin_label)
        ).scalar_one_or_none()
        if existing:
            skipped += 1
            continue
        mapping = LEDBinMapping(**item.model_dump())
        db.add(mapping)
        created += 1
    db.commit()
    return {"created": created, "skipped": skipped}


# ---------------------------------------------------------------------------
# LED Actions
# ---------------------------------------------------------------------------

@router.post("/highlight")
def highlight_bins(
    body: LEDHighlightRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    controllers_notified = set()
    bins_highlighted = 0

    for shelf in body.shelves:
        for bin_item in shelf.bins:
            mappings = db.execute(
                select(LEDBinMapping).where(LEDBinMapping.bin_label == bin_item.bin_label)
            ).scalars().all()
            for mapping in mappings:
                ctrl = db.get(LEDController, mapping.controller_id)
                if not ctrl or not ctrl.is_active:
                    continue
                pixels = list(range(mapping.pixel_start, mapping.pixel_end + 1))
                mqtt_client.publish_locate(
                    controller_id=ctrl.topic_suffix or ctrl.controller_id,
                    shelf_label=mapping.shelf_label or shelf.shelf_label,
                    bin_label=mapping.bin_label,
                    pixels=pixels,
                    color=bin_item.color or body.color,
                    pattern=bin_item.pattern or body.pattern,
                )
                controllers_notified.add(ctrl.id)
                bins_highlighted += 1

    return {
        "controllers_notified": len(controllers_notified),
        "bins_highlighted": bins_highlighted,
    }


@router.post("/locate/{device_id}")
def locate_device(
    device_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(404, "Device not found")
    if not device.location_zone_id:
        raise HTTPException(400, "Device has no zone assignment")

    zone = db.get(Zone, device.location_zone_id)
    if not zone:
        raise HTTPException(400, "Zone not found")

    mappings = db.execute(
        select(LEDBinMapping).where(LEDBinMapping.zone_id == device.location_zone_id)
    ).scalars().all()

    if not mappings:
        raise HTTPException(400, "No LED mappings found for this device's zone")

    controllers_notified = set()
    for mapping in mappings:
        ctrl = db.get(LEDController, mapping.controller_id)
        if not ctrl or not ctrl.is_active:
            continue
        pixels = list(range(mapping.pixel_start, mapping.pixel_end + 1))
        mqtt_client.publish_locate(
            controller_id=ctrl.topic_suffix or ctrl.controller_id,
            shelf_label=mapping.shelf_label or zone.code,
            bin_label=mapping.bin_label,
            pixels=pixels,
            color="#FF0000",
            pattern="breathe",
        )
        controllers_notified.add(ctrl.id)

    return {
        "device_id": device_id,
        "asset_tag": device.asset_tag,
        "zone_code": zone.code,
        "controllers_notified": len(controllers_notified),
    }


@router.post("/return/{zone_id}")
def show_return_location(
    zone_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(404, "Zone not found")

    mappings = db.execute(
        select(LEDBinMapping).where(LEDBinMapping.zone_id == zone_id)
    ).scalars().all()

    if not mappings:
        raise HTTPException(400, "No LED mappings found for this zone")

    controllers_notified = set()
    for mapping in mappings:
        ctrl = db.get(LEDController, mapping.controller_id)
        if not ctrl or not ctrl.is_active:
            continue
        pixels = list(range(mapping.pixel_start, mapping.pixel_end + 1))
        mqtt_client.publish_locate(
            controller_id=ctrl.topic_suffix or ctrl.controller_id,
            shelf_label=mapping.shelf_label or zone.code,
            bin_label=mapping.bin_label,
            pixels=pixels,
            color="#00FF00",
            pattern="solid",
        )
        controllers_notified.add(ctrl.id)

    return {
        "zone_id": zone_id,
        "zone_code": zone.code,
        "controllers_notified": len(controllers_notified),
    }


@router.post("/highlight-job/{job_id}", response_model=LEDHighlightJobResponse)
def highlight_job_bins(
    job_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> LEDHighlightJobResponse:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    requirements = db.execute(
        select(JobRequirement).where(JobRequirement.job_id == job_id)
    ).scalars().all()

    product_ids = [r.product_id for r in requirements]

    devices = db.execute(
        select(Device).where(
            Device.product_id.in_(product_ids),
            Device.location_zone_id.isnot(None),
        )
    ).scalars().all()

    shelves_map: dict[str, dict[str, LEDHighlightBin]] = {}
    controllers_notified: set[int] = set()
    highlighted_details: list[LEDJobHighlightDetail] = []

    for device in devices:
        zone = db.get(Zone, device.location_zone_id) if device.location_zone_id else None
        if not zone:
            continue

        mappings = db.execute(
            select(LEDBinMapping).where(LEDBinMapping.zone_id == device.location_zone_id)
        ).scalars().all()

        for mapping in mappings:
            ctrl = db.get(LEDController, mapping.controller_id)
            if not ctrl or not ctrl.is_active:
                continue

            shelf_key = mapping.shelf_label or zone.code
            bin_key = mapping.bin_label

            if shelf_key not in shelves_map:
                shelves_map[shelf_key] = {}
            if bin_key not in shelves_map[shelf_key]:
                shelves_map[shelf_key][bin_key] = LEDHighlightBin(
                    bin_label=bin_key, color="#FF6600", pattern="solid"
                )

            controllers_notified.add(ctrl.id)

            highlighted_details.append(
                LEDJobHighlightDetail(
                    device_id=device.id,
                    asset_tag=device.asset_tag,
                    product_name=None,
                    zone_id=zone.id,
                    zone_code=zone.code,
                    controller_id=ctrl.controller_id,
                    bin_label=mapping.bin_label,
                    pixel_start=mapping.pixel_start,
                    pixel_end=mapping.pixel_end,
                    highlighted=True,
                )
            )

    shelves = []
    for shelf_label, bins_map in shelves_map.items():
        shelves.append(
            LEDHighlightShelf(shelf_label=shelf_label, bins=list(bins_map.values()))
        )

    for shelf in shelves:
        mqtt_shelf = {
            "shelf_id": shelf.shelf_label,
            "bins": [
                {
                    "bin_id": b.bin_label,
                    "color": b.color,
                    "pattern": b.pattern,
                }
                for b in shelf.bins
            ],
        }
        for ctrl_id in controllers_notified:
            ctrl = db.get(LEDController, ctrl_id)
            if ctrl:
                mqtt_client.publish_highlight(
                    controller_id=ctrl.topic_suffix or ctrl.controller_id,
                    shelves=[mqtt_shelf],
                    color="#FF6600",
                    pattern="solid",
                )

    return LEDHighlightJobResponse(
        controllers_notified=len(controllers_notified),
        bins_highlighted=len(highlighted_details),
        shelves=shelves,
    )


@router.post("/clear")
def clear_all_leds(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    controllers = db.execute(
        select(LEDController).where(LEDController.is_active == True)
    ).scalars().all()

    cleared = 0
    for ctrl in controllers:
        if mqtt_client.publish_clear(ctrl.topic_suffix or ctrl.controller_id):
            cleared += 1

    return {"controllers_cleared": cleared}


@router.post("/identify")
def identify_all_leds(
    body: LEDIdentifyRequest | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    color = body.color if body else "#FFFFFF"
    duration = body.duration_seconds if body else 3

    controllers = db.execute(
        select(LEDController).where(LEDController.is_active == True)
    ).scalars().all()

    identified = 0
    for ctrl in controllers:
        if mqtt_client.publish_identify(
            controller_id=ctrl.topic_suffix or ctrl.controller_id,
            color=color,
            duration_seconds=duration,
        ):
            identified += 1

    return {"controllers_identified": identified}


# ---------------------------------------------------------------------------
# Status & Telemetry
# ---------------------------------------------------------------------------

@router.get("/status", response_model=list[LEDStatusResponse])
def get_all_controller_statuses(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[LEDStatusResponse]:
    controllers = db.execute(select(LEDController)).scalars().all()
    result = []
    for ctrl in controllers:
        cached = mqtt_client.get_controller_status(ctrl.topic_suffix or ctrl.controller_id)
        result.append(
            LEDStatusResponse(
                controller_id=ctrl.controller_id,
                status=cached.get("status", ctrl.status) if cached else ctrl.status,
                last_seen=ctrl.last_seen,
                ip_address=cached.get("ip_address", ctrl.ip_address) if cached else ctrl.ip_address,
                led_count=ctrl.led_count,
                wifi_rssi=cached.get("wifi_rssi", ctrl.wifi_rssi) if cached else ctrl.wifi_rssi,
            )
        )
    return result


# ---------------------------------------------------------------------------
# ESPHome Config Generation
# ---------------------------------------------------------------------------

@router.get("/esphome/{controller_id}.yaml")
def download_esphome_yaml(
    controller_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    ctrl = db.execute(
        select(LEDController).where(LEDController.controller_id == controller_id)
    ).scalar_one_or_none()

    led_count = ctrl.led_count if ctrl else 300

    from app.config import settings as app_settings

    yaml_content = generate_esphome_yaml(
        controller_id=controller_id,
        led_count=led_count,
        mqtt_broker=app_settings.mqtt_broker_host,
        mqtt_port=app_settings.mqtt_broker_port,
        mqtt_username=app_settings.mqtt_username,
        mqtt_password=app_settings.mqtt_password,
        mqtt_topic_prefix=app_settings.mqtt_topic_prefix,
    )
    return {"yaml": yaml_content, "filename": f"{controller_id}.yaml"}


@router.get("/esphome/secrets-template")
def download_secrets_template(
    _user: User = Depends(get_current_user),
) -> dict:
    return {"yaml": generate_secrets_template(), "filename": "secrets.h.template"}
