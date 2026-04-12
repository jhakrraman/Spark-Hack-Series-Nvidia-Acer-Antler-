"""NYC Open Data (SODA) ingestion → Parquet.

Datasets pulled:
- NYPD Complaint Data Historic      (qgea-i56i) — training labels
- NYPD Complaint YTD                (5uac-w243) — recent labels
- Motor Vehicle Collisions          (h9gi-nx95) — Vision Zero hotspots
- 311 Service Requests              (erm2-nwe9) — env precursors
- NYC DOT Traffic Cameras catalog   (9knp-kupa) — camera metadata

Each dataset is saved to parquet_root/<name>.parquet. Idempotent — re-runs
overwrite the same file. Pulls a bounded number of rows per dataset to keep
demo ingestion fast.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from ..config import settings

log = logging.getLogger("poi.ingest")


def _soda_client():
    from sodapy import Socrata

    return Socrata(
        "data.cityofnewyork.us",
        settings.soda_app_token,
        timeout=settings.soda_timeout_s,
    )


def _fetch(resource_id: str, where: Optional[str] = None, limit: int = 200_000) -> pd.DataFrame:
    client = _soda_client()
    log.info("[ingest] %s (limit=%d)%s", resource_id, limit, f" where={where}" if where else "")
    records = client.get(resource_id, where=where, limit=limit)
    df = pd.DataFrame.from_records(records) if records else pd.DataFrame()
    log.info("[ingest] %s rows=%d", resource_id, len(df))
    return df


def _write(df: pd.DataFrame, name: str) -> Path:
    path = settings.parquet_root / f"{name}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    log.info("[ingest] wrote %s (%d rows)", path, len(df))
    return path


def ingest_nypd_historic(limit: int | None = None) -> Path:
    df = _fetch(settings.nypd_historic_resource, limit=limit or settings.nypd_historic_limit)
    return _write(df, "nypd_historic")


def ingest_nypd_ytd(limit: int | None = None) -> Path:
    df = _fetch(settings.nypd_ytd_resource, limit=limit or settings.nypd_ytd_limit)
    return _write(df, "nypd_ytd")


def ingest_collisions(limit: int | None = None) -> Path:
    since = (datetime.utcnow() - timedelta(days=365 * 2)).strftime("%Y-%m-%dT00:00:00")
    df = _fetch(
        settings.collisions_resource,
        where=f"crash_date >= '{since}'",
        limit=limit or settings.collisions_limit,
    )
    return _write(df, "collisions")


def ingest_311(limit: int | None = None) -> Path:
    since = (datetime.utcnow() - timedelta(days=120)).strftime("%Y-%m-%dT00:00:00")
    keep_types = (
        "'Street Light Condition'",
        "'Street Condition'",
        "'Noise - Street/Sidewalk'",
        "'Traffic Signal Condition'",
        "'Blocked Driveway'",
        "'Illegal Parking'",
    )
    where = (
        f"created_date >= '{since}' AND complaint_type IN ({','.join(keep_types)})"
    )
    df = _fetch(
        settings.service_req_311_resource,
        where=where,
        limit=limit or settings.service_311_limit,
    )
    return _write(df, "service_311")


def ingest_dot_cameras(limit: int | None = None) -> Path:
    df = _fetch(settings.nyc_dot_cameras_resource, limit=limit or settings.dot_cameras_limit)
    return _write(df, "dot_cameras")


def ingest_all() -> dict:
    """Run all dataset pulls in sequence; tolerate individual failures."""
    results = {}
    for name, fn in [
        ("nypd_historic", ingest_nypd_historic),
        ("nypd_ytd", ingest_nypd_ytd),
        ("collisions", ingest_collisions),
        ("service_311", ingest_311),
        ("dot_cameras", ingest_dot_cameras),
    ]:
        try:
            results[name] = str(fn())
        except Exception as err:
            log.exception("[ingest] %s failed: %s", name, err)
            results[name] = f"error: {err}"
    return results
