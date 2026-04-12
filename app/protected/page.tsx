"use client";

import { useMemo, useState } from "react";
import { useCameras } from "@/lib/hooks/useCameras";
import { useHeatmap } from "@/lib/hooks/useHeatmap";
import { useRiskStream } from "@/lib/hooks/useRiskStream";
import { useForecastStats } from "@/lib/hooks/useForecastStats";
import { usePatrolRoutes } from "@/lib/hooks/usePatrolRoutes";
import { useBrainHealth } from "@/lib/hooks/useBrainHealth";
import { useCategories } from "@/lib/hooks/useCategories";
import { RiskHeatmapMap } from "@/components/risk-heatmap-map";
import { CameraFloat } from "@/components/camera-float";
import { ForecastPanel } from "@/components/forecast-panel";
import { CategoryPicker } from "@/components/category-picker";
import { TimeSlider } from "@/components/time-slider";
import { CameraPopup } from "@/components/camera-popup";
import type { HazardCategoryId } from "@/types";

export default function MissionControlPage() {
  const [category, setCategory] = useState<HazardCategoryId>("all");
  const [hourOfWeek, setHourOfWeek] = useState<number | undefined>(undefined);
  const categories = useCategories();
  const { cameras, source } = useCameras();
  const { heatmap, loading: heatmapLoading, error: heatmapError } = useHeatmap(
    9,
    category,
    hourOfWeek
  );
  const { risksByCamera, connected } = useRiskStream();
  const { stats } = useForecastStats(category);
  const { routes } = usePatrolRoutes();
  const health = useBrainHealth();

  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);

  const visibleCameras = useMemo(() => {
    const withGeo = cameras.filter((c) => c.latLng);
    const withRisk = withGeo
      .map((c) => ({ cam: c, risk: risksByCamera[c.id] }))
      .sort((a, b) => (b.risk?.score ?? 0) - (a.risk?.score ?? 0));
    return withRisk;
  }, [cameras, risksByCamera]);

  const topCameras = visibleCameras.slice(0, 8);

  const modelBackend = health?.vlmBackend ?? "nim";
  const rapidsOn = health?.rapids ?? false;
  const mlBackend = health?.ml?.backend ?? "—";
  const torchDevice = health?.ml?.torchDevice ?? "—";
  const hasMps = health?.ml?.mpsAvailable ?? false;
  const hasCuda = health?.ml?.cudaAvailable ?? false;

  return (
    <div className="fixed inset-0 bg-deck-bg text-deck-fg">
      <RiskHeatmapMap
        cameras={cameras}
        heatmap={heatmap}
        risksByCamera={risksByCamera}
        patrolRoutes={routes}
        selectedCameraId={selectedCameraId}
        onCameraClick={setSelectedCameraId}
      />

      <header className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-start justify-between gap-4 p-4">
        <div className="pointer-events-auto rounded-md border border-white/10 bg-black/70 px-3 py-2 backdrop-blur-md">
          <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.18em] text-deck-signal">
            <span className="h-px w-6 bg-deck-signal" />
            /mission-control — deck/00
          </div>
          <div className="mt-1 text-lg font-bold uppercase tracking-tight text-deck-fg">
            PERSON OF INTEREST
          </div>
          <div className="text-[9px] uppercase tracking-widest text-white/40">
            NYC-native predictive surveillance ·
            <span
              className={`ml-1 ${
                source === "poi-brain" ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {source === "poi-brain" ? "brain online" : "local fallback"}
            </span>
            <span
              className={`ml-2 ${
                connected ? "text-emerald-400" : "text-white/30"
              }`}
            >
              · sse {connected ? "live" : "idle"}
            </span>
            {health?.ok && (
              <span className="ml-2 text-emerald-400">
                · nim {health.nimModel ? "loaded" : "offline"}
              </span>
            )}
            {health?.ok === false && (
              <span className="ml-2 text-amber-400">· brain unreachable</span>
            )}
          </div>
          {health?.ok && (
            <div className="mt-1 flex items-center gap-2 text-[8px] uppercase tracking-[0.16em] text-white/40">
              <span>ml</span>
              <span
                className={
                  mlBackend === "cuml-xgb"
                    ? "text-[#76b900]"
                    : mlBackend === "torch"
                      ? "text-cyan-300"
                      : "text-white/60"
                }
              >
                {mlBackend}
              </span>
              <span className="text-white/20">·</span>
              <span>dev</span>
              <span
                className={
                  torchDevice === "cuda"
                    ? "text-[#76b900]"
                    : torchDevice === "mps"
                      ? "text-cyan-300"
                      : "text-white/50"
                }
              >
                {torchDevice}
              </span>
              {(hasCuda || hasMps) && (
                <>
                  <span className="text-white/20">·</span>
                  <span className="text-white/50">
                    {hasCuda ? "cuda ✓" : hasMps ? "mps ✓" : ""}
                  </span>
                </>
              )}
              {health.platform?.os && (
                <>
                  <span className="text-white/20">·</span>
                  <span className="text-white/50">
                    {health.platform.os}-{health.platform.arch}
                  </span>
                </>
              )}
            </div>
          )}
        </div>

        <div className="pointer-events-auto flex flex-col items-end gap-2">
          <ForecastPanel stats={stats} vlmBackend={modelBackend} />
          <CategoryPicker
            categories={categories}
            value={category}
            onChange={setCategory}
          />
          <TimeSlider
            value={hourOfWeek}
            onChange={setHourOfWeek}
            className="w-[420px]"
          />
        </div>
      </header>

      <aside className="pointer-events-none absolute inset-y-0 left-0 z-10 flex w-[260px] flex-col gap-2 overflow-y-auto p-4 pt-28">
        <div className="pointer-events-auto mb-1 flex items-center justify-between text-[9px] uppercase tracking-[0.2em] text-white/50">
          <span>watch list · top {topCameras.length}</span>
          <span className="tabular-nums text-white/30">
            {cameras.length.toString().padStart(3, "0")} nodes
          </span>
        </div>
        <div className="pointer-events-auto space-y-2">
          {topCameras.map(({ cam, risk }) => (
            <CameraFloat
              key={cam.id}
              camera={cam}
              risk={risk}
              selected={selectedCameraId === cam.id}
              onClick={() => setSelectedCameraId(cam.id)}
            />
          ))}
          {topCameras.length === 0 && (
            <div className="rounded-md border border-white/10 bg-black/60 p-3 text-[10px] uppercase tracking-wider text-white/40 backdrop-blur-md">
              waiting for poi-brain camera catalog…
            </div>
          )}
        </div>
      </aside>


      <footer className="pointer-events-none absolute inset-x-0 bottom-0 z-10 flex items-end justify-between gap-4 p-4">
        <div className="pointer-events-auto rounded-md border border-white/10 bg-black/70 px-3 py-2 backdrop-blur-md">
          <div className="text-[9px] uppercase tracking-[0.18em] text-white/50">
            NVIDIA Stack
          </div>
          <div className="mt-1 flex items-center gap-3 text-[10px] font-bold uppercase tracking-wider">
            <StackPill label="NIM" color="#76b900" dim={!health?.ok} />
            <StackPill label="cuDF" color="#76b900" dim={!rapidsOn} />
            <StackPill label="cuSpatial" color="#76b900" dim={!rapidsOn} />
            <StackPill label="cuML" color="#76b900" dim={!rapidsOn} />
            <StackPill label="cuOpt" color="#76b900" dim={routes.length === 0} />
          </div>
        </div>

      </footer>

      <CameraPopup
        camera={cameras.find((c) => c.id === selectedCameraId) ?? null}
        risk={
          selectedCameraId ? risksByCamera[selectedCameraId] : undefined
        }
        onClose={() => setSelectedCameraId(null)}
      />

      {heatmapError && (
        <div className="pointer-events-none absolute bottom-4 left-1/2 z-30 -translate-x-1/2 rounded-md border border-red-500/40 bg-black/80 px-3 py-2 text-[10px] uppercase tracking-wider text-red-400 backdrop-blur-md">
          heatmap unreachable — {heatmapError.message}
        </div>
      )}
      {heatmapLoading && !heatmapError && (
        <div className="pointer-events-none absolute bottom-4 left-1/2 z-30 -translate-x-1/2 rounded-md border border-white/10 bg-black/60 px-3 py-2 text-[10px] uppercase tracking-wider text-white/60 backdrop-blur-md">
          loading risk heatmap…
        </div>
      )}
    </div>
  );
}

function StackPill({
  label,
  color,
  dim,
}: {
  label: string;
  color: string;
  dim?: boolean;
}) {
  return (
    <span
      className="rounded-sm border px-1.5 py-0.5"
      style={{
        borderColor: color,
        color: dim ? `${color}80` : color,
        backgroundColor: `${color}14`,
        opacity: dim ? 0.55 : 1,
      }}
    >
      {label}
    </span>
  );
}
