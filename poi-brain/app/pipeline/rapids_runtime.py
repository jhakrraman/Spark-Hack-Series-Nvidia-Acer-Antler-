"""RAPIDS availability probe.

Import this module to get a GPU-aware namespace that transparently falls
back to pandas/numpy when cuDF/cuML aren't installed. This matters because
the repo gets developed on a Mac (no CUDA) but runs on the DGX Spark (CUDA).
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger("poi.rapids")


def _probe():
    force_cpu = os.environ.get("POI_FORCE_CPU", "").lower() in ("1", "true", "yes")
    if force_cpu:
        log.info("[rapids] POI_FORCE_CPU set — using pandas fallback")
        return False, None, None, None

    try:
        import cudf  # type: ignore
        import cuml  # type: ignore
        try:
            import cuspatial  # type: ignore
        except Exception:
            cuspatial = None  # type: ignore
        try:
            import cugraph  # type: ignore
        except Exception:
            cugraph = None  # type: ignore

        log.info(
            "[rapids] cuDF %s / cuML %s loaded — GPU path active",
            getattr(cudf, "__version__", "?"),
            getattr(cuml, "__version__", "?"),
        )
        return True, cudf, cuml, (cuspatial, cugraph)
    except Exception as err:
        log.warning("[rapids] not available (%s) — using pandas fallback", err)
        return False, None, None, None


HAS_RAPIDS, _cudf, _cuml, _spatial_graph = _probe()


def get_df_lib():
    """Return cuDF on GPU, pandas on CPU. Both expose a compatible DataFrame API."""
    if HAS_RAPIDS:
        return _cudf
    import pandas as pd  # type: ignore
    return pd


def get_ml_lib():
    """Return cuML on GPU, sklearn on CPU."""
    if HAS_RAPIDS:
        return _cuml
    try:
        import sklearn  # type: ignore
        return sklearn
    except Exception:
        return None


def get_cuspatial():
    if HAS_RAPIDS and _spatial_graph is not None:
        return _spatial_graph[0]
    return None


def get_cugraph():
    if HAS_RAPIDS and _spatial_graph is not None:
        return _spatial_graph[1]
    return None
