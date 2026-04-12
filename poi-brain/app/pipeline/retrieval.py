"""Similar-incident retrieval: given a camera's lat/lng and event description,
return recent similar incidents within a radius.

Stretch: NeMo Retriever embeddings. MVP: text+spatial filter over NYPD
complaints with FAISS vectors of the offense description.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from ..config import settings
from ..schemas import RetrievedIncident

log = logging.getLogger("poi.retrieval")


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


class IncidentIndex:
    """Lightweight spatial-first incident index.

    Keeps a pandas frame of recent NYPD incidents with lat/lng + description.
    Lookups do a bounding-box filter then a haversine sort. Good enough at
    ~200K rows for the demo; FAISS can be layered on if we want semantic
    similarity.
    """

    def __init__(self) -> None:
        self.df: Optional[pd.DataFrame] = None

    def load(self) -> None:
        path = settings.parquet_root / "nypd_ytd.parquet"
        if not path.exists():
            log.warning("[retrieval] nypd_ytd parquet missing, index stays empty")
            return
        df = pd.read_parquet(path)
        if df.empty:
            return
        for col in ("latitude", "longitude"):
            if col not in df.columns:
                return
        df = df.dropna(subset=["latitude", "longitude"])
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df = df.dropna(subset=["latitude", "longitude"])
        df["dt"] = pd.to_datetime(df.get("cmplnt_fr_dt"), errors="coerce")
        df = df.dropna(subset=["dt"])
        df["summary"] = df.get("ofns_desc", "incident").astype(str).fillna("incident")
        df["category"] = df.get("law_cat_cd", "").astype(str).fillna("")
        df["incident_id"] = df.index.astype(str)
        self.df = df[["latitude", "longitude", "dt", "summary", "category", "incident_id"]]
        log.info("[retrieval] loaded %d NYPD rows", len(self.df))

    def search(
        self, latlng: tuple[float, float], k: int | None = None, radius_m: float | None = None
    ) -> List[RetrievedIncident]:
        if self.df is None or self.df.empty:
            return []
        k = k or settings.retrieval_top_k
        radius = radius_m or settings.retrieval_radius_m
        now = datetime.utcnow()
        cutoff = now - pd.Timedelta(days=settings.retrieval_max_days_ago)

        lat_deg = radius / 111_320.0
        lon_deg = radius / (111_320.0 * max(math.cos(math.radians(latlng[0])), 0.01))

        box = self.df[
            (self.df["dt"] >= cutoff)
            & (self.df["latitude"].between(latlng[0] - lat_deg, latlng[0] + lat_deg))
            & (self.df["longitude"].between(latlng[1] - lon_deg, latlng[1] + lon_deg))
        ]
        if box.empty:
            return []

        box = box.copy()
        box["_dist_m"] = [
            _haversine_m(latlng, (float(r.latitude), float(r.longitude)))
            for r in box.itertuples(index=False)
        ]
        box = box[box["_dist_m"] <= radius].nsmallest(k, "_dist_m")

        out: List[RetrievedIncident] = []
        for r in box.itertuples(index=False):
            days_ago = max(int((now - r.dt).days), 0)
            out.append(
                RetrievedIncident(
                    incidentId=str(r.incident_id),
                    summary=str(r.summary)[:160],
                    distanceM=float(round(r._dist_m, 1)),
                    daysAgo=days_ago,
                    category=str(r.category) or None,
                )
            )
        return out


_INDEX: Optional[IncidentIndex] = None


def get_index() -> IncidentIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = IncidentIndex()
        _INDEX.load()
    return _INDEX
