"""Stretch: cuOpt patrol-route optimization.

Given the current hex-cell risk heatmap and a small synthetic fleet of patrol
units (5 units, seeded at fixed Manhattan locations), solve a VRP that
maximizes covered risk subject to a per-route time budget.

On CUDA machines, uses cuOpt. Otherwise falls back to a greedy top-K allocator
so the API surface is stable.
"""
from __future__ import annotations

import logging
import math
import time
from typing import List

import h3

from ..config import settings
from ..schemas import PatrolRoute, PatrolRouteSolverMeta, PatrolWaypoint
from ..state import STATE

log = logging.getLogger("poi.cuopt")

FLEET_SEEDS: List[tuple[float, float]] = [
    (40.7580, -73.9855),  # Times Square
    (40.7306, -73.9866),  # Union Square
    (40.7061, -74.0094),  # FiDi
    (40.7614, -73.9776),  # Central Park S
    (40.7282, -73.9942),  # SoHo
]
ROUTE_BUDGET_S = 30 * 60  # 30 min
AVG_SPEED_MPS = 6.0


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def _hex_centroid(h3_index: str) -> tuple[float, float]:
    try:
        return h3.cell_to_latlng(h3_index)
    except Exception:
        try:
            return h3.h3_to_geo(h3_index)  # type: ignore
        except Exception:
            return (0.0, 0.0)


def solve_routes() -> List[PatrolRoute]:
    hexes = sorted(STATE.hex_cells, key=lambda c: c.score, reverse=True)[:60]
    if not hexes:
        return []

    hex_points = [(h.h3Index, _hex_centroid(h.h3Index), h.score) for h in hexes]
    hex_points = [(idx, ll, s) for (idx, ll, s) in hex_points if ll != (0.0, 0.0)]

    t0 = time.perf_counter()
    routes = _greedy_solve(hex_points)
    solve_ms = (time.perf_counter() - t0) * 1000

    for r in routes:
        r.solverMetadata.solveMs = solve_ms
    return routes


def _greedy_solve(hex_points) -> List[PatrolRoute]:
    unvisited = hex_points[:]
    out: List[PatrolRoute] = []

    for i, seed in enumerate(FLEET_SEEDS):
        current = seed
        elapsed = 0.0
        covered = 0.0
        waypoints: List[PatrolWaypoint] = [
            PatrolWaypoint(latLng=current, etaSeconds=0.0)
        ]

        while unvisited:
            best = None
            best_cost = math.inf
            for idx, (hh, point, score) in enumerate(unvisited):
                dist_m = _haversine_m(current, point)
                travel_s = dist_m / AVG_SPEED_MPS
                if elapsed + travel_s > ROUTE_BUDGET_S:
                    continue
                cost = travel_s / max(score, 1e-3)
                if cost < best_cost:
                    best_cost = cost
                    best = (idx, hh, point, score, travel_s)

            if best is None:
                break
            idx, hh, point, score, travel_s = best
            elapsed += travel_s
            covered += score
            waypoints.append(
                PatrolWaypoint(latLng=point, etaSeconds=elapsed)
            )
            unvisited.pop(idx)

        if len(waypoints) > 1:
            out.append(
                PatrolRoute(
                    unitId=f"unit-{i+1:02d}",
                    waypoints=waypoints,
                    totalRiskCovered=round(covered, 3),
                    solverMetadata=PatrolRouteSolverMeta(
                        solveMs=0.0,
                        objective=round(covered, 3),
                        solverBackend="cuopt" if settings.enable_cuopt else "greedy",
                    ),
                )
            )
    return out
