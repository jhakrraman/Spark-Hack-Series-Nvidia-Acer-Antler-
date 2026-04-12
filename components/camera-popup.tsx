"use client";

import { useEffect, useRef, useState } from "react";
import type { Camera, RiskScore } from "@/types";
import { TIER_COLOR } from "@/lib/risk/tier";
import { RiskBadge } from "./risk-badge";
import { cn } from "@/lib/utils";

interface CameraPopupProps {
  camera: Camera | null;
  risk?: RiskScore;
  onClose: () => void;
}

const REFRESH_MS = 5_000;

export function CameraPopup({ camera, risk, onClose }: CameraPopupProps) {
  const [imageSeed, setImageSeed] = useState(Date.now());
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    if (!camera) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [camera, onClose]);

  useEffect(() => {
    if (!camera) return;
    setImgError(false);
    setImageSeed(Date.now());
    const iv = setInterval(() => setImageSeed(Date.now()), REFRESH_MS);
    return () => clearInterval(iv);
  }, [camera?.id]);

  if (!camera) return null;

  const tier = risk?.tier ?? "low";
  const color = TIER_COLOR[tier];

  const snapshotUrl = camera.snapshotUrl;
  const liveUrl = snapshotUrl
    ? `${snapshotUrl}${snapshotUrl.includes("?") ? "&" : "?"}t=${imageSeed}`
    : null;

  return (
    <div
      className="pointer-events-auto absolute inset-0 z-40 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className={cn(
          "relative w-[680px] max-w-[92vw] overflow-hidden rounded-md border-2 bg-black shadow-[0_30px_100px_rgba(0,0,0,0.8)]"
        )}
        style={{
          borderColor: color,
          boxShadow: `0 0 0 1px ${color}, 0 30px 100px rgba(0,0,0,0.9), 0 0 40px ${color}44`,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative aspect-video w-full bg-deck-bg">
          {liveUrl && !imgError ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              key={imageSeed}
              src={liveUrl}
              alt={camera.name}
              className="absolute inset-0 h-full w-full object-cover"
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-[12px] font-bold uppercase tracking-[0.2em] text-white/30">
              {imgError ? "camera offline" : "no feed url"}
            </div>
          )}
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/50" />
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(rgba(0,0,0,0.3)_1px,transparent_1px)] [background-size:3px_3px] opacity-30 mix-blend-overlay" />

          <div className="absolute left-3 top-3 flex items-center gap-2 rounded-sm bg-black/70 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
            LIVE · NYC DOT
          </div>
          <div className="absolute right-3 top-3">
            <RiskBadge tier={tier} score={risk?.score} />
          </div>
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 bottom-3 rounded-sm border border-white/30 bg-black/60 px-2 py-1 text-[9px] font-bold uppercase tracking-[0.2em] text-white/80 hover:bg-white/10"
            aria-label="Close"
          >
            close · esc
          </button>
          <div className="absolute bottom-3 left-3 right-24">
            <div className="text-[9px] uppercase tracking-[0.2em] text-white/40">
              NYC DOT · {camera.id}
            </div>
            <div className="mt-0.5 truncate text-sm font-bold uppercase tracking-tight text-white">
              {camera.name}
            </div>
            <div className="truncate text-[10px] text-white/60">{camera.address}</div>
          </div>
        </div>

        <div className="grid grid-cols-[1fr_180px] gap-4 border-t border-white/10 px-4 py-3">
          <div>
            <div className="text-[9px] uppercase tracking-[0.2em] text-white/40">
              Why flagged
            </div>
            {risk?.reasons && risk.reasons.length > 0 ? (
              <ul className="mt-1 space-y-1 text-[11px] leading-snug text-white/80">
                {risk.reasons.slice(0, 5).map((r, i) => (
                  <li key={i} className="flex gap-2">
                    <span style={{ color }}>›</span>
                    {r}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="mt-1 text-[11px] italic text-white/40">
                no risk reasons — no feature coverage
              </div>
            )}
          </div>
          <div className="border-l border-white/10 pl-4">
            <div className="text-[9px] uppercase tracking-[0.2em] text-white/40">
              Coordinates
            </div>
            <div className="mt-1 font-mono text-[10px] text-white/70">
              {camera.latLng ? camera.latLng[0].toFixed(4) : "—"}° N
              <br />
              {camera.latLng ? Math.abs(camera.latLng[1]).toFixed(4) : "—"}° W
            </div>
            {camera.h3Cell && (
              <>
                <div className="mt-2 text-[9px] uppercase tracking-[0.2em] text-white/40">
                  H3 cell
                </div>
                <div className="mt-0.5 truncate font-mono text-[10px] text-white/70">
                  {camera.h3Cell}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
