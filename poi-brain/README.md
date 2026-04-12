# poi-brain

Person of Interest — predictive intelligence brain.

FastAPI service that runs on the **Acer Veriton GN100 DGX Spark**. Fuses NYC
Open Data through a RAPIDS pipeline, trains a cuML XGBoost risk forecaster,
hosts an NVIDIA NIM Vision model, polls NYC DOT traffic cameras, and serves
risk/heatmap/routes endpoints over HTTP + SSE to the Next.js dashboard.

## What it does

```
   NYC Open Data (SODA)           NYC DOT Traffic Cams
          │                               │
          ▼                               ▼
   ingest.py → parquet            camera_poller.py (JPEG snapshots)
          │                               │
          ▼                               ▼
   fuse_cudf.py (H3 res 9)                │
          │                               │
          ▼                               │
   train_cuml.py (XGBoost/cuML)           │
          │                               │
          ▼                               ▼
   risk_engine.py ─────────▶ NIM Llama 3.2 Vision (OpenAI-compat)
          │                               │
          ▼                               ▼
   /risk/heatmap   /cameras   /cameras/stream   /frames/analyze
          │
          ▼
   Next.js mission-control dashboard (maplibre + h3-js)
```

## NVIDIA stack

| Library | Used For |
|---|---|
| **NIM** | Llama 3.2 Vision container for frame analysis |
| **cuDF** | Fusing NYPD + collisions + 311 into a single H3-indexed frame |
| **cuSpatial / h3-py** | H3 res 9 binning, spatial joins |
| **cuML (XGBoost)** | Binary risk classifier per H3 cell × 15-min window |
| **cuGraph** (stretch) | PageRank on incident co-occurrence graph |
| **cuOpt** (stretch) | Patrol-route VRP over risk heatmap |

On CUDA machines the full RAPIDS path runs. On laptops (no CUDA) the code
transparently falls back to pandas + sklearn + networkx so the same codebase
boots end-to-end for development.

## DGX setup — end to end

Assumes you've already got the DGX reachable on your tailnet (or local LAN)
and that the NGC CLI is logged in (`ngc config set`). If not, do that first
at https://org.ngc.nvidia.com/setup/api-key.

### 1. Pull the repo

```bash
# On the DGX (over Tailscale or SSH)
git clone https://github.com/<user>/nvidia-hackathon-26-apr.git
cd nvidia-hackathon-26-apr/poi-brain
```

### 2. Install the NIM vision container

```bash
# Log in to NGC's container registry
echo $NGC_API_KEY | docker login nvcr.io -u '$oauthtoken' --password-stdin

# Pick a vision NIM (Llama 3.2 Vision is the best OpenAI-compatible option)
export NIM_IMAGE=nvcr.io/nim/meta/llama-3.2-11b-vision-instruct:latest

# Pre-pull the image (20-25 GB, do this well before the demo)
docker pull $NIM_IMAGE

# Run it, binding to port 8000 on all interfaces so poi-brain can reach it
docker run -d --name poi-nim \
    --gpus all \
    --shm-size=16g \
    -e NGC_API_KEY=$NGC_API_KEY \
    -p 8000:8000 \
    -v /data/poi/nim-cache:/opt/nim/.cache \
    $NIM_IMAGE

# Verify: this should list the model you just launched
curl http://localhost:8000/v1/models
```

Note the DGX's IP/hostname — this is what the Next.js app will point at.
For example `http://dgx.tailnet.ts.net:8000/v1` or `http://192.168.1.42:8000/v1`.

### 3. Install poi-brain Python deps

**Option A — venv + pip (fastest)**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-cpu.txt
pip install --extra-index-url=https://pypi.nvidia.com \
    cudf-cu12 cuml-cu12 cuspatial-cu12
# optional stretch: cugraph-cu12
```

**Option B — RAPIDS Docker image (bulletproof if pip is painful)**

```bash
docker run --gpus all --network host -it \
    -v $PWD:/workspace/poi-brain \
    -w /workspace/poi-brain \
    rapidsai/notebooks:25.04-cuda12.0-py3.11 \
    bash -lc "pip install -r requirements-cpu.txt && bash"
```

### 4. Configure env

```bash
cp .env.example .env
# edit .env:
#   NIM_BASE_URL=http://localhost:8000/v1       (same host as the NIM container)
#   NIM_MODEL=meta/llama-3.2-11b-vision-instruct
#   SODA_APP_TOKEN=<get a free one at data.cityofnewyork.us>
```

### 5. One-shot data pull + model training (~2–5 min)

```bash
python scripts/bootstrap_data.py
```

This pulls NYPD complaints, Vision Zero collisions, 311 street-light reports,
and the NYC DOT camera catalog. Writes parquet to `/data/poi/parquet/` and
trains a cuML/XGBoost risk classifier saved to `/data/poi/models/risk_model.pkl`.

### 6. Run poi-brain

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
# Verify:
curl http://localhost:8080/health
# Expected: {"status":"ok","rapids":true,"cameras":12,"hexCells":...}
```

### 7. Point the Next.js app at the DGX

On your laptop, in `nvidia-hackathon-26-apr/.env.local`:

```bash
POI_VLM_BACKEND=poi-brain
POI_BRAIN_URL=http://<dgx-ip-or-hostname>:8080
NEXT_PUBLIC_POI_BRAIN_URL=http://<dgx-ip-or-hostname>:8080
```

Then `npm run dev` and open http://localhost:3000/protected — you should see
the mission-control dashboard with the H3 heatmap glowing over NYC, NYC DOT
camera tiles pinned to their real locations, and live risk scores flowing in
over SSE.

## Local dev on Mac (Apple Silicon GPU via MPS)

