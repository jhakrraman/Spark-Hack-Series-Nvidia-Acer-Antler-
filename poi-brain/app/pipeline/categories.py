"""Hazard category definitions used to slice the risk model by type.

Mappings are grounded in real NYPD `ofns_desc` values from the complaint feed
and real 311 `complaint_type` values. The "all" category is the default
aggregate — it's what the trained model scores.

Per-category scores are computed analytically from raw counts (percentile
tiered against the current batch) rather than requiring a separate model per
category. This lets the dashboard swap layers instantly without retraining.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class HazardCategory:
    id: str
    label: str
    description: str
    nypd_keywords: tuple[str, ...] = ()
    svc311_types: tuple[str, ...] = ()
    uses_collisions: bool = False


CATEGORIES: List[HazardCategory] = [
    HazardCategory(
        id="all",
        label="All hazards",
        description="Aggregate model score — every signal combined",
    ),
    HazardCategory(
        id="violent",
        label="Violent crime",
        description="Murder, assault, robbery, sex crimes, weapons",
        nypd_keywords=(
            "MURDER",
            "HOMICIDE",
            "MANSLAUGHTER",
            "ASSAULT",
            "FELONY ASSAULT",
            "ROBBERY",
            "KIDNAPPING",
            "RAPE",
            "SEX CRIMES",
            "WEAPONS",
            "DANGEROUS WEAPONS",
            "ARSON",
        ),
    ),
    HazardCategory(
        id="property",
        label="Property crime",
        description="Theft, burglary, larceny, motor vehicle",
        nypd_keywords=(
            "GRAND LARCENY",
            "PETIT LARCENY",
            "BURGLARY",
            "THEFT",
            "GRAND LARCENY OF MOTOR VEHICLE",
            "POSSESSION OF STOLEN PROPERTY",
            "OFFENSES INVOLVING FRAUD",
            "THEFT-FRAUD",
            "FORGERY",
            "CRIMINAL MISCHIEF & RELATED OF",
        ),
    ),
    HazardCategory(
        id="public_order",
        label="Public order",
        description="Harassment, trespass, disorderly, drugs",
        nypd_keywords=(
            "HARRASSMENT",
            "HARASSMENT",
            "CRIMINAL TRESPASS",
            "OFF. AGNST PUB ORD SENSBLTY",
            "DISORDERLY",
            "DANGEROUS DRUGS",
            "GAMBLING",
            "PROSTITUTION",
            "INTOXICATED",
            "LOITERING",
            "NUISANCE",
        ),
    ),
    HazardCategory(
        id="traffic_hazard",
        label="Traffic hazard",
        description="Collisions + traffic-law violations (Vision Zero)",
        nypd_keywords=(
            "VEHICLE AND TRAFFIC LAWS",
            "UNAUTHORIZED USE OF VEHICLE",
        ),
        svc311_types=(
            "Traffic Signal Condition",
            "Blocked Driveway",
            "Illegal Parking",
        ),
        uses_collisions=True,
    ),
    HazardCategory(
        id="environmental",
        label="Environmental",
        description="311 streetlights, road conditions, noise",
        svc311_types=(
            "Street Light Condition",
            "Street Condition",
            "Noise - Street/Sidewalk",
        ),
    ),
]


ALL_CATEGORY_IDS: List[str] = [c.id for c in CATEGORIES]
NON_ALL_IDS: List[str] = [c.id for c in CATEGORIES if c.id != "all"]


def categorize_nypd(ofns_desc: str | None) -> str | None:
    """Return the first matching hazard category id for an NYPD ofns_desc."""
    if not ofns_desc:
        return None
    up = str(ofns_desc).upper()
    for cat in CATEGORIES:
        if cat.id == "all":
            continue
        for kw in cat.nypd_keywords:
            if kw in up:
                return cat.id
    return None


def svc311_category(complaint_type: str | None) -> str | None:
    if not complaint_type:
        return None
    for cat in CATEGORIES:
        if cat.id == "all":
            continue
        if complaint_type in cat.svc311_types:
            return cat.id
    return None


def category_by_id(category_id: str) -> HazardCategory | None:
    for cat in CATEGORIES:
        if cat.id == category_id:
            return cat
    return None


# Column name convention: `<category>_count` in the fused hex frame.
def count_column(category_id: str) -> str:
    return f"{category_id}_count"


COUNT_COLUMNS: Dict[str, str] = {c.id: count_column(c.id) for c in CATEGORIES}
