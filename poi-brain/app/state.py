"""Shared in-memory state owned by the FastAPI process.

Holds the camera catalog, latest frame thumbnails, latest risk scores, the
trained model handle, the fused dataframe (cuDF or pandas), and simple pub/sub
queues for SSE streams.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from .schemas import Camera, HexCell, PatrolRoute, RiskScore


@dataclass
class FrameMemory:
    latest_thumb_b64: Optional[str] = None
    latest_events: list = field(default_factory=list)
    last_updated: float = 0.0


@dataclass
class AppState:
    cameras: Dict[str, Camera] = field(default_factory=dict)
    risk_by_camera: Dict[str, RiskScore] = field(default_factory=dict)
    frame_memory: Dict[str, FrameMemory] = field(default_factory=lambda: defaultdict(FrameMemory))
    hex_cells: List[HexCell] = field(default_factory=list)
    patrol_routes: List[PatrolRoute] = field(default_factory=list)
    model_version: str = "cuml-xgb@stub"
    fused_df: Any = None
    model: Any = None
    retrieval_index: Any = None
    started_at: float = field(default_factory=time.time)

    risk_subscribers: List[asyncio.Queue] = field(default_factory=list)
    camera_subscribers: List[asyncio.Queue] = field(default_factory=list)
    recent_risk_events: Deque = field(default_factory=lambda: deque(maxlen=200))


STATE = AppState()


async def publish_risk(risk: RiskScore) -> None:
    STATE.risk_by_camera[risk.cameraId] = risk
    STATE.recent_risk_events.append(risk)
    dead = []
    for q in STATE.risk_subscribers:
        try:
            q.put_nowait(risk)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            STATE.risk_subscribers.remove(q)
        except ValueError:
            pass


async def publish_camera_update(payload: dict) -> None:
    dead = []
    for q in STATE.camera_subscribers:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            STATE.camera_subscribers.remove(q)
        except ValueError:
            pass


def subscribe_risk() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=256)
    STATE.risk_subscribers.append(q)
    return q


def subscribe_camera() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=256)
    STATE.camera_subscribers.append(q)
    return q


def unsubscribe_risk(q: asyncio.Queue) -> None:
    try:
        STATE.risk_subscribers.remove(q)
    except ValueError:
        pass


def unsubscribe_camera(q: asyncio.Queue) -> None:
    try:
        STATE.camera_subscribers.remove(q)
    except ValueError:
        pass
