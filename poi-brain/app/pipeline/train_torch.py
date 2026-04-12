"""PyTorch risk classifier — portable across Apple MPS, NVIDIA CUDA, and CPU.

Why this exists: cuML/XGBoost(CUDA) only run on NVIDIA GPUs. Developers on Apple
Silicon want to exercise their Metal GPU during dev. PyTorch has first-class MPS
support, and a state_dict saved on MPS loads directly on CUDA (and vice versa)
via `map_location`, so the SAME model file is usable on Mac GPU and on the DGX.

Used when `POI_ML_BACKEND=torch` or when cuML isn't available and torch is.
The cuML/XGBoost path (train_cuml.py) remains the DGX default so the RAPIDS
pitch stays intact for the hackathon demo.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from ..config import settings

log = logging.getLogger("poi.torch")

FEATURE_COLS = [
    "crime_90d",
    "collision_365d",
    "streetlight_30d",
    "signal_30d",
    "noise_30d",
    "hour_of_week",
    "is_weekend",
]

ARCH_ID = "RiskMLP-32-16-v1"


def _torch():
    import torch  # local import so non-torch installs still load other modules

    return torch


def resolve_device(pref: str | None = None):
    """Pick the best device available.

    Uses settings.torch_device (default "auto") unless `pref` overrides.

    Auto order:
        1. NVIDIA CUDA (DGX, workstation GPUs)
        2. Apple MPS   (M1/M2/M3 Macs)
        3. CPU
    """
    torch = _torch()
    raw = (pref or settings.torch_device or "auto").lower()

    if raw == "cpu":
        return torch.device("cpu")
    if raw == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available")
        return torch.device("cuda")
    if raw == "mps":
        if not (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()):
            raise RuntimeError("MPS requested but not available")
        return torch.device("mps")

    # auto
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _build_model(n_features: int):
    torch = _torch()
    from torch import nn

    class RiskMLP(nn.Module):
        def __init__(self, n: int) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(n, 32),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(32, 16),
                nn.ReLU(),
                nn.Linear(16, 1),
            )

        def forward(self, x):  # type: ignore[override]
            return self.net(x).squeeze(-1)

    return RiskMLP(n_features)


def train_pytorch_model(
    X: np.ndarray,
    y: np.ndarray,
    *,
    device_pref: str | None = None,
    epochs: int = 120,
    lr: float = 1e-3,
    batch_size: int = 512,
) -> dict[str, Any]:
    """Train the RiskMLP on the given feature matrix.

    Returns a bundle suitable for pickling (state_dict lives inside; the model
    itself is instantiated fresh on load).
    """
    torch = _torch()

    device_pref = device_pref or os.environ.get("POI_TORCH_DEVICE", "auto")
    device = resolve_device(device_pref)
    log.info("[torch] training on device=%s", device)

    model = _build_model(X.shape[1]).to(device)

    X_t = torch.from_numpy(X.astype("float32")).to(device)
    y_t = torch.from_numpy(y.astype("float32")).to(device)

    pos = float(y_t.sum().item())
    neg = float((y_t == 0).sum().item())
    pos_weight = torch.tensor([neg / max(pos, 1.0)], device=device)
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optim = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)

    n = int(X_t.shape[0])
    model.train()
    last_loss = float("nan")

    for epoch in range(epochs):
        perm = torch.randperm(n, device=device)
        running = 0.0
        steps = 0
        for start in range(0, n, batch_size):
            idx = perm[start : start + batch_size]
            logits = model(X_t[idx])
            loss = loss_fn(logits, y_t[idx])
            optim.zero_grad()
            loss.backward()
            optim.step()
            running += float(loss.item())
            steps += 1
        last_loss = running / max(steps, 1)
        if epoch % 20 == 0 or epoch == epochs - 1:
            log.info("[torch] epoch %3d/%3d loss=%.4f", epoch + 1, epochs, last_loss)

    model.eval()
    return {
        "backend": "torch",
        "arch": ARCH_ID,
        "state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
        "features": FEATURE_COLS,
        "n_features": int(X.shape[1]),
        "device_trained_on": str(device),
        "epochs": epochs,
        "final_loss": last_loss,
    }


def save_bundle(bundle: dict[str, Any]) -> Path:
    torch = _torch()
    path = settings.models_root / "risk_model.pt"
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(bundle, path)
    log.info(
        "[torch] wrote %s (trained on %s, final loss %.4f)",
        path,
        bundle.get("device_trained_on"),
        bundle.get("final_loss", float("nan")),
    )
    return path


def load_bundle(device_pref: str | None = None) -> dict[str, Any] | None:
    """Load the torch bundle and re-instantiate the model on the chosen device.

    If a `.pt` file doesn't exist, returns None so callers can fall back to the
    sklearn pickle.
    """
    torch = _torch()
    path = settings.models_root / "risk_model.pt"
    if not path.exists():
        return None

    bundle = torch.load(path, map_location="cpu", weights_only=False)
    model = _build_model(bundle["n_features"])
    model.load_state_dict(bundle["state_dict"])
    model.eval()

    device_pref = device_pref or os.environ.get("POI_TORCH_DEVICE", "auto")
    device = resolve_device(device_pref)
    model.to(device)
    log.info(
        "[torch] loaded %s onto %s (originally trained on %s)",
        path,
        device,
        bundle.get("device_trained_on", "unknown"),
    )
    bundle["model"] = model
    bundle["device"] = str(device)
    return bundle


def score(bundle: dict[str, Any], features: np.ndarray) -> np.ndarray:
    torch = _torch()
    model = bundle["model"]
    device = next(model.parameters()).device
    X_t = torch.from_numpy(features.astype("float32")).to(device)
    with torch.no_grad():
        logits = model(X_t)
        probs = torch.sigmoid(logits)
    return probs.detach().cpu().numpy().astype("float32")
