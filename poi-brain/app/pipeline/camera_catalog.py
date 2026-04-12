"""NYC DOT traffic camera catalog loader.

Primary source: the public NYC DOT Traffic Management Center API at
https://webcams.nyctmc.org/api/cameras — which the existing Next.js side
already uses via `lib/nyctmc.ts`. Returns ~962 cameras across all five
boroughs with live-updating JPEG snapshot URLs.

We fetch at startup, filter to online cameras in the boroughs we care about,
tag each with an H3 res-9 cell, and return them. The result feeds both the
mission-control dashboard's camera-pin overlay and the camera poller that
pipes frames into the NIM/LM Studio VLM.

Fallback chain:
1. Live HTTP fetch from webcams.nyctmc.org (primary)
2. Parquet cache at `poi-brain/parquet/dot_cameras.parquet` (if ingest wrote it)
3. Hardcoded 12-camera Manhattan seed list (last-resort for offline dev)
"""
from __future__ import annotations

import logging
from typing import List

import h3
import httpx
import pandas as pd

from ..config import settings
from ..schemas import Camera

log = logging.getLogger("poi.camera_catalog")

NYCTMC_API = "https://webcams.nyctmc.org/api/cameras"

# 12-camera last-resort fallback for offline dev. Real IDs verified against
# the live API — each snapshotUrl returns a real JPEG. Used ONLY when both
# the live fetch and the parquet cache fail.
FALLBACK_MANHATTAN_SEEDS: List[dict] = [
    {
        "id": "nyc-053e8995",
        "name": "Broadway @ 45 St",
        "borough": "Manhattan",
        "latLng": (40.757953, -73.985490),
        "address": "Broadway @ 45 St (Times Square), Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/053e8995-f8cb-4d02-a659-70ac7c7da5db/image",
    },
    {
        "id": "nyc-8cc75cbc",
        "name": "Canal St @ Chrystie St",
        "borough": "Manhattan",
        "latLng": (40.715821, -73.994913),
        "address": "Canal Street @ Chrystie Street, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/8cc75cbc-e050-4947-aee8-639f63fe4ca7/image",
    },
    {
        "id": "nyc-0952329e",
        "name": "Broadway @ Chambers St",
        "borough": "Manhattan",
        "latLng": (40.714177, -74.006307),
        "address": "Broadway @ Chambers St, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/0952329e-6b6f-4286-b5e3-b682eae94e52/image",
    },
    {
        "id": "nyc-9cc8495e",
        "name": "3 Ave @ 23 St",
        "borough": "Manhattan",
        "latLng": (40.738833, -73.983156),
        "address": "3 Ave @ 23 St, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/9cc8495e-aeee-4759-adba-5a6bf5efd4b9/image",
    },
    {
        "id": "nyc-332f161d",
        "name": "6 Ave @ Central Park South",
        "borough": "Manhattan",
        "latLng": (40.765683, -73.976229),
        "address": "Ave of Americas @ Central Park South, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/332f161d-47cb-4c8a-b6b6-5ad48a55c978/image",
    },
    {
        "id": "nyc-6d3a21dd",
        "name": "5 Ave @ 58 St",
        "borough": "Manhattan",
        "latLng": (40.763753, -73.973548),
        "address": "5 Ave @ E 58 St, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/6d3a21dd-0434-4d92-a0d1-3ca8b77297db/image",
    },
    {
        "id": "nyc-ec9eda79",
        "name": "Amsterdam Ave @ 60 St",
        "borough": "Manhattan",
        "latLng": (40.771057, -73.987139),
        "address": "Amsterdam Ave @ 60 St, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/ec9eda79-e250-4e6f-a8f6-e51021fb054f/image",
    },
    {
        "id": "nyc-984ebbad",
        "name": "Central Park West @ 72 St",
        "borough": "Manhattan",
        "latLng": (40.776225, -73.975974),
        "address": "Central Park West @ 72 St, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/984ebbad-ca64-41d8-8008-63aaae316952/image",
    },
    {
        "id": "nyc-8a6bc417",
        "name": "Central Park West @ 86 St",
        "borough": "Manhattan",
        "latLng": (40.785302, -73.969353),
        "address": "Central Park West @ 86 St, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/8a6bc417-4877-4ebe-8052-88c1b261baf1/image",
    },
    {
        "id": "nyc-4f8c2e84",
        "name": "Central Park West @ 65 St",
        "borough": "Manhattan",
        "latLng": (40.771797, -73.979217),
        "address": "Central Park West @ 65 St, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/4f8c2e84-c15a-4474-91fb-7e14554d4c4e/image",
    },
    {
        "id": "nyc-ec1e7b42",
        "name": "FDR Drive @ 122 St",
        "borough": "Manhattan",
        "latLng": (40.798685, -73.929148),
        "address": "FDR Drive @ 122 St, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/ec1e7b42-18de-4475-8c89-9e80f21e5b6c/image",
    },
    {
        "id": "nyc-0ccf3a51",
        "name": "South St @ Brooklyn Bridge",
        "borough": "Manhattan",
        "latLng": (40.708186, -73.999623),
        "address": "South St @ Brooklyn Bridge, Manhattan, NY",
        "snapshotUrl": "https://webcams.nyctmc.org/api/cameras/0ccf3a51-8981-4e03-92a9-00b1c59f0b9b/image",
    },
]


def _h3_for(lat: float, lon: float) -> str | None:
    try:
        return h3.latlng_to_cell(float(lat), float(lon), settings.h3_resolution)
    except Exception:
        return None


