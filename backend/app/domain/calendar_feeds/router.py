import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from icalendar import Calendar, Event
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_admin
from app.domain.auth.models import User
from app.domain.calendar_feeds.models import CalendarFeed
from app.domain.calendar_feeds.schemas import CalendarFeedCreate, CalendarFeedRead, CalendarFeedUpdate
from app.domain.crew.models import CrewMember, JobCrewAssignment, JobCrewRequirement
from app.domain.jobs.models import Job


router = APIRouter(prefix="/calendar", tags=["calendar"])


def _generate_token() -> str:
    return secrets.token_hex(32)


def _build_ics_response(cal: Calendar) -> Response:
    return Response(
        content=cal.to_ical(),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=feed.ics"},
    )


def _add_job_event(cal: Calendar, job: Job) -> None:
    event = Event()
    event.add("uid", f"job-{job.id}@stockwire")
    event.add("summary", job.job_code)
    if job.description:
        event.add("description", job.description)
    if job.start_date:
        event.add("dtstart", job.start_date)
    if job.end_date:
        event.add("dtend", job.end_date + timedelta(days=1))
    if job.venue_name:
        event.add("location", job.venue_name)
    event.add("dtstamp", datetime.now(timezone.utc))
    cal.add_component(event)


def _add_crew_event(cal: Calendar, assignment: JobCrewAssignment, crew_name: str) -> None:
    job = assignment.job_crew_requirement.job
    if not job or not job.start_date:
        return
    event = Event()
    event.add("uid", f"crew-{assignment.id}@stockwire")
    role_name = ""
    if assignment.job_crew_requirement.crew_role:
        role_name = f" ({assignment.job_crew_requirement.crew_role.name})"
    event.add("summary", f"{crew_name}{role_name} - {job.job_code}")
    if job.description:
        event.add("description", job.description)
    event.add("dtstart", job.start_date)
    if job.end_date:
        event.add("dtend", job.end_date + timedelta(days=1))
    if job.venue_name:
        event.add("location", job.venue_name)
    event.add("dtstamp", datetime.now(timezone.utc))
    cal.add_component(event)


@router.get("/{token}/feed.ics")
def get_feed(token: str, db: Session = Depends(get_db)) -> Response:
    feed = db.execute(
        select(CalendarFeed).where(CalendarFeed.token == token, CalendarFeed.is_active.is_(True))
    ).scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")

    cal = Calendar()
    cal.add("prodid", "-//Stockwire//Calendar Feed//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", feed.name)

    if feed.feed_type == "jobs":
        jobs = db.execute(
            select(Job).where(Job.start_date.isnot(None)).order_by(Job.start_date)
        ).scalars().all()
        for job in jobs:
            _add_job_event(cal, job)

    elif feed.feed_type == "crew":
        query = (
            select(JobCrewAssignment)
            .join(JobCrewRequirement, JobCrewRequirement.id == JobCrewAssignment.job_crew_requirement_id)
            .join(Job, Job.id == JobCrewRequirement.job_id)
            .where(Job.start_date.isnot(None))
            .options(
                selectinload(JobCrewAssignment.crew_member),
                selectinload(JobCrewAssignment.job_crew_requirement)
                .selectinload(JobCrewRequirement.crew_role),
                selectinload(JobCrewAssignment.job_crew_requirement)
                .selectinload(JobCrewRequirement.job),
            )
        )
        if feed.crew_member_id:
            query = query.where(JobCrewAssignment.crew_member_id == feed.crew_member_id)
        assignments = db.execute(query).scalars().all()
        for assignment in assignments:
            _add_crew_event(cal, assignment, assignment.crew_member.name)

    return _build_ics_response(cal)


@router.get("/my-feed", response_model=CalendarFeedRead | None)
def get_my_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarFeedRead | None:
    """Return the crew calendar feed for the current user's linked crew member, or None."""
    member = db.execute(
        select(CrewMember).where(CrewMember.user_id == current_user.id)
    ).scalar_one_or_none()
    if not member:
        return None
    feed = db.execute(
        select(CalendarFeed).where(
            CalendarFeed.feed_type == "crew",
            CalendarFeed.crew_member_id == member.id,
        )
    ).scalar_one_or_none()
    if feed:
        return CalendarFeedRead.model_validate(feed)
    feed = CalendarFeed(
        name="Crew Calendar",
        token=_generate_token(),
        feed_type="crew",
        crew_member_id=member.id,
    )
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return CalendarFeedRead.model_validate(feed)


# ── Admin management endpoints ────────────────────────────────────────────────


@router.get("/feeds", response_model=list[CalendarFeedRead])
def list_feeds(
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
) -> list[CalendarFeedRead]:
    feeds = db.execute(
        select(CalendarFeed).order_by(CalendarFeed.id)
    ).scalars().all()
    return [CalendarFeedRead.model_validate(f) for f in feeds]


@router.post("/feeds", response_model=CalendarFeedRead, status_code=status.HTTP_201_CREATED)
def create_feed(
    payload: CalendarFeedCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
) -> CalendarFeedRead:
    if payload.feed_type not in ("crew", "jobs"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="feed_type must be 'crew' or 'jobs'",
        )
    feed = CalendarFeed(
        name=payload.name,
        token=_generate_token(),
        feed_type=payload.feed_type,
        crew_member_id=payload.crew_member_id,
    )
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return CalendarFeedRead.model_validate(feed)


@router.put("/feeds/{feed_id}", response_model=CalendarFeedRead)
def update_feed(
    feed_id: int,
    payload: CalendarFeedUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
) -> CalendarFeedRead:
    feed = db.get(CalendarFeed, feed_id)
    if not feed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    if payload.name is not None:
        feed.name = payload.name
    if payload.feed_type is not None:
        if payload.feed_type not in ("crew", "jobs"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="feed_type must be 'crew' or 'jobs'",
            )
        feed.feed_type = payload.feed_type
    if payload.crew_member_id is not None:
        feed.crew_member_id = payload.crew_member_id
    if payload.is_active is not None:
        feed.is_active = payload.is_active
    db.commit()
    db.refresh(feed)
    return CalendarFeedRead.model_validate(feed)


@router.delete("/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feed(
    feed_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
) -> None:
    feed = db.get(CalendarFeed, feed_id)
    if not feed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    db.delete(feed)
    db.commit()


@router.post("/feeds/{feed_id}/regenerate-token", response_model=CalendarFeedRead)
def regenerate_token(
    feed_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
) -> CalendarFeedRead:
    feed = db.get(CalendarFeed, feed_id)
    if not feed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found")
    feed.token = _generate_token()
    db.commit()
    db.refresh(feed)
    return CalendarFeedRead.model_validate(feed)


@router.get("/crew-member/{crew_member_id}/feed", response_model=CalendarFeedRead)
def get_or_create_crew_feed(
    crew_member_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
) -> CalendarFeedRead:
    feed = db.execute(
        select(CalendarFeed).where(
            CalendarFeed.feed_type == "crew",
            CalendarFeed.crew_member_id == crew_member_id,
        )
    ).scalar_one_or_none()
    if feed:
        return CalendarFeedRead.model_validate(feed)
    feed = CalendarFeed(
        name=f"Crew Member {crew_member_id}",
        token=_generate_token(),
        feed_type="crew",
        crew_member_id=crew_member_id,
    )
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return CalendarFeedRead.model_validate(feed)
