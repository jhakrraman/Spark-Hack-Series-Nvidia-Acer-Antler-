"use client";

import type { ForecastStats } from "@/types";
import { TIER_COLOR } from "@/lib/risk/tier";

interface ForecastPanelProps {
  stats: ForecastStats | null;
  vlmBackend?: string;
}

export function ForecastPanel({ stats, vlmBackend }: ForecastPanelProps) {
  return (
    <div className="pointer-events-auto flex items-stretch gap-3 rounded-md border border-white/10 bg-black/70 px-3 py-2 backdrop-blur-md">
      <Stat
        label="Predicted 24h"
        value={stats ? String(stats.predictedNext24h).padStart(3, "0") : "···"}
        color="#67e8f9"
      />
      <Divider />
      <Stat
        label="Top precinct"
        value={stats?.highestRiskPrecinct?.name ?? "—"}
        color={
          stats?.highestRiskPrecinct?.tier
            ? TIER_COLOR[stats.highestRiskPrecinct.tier]
            : "#67e8f9"
        }
      />
      <Divider />
      <Stat
        label="Hex grid"
        value={
          stats ? `${stats.hottestHexes?.length ?? 0} hot cells` : "—"
        }
        color="#f97316"
      />
      <Divider />
      <Stat
        label="VLM"
        value={(vlmBackend ?? "lmstudio").toUpperCase()}
        color="#a3e635"
      />
      <Divider />
      <Stat
        label="Model"
        value={stats?.modelVersion ?? "cuml-xgb@stub"}
        color="#a78bfa"
        mono
      />
    </div>
  );
}

function Stat({
  label,
  value,
  color,
  mono,
}: {
  label: string;
  value: string;
  color: string;
  mono?: boolean;
}) {
  return (
    <div className="flex min-w-0 flex-col">
      <div className="text-[8px] uppercase tracking-[0.18em] text-white/50">
        {label}
      </div>
      <div
        className={`mt-0.5 truncate text-[13px] font-bold ${
          mono ? "font-mono" : ""
        }`}
        style={{ color }}
      >
        {value}
      </div>
    </div>
  );
}

function Divider() {
  return <div className="w-px self-stretch bg-white/10" />;
}
