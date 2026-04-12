# Person of Interest — DECK/01

A local-inference tactical HUD for live NYC infrastructure.

DECK/01 watches the public NYC Traffic Management Center camera catalog
(hundreds of feeds) and runs every frame through a **local** Gemma 4
vision-language model served by LM Studio. Nothing leaves the machine.
No API bills. No rate limits. No external inference hops.

## What it does

- **Map tab** — every NYC TMC camera with known coordinates rendered as
  a tactical marker over a dark basemap. Click any marker to pull the
  live still and run on-device inference.
- **NYC deck tab** — sortable catalog with operator notes, inline
  analysis, and a structured detection stream.
- **Realtime tab** — browser webcam or uploaded MP4 → local Gemma 4
  frame detection with pose keypoints, event timeline, and a chat
  assistant fed the detection stream.
- **Grid dashboard** — tactical overview of every registered camera
  with an event log sidebar.
- **Statistics tab** — charts over historical key-moment data, plus an
  LLM summary of notable patterns.

## Stack

- **Next.js 15 / App Router** · React 19 · TypeScript · Tailwind CSS
- **LM Studio** running `google/gemma-4-26b-a4b` (or any vision-capable
  model) via an OpenAI-compatible endpoint at `http://localhost:1234/v1`
- **JSON Schema** structured output for deterministic detections and
  zero reasoning-token overhead on Gemma 4
- **Leaflet + react-leaflet** with Carto Dark Matter tiles for the map
- **Chart.js** for the statistics page
- **Resend** for alert emails (optional)

## Architecture

```
┌─────────────────┐   ┌────────────────────┐   ┌──────────────────┐
│  webcams.nyctmc │──►│ /api/nyctmc/*      │──►│  lib/lmstudio.ts │
│  .org/api       │   │  cameras | analyze │   │  (Gemma 4 VLM)   │
│  ~900 feeds     │   └────────────────────┘   └──────────────────┘
└─────────────────┘                                      ▲
                                                         │
       ┌─────────────────────────────────────────────────┘
       │
┌──────┴───────────────────────────────────────────────────┐
│               Next.js App Router UI                       │
│   /pages/map   /pages/nyctmc   /pages/realtimeStreamPage  │
│   /protected   /pages/statistics   /pages/upload          │
└───────────────────────────────────────────────────────────┘
```

## Running it

**Prereqs**

1. Node 18+ and `npm`
2. [LM Studio](https://lmstudio.ai) with a vision-capable Gemma 4 model
   loaded and the developer server started (default: `http://localhost:1234`)

**Setup**

```bash
npm install
cp .env.example .env.local     # adjust LMSTUDIO_MODEL if needed
npm run dev
```

Open `http://localhost:3000`.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `LMSTUDIO_BASE_URL` | no | `http://localhost:1234/v1` | Local LM Studio OpenAI-compatible endpoint |
| `LMSTUDIO_MODEL` | no | `google/gemma-4-26b-a4b` | Must match an `id` returned by `GET /v1/models` |
| `LMSTUDIO_API_KEY` | no | `lm-studio` | LM Studio ignores this; any non-empty string works |
| `OPENAI_API_KEY` | no | — | Only used by the optional chat assistant (`/api/chat`) and summary (`/api/summary`) routes |
| `RESEND_API_KEY` | no | — | Required only if you want email alerts |
| `ALERT_EMAIL_TO` | no | — | Comma-separated recipient list for alert emails |
| `ALERT_EMAIL_FROM` | no | `DECK/01 <onboarding@resend.dev>` | Alert email `from` header |

## Layout

```
app/
  layout.tsx                       # app shell, status strip, nav, footer
  page.tsx                         # landing (boot screen + CTAs)
  globals.css                      # DECK/01 design tokens + utilities
  protected/page.tsx               # tactical camera grid dashboard
  pages/
    map/page.tsx                   # Leaflet-based NYC camera map
    nyctmc/page.tsx                # NYC TMC catalog + analysis
    realtimeStreamPage/page.tsx    # live browser capture + inference
    upload/page.tsx                # MP4 upload + inference
    saved-videos/page.tsx          # saved library
    statistics/page.tsx            # charts + LLM summary
    video/[id]/page.tsx            # single-video deep dive
  api/
    nyctmc/cameras/route.ts        # proxy to NYC TMC camera catalog
    nyctmc/analyze/route.ts        # frame → local VLM
    chat/route.ts                  # assistant chat (OpenAI, optional)
    summary/route.ts               # stats summary (OpenAI, optional)
    send-email/route.ts            # Resend alerts (optional)
lib/
  lmstudio.ts                      # shared LM Studio client + frame schema
  nyctmc.ts                        # NYC TMC fetch + normalization
  data.ts                          # demo camera + event mock data
components/
  nyc-map.tsx                      # Leaflet wrapper (dynamic-imported)
  camera-feed.tsx                  # looping video tile for the dashboard
  camera-modal.tsx                 # full-screen camera viewer
  event-feed.tsx                   # recent-incident sidebar
  timestamp-list.tsx               # keymoment list
  chat-interface.tsx               # assistant chat widget
  stats-overview.tsx               # dashboard metric tiles
  header-nav.tsx                   # primary nav with numbered codes
  header-auth.tsx                  # operator badge
  home-link.tsx                    # DECK/01 wordmark
```

## Design

The UI is a terminal-brutalist tactical HUD:

- **Monospace** (JetBrains Mono) for everything except long prose
- **Hard rectangles** with amber corner brackets — zero border-radius
- **Monochrome + one signal color** — near-black base, off-white
  foreground, tactical amber `#ffb81c` for active state, dull military
  olive `#6c8a4e` for alerts, mint green for OK status
- **Subtle scan lines** on video containers
- **Tabular numerals** and ASCII markers (`▲`, `■`, `//`, `[01/200]`)
  everywhere data lives
- **Dark Leaflet tiles** (Carto Dark Matter) so the map blends into the
  page chrome

## Notes

- All inference runs locally. No frames are uploaded anywhere.
- The optional `/api/chat` and `/api/summary` routes still call the
  OpenAI API for the conversational assistant and the stats summary —
  you can swap them to hit `lib/lmstudio.ts` instead if you prefer
  zero cloud dependencies.
- Geographic coordinates on the NYC TMC feed are inconsistent upstream;
  the map page shows a `LOCATABLE / TOTAL` counter so you can see the
  split at a glance.
