"use client";

import { useEffect, useState } from "react";
import { fetchForecastStats } from "@/lib/risk/client";
import type { ForecastStats, HazardCategoryId } from "@/types";

export function useForecastStats(
  category: HazardCategoryId = "all",
  pollMs = 30_000
) {
  const [stats, setStats] = useState<ForecastStats | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function tick() {
      try {
        const data = await fetchForecastStats(category);
        if (!cancelled) {
          setStats(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err as Error);
      } finally {
        if (!cancelled) timer = setTimeout(tick, pollMs);
      }
    }

    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [category, pollMs]);

  return { stats, error };
}
