"use client";

import type { RiskTier } from "@/types";
import { TIER_COLOR, TIER_LABEL } from "@/lib/risk/tier";
import { cn } from "@/lib/utils";

interface RiskBadgeProps {
  tier: RiskTier;
  score?: number;
  compact?: boolean;
  className?: string;
}

export function RiskBadge({ tier, score, compact, className }: RiskBadgeProps) {
  const color = TIER_COLOR[tier];
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.16em] backdrop-blur-sm",
        className
      )}
      style={{
        borderColor: color,
        color,
        backgroundColor: `${color}1a`,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
      />
      {TIER_LABEL[tier]}
      {!compact && typeof score === "number" && (
        <span className="ml-1 tabular-nums opacity-80">
          {score.toFixed(2)}
        </span>
      )}
    </div>
  );
}
