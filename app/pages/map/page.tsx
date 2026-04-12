"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { NyctmcCamera } from "@/lib/nyctmc";
import type { FrameEvent } from "@/lib/lmstudio";

// Leaflet touches `window`, so dynamic-import the map with ssr disabled.
const NycMap = dynamic(() => import("@/components/nyc-map"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-deck-bg">
      <span className="text-[12px] font-bold uppercase tracking-[0.14em] text-deck-dim">
        // loading tactical map…
      </span>
    </div>
  ),
});

interface AnalyzeResponse {
  events: FrameEvent[];
  rawResponse?: string;
}

const CAMERA_LIMIT = 900;
const REFRESH_MS = 5000;

export default function MapPage() {
  const [cameras, setCameras] = useState<NyctmcCamera[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<NyctmcCamera | null>(null);
  const [imageSeed, setImageSeed] = useState(Date.now());
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [clock, setClock] = useState("");

  // Live clock
  useEffect(() => {
    const u = () =>
      setClock(
        new Date().toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    u();
    const i = setInterval(u, 1000);
    return () => clearInterval(i);
  }, []);

  // Load the full camera catalog once.
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setIsLoading(true);
        const r = await fetch(`/api/nyctmc/cameras?limit=${CAMERA_LIMIT}`);
        if (!r.ok) throw new Error("failed to load camera catalog");
        const data = await r.json();
        if (!cancelled) setCameras(data.cameras ?? []);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "unknown");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Live-refresh the active camera frame every few seconds.
  useEffect(() => {
    if (!selected) return;
    const i = setInterval(() => setImageSeed(Date.now()), REFRESH_MS);
    return () => clearInterval(i);
  }, [selected]);

  const locatable = useMemo(
    () =>
      cameras.filter(
        (c) =>
          c.latitude != null &&
          c.longitude != null &&
          Number.isFinite(c.latitude) &&
          Number.isFinite(c.longitude)
      ),
    [cameras]
  );

  const imageUrl = selected
    ? `${selected.imageUrl}${selected.imageUrl.includes("?") ? "&" : "?"}t=${imageSeed}`
    : null;

  const handleSelect = (camera: NyctmcCamera) => {
    setSelected(camera);
    setAnalysis(null);
    setAnalysisError(null);
    setImageSeed(Date.now());
  };

  const handleAnalyze = async () => {
    if (!selected) return;
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const r = await fetch("/api/nyctmc/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cameraId: selected.id }),
      });
      if (!r.ok) throw new Error("model analysis failed");
      const data: AnalyzeResponse = await r.json();
      setAnalysis(data);
    } catch (e) {
      setAnalysisError(e instanceof Error ? e.message : "analysis failed");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const hasHazard = analysis?.events?.some((e) => e.isDangerous);

  return (
    <div className="relative mx-auto max-w-[1600px] px-6 py-6">
      {/* Page header */}
      <div className="mb-4 flex items-end justify-between">
        <div>
          <div className="flex items-center gap-3 text-[11px] font-bold uppercase tracking-[0.14em] text-deck-dim">
            <span className="h-px w-8 bg-deck-signal" />
            <span className="text-deck-signal">/pages/map — deck/01</span>
          </div>
          <h1 className="mt-3 text-4xl font-extrabold uppercase tracking-tight text-deck-fg">
            GRID MAP <span className="text-deck-signal">·</span> NYC
          </h1>
          <p className="mt-2 max-w-[60ch] text-[13px] font-medium text-deck-dim">
            Tactical overview of every NYC TMC camera with a known
            position. Click any marker to pull its live feed and run
            on-device inference.
          </p>
        </div>
        <div className="hidden flex-col items-end gap-1.5 text-right text-[11px] font-bold uppercase tracking-[0.14em] text-deck-dim md:flex">
          <div className="flex items-center gap-2">
            <span className="deck-dot text-deck-signal deck-blink" />
            <span className="text-deck-signal">MAP LIVE</span>
          </div>
          <div className="deck-num tabular-nums text-deck-fg text-[13px]">
            {clock} UTC
          </div>
          <div className="deck-num tabular-nums">
            [{String(locatable.length).padStart(3, "0")}/
            {String(cameras.length).padStart(3, "0")} LOCATABLE]
          </div>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        {/* ----- MAP ----- */}
        <div className="deck-panel relative h-[70vh] overflow-hidden">
          <div className="absolute left-3 top-3 z-[500] flex items-center gap-2 bg-deck-bg/85 px-2.5 py-1.5 text-[11px] font-bold uppercase tracking-[0.14em] text-deck-signal">
            <span className="deck-dot deck-blink" />
            {isLoading ? "LOADING…" : `${locatable.length} NODES ON MAP`}
          </div>
          {error && (
            <div className="absolute right-3 top-3 z-[500] bg-deck-alert/20 px-2.5 py-1.5 text-[11px] font-bold uppercase tracking-[0.14em] text-deck-alert">
              err · {error}
            </div>
          )}
          <NycMap
            cameras={locatable}
            selectedId={selected?.id}
            onSelect={handleSelect}
          />
        </div>

        {/* ----- SIDE PANEL: live feed + analysis ----- */}
        <aside className="deck-panel flex max-h-[70vh] flex-col overflow-hidden">
          {selected ? (
            <>
              <div className="border-b border-deck-line p-4">
                <div className="deck-label-hi">ACTIVE FEED</div>
                <div className="mt-1.5 text-base font-extrabold uppercase text-deck-fg">
                  {selected.name}
                </div>
                <div className="deck-label mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span>◉ {selected.area ?? "unknown area"}</span>
                  {selected.latitude != null && selected.longitude != null && (
                    <span className="deck-num">
                      {selected.latitude.toFixed(4)}°N{" "}
                      {Math.abs(selected.longitude).toFixed(4)}°W
                    </span>
                  )}
                </div>
              </div>

              {/* Video container */}
              <div className="relative deck-scanlines border-b border-deck-line bg-deck-bg">
                <div className="absolute left-2 top-2 z-10 flex items-center gap-2 bg-deck-bg/80 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-deck-signal">
                  <span className="deck-dot deck-blink" />
                  LIVE · CAM {selected.id}
                </div>
                <div className="absolute right-2 top-2 z-10 deck-num text-[11px] font-bold text-deck-fg bg-deck-bg/80 px-2 py-1">
                  {clock}
                </div>
                {imageUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={imageSeed}
                    src={imageUrl}
                    alt={selected.name}
                    className="block w-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="flex aspect-video items-center justify-center text-[12px] font-bold text-deck-dim">
                    no signal
                  </div>
                )}
              </div>

              {/* Controls */}
              <div className="border-b border-deck-line p-4">
                <button
                  type="button"
                  onClick={handleAnalyze}
                  disabled={isAnalyzing}
                  className="deck-btn deck-btn--primary w-full justify-center"
                >
                  {isAnalyzing ? "▸ INFERENCE RUNNING…" : "▸ ANALYZE FRAME"}
                </button>
                {analysisError && (
                  <div className="mt-3 border-l-2 border-deck-alert bg-deck-alert/10 px-3 py-2 text-[12px] font-bold text-deck-alert">
                    err · {analysisError}
                  </div>
                )}
              </div>

              {/* Detection stream */}
              <div className="flex-1 overflow-y-auto">
                <div className="flex items-center justify-between border-b border-deck-line px-4 py-3">
                  <div className="deck-label-hi">DETECTION STREAM</div>
                  <div
                    className={`flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.14em] ${
                      hasHazard
                        ? "text-deck-alert"
                        : analysis
                        ? "text-deck-ok"
                        : "text-deck-dim"
                    }`}
                  >
                    <span className="deck-dot" />
                    {hasHazard ? "HAZARD" : analysis ? "NOMINAL" : "IDLE"}
                  </div>
                </div>
                {!analysis && !isAnalyzing && (
                  <div className="p-4 text-[12px] font-bold text-deck-dim">
                    // run analysis to populate
                  </div>
                )}
                {isAnalyzing && (
                  <div className="flex items-center gap-2 p-4 text-[12px] font-bold text-deck-signal">
                    <span className="deck-dot deck-blink" />
                    inference in progress…
                  </div>
                )}
                <ul>
                  {analysis?.events?.map((ev, i) => (
                    <li
                      key={`${ev.timestamp}-${i}`}
                      className={`border-l-2 px-4 py-3 ${
                        ev.isDangerous
                          ? "border-deck-alert bg-deck-alert/10"
                          : "border-deck-line"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-[0.14em]">
                        <span
                          className={
                            ev.isDangerous ? "text-deck-alert" : "text-deck-dim"
                          }
                        >
                          {ev.isDangerous ? "▲ HAZARD" : "■ OBSERVATION"}
                        </span>
                        <span className="deck-num text-deck-faint">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                      </div>
                      <div className="deck-num mt-2 text-[12px] font-bold text-deck-signal">
                        T{ev.timestamp}
                      </div>
                      <div className="mt-1.5 text-[13px] font-medium leading-snug text-deck-fg">
                        {ev.description}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 p-10 text-center">
              <div className="deck-label-hi">NO NODE SELECTED</div>
              <div className="text-[12px] font-bold text-deck-dim">
                › click any marker on the map to pull its live feed
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
