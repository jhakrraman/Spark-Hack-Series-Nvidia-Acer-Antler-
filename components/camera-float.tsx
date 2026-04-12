"use client";

import Image from "next/image";
import type { Camera, RiskScore } from "@/types";
import { RiskBadge } from "./risk-badge";
import { TIER_COLOR } from "@/lib/risk/tier";
import { cn } from "@/lib/utils";

interface CameraFloatProps {
  camera: Camera;
  risk?: RiskScore;
  thumbB64?: string;
  selected?: boolean;
  onClick?: () => void;
  className?: string;
}

export function CameraFloat({
  camera,
  risk,
  thumbB64,
  selected,
  onClick,
  className,
}: CameraFloatProps) {
  const tier = risk?.tier ?? "low";
  const color = TIER_COLOR[tier];
  const thumbSrc = thumbB64
    ? `data:image/jpeg;base64,${thumbB64}`
    : camera.snapshotUrl ?? camera.thumbnail;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group relative flex w-56 flex-col overflow-hidden rounded-md border bg-black/70 text-left backdrop-blur-md shadow-[0_8px_32px_rgba(0,0,0,0.65)] transition-transform hover:scale-[1.03]",
        selected && "scale-[1.05]",
        className
      )}
      style={{
        borderColor: color,
        boxShadow: `0 0 0 1px ${color}55, 0 8px 32px rgba(0,0,0,0.7)`,
      }}
    >
      <div className="relative aspect-video w-full overflow-hidden bg-deck-bg">
        {thumbSrc ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={thumbSrc}
            alt={camera.name}
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-[9px] uppercase tracking-[0.2em] text-deck-dim">
            offline
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/40" />
        <div className="absolute left-1.5 top-1.5 flex items-center gap-1 rounded-sm bg-black/60 px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-[0.18em] text-emerald-400">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
          LIVE
        </div>
        <div className="absolute right-1.5 top-1.5">
          <RiskBadge tier={tier} score={risk?.score} compact />
        </div>
        <div className="absolute bottom-1.5 left-1.5 right-1.5 flex items-end justify-between gap-1">
          <div className="flex-1 min-w-0">
            <div className="truncate text-[10px] font-semibold uppercase tracking-wide text-white">
              {camera.name}
            </div>
            <div className="truncate text-[8px] uppercase tracking-wider text-white/60">
              {camera.borough ?? camera.location}
            </div>
          </div>
          {camera.latLng && (
            <div className="text-right text-[8px] tabular-nums text-white/50">
              {camera.latLng[0].toFixed(3)}
              <br />
              {camera.latLng[1].toFixed(3)}
            </div>
          )}
        </div>
      </div>
      {risk?.reasons && risk.reasons.length > 0 && (
        <div className="border-t border-white/10 px-2 py-1.5">
          <div className="text-[8px] uppercase tracking-[0.18em] text-white/40">
            why flagged
          </div>
          <div className="mt-0.5 line-clamp-2 text-[9px] leading-tight text-white/70">
            {risk.reasons.slice(0, 2).join(" · ")}
          </div>
        </div>
      )}
    </button>
  );
}
