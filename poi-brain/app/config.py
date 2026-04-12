"""Runtime configuration loaded from env."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "info"
    cors_allow_origins: List[str] = ["*"]

    # NIM (primary VLM)
    nim_base_url: str = "http://localhost:8000/v1"
    nim_model: str = "meta/llama-3.2-11b-vision-instruct"
    nim_api_key: str = "nim"
    nim_warmup_on_startup: bool = True

    # LM Studio fallback
    lmstudio_base_url: str = "http://localhost:1234/v1"
    lmstudio_model: str = "google/gemma-4-26b-a4b"
    vlm_backend: str = "nim"

    # NYC Open Data (SODA)
    soda_app_token: Optional[str] = None
    soda_timeout_s: float = 60.0

    # Dataset resource IDs — hard-pinned to avoid confusion.
    nypd_historic_resource: str = "qgea-i56i"
    nypd_ytd_resource: str = "5uac-w243"
    collisions_resource: str = "h9gi-nx95"
    service_req_311_resource: str = "erm2-nwe9"
    nyc_dot_cameras_resource: str = "9knp-kupa"

    # Per-dataset row caps. Dev-scale defaults — enough to produce a real
    # training frame with meaningful spread. Override for DGX full-fat runs:
    #   NYPD_HISTORIC_LIMIT=500000 NYPD_YTD_LIMIT=300000 COLLISIONS_LIMIT=300000 ...
    nypd_historic_limit: int = 250_000
    nypd_ytd_limit: int = 150_000
    collisions_limit: int = 150_000
    service_311_limit: int = 200_000
    dot_cameras_limit: int = 10_000

    # Storage
    data_root: Path = Path("/data/poi")
    parquet_root: Path = Path("/data/poi/parquet")
    models_root: Path = Path("/data/poi/models")
    cache_root: Path = Path("/data/poi/cache")

    # Camera ingestion
    webcams_base: str = "https://webcams.nyctmc.org"
    camera_poll_interval_s: float = 3.0
    camera_subset_size: int = 400
    camera_manual_subset: List[str] = []
    camera_boroughs: List[str] = ["Manhattan"]

    # Risk model
    h3_resolution: int = 9
    prediction_window_minutes: int = 15
    nyc_bbox: List[float] = [-74.26, 40.49, -73.68, 40.92]
    model_version: str = "cuml-xgb-v0"

    # RAPIDS
    enable_rapids: bool = True
    enable_cuspatial: bool = True
    enable_cugraph: bool = False
    enable_cuopt: bool = False

    # ML backend: "auto" | "cuml-xgb" | "torch" | "sklearn"
    # auto = pick cuml-xgb on NVIDIA (DGX), torch on Mac/MPS, sklearn otherwise
    ml_backend: str = "auto"
    torch_device: str = "auto"  # "auto" | "cuda" | "mps" | "cpu"

    # Retrieval
    retrieval_backend: str = "faiss"
    retrieval_top_k: int = 5
    retrieval_radius_m: float = 500.0
    retrieval_max_days_ago: int = 30


settings = Settings()

# Best-effort data directory creation. On Mac dev machines /data is read-only,
# so if the default path fails we fall back to ~/.poi so imports don't crash
# at module load time. Users can override via DATA_ROOT in .env.
def _ensure_writable_paths() -> None:
    import os

    for attr in ("data_root", "parquet_root", "models_root", "cache_root"):
        p = getattr(settings, attr)
        try:
            p.mkdir(parents=True, exist_ok=True)
            continue
        except (PermissionError, OSError):
            pass
        home_fallback = Path.home() / ".poi" / p.name
        home_fallback.mkdir(parents=True, exist_ok=True)
        setattr(settings, attr, home_fallback)
        os.environ.setdefault(attr.upper(), str(home_fallback))


_ensure_writable_paths()
