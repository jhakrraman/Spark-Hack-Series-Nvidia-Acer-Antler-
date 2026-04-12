"""Forecast stats for the dashboard top strip."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..pipeline.categories import ALL_CATEGORY_IDS
from ..schemas import ForecastStats, HexCell, Precinct
from ..state import STATE

router = APIRouter(prefix="/stats", tags=["stats"])


def _project(cell: HexCell, category: str) -> HexCell:
    if category == "all":
        return cell
    info = cell.categories.get(category)
    if info is None:
        return cell.model_copy(update={"score": 0.0, "tier": "low"})
    return cell.model_copy(update={"score": info.score, "tier": info.tier})


def _highest_risk_precinct(cells: List[HexCell]) -> Optional[Precinct]:
    if not cells:
        return None
    hottest = max(cells, key=lambda c: c.score)
    return Precinct(
        id=hottest.h3Index[:6].upper(),
        name=f"HEX {hottest.h3Index[:6].upper()}",
        centroidLatLng=(40.7484, -73.9857),
        riskScore=hottest.score,
        tier=hottest.tier,
    )


@router.get("/forecast", response_model=ForecastStats)
async def forecast(category: str = Query(default="all")):
    if category not in ALL_CATEGORY_IDS:
        raise HTTPException(status_code=400, detail=f"unknown category {category}")
    cells = [_project(c, category) for c in STATE.hex_cells]
    hottest = sorted(cells, key=lambda c: c.score, reverse=True)[:10]
    total_forecast = sum((c.incidentCountForecast or 0) for c in cells)
    return ForecastStats(
        predictedNext24h=int(round(total_forecast * 96)),
        highestRiskPrecinct=_highest_risk_precinct(cells),
        modelVersion=STATE.model_version,
        generatedAt=datetime.now(tz=timezone.utc).isoformat(),
        hottestHexes=hottest,
    )
