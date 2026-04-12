"use client";

import { useEffect, useState } from "react";

export interface BrainPlatform {
  os?: string;
  arch?: string;
  python?: string;
}

export interface BrainMlInfo {
  backend?: "auto" | "cuml-xgb" | "torch" | "sklearn" | string;
  torchDevice?: "cuda" | "mps" | "cpu" | string;
  hasTorch?: boolean;
  torchVersion?: string | null;
  cudaAvailable?: boolean;
  mpsAvailable?: boolean;
  cpuCount?: number;
}

export interface BrainHealth {
  ok: boolean;
  rapids?: boolean;
  cameras?: number;
  hexCells?: number;
  modelVersion?: string;
  vlmBackend?: string;
  nimBaseUrl?: string;
  nimModel?: string;
  uptimeSeconds?: number;
  platform?: BrainPlatform;
  ml?: BrainMlInfo;
  error?: string;
}

export function useBrainHealth(pollMs = 15_000) {
  const [health, setHealth] = useState<BrainHealth | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function tick() {
      try {
        const res = await fetch("/api/risk/health", { cache: "no-store" });
        const data = await res.json();
        if (!cancelled) setHealth(data);
      } catch (err) {
        if (!cancelled)
          setHealth({ ok: false, error: (err as Error).message ?? "unreachable" });
      } finally {
        if (!cancelled) timer = setTimeout(tick, pollMs);
      }
    }

    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [pollMs]);

  return health;
}
