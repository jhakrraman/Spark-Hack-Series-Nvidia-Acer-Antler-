# Person of Interest — DECK/01

> **Spark Hack Series — New York** · Human Impact Challenge
> Presented by NVIDIA · Acer · Antler · April 10–12, 2026

A predictive surveillance intelligence platform for New York City.
Fuses NYC Open Data through an NVIDIA RAPIDS pipeline, trains a
per-neighborhood risk forecaster on-device, polls 364 live NYC DOT
traffic cameras, and runs every frame through an NVIDIA NIM vision
model — all on a single **Acer Veriton GN100** (DGX Spark, Grace
Blackwell GB10, 128 GB unified memory).

Nothing leaves the box. No cloud APIs. No compliance risk.
**Your Code. Your Hardware. Your Edge.**

## Challenge track: Human Impact

## Team Members:
**Raman Jha**  
**Pratham Saraf**  
**Jay Daftari**  
**Siddhant Mohan**  
**Athul Radhakrishnan**

> *Improvements in health, safety, and economic opportunity for residents.*

Person of Interest addresses the safety dimension. NYC already publishes
the data — NYPD complaints, Vision Zero collisions, 311 street-condition
reports, and hundreds of live camera feeds. What the city lacks is a
system that fuses all of it in real time and tells you where trouble is
forming *before* it happens. That's what this builds.

## What it does

### Mission Control (`/protected`)
Fullscreen MapLibre heatmap rendering H3 resolution-9 hex cells (~150 m)
colored by predicted 15-minute risk scores. Time-of-week slider for
dynamic forecasting, category picker for hazard filtering, top-risk
camera watch list, NVIDIA stack status pills (NIM · cuDF · cuSpatial ·
cuML · cuOpt), and live SSE risk streaming.

### Camera Map (`/pages/map`)
Leaflet-based tactical map with 364 amber markers over Carto Dark Matter
tiles. Click any marker to pull the live JPEG snapshot and run on-device
VLM analysis. Side panel shows the detection stream.

### NYC TMC Catalog (`/pages/nyctmc`)
Searchable 3-column catalog of NYC DOT cameras with operator notes,
inline frame analysis, and structured event output.

### Realtime Stream (`/pages/realtimeStreamPage`)
Browser webcam capture with TensorFlow.js pose detection, per-frame VLM
analysis, timestamped key-moments timeline, and a chat assistant.

### Dispatch (`/pages/dispatch`)
Patrol-route visualization powered by NVIDIA cuOpt VRP solver.

### Statistics (`/pages/statistics`)
Historical key-moment charts with LLM-generated summaries.

## NVIDIA stack

| Library | Used for |
|---|---|
| **NIM** | Llama 3.2 11B Vision container for frame analysis (OpenAI-compatible) |
| **cuDF** | GPU dataframe fusion of NYPD + Vision Zero + 311 on H3 cells |
| **cuSpatial / H3** | H3 resolution-9 spatial binning, ~30K hex cells across five boroughs |
| **cuML (XGBoost)** | Binary risk classifier per hex cell × 15-minute window |
| **cuGraph** | Incident co-occurrence PageRank (stretch) |
| **cuOpt** | Patrol-route VRP over the live heatmap (stretch) |

On CUDA machines the full RAPIDS path runs. On laptops (no CUDA) the
code transparently falls back to pandas + sklearn + networkx.

## Architecture

```
NYC Open Data (SODA)              NYC DOT Traffic Cams (364)
      │                                     │
      ▼                                     ▼
  ingest.py → parquet              camera_poller.py (JPEG every 3s)
      │                                     │
      ▼                                     │
  fuse_cudf.py (H3 res 9)                  │
      │                                     │
      ▼                                     ▼
  train_cuml.py (XGBoost)          NIM Llama 3.2 Vision (local)
      │                                     │
      ▼                                     ▼
  risk_engine.py ────────► /risk/heatmap   /frames/analyze
      │
      ▼
  Next.js Mission Control (MapLibre + H3)
```

**Hardware:** Acer Veriton GN100 — NVIDIA GB10 Grace Blackwell Superchip,
128 GB unified memory. The parquet cache, cuDF frame, cuML model, NIM
vision weights, and live frame buffers all coexist in the same address
space. One box, no swapping.

## Running it

### Option A — Full stack (DGX Spark / GN100)

```bash
# 1. Start NVIDIA NIM container
docker run -d --name poi-nim --gpus all --shm-size=16g \
    -e NGC_API_KEY -p 8000:8000 \
    nvcr.io/nim/meta/llama-3.2-11b-vision-instruct:latest

# 2. Start poi-brain
cd poi-brain
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-cpu.txt
pip install --extra-index-url=https://pypi.nvidia.com cudf-cu12 cuml-cu12 cuspatial-cu12
python scripts/bootstrap_data.py          # pulls NYC Open Data + trains model
uvicorn app.main:app --host 0.0.0.0 --port 8080

# 3. Start the dashboard
cd ..
npm install
cp .env.example .env.local
# Set POI_VLM_BACKEND=poi-brain and POI_BRAIN_URL=http://localhost:8080
npm run dev
```

### Option B — Local dev (MacBook / no CUDA)

```bash
# poi-brain with CPU fallback
cd poi-brain
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-cpu.txt
export POI_FORCE_CPU=1
python scripts/bootstrap_data.py
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Next.js
cd ..
npm install
cp .env.example .env.local
# Set POI_VLM_BACKEND=poi-brain and POI_BRAIN_URL=http://localhost:8080
npm run dev
```

