"""Pydantic schemas mirroring types/index.ts on the Next.js side."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

RiskTier = Literal["low", "med", "high", "critical"]
ModelCoverage = Literal["full", "partial", "none"]


class Camera(BaseModel):
    id: str
    name: str
    location: str
    address: str
    thumbnail: str = ""
    snapshotUrl: Optional[str] = None
    latLng: Optional[Tuple[float, float]] = None
    precinctId: Optional[str] = None
    h3Cell: Optional[str] = None
    borough: Optional[str] = None
    modelCoverage: ModelCoverage = "full"
    online: bool = True


class RiskScore(BaseModel):
    cameraId: str
    score: float = Field(ge=0.0, le=1.0)
    tier: RiskTier
    reasons: List[str] = []
    windowStart: str
    windowEnd: str
    modelVersion: str


class CategoryScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    tier: RiskTier
    count: int


class HexCell(BaseModel):
    h3Index: str
    score: float = Field(ge=0.0, le=1.0)
    tier: RiskTier
    contributingFactors: Dict[str, float] = {}
    incidentCountForecast: Optional[float] = None
    categories: Dict[str, CategoryScore] = {}


class Heatmap(BaseModel):
    resolution: int
    cells: List[HexCell]
    generatedAt: str
    windowStart: str
    windowEnd: str


class Precinct(BaseModel):
    id: str
    name: str
    centroidLatLng: Tuple[float, float]
    riskScore: Optional[float] = None
    tier: Optional[RiskTier] = None


class PredictionWindow(BaseModel):
    windowStart: str
    windowEnd: str
    granularityMinutes: int
    incidentCountForecast: float
    confidenceInterval: Tuple[float, float]


class ForecastStats(BaseModel):
    predictedNext24h: int
    highestRiskPrecinct: Optional[Precinct] = None
    modelVersion: str
    generatedAt: str
    hottestHexes: List[HexCell]


class PatrolWaypoint(BaseModel):
    latLng: Tuple[float, float]
    etaSeconds: float
    cameraId: Optional[str] = None


class PatrolRouteSolverMeta(BaseModel):
    solveMs: float
    objective: float
    solverBackend: Literal["cuopt", "greedy"]


class PatrolRoute(BaseModel):
    unitId: str
    waypoints: List[PatrolWaypoint]
    totalRiskCovered: float
    solverMetadata: PatrolRouteSolverMeta


class RetrievedIncident(BaseModel):
    incidentId: str
    summary: str
    distanceM: float
    daysAgo: int
    category: Optional[str] = None


class FrameAnalyzeRequest(BaseModel):
    cameraId: Optional[str] = None
    frameJpegB64: str
    transcript: str = ""


class FrameEvent(BaseModel):
    timestamp: str
    description: str
    isDangerous: bool


class FrameAnalyzeResponse(BaseModel):
    events: List[FrameEvent]
    riskScoreAtTime: Optional[float] = None
    retrievedContext: List[RetrievedIncident] = []
    rawResponse: str = ""