The ML backend auto-detects your hardware at startup and picks the fastest
path available. On an M-series Mac with `torch>=2.3` installed, it will pick
**PyTorch MPS** and train on the Apple GPU. The model file it saves
(`risk_model.pt`) is a plain PyTorch state_dict and is **fully portable** —
the SAME file loads on the DGX's NVIDIA CUDA via `map_location`, so you can
dev on your Mac and ship the trained model to the DGX without any code change.

```bash
cd poi-brain
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-cpu.txt   # includes torch with MPS support
cp .env.example .env
# .env defaults: ML_BACKEND=auto, TORCH_DEVICE=auto — leave as-is
python scripts/bootstrap_data.py
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

At startup you should see the device probe log something like:

```
[device] platform=darwin-arm64 python=3.11.7
[device]   rapids=no (cuDF/cuML not installed)
[device]   torch=yes (2.8.0) cuda=no mps=yes cpu=12
[device]   -> ml_backend=torch torch_device=mps
[device]   Apple Silicon detected — Metal Performance Shaders active.
[torch] training on device=mps
```

On the DGX that same probe will print:

```
[device] platform=linux-x86_64 python=3.11.7
[device]   rapids=yes (cuDF/cuML loaded)
[device]   torch=yes (2.8.0) cuda=yes mps=no cpu=32
[device]   -> ml_backend=cuml-xgb torch_device=cuda
[device]   NVIDIA Linux + RAPIDS — full GPU pipeline active.
```

### Forcing a specific backend

```bash
# In .env (or shell env)
ML_BACKEND=torch        # force torch path even on NVIDIA
ML_BACKEND=cuml-xgb     # force RAPIDS path (errors if not installed)
ML_BACKEND=sklearn      # CPU-only safety net
TORCH_DEVICE=cpu        # force torch onto CPU even if MPS/CUDA available
TORCH_DEVICE=mps
TORCH_DEVICE=cuda
```

### Transferring a Mac-trained model to the DGX

```bash
# On Mac, after bootstrap finishes
scp ~/.poi/models/risk_model.pt dgx:/data/poi/models/risk_model.pt
# On DGX, poi-brain will load it automatically on next start.
# The state_dict is device-agnostic; load_bundle() moves it onto CUDA.
```

### Honest notes

- **NIM is NVIDIA-only.** On Mac the camera poller will log errors hitting
  NIM — that's expected. The risk pipeline still works without NIM (you
  get the heatmap, per-camera risk, SSE stream, cuOpt routes). Optionally
  point `NIM_BASE_URL` at a local vLLM server to get frame analysis
  working locally.
- **For the hackathon demo, the DGX should use `cuml-xgb`, not torch.** The
  RAPIDS pitch is a scoring criterion. Torch on MPS is for dev iteration.
- The default data root is `/data/poi/` which is read-only on Mac. Config
  auto-falls-back to `~/.poi/` so imports don't crash. Override with
  `DATA_ROOT=/path/to/somewhere` in `.env` if you want a custom location.

## Configuration (`.env`)

```bash
# NVIDIA NIM
NIM_BASE_URL=http://localhost:8000/v1
NIM_MODEL=meta/llama-3.2-11b-vision-instruct
NIM_API_KEY=nim

# NYC Open Data (get a free token at data.cityofnewyork.us)
SODA_APP_TOKEN=

# Storage
DATA_ROOT=/data/poi

# Risk model
H3_RESOLUTION=9
PREDICTION_WINDOW_MINUTES=15

# Cameras
CAMERA_POLL_INTERVAL_S=3.0
CAMERA_SUBSET_SIZE=12

# Feature flags
ENABLE_RAPIDS=true
ENABLE_CUSPATIAL=true
ENABLE_CUGRAPH=false
ENABLE_CUOPT=false
```

## API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | status, rapids/vlm flags, counts |
| GET | `/cameras` | NYC DOT camera catalog, tagged with H3 cells |
| GET | `/cameras/{id}` | one camera |
| GET | `/cameras/stream` | SSE stream of per-camera frame updates |
| GET | `/risk/heatmap?resolution=9` | H3 hex risk grid for the dashboard |
| GET | `/risk/hex` | raw hex cells |
| GET | `/risk/camera/{id}` | per-camera risk score |
| GET | `/risk/stream` | SSE stream of risk updates |
| GET | `/stats/forecast` | dashboard top strip numbers |
| POST | `/frames/analyze` | one-shot frame analysis (fallback path) |
| WS | `/frames/ws` | streaming frame ingest (fallback path) |
| GET | `/routes/current` | cuOpt patrol routes |
| POST | `/routes/resolve` | force re-solve |

## Background loops

Both start in `app.main.lifespan`:

1. **risk_engine.run_risk_engine_forever** — every 60s, recomputes hex scores
   from the fused dataframe and publishes per-camera `RiskScore` via SSE.
2. **camera_poller.run_poller_forever** — every 3s, polls each camera's
   snapshot URL, calls NIM with risk context, publishes the frame update.

## Notes for the judges

- **RAPIDS runtime**: `app/pipeline/rapids_runtime.py` probes for cuDF/cuML
  at import time and logs the decision. `/health` reports `rapids: true/false`.
- **Risk granularity**: H3 resolution 9 (~150m hex cells), 15-minute windows.
  NYC covered by ~30K cells. Training rows scale with `hex × time` — this is
  where cuDF joins + cuML training become GPU-sized.
- **Privacy**: nothing leaves the box. NIM is local, RAPIDS is local, camera
  frames are local. The only outbound traffic is to SODA (historical data)
  and webcams.nyctmc.org (public snapshots).
- **Spark Story**: 128 GB unified memory holds the full parquet cache,
  the in-memory cuDF fused frame, the cuML model, the NIM vision model, and
  the live frame buffers simultaneously. One box, no swapping.
