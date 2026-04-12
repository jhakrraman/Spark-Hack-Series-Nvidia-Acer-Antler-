#!/usr/bin/env python
"""One-shot ingestion + training script.

Run before the demo session:

    cd poi-brain
    python scripts/bootstrap_data.py

This will:
1. Pull NYC Open Data into parquet/
2. Build the fused H3 × features frame
3. Train a risk model (cuML on GPU, sklearn on CPU)
4. Save everything to /data/poi (or settings.data_root)
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import ingest, train_cuml  # noqa: E402


def main() -> int:
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s %(levelname)-5s %(name)s %(message)s",
    )
    log = logging.getLogger("bootstrap")
    log.info("STEP 1/2 — ingesting NYC Open Data into parquet…")
    results = ingest.ingest_all()
    for k, v in results.items():
        log.info("  %-16s %s", k, v)

    log.info("STEP 2/2 — training risk model…")
    outcome = train_cuml.train_risk_model()
    log.info("training outcome: %s", outcome)

    log.info("bootstrap complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
