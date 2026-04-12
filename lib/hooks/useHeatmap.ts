"use client";

import { useEffect, useState } from "react";
import { fetchHeatmap } from "@/lib/risk/client";
import type { HazardCategoryId, Heatmap } from "@/types";

export function useHeatmap(
  resolution = 9,
  category: HazardCategoryId = "all",
  hourOfWeek?: number,
  pollMs = 10_000
) {
  const [heatmap, setHeatmap] = useState<Heatmap | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function tick() {
      try {
        const data = await fetchHeatmap(resolution, category, hourOfWeek);
        if (!cancelled) {
          setHeatmap(data);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err as Error);
          setLoading(false);
        }
      } finally {
        // When the slider is active we don't poll — the user drives updates.
        if (!cancelled && hourOfWeek === undefined) timer = setTimeout(tick, pollMs);
      }
    }

    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [resolution, category, hourOfWeek, pollMs]);

  return { heatmap, error, loading };
}
