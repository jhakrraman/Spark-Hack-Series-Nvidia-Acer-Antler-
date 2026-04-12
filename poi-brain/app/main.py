"""poi-brain FastAPI entrypoint.

Startup orchestration:
1. Load the NYC DOT camera catalog into STATE.cameras.
2. Train (or reload) the risk model from parquet. Non-fatal if parquet missing.
3. Warm up the NIM container (best-effort).
4. Load the retrieval index.
5. Spawn background tasks: risk engine loop + camera poller loop.

Run:
    uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .pipeline.camera_catalog import load_camera_catalog
from .pipeline.camera_poller import run_poller_forever
from .pipeline.device_probe import detect_environment
from .pipeline.rapids_runtime import HAS_RAPIDS
from .pipeline.retrieval import get_index
from .pipeline.risk_engine import recompute_once, run_risk_engine_forever
from .pipeline.train_cuml import load_model, train_risk_model
from .routers import cameras, dispatch, frames, health, risk, stats
from .state import STATE
from .vlm import get_vlm_client

log = logging.getLogger("poi")


def _configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-5s %(name)s %(message)s",
    )


async def _startup() -> None:
    _configure_logging()
    log.info("=" * 60)
    log.info("poi-brain starting — vlm=%s", settings.vlm_backend)
    log.info("NIM: %s (%s)", settings.nim_base_url, settings.nim_model)
    log.info("=" * 60)

    env = detect_environment()
    STATE.device_env = env  # type: ignore[attr-defined]

    cams = load_camera_catalog()
    STATE.cameras = {c.id: c for c in cams}
    log.info("loaded %d cameras", len(cams))

    bundle = load_model()
    if bundle is None:
        log.info("no saved model — training from parquet")
        try:
            result = await asyncio.to_thread(train_risk_model)
            log.info("train result: %s", result)
            STATE.model_version = f"{result.get('backend', 'sklearn')}-v0"
        except Exception as err:
            log.warning("training failed: %s", err)
    else:
        STATE.model_version = f"{bundle.get('backend', 'sklearn')}-v0"
        log.info(
            "loaded model backend=%s device=%s",
            bundle.get("backend"),
            bundle.get("device", "n/a"),
        )

    try:
        await asyncio.to_thread(get_index().load)
    except Exception as err:
        log.warning("retrieval index load failed: %s", err)

    try:
        await recompute_once()
    except Exception as err:
        log.warning("initial risk compute failed: %s", err)

    if settings.nim_warmup_on_startup:
        try:
            await asyncio.to_thread(get_vlm_client().warmup)
        except Exception as err:
            log.warning("NIM warmup failed: %s", err)


async def _spawn_background_tasks(app: FastAPI) -> list[asyncio.Task]:
    tasks = [
        asyncio.create_task(run_risk_engine_forever(interval_s=60.0)),
        asyncio.create_task(run_poller_forever()),
    ]
    return tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _startup()
    tasks = await _spawn_background_tasks(app)
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        for t in tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass


app = FastAPI(
    title="poi-brain",
    description="Person of Interest — predictive intelligence brain",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    # allow_credentials must be False when origins=["*"] — the CORS spec
    # forbids wildcards with credentials and modern browsers reject it.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(cameras.router)
app.include_router(risk.router)
app.include_router(stats.router)
app.include_router(frames.router)
app.include_router(dispatch.router)


@app.get("/")
async def root():
    return {
        "service": "poi-brain",
        "version": "0.1.0",
        "endpoints": [
            "/health",
            "/cameras",
            "/cameras/stream",
            "/risk/heatmap",
            "/risk/stream",
            "/stats/forecast",
            "/frames/analyze",
            "/frames/ws",
            "/routes/current",
        ],
    }
