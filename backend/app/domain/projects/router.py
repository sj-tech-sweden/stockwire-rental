from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.customers.models import Customer
from app.domain.jobs.models import Job
from app.domain.projects.models import Project
from app.domain.venues.models import Venue
from app.domain.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from app.domain.realtime.events import emit_realtime_event
from app.services.metrics import created_total, deleted_total, entities_count

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(get_current_user)])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "projects", "status": "scaffolded"}


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())).all())


@router.post("", response_model=ProjectRead)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> Project:
    data = payload.model_dump()
    if data.get("customer_id") is not None:
        customer = db.get(Customer, data["customer_id"])
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
    if data.get("venue_id") is not None:
        venue = db.get(Venue, data["venue_id"])
        if venue is None:
            raise HTTPException(status_code=404, detail="Venue not found")

    project = Project(**data)
    db.add(project)
    db.commit()
    db.refresh(project)
    emit_realtime_event("projects.updated", {"entity": "project", "action": "create", "id": project.id})
    created_total.labels(entity="project").inc()
    entities_count.labels(entity="project").inc()
    db.commit()
    return project


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    data = payload.model_dump(exclude_unset=True)
    if "customer_id" in data and data["customer_id"] is not None:
        customer = db.get(Customer, data["customer_id"])
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
    if "venue_id" in data and data["venue_id"] is not None:
        venue = db.get(Venue, data["venue_id"])
        if venue is None:
            raise HTTPException(status_code=404, detail="Venue not found")

    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    emit_realtime_event("projects.updated", {"entity": "project", "action": "update", "id": project.id})
    db.commit()
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db), _: User = Depends(require_editor)) -> None:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    jobs = list(db.scalars(select(Job).where(Job.project_id == project_id)).all())
    for job in jobs:
        job.project_id = None

    db.delete(project)
    db.commit()
    emit_realtime_event("projects.updated", {"entity": "project", "action": "delete", "id": project_id})
    deleted_total.labels(entity="project").inc()
    entities_count.labels(entity="project").dec()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
