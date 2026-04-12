"""Top-level training + scoring dispatcher.

Three backends, chosen by `POI_ML_BACKEND` (config.ml_backend) or auto-detected:

- **cuml-xgb** — NVIDIA RAPIDS cuML / xgboost(CUDA). DGX default, the RAPIDS pitch.
- **torch**    — PyTorch MLP on MPS (Mac GPU) or CUDA. Dev default on Apple Silicon.
               Saves a state_dict that's portable across MPS↔CUDA↔CPU.
- **sklearn**  — GradientBoostingClassifier. CPU-only safety net.

`auto` resolves at runtime: cuml if RAPIDS available → torch if torch available
→ sklearn otherwise. Set POI_ML_BACKEND=torch to force the torch path on Mac.
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..config import settings
from .fuse_cudf import fuse_to_training_frame
from .rapids_runtime import HAS_RAPIDS

log = logging.getLogger("poi.train")

FEATURE_COLS = [
    "crime_90d",
    "collision_365d",
    "streetlight_30d",
    "signal_30d",
    "noise_30d",
    "hour_of_week",
    "is_weekend",
]


def _to_pandas(df) -> pd.DataFrame:
    if hasattr(df, "to_pandas"):
        return df.to_pandas()
    return df


def _resolve_backend() -> str:
    """Decide which backend to use this run."""
    pref = (settings.ml_backend or "auto").lower()
    if pref != "auto":
        return pref

    if HAS_RAPIDS:
        return "cuml-xgb"

    try:
        import torch  # noqa: F401

        return "torch"
    except Exception:
        return "sklearn"


# ---------- Backends ----------


def _train_cuml_xgb(X: np.ndarray, y: np.ndarray):
    import xgboost as xgb  # type: ignore

    dtrain = xgb.DMatrix(X, label=y)
    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "tree_method": "hist",
        "device": "cuda" if HAS_RAPIDS else "cpu",
        "max_depth": 6,
        "eta": 0.1,
    }
    return xgb.train(params, dtrain, num_boost_round=120)


def _train_cuml_rf(X: np.ndarray, y: np.ndarray):
    from cuml.ensemble import RandomForestClassifier  # type: ignore

    clf = RandomForestClassifier(n_estimators=128, max_depth=8, random_state=42)
    clf.fit(X.astype("float32"), y.astype("int32"))
    return clf


def _train_sklearn(X: np.ndarray, y: np.ndarray):
    from sklearn.ensemble import GradientBoostingClassifier

    clf = GradientBoostingClassifier(n_estimators=120, max_depth=4, random_state=42)
    clf.fit(X, y)
    return clf


# ---------- Save / load ----------


def _save_pickle(model: Any, backend: str) -> Path:
    path = settings.models_root / "risk_model.pkl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump({"backend": backend, "model": model, "features": FEATURE_COLS}, f)
    log.info("[train] wrote %s (backend=%s)", path, backend)
    return path


def _load_pickle() -> dict | None:
    path = settings.models_root / "risk_model.pkl"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


# ---------- Public API ----------


def train_risk_model() -> dict:
    """Build the fused frame, train the chosen backend, persist the model."""
    fused = fuse_to_training_frame()
    if fused is None or len(fused) == 0:
        log.warning("[train] no fused data — skipping training")
        return {"trained": False, "reason": "no data"}

    pdf = _to_pandas(fused)
    missing = [c for c in FEATURE_COLS if c not in pdf.columns]
    if missing:
        log.error("[train] missing feature cols: %s", missing)
        return {"trained": False, "reason": f"missing cols {missing}"}

    X = pdf[FEATURE_COLS].to_numpy(dtype="float32")
    y = pdf["label"].to_numpy(dtype="int32")

    backend = _resolve_backend()
    log.info("[train] backend=%s rows=%d label_rate=%.3f", backend, len(pdf), float(np.mean(y)))

    if backend == "torch":
        from . import train_torch

        bundle = train_torch.train_pytorch_model(X, y)
        path = train_torch.save_bundle(bundle)
        return {
            "trained": True,
            "backend": "torch",
            "device": bundle.get("device_trained_on"),
            "rows": int(len(pdf)),
            "label_rate": float(np.mean(y)),
            "path": str(path),
        }

    if backend == "cuml-xgb":
        model: Any = None
        try:
            model = _train_cuml_xgb(X, y)
        except Exception as err:
            log.warning("[train] xgb path failed (%s), trying cuML RF", err)
            try:
                model = _train_cuml_rf(X, y)
                backend = "cuml-rf"
            except Exception as err2:
                log.warning("[train] cuML RF also failed (%s), falling back to sklearn", err2)
                backend = "sklearn"

        if backend == "sklearn":
            model = _train_sklearn(X, y)

        path = _save_pickle(model, backend)
        return {
            "trained": True,
            "backend": backend,
            "rows": int(len(pdf)),
            "label_rate": float(np.mean(y)),
            "path": str(path),
        }

    # sklearn
    model = _train_sklearn(X, y)
    path = _save_pickle(model, "sklearn")
    return {
        "trained": True,
        "backend": "sklearn",
        "rows": int(len(pdf)),
        "label_rate": float(np.mean(y)),
        "path": str(path),
    }


_CACHED_BUNDLE: dict | None = None


def load_model() -> dict | None:
    """Load whichever model was last trained.

    Checks for the torch `.pt` file first (fresh dev path), then falls back to
    the pickle bundle (cuml/xgboost/sklearn). Result is cached; call
    `invalidate_model_cache()` after retraining.
    """
    global _CACHED_BUNDLE
    if _CACHED_BUNDLE is not None:
        return _CACHED_BUNDLE

    try:
        from . import train_torch

        torch_bundle = train_torch.load_bundle()
        if torch_bundle is not None:
            _CACHED_BUNDLE = torch_bundle
            return _CACHED_BUNDLE
    except Exception as err:
        log.debug("[train] torch load skipped: %s", err)

    pickle_bundle = _load_pickle()
    if pickle_bundle is not None:
        _CACHED_BUNDLE = pickle_bundle
    return _CACHED_BUNDLE


def invalidate_model_cache() -> None:
    global _CACHED_BUNDLE
    _CACHED_BUNDLE = None


def score_features(feature_rows: pd.DataFrame) -> np.ndarray:
    """Return a probability per row for the binary 'incident likely' label."""
    bundle = load_model()
    if bundle is None:
        return np.full(len(feature_rows), 0.25, dtype="float32")

    features = bundle.get("features", FEATURE_COLS)
    for c in features:
        if c not in feature_rows.columns:
            feature_rows[c] = 0
    X = feature_rows[features].to_numpy(dtype="float32")

    backend = bundle.get("backend", "sklearn")

    try:
        if backend == "torch":
            from . import train_torch

            return train_torch.score(bundle, X)

        model = bundle["model"]

        if backend.startswith("cuml-xgb") or backend == "xgb":
            import xgboost as xgb  # type: ignore

            return model.predict(xgb.DMatrix(X)).astype("float32")

        if backend == "cuml-rf":
            return model.predict_proba(X)[:, 1].astype("float32")

        return model.predict_proba(X)[:, 1].astype("float32")
    except Exception as err:
        log.warning("[train] scoring failed (%s), returning baseline", err)
        return np.full(len(feature_rows), 0.25, dtype="float32")
