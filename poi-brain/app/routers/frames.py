"""Frame analysis endpoints — HTTP POST for one-shot analysis, websocket for
streaming frame ingest from the Next.js laptop (fallback path when the DGX
poller isn't the source of truth)."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from ..schemas import FrameAnalyzeRequest, FrameAnalyzeResponse, FrameEvent
from ..state import STATE
from ..vlm import get_vlm_client
from ..pipeline.retrieval import get_index

router = APIRouter(prefix="/frames", tags=["frames"])
log = logging.getLogger("poi.frames")


def _enrich(camera_id: Optional[str], events, raw: str) -> FrameAnalyzeResponse:
    risk = STATE.risk_by_camera.get(camera_id or "")
    score = risk.score if risk else None
    retrieved = []
    cam = STATE.cameras.get(camera_id or "")
    if cam and cam.latLng and any(e.isDangerous for e in events):
        try:
            retrieved = get_index().search(cam.latLng)
        except Exception as err:
            log.debug("[frames] retrieval failed: %s", err)
    return FrameAnalyzeResponse(
        events=events,
        riskScoreAtTime=score,
        retrievedContext=retrieved,
        rawResponse=raw,
    )


@router.post("/analyze", response_model=FrameAnalyzeResponse)
async def analyze(req: FrameAnalyzeRequest):
    if not req.frameJpegB64:
        raise HTTPException(status_code=400, detail="frameJpegB64 required")

    vlm = get_vlm_client()
    try:
        events, raw = await asyncio.to_thread(
            vlm.analyze_frame,
            req.frameJpegB64,
            req.transcript,
            STATE.risk_by_camera.get(req.cameraId or ""),
        )
    except Exception as err:
        log.error("[frames] VLM failed: %s", err)
        raise HTTPException(status_code=502, detail=f"vlm failure: {err}")

    return _enrich(req.cameraId, events, raw)


@router.websocket("/ws")
async def ws_frames(ws: WebSocket):
    await ws.accept()
    vlm = get_vlm_client()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                await ws.send_json({"error": "invalid json"})
                continue

            frame_b64 = msg.get("frameJpegB64") or msg.get("base64")
            camera_id = msg.get("cameraId")
            transcript = msg.get("transcript", "")
            if not frame_b64:
                await ws.send_json({"error": "frameJpegB64 missing"})
                continue

            try:
                events, raw_resp = await asyncio.to_thread(
                    vlm.analyze_frame,
                    frame_b64,
                    transcript,
                    STATE.risk_by_camera.get(camera_id or ""),
                )
            except Exception as err:
                await ws.send_json({"error": str(err)})
                continue

            response = _enrich(camera_id, events, raw_resp)
            await ws.send_text(response.model_dump_json())
    except WebSocketDisconnect:
        return
