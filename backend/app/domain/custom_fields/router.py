import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_admin
from app.domain.auth.models import User
from app.domain.custom_fields.models import CustomFieldDefinition, CustomFieldValue
from app.domain.custom_fields.schemas import (
    CustomFieldBulkValuesRead,
    CustomFieldDefinitionCreate,
    CustomFieldDefinitionRead,
    CustomFieldDefinitionUpdate,
    CustomFieldEntityTypes,
    CustomFieldValueRead,
    CustomFieldValuesRead,
    CustomFieldValuesUpsertRequest,
    CustomFieldValueTypes,
)
from app.domain.customers.models import Customer
from app.domain.inventory.models import Product
from app.domain.jobs.models import Job
from app.domain.venues.models import Venue

router = APIRouter(prefix="/custom-fields", tags=["custom-fields"], dependencies=[Depends(get_current_user)])


@router.get("/definitions", response_model=list[CustomFieldDefinitionRead])
def list_definitions(
    entity_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CustomFieldDefinitionRead]:
    query = select(CustomFieldDefinition).order_by(
        CustomFieldDefinition.entity_type,
        CustomFieldDefinition.label,
    )
    if entity_type:
        _validate_entity_type(entity_type)
        query = query.where(CustomFieldDefinition.entity_type == entity_type)
    return [_to_definition_read(definition) for definition in db.scalars(query).all()]


