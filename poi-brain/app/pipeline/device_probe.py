"""OS + accelerator detection used by the ML backend dispatcher.

Prints exactly what we found so the user can trust the auto-selection:

    [device] platform=darwin-arm64 python=3.11.7
    [device]   rapids=no (cuDF/cuML not installed)
    [device]   torch=yes (2.5.1) cuda=no mps=yes cpu=12
    [device]   -> ml_backend=torch torch_device=mps

Runs once at startup and caches the result.
"""
from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import dataclass
from functools import lru_cache

from ..config import settings
from .rapids_runtime import HAS_RAPIDS

log = logging.getLogger("poi.device")


@dataclass(frozen=True)
class DeviceEnvironment:
    os_name: str
    arch: str
    python: str
    has_rapids: bool
    has_torch: bool
    torch_version: str | None
    cuda_available: bool
    mps_available: bool
    cpu_count: int
    ml_backend: str
    torch_device: str


def _probe_torch():
    try:
        import torch
    except Exception:
        return False, None, False, False

    cuda = bool(torch.cuda.is_available())
    mps = bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
    return True, torch.__version__, cuda, mps


def _resolve_ml_backend(has_rapids: bool, has_torch: bool) -> str:
    pref = (settings.ml_backend or "auto").lower()
    if pref != "auto":
        return pref
    if has_rapids:
        return "cuml-xgb"
    if has_torch:
        return "torch"
    return "sklearn"


def _resolve_torch_device(has_torch: bool, cuda: bool, mps: bool) -> str:
    pref = (settings.torch_device or "auto").lower()
    if pref != "auto":
        return pref
    if not has_torch:
        return "cpu"
    if cuda:
        return "cuda"
    if mps:
        return "mps"
    return "cpu"


@lru_cache(maxsize=1)
def detect_environment() -> DeviceEnvironment:
    os_name = platform.system().lower()
    arch = platform.machine().lower()
    py = sys.version.split()[0]
    has_torch, torch_ver, cuda, mps = _probe_torch()
    cpu_count = os.cpu_count() or 1

    ml_backend = _resolve_ml_backend(HAS_RAPIDS, has_torch)
    torch_device = _resolve_torch_device(has_torch, cuda, mps)

    env = DeviceEnvironment(
        os_name=os_name,
        arch=arch,
        python=py,
        has_rapids=HAS_RAPIDS,
        has_torch=has_torch,
        torch_version=torch_ver,
        cuda_available=cuda,
        mps_available=mps,
        cpu_count=cpu_count,
        ml_backend=ml_backend,
        torch_device=torch_device,
    )

    log.info("[device] platform=%s-%s python=%s", env.os_name, env.arch, env.python)
    log.info(
        "[device]   rapids=%s (%s)",
        "yes" if env.has_rapids else "no",
        "cuDF/cuML loaded" if env.has_rapids else "cuDF/cuML not installed",
    )
    log.info(
        "[device]   torch=%s%s cuda=%s mps=%s cpu=%d",
        "yes" if env.has_torch else "no",
        f" ({env.torch_version})" if env.torch_version else "",
        "yes" if env.cuda_available else "no",
        "yes" if env.mps_available else "no",
        env.cpu_count,
    )
    log.info(
        "[device]   -> ml_backend=%s torch_device=%s",
        env.ml_backend,
        env.torch_device,
    )

    if env.os_name == "darwin" and env.arch in ("arm64", "aarch64"):
        if env.has_torch and env.mps_available:
            log.info("[device]   Apple Silicon detected — Metal Performance Shaders active.")
        elif env.has_torch:
            log.warning(
                "[device]   Apple Silicon detected but MPS unavailable — install "
                "a recent torch (>=2.0) to enable Metal."
            )

    if env.os_name == "linux" and env.has_rapids:
        log.info("[device]   NVIDIA Linux + RAPIDS — full GPU pipeline active.")

    return env
