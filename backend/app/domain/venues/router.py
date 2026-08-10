from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.pagination import PaginationParams, PaginatedResponse, paginate_query
from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.audit.service import record_activity
from app.domain.jobs.models import Job
from app.domain.realtime.events import emit_realtime_event
from app.domain.venues.models import Venue
from app.domain.venues.schemas import VenueCreate, VenueRead, VenueUpdate
from app.services.metrics import created_total, deleted_total, entities_count

router = APIRouter(prefix="/venues", tags=["venues"], dependencies=[Depends(get_current_user)])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "venues", "status": "scaffolded"}


@router.get("", response_model=PaginatedResponse[VenueRead])
def list_venues(
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[VenueRead]:
    stmt = select(Venue).order_by(Venue.name, Venue.id)
    items, total = paginate_query(db, stmt, pagination.skip, pagination.limit)
    return PaginatedResponse(
        items=items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + pagination.limit) < total,
    )


@router.post("", response_model=VenueRead)
def create_venue(payload: VenueCreate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Venue:
    venue = Venue(**payload.model_dump())
    db.add(venue)
    db.commit()
    db.refresh(venue)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="venue",
        entity_id=venue.id,
        action="create",
        message_format="venue_created",
        message_params={"name": venue.name},
        details={"name": venue.name},
    )
    emit_realtime_event("venues.updated", {"entity": "venue", "action": "create", "id": venue.id})
    created_total.labels(entity="venue").inc()
    entities_count.labels(entity="venue").inc()
    db.commit()
    return venue


@router.put("/{venue_id}", response_model=VenueRead)
def update_venue(venue_id: int, payload: VenueUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> Venue:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(venue, key, value)
    db.commit()
    db.refresh(venue)
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="venue",
        entity_id=venue.id,
        action="update",
        message_format="venue_updated",
        message_params={"name": venue.name},
        details={"name": venue.name},
    )
    emit_realtime_event("venues.updated", {"entity": "venue", "action": "update", "id": venue.id})
    db.commit()
    return venue


@router.delete("/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_venue(venue_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_editor)) -> None:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")

    venue_name = venue.name
    jobs = list(db.scalars(select(Job).where(Job.venue_id == venue_id)).all())
    for job in jobs:
        job.venue_id = None
        job.venue_name = None

    db.delete(venue)
    db.commit()
    record_activity(
        db,
        user_id=current_user.id,
        entity_type="venue",
        entity_id=venue_id,
        action="delete",
        message_format="venue_deleted",
        message_params={"name": venue_name},
        details={"name": venue_name},
    )
    emit_realtime_event("venues.updated", {"entity": "venue", "action": "delete", "id": venue_id})
    deleted_total.labels(entity="venue").inc()
    entities_count.labels(entity="venue").dec()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)