def _fetch_live_nyctmc() -> List[Camera]:
    """Primary source: pull the full camera catalog from the NYC DOT public API."""
    try:
        resp = httpx.get(NYCTMC_API, timeout=10.0)
        resp.raise_for_status()
    except Exception as err:
        log.warning("[catalog] NYCTMC live fetch failed: %s", err)
        return []

    payload = resp.json()
    raw_list = payload if isinstance(payload, list) else payload.get("cameras", [])
    if not isinstance(raw_list, list):
        log.warning("[catalog] NYCTMC payload has unexpected shape")
        return []

    cameras: List[Camera] = []
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        cam_id = raw.get("id")
        if not cam_id:
            continue
        if str(raw.get("isOnline", "true")).lower() != "true":
            continue
        try:
            lat = float(raw.get("latitude"))
            lon = float(raw.get("longitude"))
        except (TypeError, ValueError):
            continue
        name = str(raw.get("name") or "Unnamed Camera")
        borough = str(raw.get("area") or "Unknown")
        image_url = (
            raw.get("imageUrl")
            or f"{NYCTMC_API}/{cam_id}/image"
        )
        cameras.append(
            Camera(
                id=f"nyc-{cam_id[:8]}",
                name=name[:80],
                location=borough,
                address=f"{name}, {borough}, NY",
                thumbnail="",
                snapshotUrl=image_url,
                latLng=(lat, lon),
                borough=borough,
                h3Cell=_h3_for(lat, lon),
                modelCoverage="full",
                online=True,
            )
        )
    log.info("[catalog] live NYCTMC fetch: %d cameras", len(cameras))
    return cameras


def _load_from_parquet() -> List[Camera]:
    path = settings.parquet_root / "dot_cameras.parquet"
    if not path.exists():
        return []
    try:
        df = pd.read_parquet(path)
    except Exception as err:
        log.warning("[catalog] parquet load failed: %s", err)
        return []
    if df.empty:
        return []

    lat_col = next((c for c in df.columns if c.lower() in ("latitude", "lat")), None)
    lon_col = next(
        (c for c in df.columns if c.lower() in ("longitude", "lon", "lng")), None
    )
    name_col = next(
        (c for c in df.columns if c.lower() in ("name", "cameraname", "intersection")),
        None,
    )
    borough_col = next(
        (c for c in df.columns if c.lower() in ("area", "borough", "boro")), None
    )
    id_col = next(
        (c for c in df.columns if c.lower() in ("id", "cameraid", "camera_id")), None
    )
    url_col = next(
        (c for c in df.columns if "url" in c.lower() and "image" in c.lower()), None
    )

    if not lat_col or not lon_col or not id_col:
        return []

    cameras: List[Camera] = []
    for _, row in df.iterrows():
        try:
            lat = float(row[lat_col])
            lon = float(row[lon_col])
        except (TypeError, ValueError):
            continue
        cam_uuid = str(row[id_col])
        name = str(row.get(name_col, "Camera")) if name_col else "Camera"
        borough = str(row.get(borough_col, "Unknown")) if borough_col else "Unknown"
        snapshot = (
            str(row[url_col])
            if url_col
            else f"{NYCTMC_API}/{cam_uuid}/image"
        )
        cameras.append(
            Camera(
                id=f"nyc-{cam_uuid[:8]}",
                name=name[:80],
                location=borough,
                address=f"{name}, {borough}, NY",
                thumbnail="",
                snapshotUrl=snapshot,
                latLng=(lat, lon),
                borough=borough,
                h3Cell=_h3_for(lat, lon),
                modelCoverage="full",
            )
        )
    log.info("[catalog] parquet fetch: %d cameras", len(cameras))
    return cameras


def _load_fallback_seeds() -> List[Camera]:
    log.info("[catalog] using hardcoded %d-camera fallback", len(FALLBACK_MANHATTAN_SEEDS))
    return [
        Camera(
            id=c["id"],
            name=c["name"],
            location=c["borough"],
            address=c["address"],
            thumbnail="",
            snapshotUrl=c["snapshotUrl"],
            latLng=c["latLng"],
            borough=c["borough"],
            modelCoverage="full",
            h3Cell=_h3_for(c["latLng"][0], c["latLng"][1]),
        )
        for c in FALLBACK_MANHATTAN_SEEDS
    ]


def _apply_filters(cameras: List[Camera]) -> List[Camera]:
    """Respect settings: borough filter, manual subset override, size cap."""
    # Borough filter: if camera_boroughs is set, keep only matching boroughs.
    # Otherwise return all.
    borough_filter = getattr(settings, "camera_boroughs", None)
    if borough_filter:
        wanted = {b.lower() for b in borough_filter}
        cameras = [c for c in cameras if (c.borough or "").lower() in wanted]

    if settings.camera_manual_subset:
        manual = set(settings.camera_manual_subset)
        cameras = [c for c in cameras if c.id in manual]

    # The default subset size is large enough to show most of Manhattan.
    # Override with CAMERA_SUBSET_SIZE=0 to disable the cap.
    cap = settings.camera_subset_size
    if cap and cap > 0 and len(cameras) > cap:
        cameras = cameras[:cap]

    return cameras


def load_camera_catalog() -> List[Camera]:
    """Live → parquet → hardcoded-seed fallback chain."""
    cameras = _fetch_live_nyctmc()
    if not cameras:
        cameras = _load_from_parquet()
    if not cameras:
        cameras = _load_fallback_seeds()

    filtered = _apply_filters(cameras)
    log.info(
        "[catalog] loaded %d cameras (filtered from %d)", len(filtered), len(cameras)
    )
    return filtered
