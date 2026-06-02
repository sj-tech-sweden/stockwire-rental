from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import asyncio

import anyio

from app.domain.realtime.hub import realtime_hub


def emit_realtime_event(topic: str, payload: dict[str, Any] | None = None) -> None:
    event = {
        "topic": topic,
        "payload": payload or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        anyio.from_thread.run(realtime_hub.broadcast, event)
        return
    except RuntimeError:
        pass

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    loop.create_task(realtime_hub.broadcast(event))
