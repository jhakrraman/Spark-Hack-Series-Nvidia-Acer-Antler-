import type { RiskTier } from "@/types";

export function scoreToTier(score: number): RiskTier {
  if (score >= 0.8) return "critical";
  if (score >= 0.6) return "high";
  if (score >= 0.35) return "med";
  return "low";
}

export const TIER_COLOR: Record<RiskTier, string> = {
  low: "#22c55e",
  med: "#eab308",
  high: "#f97316",
  critical: "#ef4444",
};

export const TIER_GLOW: Record<RiskTier, string> = {
  low: "rgba(34,197,94,0.35)",
  med: "rgba(234,179,8,0.45)",
  high: "rgba(249,115,22,0.55)",
  critical: "rgba(239,68,68,0.65)",
};

export const TIER_RING: Record<RiskTier, string> = {
  low: "ring-green-500/60",
  med: "ring-yellow-500/70",
  high: "ring-orange-500/80",
  critical: "ring-red-500/90",
};

export const TIER_LABEL: Record<RiskTier, string> = {
  low: "LOW",
  med: "MED",
  high: "HIGH",
  critical: "CRIT",
};
