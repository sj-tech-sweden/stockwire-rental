from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.models import User
from app.domain.auth.schemas import UserCreate, UserSummary

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "auth", "status": "scaffolded"}


@router.get("/users", response_model=list[UserSummary])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())


@router.post("/users", response_model=UserSummary)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserSummary)
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
