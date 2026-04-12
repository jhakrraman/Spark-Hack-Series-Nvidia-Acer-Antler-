"""Camera catalog + SSE stream of per-camera frame updates."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, List

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..schemas import Camera
from ..state import STATE, subscribe_camera, unsubscribe_camera

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=List[Camera])
async def list_cameras() -> List[Camera]:
    return list(STATE.cameras.values())


@router.get("/{camera_id}", response_model=Camera)
async def get_camera(camera_id: str) -> Camera:
    cam = STATE.cameras.get(camera_id)
    if cam is None:
        raise HTTPException(status_code=404, detail="camera not found")
    return cam


async def _camera_event_stream() -> AsyncIterator[dict]:
    q = subscribe_camera()
    try:
        yield {
            "event": "hello",
            "data": json.dumps(
                {
                    "cameras": len(STATE.cameras),
                    "modelVersion": STATE.model_version,
                }
            ),
        }
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=20.0)
                yield {"event": "message", "data": json.dumps(msg)}
            except asyncio.TimeoutError:
                yield {"event": "heartbeat", "data": "{}"}
    finally:
        unsubscribe_camera(q)


@router.get("/stream")
async def stream_cameras():
    return EventSourceResponse(_camera_event_stream())
