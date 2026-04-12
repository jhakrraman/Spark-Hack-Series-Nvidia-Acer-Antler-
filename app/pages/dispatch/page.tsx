"use client";

import { useState } from "react";
import { useCameras } from "@/lib/hooks/useCameras";
import { useHeatmap } from "@/lib/hooks/useHeatmap";
import { useRiskStream } from "@/lib/hooks/useRiskStream";
import { usePatrolRoutes } from "@/lib/hooks/usePatrolRoutes";
import { RiskHeatmapMap } from "@/components/risk-heatmap-map";
import { RiskBadge } from "@/components/risk-badge";

export default function DispatchPage() {
  const { cameras } = useCameras();
  const { heatmap } = useHeatmap(9);
  const { risksByCamera } = useRiskStream();
  const { routes } = usePatrolRoutes(10_000);
  const [selected, setSelected] = useState<string | null>(null);

  const totalCovered = routes.reduce((a, r) => a + r.totalRiskCovered, 0);
  const solveMs =
    routes.length > 0 ? Math.round(routes[0].solverMetadata.solveMs) : 0;
  const backend = routes.length > 0 ? routes[0].solverMetadata.solverBackend : "—";

  return (
    <div className="fixed inset-0 bg-deck-bg text-deck-fg">
      <RiskHeatmapMap
        cameras={cameras}
        heatmap={heatmap}
        risksByCamera={risksByCamera}
        patrolRoutes={routes}
        selectedCameraId={selected}
        onCameraClick={setSelected}
      />

      <header className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-start justify-between gap-4 p-4">
        <div className="pointer-events-auto rounded-md border border-white/10 bg-black/70 px-3 py-2 backdrop-blur-md">
          <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.18em] text-deck-signal">
            <span className="h-px w-6 bg-deck-signal" />
            /dispatch — deck/01
          </div>
          <div className="mt-1 text-lg font-bold uppercase tracking-tight text-deck-fg">
            PATROL ROUTES · cuOpt
          </div>
          <div className="text-[9px] uppercase tracking-widest text-white/40">
            VRP over H3 risk heatmap
          </div>
        </div>

        <div className="pointer-events-auto flex items-stretch gap-3 rounded-md border border-white/10 bg-black/70 px-3 py-2 backdrop-blur-md">
          <Stat label="Units dispatched" value={String(routes.length).padStart(2, "0")} color="#67e8f9" />
          <Divider />
          <Stat label="Risk covered" value={totalCovered.toFixed(2)} color="#f97316" />
          <Divider />
          <Stat label="Solve time" value={`${solveMs} ms`} color="#a3e635" />
          <Divider />
          <Stat label="Solver" value={backend.toUpperCase()} color="#a78bfa" />
        </div>
      </header>

      <aside className="pointer-events-auto absolute bottom-4 left-4 top-28 z-10 flex w-[320px] flex-col gap-2 overflow-y-auto rounded-md border border-white/10 bg-black/70 p-3 backdrop-blur-md">
        <div className="mb-1 text-[9px] uppercase tracking-[0.2em] text-white/50">
          ROUTE PLAN · {routes.length} units
        </div>
        {routes.map((r) => (
          <div
            key={r.unitId}
            className="rounded-md border border-white/10 bg-black/50 p-2"
          >
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-bold uppercase tracking-wider text-cyan-300">
                {r.unitId}
              </div>
              <div className="text-[9px] tabular-nums text-white/50">
                risk {r.totalRiskCovered.toFixed(2)}
              </div>
            </div>
            <div className="mt-1 text-[9px] uppercase tracking-wider text-white/40">
              {r.waypoints.length} stops · budget{" "}
              {Math.round(
                r.waypoints[r.waypoints.length - 1]?.etaSeconds ?? 0
              )}
              s
            </div>
          </div>
        ))}
        {routes.length === 0 && (
          <div className="rounded-md border border-white/10 bg-black/50 p-3 text-[10px] uppercase tracking-wider text-white/40">
            waiting for cuOpt solver…
          </div>
        )}
      </aside>

      {selected &&
        (() => {
          const cam = cameras.find((c) => c.id === selected);
          const risk = cam ? risksByCamera[cam.id] : undefined;
          if (!cam) return null;
          return (
            <div className="pointer-events-auto absolute bottom-4 right-4 z-10 w-[360px] rounded-md border border-white/10 bg-black/80 p-3 backdrop-blur-md">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-[9px] uppercase tracking-[0.2em] text-white/40">
                    camera
                  </div>
                  <div className="truncate text-sm font-bold uppercase tracking-tight text-white">
                    {cam.name}
                  </div>
                  <div className="truncate text-[10px] text-white/60">
                    {cam.address}
                  </div>
                </div>
                {risk && <RiskBadge tier={risk.tier} score={risk.score} />}
              </div>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="mt-2 text-[9px] uppercase tracking-[0.2em] text-white/40 hover:text-white/80"
              >
                close
              </button>
            </div>
          );
        })()}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex min-w-0 flex-col">
      <div className="text-[8px] uppercase tracking-[0.18em] text-white/50">
        {label}
      </div>
      <div className="mt-0.5 truncate text-[13px] font-bold tabular-nums" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

function Divider() {
  return <div className="w-px self-stretch bg-white/10" />;
}
