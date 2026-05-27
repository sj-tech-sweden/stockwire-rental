import json

from sqlalchemy.orm import Session

from app.domain.audit.models import ActivityLog
from app.domain.realtime.events import emit_realtime_event


def record_activity(
    db: Session,
    *,
    user_id: int | None,
    entity_type: str,
    entity_id: int | None,
    action: str,
    message: str,
    details: dict | None = None,
) -> None:
    db.add(
        ActivityLog(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            message=message,
            details_json=json.dumps(details, ensure_ascii=True) if details else None,
        )
    )
    emit_realtime_event(
        "activity.updated",
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "message": message,
        },
    )
