"""Risk scoring engine — turns fused features + trained model into per-camera
and per-hex risk scores, then publishes them to the SSE queue.

Runs on a loop. Every cycle:
1. Reload the fused frame if newer than cached copy.
2. Score every H3 cell in the fused frame.
3. Assign tiers via percentile of the current batch (top 5% critical, next 15%
   high, next 30% med, rest low) so some cells always glow red regardless of
   the absolute score distribution.
4. For each camera, look up its H3 cell. If not in the fused frame, fall back
   to nearest neighbor within a 3-ring H3 disk (~450m).
5. Publish per-camera RiskScore and populate STATE.hex_cells.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import h3
import numpy as np
import pandas as pd

from ..config import settings
from ..schemas import HexCell, RiskScore
from ..state import STATE, publish_risk
from .categories import ALL_CATEGORY_IDS, NON_ALL_IDS, count_column
from .fuse_cudf import fuse_to_training_frame
from .train_cuml import score_features

log = logging.getLogger("poi.risk")


def _assign_tiers(scores: np.ndarray) -> list[str]:
    """Rank-based tier assignment.

    Sort cells by score descending, then assign:
    - top 5% of ranks  → critical
    - next 15%         → high
    - next 30%         → med
    - rest             → low

    Rank-based (not value-based) so ties don't collapse everything into one
    tier when the model produces a flat baseline distribution.

    Special cases:
    - n < 20 → absolute thresholds so tiny batches still get spread
    - all scores identical → everything "low" (no meaningful signal)
    - cells with score == 0 are always forced to "low" regardless of rank,
      so a flat baseline doesn't light up the dashboard with false hotspots.
    """
    n = len(scores)
    if n == 0:
        return []
    if n < 20:
        out: list[str] = []
        for s in scores:
            if s >= 0.8:
                out.append("critical")
            elif s >= 0.6:
                out.append("high")
            elif s >= 0.35:
                out.append("med")
            else:
                out.append("low")
        return out

    if float(np.ptp(scores)) < 1e-4:
        return ["low"] * n

    order = np.argsort(-scores, kind="stable")
    crit_n = max(1, int(round(n * 0.05)))
    high_n = max(1, int(round(n * 0.15)))
    med_n = max(1, int(round(n * 0.30)))

    tiers = np.full(n, "low", dtype=object)
    tiers[order[:crit_n]] = "critical"
    tiers[order[crit_n : crit_n + high_n]] = "high"
    tiers[order[crit_n + high_n : crit_n + high_n + med_n]] = "med"

    # Never let a zero (or near-zero) score be a "hotspot" — those are
    # cells where the pipeline found no signal, not high-risk cells.
    zero_mask = scores <= 1e-6
    tiers[zero_mask] = "low"

    return tiers.tolist()


def _reasons_for_row(row) -> List[str]:
    reasons: List[str] = []
    if row.get("crime_90d", 0) >= 3:
        reasons.append(f"{int(row['crime_90d'])} NYPD incidents last 90 days")
    if row.get("collision_365d", 0) >= 5:
        reasons.append(
            f"Vision Zero hotspot ({int(row['collision_365d'])} collisions/yr)"
        )
    if row.get("streetlight_30d", 0) >= 1:
        reasons.append(
            f"{int(row['streetlight_30d'])} 311 streetlight outage(s) within 150m"
        )
    if row.get("signal_30d", 0) >= 1:
        reasons.append("Traffic signal complaint nearby")
    if row.get("noise_30d", 0) >= 3:
        reasons.append("Elevated 311 noise complaints")
    if not reasons:
        reasons.append("baseline neighborhood risk")
    return reasons


def _normalize_counts_to_scores(counts: np.ndarray) -> np.ndarray:
    """Turn raw per-category counts into 0-1 scores.

    Uses log-ish normalization against the 99th percentile of the current
    batch so a single hotspot doesn't dominate. Empty / zero counts become 0.
    """
    counts = np.asarray(counts, dtype="float32")
    if counts.size == 0:
        return counts
    top = float(np.quantile(counts, 0.99))
    if top <= 0:
        return np.zeros_like(counts, dtype="float32")
    clipped = np.clip(counts, 0, top)
    return (clipped / top).astype("float32")


def _load_or_refresh_fused_cache() -> pd.DataFrame | None:
    """Fuse once, cache in STATE so time-of-week re-scoring is cheap."""
    if STATE.fused_df is not None:
        return STATE.fused_df
    fused = fuse_to_training_frame()
    if fused is None or len(fused) == 0:
        return None
    pdf = fused.to_pandas() if hasattr(fused, "to_pandas") else fused
    STATE.fused_df = pdf
    return pdf


def _compute_hex_scores(
    hour_of_week_override: int | None = None,
) -> Dict[str, dict]:
    pdf = _load_or_refresh_fused_cache()
    if pdf is None or pdf.empty:
        return {}

    pdf = pdf.copy()
    if hour_of_week_override is not None:
        clamped = int(hour_of_week_override) % (24 * 7)
        pdf["hour_of_week"] = clamped
        pdf["is_weekend"] = int(clamped >= 24 * 5)

    scores = np.asarray(score_features(pdf), dtype="float32")
    tiers = _assign_tiers(scores)
    pdf["score"] = scores
    pdf["tier"] = tiers

    # Per-category scores: derived analytically from raw counts (percentile-
    # normalized, then percentile-tiered). The trained model is only used for
    # the "all" category — category-specific layers don't need separate training
    # and stay interpretable ("these are hexes with N robberies in 90 days").
    category_layers: Dict[str, Dict[str, dict]] = {"all": {}}
    for cat_id in NON_ALL_IDS:
        col = count_column(cat_id)
        if col not in pdf.columns:
            continue
        raw_counts = pdf[col].to_numpy(dtype="float32")
        cat_scores = _normalize_counts_to_scores(raw_counts)
        cat_tiers = _assign_tiers(cat_scores)
        category_layers[cat_id] = {
            pdf.iloc[i]["h3"]: {
                "score": float(cat_scores[i]),
                "tier": cat_tiers[i],
                "count": int(raw_counts[i]),
            }
            for i in range(len(pdf))
        }

    out: Dict[str, dict] = {}
    for row in pdf.itertuples(index=False):
        rowdict = row._asdict()
        cat_scores_for_cell: Dict[str, dict] = {}
        for cat_id in NON_ALL_IDS:
            layer = category_layers.get(cat_id, {})
            info = layer.get(row.h3)
            if info is not None:
                cat_scores_for_cell[cat_id] = info
        out[row.h3] = {
            "score": float(row.score),
            "tier": row.tier,
            "reasons": _reasons_for_row(rowdict),
            "features": {
                "crime_90d": float(row.crime_90d),
                "collision_365d": float(row.collision_365d),
                "streetlight_30d": float(row.streetlight_30d),
                "signal_30d": float(row.signal_30d),
                "noise_30d": float(row.noise_30d),
            },
            "categories": cat_scores_for_cell,
        }
    return out


def _lookup_camera_score(
    camera_h3: str | None, hex_scores: Dict[str, dict], max_ring: int = 3
) -> tuple[dict | None, int]:
    """Find a hex score for a camera.

    Returns (score_dict_or_None, ring_used).
    ring_used = 0 means exact hex match; 1-3 means neighbor within that ring.
    """
    if not camera_h3:
        return None, -1
    if camera_h3 in hex_scores:
        return hex_scores[camera_h3], 0
    for k in range(1, max_ring + 1):
        try:
            neighbors = h3.grid_disk(camera_h3, k)
        except Exception:
            continue
        best: dict | None = None
        for n in neighbors:
            info = hex_scores.get(n)
            if info is None:
                continue
            if best is None or info["score"] > best["score"]:
                best = info
        if best is not None:
            return best, k
    return None, -1


def _now_window():
    now = datetime.now(tz=timezone.utc)
    end = now + timedelta(minutes=settings.prediction_window_minutes)
    return now.isoformat(), end.isoformat()


def _compute_hex_cells_for_hour(hour_of_week: int) -> list[HexCell]:
    """On-demand scoring for a user-supplied hour. Returns HexCells rather
    than mutating STATE, so multiple slider positions can query in parallel.
    """
    hex_scores = _compute_hex_scores(hour_of_week_override=hour_of_week)
    if not hex_scores:
        return []
    return [
        HexCell(
            h3Index=h3_idx,
            score=info["score"],
            tier=info["tier"],
            contributingFactors=info["features"],
            incidentCountForecast=info["features"].get("crime_90d", 0) / 90.0,
            categories=info.get("categories", {}),
        )
        for h3_idx, info in hex_scores.items()
    ]


async def recompute_once() -> None:
    STATE.fused_df = None  # force re-fuse so 60s tick picks up fresh wall-clock
    hex_scores = await asyncio.to_thread(_compute_hex_scores)
    if not hex_scores:
        log.warning("[risk] no hex scores computed")
        return

    start_iso, end_iso = _now_window()

    STATE.hex_cells = [
        HexCell(
            h3Index=h3_idx,
            score=info["score"],
            tier=info["tier"],
            contributingFactors=info["features"],
            incidentCountForecast=info["features"].get("crime_90d", 0) / 90.0,
            categories=info.get("categories", {}),
        )
        for h3_idx, info in hex_scores.items()
    ]
    tier_counts: Dict[str, int] = {}
    for c in STATE.hex_cells:
        tier_counts[c.tier] = tier_counts.get(c.tier, 0) + 1
    log.info("[risk] hex_cells=%d tiers=%s", len(STATE.hex_cells), tier_counts)

    ring_hits = 0
    for cam in STATE.cameras.values():
        info, ring = _lookup_camera_score(cam.h3Cell, hex_scores)
        if info is None:
            score = 0.2
            tier = "low"
            reasons = ["no feature coverage within 3 hex rings"]
        else:
            score = info["score"]
            tier = info["tier"]
            reasons = list(info["reasons"])
            if ring > 0:
                reasons.append(
                    f"score inherited from neighbor hex (k={ring})"
                )
                ring_hits += 1

        risk = RiskScore(
            cameraId=cam.id,
            score=round(float(score), 3),
            tier=tier,  # type: ignore[arg-type]
            reasons=reasons,
            windowStart=start_iso,
            windowEnd=end_iso,
            modelVersion=STATE.model_version,
        )
        await publish_risk(risk)
    if ring_hits:
        log.info("[risk] %d/%d cameras used k-ring neighbor fallback", ring_hits, len(STATE.cameras))


async def run_risk_engine_forever(interval_s: float = 60.0) -> None:
    while True:
        try:
            await recompute_once()
        except Exception as err:
            log.exception("[risk] cycle failed: %s", err)
        await asyncio.sleep(interval_s)