Open `http://localhost:3000`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `POI_VLM_BACKEND` | `poi-brain` | VLM backend selector: `nim` / `poi-brain` |
| `POI_BRAIN_URL` | `http://dgx.tailnet.ts.net:8080` | poi-brain server URL (server-side) |
| `NEXT_PUBLIC_POI_BRAIN_URL` | `http://dgx.tailnet.ts.net:8080` | poi-brain URL (client-side hooks) |
| `NIM_BASE_URL` | `http://dgx.tailnet.ts.net:8000/v1` | NVIDIA NIM endpoint (direct mode) |
| `NIM_MODEL` | `meta/llama-3.2-11b-vision-instruct` | NIM model ID |
| `OPENAI_API_KEY` | — | Optional: chat assistant + stats summary |
| `RESEND_API_KEY` | — | Optional: email alerts |
| `ALERT_EMAIL_TO` | — | Optional: alert recipients |

## Fine-tuning Qwen VL

A QLoRA fine-tuning pipeline is included at `poi-brain/finetune/` for
adapting Qwen2.5-VL or Qwen3-VL to the POI detection schema. The
trained adapter is a drop-in replacement — same FrameEvent JSON output,
zero frontend changes.

```bash
cd poi-brain/finetune
pip install -r requirements.txt

# Prepare data from existing annotations
python prepare_dataset.py \
    --from-bounding-boxes ../../public/bounding_boxes \
    --output ./train.jsonl

# Train (7B fits in 24 GB with QLoRA 4-bit)
python train_qwen_vl.py \
    --model-name Qwen/Qwen2.5-VL-7B-Instruct \
    --dataset ./train.jsonl \
    --output-dir ./adapter_out
```

See [`poi-brain/finetune/README.md`](poi-brain/finetune/README.md) for
supported models, VRAM requirements, and all training arguments.

## Project layout

```
app/
  layout.tsx                         # app shell with status strip + nav
  page.tsx                           # boot-screen landing page
  globals.css                        # DECK/01 design tokens
  protected/page.tsx                 # Mission Control (fullscreen heatmap)
  pages/
    map/                             # Leaflet camera map
    nyctmc/                          # NYC TMC catalog + analysis
    dispatch/                        # cuOpt patrol routes
    realtimeStreamPage/              # live browser capture
    upload/                          # MP4 upload + analysis
    saved-videos/                    # saved library
    statistics/                      # charts + LLM summary
  api/
    nyctmc/{cameras,analyze}/        # NYC TMC proxy + VLM
    risk/{heatmap,cameras,stats,..}/ # poi-brain proxy routes
    chat/                            # assistant (OpenAI, optional)
    summary/                         # stats summary (OpenAI, optional)
    send-email/                      # alerts (Resend, optional)

lib/
  vlm/                               # pluggable VLM clients (nim/poi-brain)
  risk/                              # risk tier + API client
  hooks/                             # React hooks for poi-brain SSE/REST
  nyctmc.ts                          # NYC TMC camera catalog
  data.ts                            # demo mock data

components/
  risk-heatmap-map.tsx               # MapLibre H3 heatmap (313 lines)
  nyc-map.tsx                        # Leaflet tactical map
  camera-popup.tsx                   # camera click popup
  camera-float.tsx                   # watch-list sidebar cards
  forecast-panel.tsx                 # top-strip forecast numbers
  time-slider.tsx                    # time-of-week scrubber
  category-picker.tsx                # hazard category filter
  risk-badge.tsx                     # risk tier pill

poi-brain/
  app/main.py                        # FastAPI entrypoint
  app/pipeline/                      # RAPIDS data pipeline
    ingest.py → fuse_cudf.py → train_cuml.py → risk_engine.py
    camera_catalog.py, camera_poller.py
    solve_cuopt.py, graph_cugraph.py
    device_probe.py, categories.py
  app/vlm/nim_client.py              # NVIDIA NIM vision client
  app/routers/                       # HTTP + SSE endpoints
  finetune/                          # Qwen VL QLoRA fine-tuning
    train_qwen_vl.py, prepare_dataset.py
```

## Design

Terminal-brutalist tactical HUD built for a dark control-room context:

- **JetBrains Mono 500–800** for all UI; Inter for long prose
- **Hard rectangles** with amber corner brackets — zero border-radius
- **Monochrome + amber signal** — near-black `#08080a` base, `#fafafc`
  foreground, tactical amber `#ffb81c`, military olive `#6c8a4e` for
  alerts, mint `#34d399` for OK
- **Scan-line overlays** on video containers, tactical grid background
- **Tabular numerals** and ASCII markers everywhere data lives

## Data sources (all public, all NYC)

| Source | What | Endpoint |
|---|---|---|
| NYC Open Data (SODA) | NYPD complaints, Vision Zero crashes, 311 reports | `data.cityofnewyork.us` |
| NYC DOT TMC | 364 live traffic camera JPEG streams | `webcams.nyctmc.org/api` |
| NWS | Central Park weather observations | `api.weather.gov` |

## Privacy

All inference is local. Camera frames never leave the GN100. The only
outbound traffic is to SODA (historical CSV pulls, one-shot) and
`webcams.nyctmc.org` (public JPEG snapshots). No PII is stored,
transmitted, or used for training.