@router.post("/definitions", response_model=CustomFieldDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_definition(
    payload: CustomFieldDefinitionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CustomFieldDefinitionRead:
    _validate_entity_type(payload.entity_type)
    _validate_value_type(payload.value_type)

    definition = CustomFieldDefinition(
        entity_type=payload.entity_type,
        key=_normalize_key(payload.key),
        label=payload.label.strip(),
        value_type=payload.value_type,
        options_json=_to_options_json(payload.options),
        is_required=payload.is_required,
        is_active=payload.is_active,
    )
    db.add(definition)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Custom field key already exists for this entity")
    db.refresh(definition)
    return _to_definition_read(definition)


@router.put("/definitions/{definition_id}", response_model=CustomFieldDefinitionRead)
def update_definition(
    definition_id: int,
    payload: CustomFieldDefinitionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CustomFieldDefinitionRead:
    definition = db.get(CustomFieldDefinition, definition_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Custom field definition not found")

    updates = payload.model_dump(exclude_unset=True)
    if "value_type" in updates and updates["value_type"] is not None:
        _validate_value_type(updates["value_type"])

    if "key" in updates and updates["key"] is not None:
        definition.key = _normalize_key(updates["key"])
    if "label" in updates and updates["label"] is not None:
        definition.label = updates["label"].strip()
    if "value_type" in updates and updates["value_type"] is not None:
        definition.value_type = updates["value_type"]
    if "options" in updates:
        definition.options_json = _to_options_json(updates["options"] or [])
    if "is_required" in updates and updates["is_required"] is not None:
        definition.is_required = updates["is_required"]
    if "is_active" in updates and updates["is_active"] is not None:
        definition.is_active = updates["is_active"]

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Custom field key already exists for this entity")
    db.refresh(definition)
    return _to_definition_read(definition)


@router.delete("/definitions/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_definition(
    definition_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    definition = db.get(CustomFieldDefinition, definition_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Custom field definition not found")
    db.delete(definition)
    db.commit()
    return None


@router.get("/values/bulk", response_model=CustomFieldBulkValuesRead)
def list_all_entity_values_bulk(
    entity_type: str = Query(...),
    db: Session = Depends(get_db),
) -> CustomFieldBulkValuesRead:
    _validate_entity_type(entity_type)

    definitions = list(
        db.scalars(
            select(CustomFieldDefinition)
            .where(CustomFieldDefinition.entity_type == entity_type)
            .where(CustomFieldDefinition.is_active.is_(True))
        ).all()
    )
    definition_by_id = {d.id: d for d in definitions}

    values = list(
        db.scalars(
            select(CustomFieldValue)
            .where(CustomFieldValue.entity_type == entity_type)
        ).all()
    )

    values_by_entity_id: dict[str, dict[str, str | None]] = {}
    for value in values:
        defn = definition_by_id.get(value.field_definition_id)
        if defn is None:
            continue
        entity_str = str(value.entity_id)
        if entity_str not in values_by_entity_id:
            values_by_entity_id[entity_str] = {}
        values_by_entity_id[entity_str][defn.key] = value.value_text

    return CustomFieldBulkValuesRead(
        entity_type=entity_type,
        values_by_entity_id=values_by_entity_id,
    )


@router.get("/values/{entity_type}/{entity_id}", response_model=CustomFieldValuesRead)
def list_entity_values(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
) -> CustomFieldValuesRead:
    _validate_entity_type(entity_type)
    _ensure_entity_exists(entity_type, entity_id, db)

    definitions = list(
        db.scalars(
            select(CustomFieldDefinition)
            .where(CustomFieldDefinition.entity_type == entity_type)
            .where(CustomFieldDefinition.is_active.is_(True))
            .order_by(CustomFieldDefinition.label)
        ).all()
    )

    values = list(
        db.scalars(
            select(CustomFieldValue)
            .where(CustomFieldValue.entity_type == entity_type)
            .where(CustomFieldValue.entity_id == entity_id)
        ).all()
    )
    value_by_field_id = {value.field_definition_id: value for value in values}

    return CustomFieldValuesRead(
        entity_type=entity_type,
        entity_id=entity_id,
        values=[
            CustomFieldValueRead(
                id=existing.id if existing else None,
                field_definition_id=defn.id,
                key=defn.key,
                label=defn.label,
                value_type=defn.value_type,
                options=_from_options_json(defn.options_json),
                value=existing.value_text if existing else None,
            )
            for defn in definitions
            for existing in [value_by_field_id.get(defn.id)]
        ],
    )


@router.put("/values/{entity_type}/{entity_id}", response_model=CustomFieldValuesRead)
def upsert_entity_values(
    entity_type: str,
    entity_id: int,
    payload: CustomFieldValuesUpsertRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CustomFieldValuesRead:
    _validate_entity_type(entity_type)
    _ensure_entity_exists(entity_type, entity_id, db)

    definition_ids = {entry.field_definition_id for entry in payload.values}
    definitions = list(
        db.scalars(
            select(CustomFieldDefinition)
            .where(CustomFieldDefinition.id.in_(definition_ids))
            .where(CustomFieldDefinition.entity_type == entity_type)
        ).all()
    )
    definition_by_id = {definition.id: definition for definition in definitions}

    for entry in payload.values:
        definition = definition_by_id.get(entry.field_definition_id)
        if definition is None:
            raise HTTPException(status_code=404, detail=f"Field definition {entry.field_definition_id} not found")
        _validate_value_for_definition(entry.value, definition)

        existing = db.scalar(
            select(CustomFieldValue)
            .where(CustomFieldValue.field_definition_id == entry.field_definition_id)
            .where(CustomFieldValue.entity_type == entity_type)
            .where(CustomFieldValue.entity_id == entity_id)
        )

        if entry.value is None or entry.value == "":
            if existing is not None:
                db.execute(
                    delete(CustomFieldValue).where(CustomFieldValue.id == existing.id)
                )
            continue

        if existing is None:
            existing = CustomFieldValue(
                field_definition_id=entry.field_definition_id,
                entity_type=entity_type,
                entity_id=entity_id,
                value_text=entry.value,
            )
            db.add(existing)
        else:
            existing.value_text = entry.value

    db.commit()
    return list_entity_values(entity_type=entity_type, entity_id=entity_id, db=db)


@router.post("/definitions/prefill-product-cable", response_model=list[CustomFieldDefinitionRead])
def prefill_product_cable_definitions(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[CustomFieldDefinitionRead]:
    common_connector_options = [
        # Power
        "PowerCON True1",
        "PowerCON 20A",
        "Schuko",
        "CEE 16A",
        "CEE 32A",
        "CEE 64A",
        "CEE 128A",
        "IEC C13",
        "IEC C19",
        # DMX
        "XLR 3-pin",
        "XLR 5-pin",
        # Data
        "EtherCON RJ45",
        "RJ45",
        "USB-A",
        "USB-C",
        # Video
        "BNC",
        "SDI BNC",
        "HDMI Type A",
        "DisplayPort",
        "HDMI"
        # Audio
        "XLR",
        "TRS 6.35mm",
        "TS 6.35mm",
        "RCA",
        "Speakon NL2",
        "Speakon NL4",
    ]

    defaults = [
        {
            "key": "cable_type",
            "label": "Cable Type",
            "value_type": CustomFieldValueTypes.SELECT,
            "options": ["XLR", "PowerCon", "DMX", "Ethernet", "TRS", "BNC", "HDMI", "Other"],
        },
        {
            "key": "connector_a",
            "label": "Connector A",
            "value_type": CustomFieldValueTypes.SELECT,
            "options": common_connector_options,
        },
        {
            "key": "connector_b",
            "label": "Connector B",
            "value_type": CustomFieldValueTypes.SELECT,
            "options": common_connector_options,
        },
        {
            "key": "length_m",
            "label": "Length (m)",
            "value_type": CustomFieldValueTypes.NUMBER,
            "options": [],
        },
        {
            "key": "cable_area_mm2",
            "label": "Cable Area (mm²)",
            "value_type": CustomFieldValueTypes.NUMBER,
            "options": [],
        },
        {
            "key": "is_balanced",
            "label": "Balanced",
            "value_type": CustomFieldValueTypes.BOOLEAN,
            "options": [],
        },
    ]

    for item in defaults:
        existing = db.scalar(
            select(CustomFieldDefinition)
            .where(CustomFieldDefinition.entity_type == CustomFieldEntityTypes.PRODUCT)
            .where(CustomFieldDefinition.key == item["key"])
        )
        if existing is None and item["key"] == "cable_area_mm2":
            # Backward compatibility: migrate legacy AWG field key to mm² field.
            existing = db.scalar(
                select(CustomFieldDefinition)
                .where(CustomFieldDefinition.entity_type == CustomFieldEntityTypes.PRODUCT)
                .where(CustomFieldDefinition.key == "awg")
            )
        if existing is None:
            existing = CustomFieldDefinition(
                entity_type=CustomFieldEntityTypes.PRODUCT,
                key=item["key"],
                label=item["label"],
                value_type=item["value_type"],
                options_json=_to_options_json(item["options"]),
                is_required=False,
                is_active=True,
            )
            db.add(existing)
        else:
            existing.key = item["key"]
            existing.label = item["label"]
            existing.value_type = item["value_type"]
            existing.options_json = _to_options_json(item["options"])
            existing.is_active = True

    db.commit()

    definitions = list(
        db.scalars(
            select(CustomFieldDefinition)
            .where(CustomFieldDefinition.entity_type == CustomFieldEntityTypes.PRODUCT)
            .order_by(CustomFieldDefinition.label)
        ).all()
    )
    return [_to_definition_read(definition) for definition in definitions]


def _normalize_key(value: str) -> str:
    key = value.strip().lower().replace(" ", "_")
    if not key:
        raise HTTPException(status_code=400, detail="Field key cannot be empty")
    return key


def _validate_entity_type(entity_type: str) -> None:
    if entity_type not in CustomFieldEntityTypes.ALL:
        raise HTTPException(status_code=400, detail="Invalid entity_type")


def _validate_value_type(value_type: str) -> None:
    if value_type not in CustomFieldValueTypes.ALL:
        raise HTTPException(status_code=400, detail="Invalid value_type")


def _to_options_json(options: list[str]) -> str:
    normalized = [option.strip() for option in options if option and option.strip()]
    return json.dumps(normalized)


def _from_options_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        return []
    return []


def _to_definition_read(definition: CustomFieldDefinition) -> CustomFieldDefinitionRead:
    return CustomFieldDefinitionRead(
        id=definition.id,
        entity_type=definition.entity_type,
        key=definition.key,
        label=definition.label,
        value_type=definition.value_type,
        options=_from_options_json(definition.options_json),
        is_required=definition.is_required,
        is_active=definition.is_active,
        created_at=definition.created_at,
    )


def _ensure_entity_exists(entity_type: str, entity_id: int, db: Session) -> None:
    if entity_type == CustomFieldEntityTypes.PRODUCT:
        entity = db.get(Product, entity_id)
    elif entity_type == CustomFieldEntityTypes.JOB:
        entity = db.get(Job, entity_id)
    elif entity_type == CustomFieldEntityTypes.CUSTOMER:
        entity = db.get(Customer, entity_id)
    else:
        entity = db.get(Venue, entity_id)

    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")


def _validate_value_for_definition(value: str | None, definition: CustomFieldDefinition) -> None:
    if value is None or value == "":
        if definition.is_required:
            raise HTTPException(status_code=400, detail=f"Field '{definition.label}' is required")
        return

    value_type = definition.value_type
    if value_type == CustomFieldValueTypes.NUMBER:
        try:
            float(value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Field '{definition.label}' expects a number")
    elif value_type == CustomFieldValueTypes.BOOLEAN:
        if str(value).lower() not in {"true", "false", "1", "0", "yes", "no"}:
            raise HTTPException(status_code=400, detail=f"Field '{definition.label}' expects a boolean")
    elif value_type == CustomFieldValueTypes.DATE:
        parts = str(value).split("-")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise HTTPException(status_code=400, detail=f"Field '{definition.label}' expects YYYY-MM-DD")
    elif value_type == CustomFieldValueTypes.SELECT:
        allowed = set(_from_options_json(definition.options_json))
        if allowed and value not in allowed:
            raise HTTPException(status_code=400, detail=f"Field '{definition.label}' must be one of: {', '.join(sorted(allowed))}")
