from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.domain.auth.security import decode_token
from app.domain.realtime.hub import realtime_hub

router = APIRouter(prefix="/realtime", tags=["realtime"])


@router.websocket("/ws")
async def websocket_updates(websocket: WebSocket, token: str | None = None) -> None:
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return

    try:
        decode_token(token)
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await realtime_hub.connect(websocket)

    try:
        while True:
            # Keep socket open; client may send ping frames/messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await realtime_hub.disconnect(websocket)
