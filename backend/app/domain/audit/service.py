import json

from sqlalchemy.orm import Session

from app.domain.audit.models import ActivityLog
from app.domain.realtime.events import emit_realtime_event


def _format_message_from_format(message_format: str, message_params: dict | None) -> str:
    if not message_params:
        return message_format
    try:
        return message_format.format(**message_params)
    except (KeyError, ValueError, AttributeError):
        return message_format


def record_activity(
    db: Session,
    *,
    user_id: int | None,
    entity_type: str,
    entity_id: int | None,
    action: str,
    message: str | None = None,
    message_format: str | None = None,
    message_params: dict | None = None,
    details: dict | None = None,
) -> None:
    if message_format and message is None:
        message = _format_message_from_format(message_format, message_params)

    params_json = json.dumps(message_params, ensure_ascii=True) if message_params else None

    db.add(
        ActivityLog(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            message=message or '',
            message_format=message_format,
            message_params_json=params_json,
            details_json=json.dumps(details, ensure_ascii=True) if details else None,
        )
    )
    emit_realtime_event(
        "activity.updated",
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "message": message or '',
        },
    )
