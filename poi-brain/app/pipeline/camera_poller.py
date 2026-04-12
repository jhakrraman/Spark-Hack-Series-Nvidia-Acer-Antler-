"""Polls NYC DOT traffic camera snapshots and feeds them into the NIM VLM.

Runs as an asyncio background task. For each camera in the state's catalog,
it fetches a JPEG every `camera_poll_interval_s` seconds, calls the NIM
client, looks up the camera's current risk context, optionally enriches
via retrieval, and publishes the result to the SSE channel.

Robust to offline cameras: transient 404/500s are logged and the camera is
skipped for this cycle. If all cameras fail, the poller keeps retrying on
the next cycle.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import random
from datetime import datetime, timezone
from typing import List

import httpx

from ..config import settings
from ..schemas import Camera, FrameEvent, RiskScore
from ..state import STATE, FrameMemory, publish_camera_update
from ..vlm import get_vlm_client
from .retrieval import get_index

log = logging.getLogger("poi.poller")


def _stub_jpeg_b64() -> str:
    """Return a tiny gray JPEG as base64, used when a camera is offline."""
    gray = bytes.fromhex(
        "ffd8ffe000104a46494600010101004800480000ffdb004300080606070605080707"
        "07090908" + "0a" * 48 + "ffd9"
    )
    return base64.b64encode(gray).decode()


async def _fetch_jpeg(client: httpx.AsyncClient, camera: Camera) -> str | None:
    if not camera.snapshotUrl:
        return None
    try:
        resp = await client.get(camera.snapshotUrl, timeout=8.0)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode()
    except Exception as err:
        log.debug("[poller] %s fetch failed: %s", camera.id, err)
        return None


async def _analyze(camera: Camera, jpeg_b64: str) -> List[FrameEvent]:
    vlm = get_vlm_client()
    risk = STATE.risk_by_camera.get(camera.id)

    def _call():
        return vlm.analyze_frame(jpeg_b64, transcript="", risk_context=risk)

    try:
        events, _raw = await asyncio.to_thread(_call)
        return events
    except Exception as err:
        log.warning("[poller] VLM failed for %s: %s", camera.id, err)
        return []


POLLER_MAX_CAMERAS = 12


async def _poll_once(client: httpx.AsyncClient) -> None:
    all_cameras = list(STATE.cameras.values())
    if not all_cameras:
        return

    # The map/dashboard can show hundreds of cameras, but the poller only
    # processes a small rotating window each cycle to avoid overloading
    # the VLM. Each cycle picks the next POLLER_MAX_CAMERAS cameras in a
    # round-robin. Risk scores + snapshot thumbnails accumulate over time.
    cycle = getattr(_poll_once, "_cycle", 0)
    start = (cycle * POLLER_MAX_CAMERAS) % len(all_cameras)
    cameras = all_cameras[start : start + POLLER_MAX_CAMERAS]
    _poll_once._cycle = cycle + 1  # type: ignore[attr-defined]

    index = get_index()

    for cam in cameras:
        jpeg_b64 = await _fetch_jpeg(client, cam)
        if jpeg_b64 is None:
            jpeg_b64 = _stub_jpeg_b64()
            cam.online = False
        else:
            cam.online = True

        events = await _analyze(cam, jpeg_b64)

        retrieved = []
        if cam.latLng and any(e.isDangerous for e in events):
            try:
                retrieved = index.search(cam.latLng)
            except Exception as err:
                log.debug("[poller] retrieval failed: %s", err)

        STATE.frame_memory[cam.id] = FrameMemory(
            latest_thumb_b64=jpeg_b64,
            latest_events=[e.model_dump() for e in events],
            last_updated=datetime.now(tz=timezone.utc).timestamp(),
        )

        await publish_camera_update(
            {
                "cameraId": cam.id,
                "latestThumbB64": jpeg_b64,
                "latestEvents": [e.model_dump() for e in events],
                "riskScoreAtTime": (
                    STATE.risk_by_camera[cam.id].score
                    if cam.id in STATE.risk_by_camera
                    else None
                ),
                "retrievedContext": [r.model_dump() for r in retrieved],
            }
        )


async def run_poller_forever() -> None:
    jitter_s = 0.15
    async with httpx.AsyncClient(follow_redirects=True) as client:
        while True:
            try:
                await _poll_once(client)
            except Exception as err:
                log.exception("[poller] cycle failed: %s", err)
            await asyncio.sleep(
                settings.camera_poll_interval_s + random.uniform(-jitter_s, jitter_s)
            )
