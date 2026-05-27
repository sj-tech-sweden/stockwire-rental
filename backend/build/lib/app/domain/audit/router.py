import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user
from app.domain.auth.models import User
from app.domain.audit.models import ActivityLog
from app.domain.audit.schemas import ActivityLogRead
from app.domain.inventory.models import InventoryAuditLog

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(get_current_user)])


@router.get("/activity", response_model=list[ActivityLogRead])
def list_activity_logs(
    limit: int = 200,
    entity_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[ActivityLogRead]:
    safe_limit = min(max(limit, 1), 1000)
    events: list[ActivityLogRead] = []

    if entity_type != "scan":
        query = select(ActivityLog).order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        if entity_type:
            query = query.where(ActivityLog.entity_type == entity_type)
        rows = list(db.scalars(query.limit(safe_limit)).all())
        events.extend(_to_activity_log_read(row) for row in rows)

    if entity_type is None or entity_type == "scan":
        scan_rows = list(
            db.scalars(
                select(InventoryAuditLog)
                .order_by(InventoryAuditLog.created_at.desc(), InventoryAuditLog.id.desc())
                .limit(safe_limit)
            ).all()
        )
        events.extend(_scan_audit_to_activity_log_read(row) for row in scan_rows)

    events.sort(key=lambda item: (item.created_at, item.id), reverse=True)
    limited = events[:safe_limit]

    user_ids = sorted({row.user_id for row in limited if row.user_id is not None})
    if user_ids:
        users = list(db.scalars(select(User).where(User.id.in_(user_ids))).all())
        users_by_id = {user.id: user.full_name for user in users}
        for row in limited:
            if row.user_id is not None:
                row.user_full_name = users_by_id.get(row.user_id)

    return limited


def _to_activity_log_read(row: ActivityLog) -> ActivityLogRead:
    details = None
    if row.details_json:
        try:
            details = json.loads(row.details_json)
        except json.JSONDecodeError:
            details = {"raw": row.details_json}

    return ActivityLogRead(
        id=row.id,
        created_at=row.created_at,
        user_id=row.user_id,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        action=row.action,
        message=row.message,
        details=details,
    )


def _scan_audit_to_activity_log_read(row: InventoryAuditLog) -> ActivityLogRead:
    details = None
    if row.details_json:
        try:
            details = json.loads(row.details_json)
        except json.JSONDecodeError:
            details = {"raw": row.details_json}

    if details is None:
        details = {}
    details.setdefault("source", row.source)
    details.setdefault("success", row.success)
    details.setdefault("scan_code", row.scan_code)
    details.setdefault("job_id", row.job_id)
    details.setdefault("zone_id", row.zone_id)
    details.setdefault("product_id", row.product_id)

    return ActivityLogRead(
        id=-row.id,
        created_at=row.created_at,
        user_id=row.user_id,
        entity_type="scan",
        entity_id=row.device_id,
        action=row.action,
        message=row.message,
        details=details,
    )
