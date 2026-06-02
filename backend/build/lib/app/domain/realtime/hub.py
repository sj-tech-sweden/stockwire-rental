from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import asyncio

from fastapi import WebSocket


@dataclass
class RealtimeConnection:
    websocket: WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, event: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._connections)

        stale: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(event)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                for ws in stale:
                    self._connections.discard(ws)


realtime_hub = RealtimeHub()
