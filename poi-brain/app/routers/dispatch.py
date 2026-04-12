"""Patrol route dispatch — cuOpt-backed (or greedy fallback) VRP over the heatmap."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter

from ..pipeline.solve_cuopt import solve_routes
from ..schemas import PatrolRoute
from ..state import STATE

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("/current", response_model=List[PatrolRoute])
async def current_routes():
    if not STATE.patrol_routes:
        STATE.patrol_routes = solve_routes()
    return STATE.patrol_routes


@router.post("/resolve", response_model=List[PatrolRoute])
async def resolve_routes():
    STATE.patrol_routes = solve_routes()
    return STATE.patrol_routes
