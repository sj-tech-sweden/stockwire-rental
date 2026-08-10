"""Shared pagination utilities for list endpoints."""

from typing import TypeVar, Generic

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class PaginationParams:
    """Dependency for skip/limit pagination."""

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    ):
        self.skip = skip
        self.limit = limit


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response envelope."""

    items: list[T]
    total: int
    skip: int
    limit: int
    has_more: bool


def paginate_query(
    db: Session,
    stmt,
    skip: int,
    limit: int,
) -> tuple[list, int]:
    """Execute a paginated query and return (items, total_count)."""
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.offset(skip).limit(limit)).all())
    return items, int(total)
