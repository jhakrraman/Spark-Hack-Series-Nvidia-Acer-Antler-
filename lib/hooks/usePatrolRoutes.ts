"use client";

import { useEffect, useState } from "react";
import { fetchPatrolRoutes } from "@/lib/risk/client";
import type { PatrolRoute } from "@/types";

export function usePatrolRoutes(pollMs = 15_000) {
  const [routes, setRoutes] = useState<PatrolRoute[]>([]);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function tick() {
      try {
        const data = await fetchPatrolRoutes();
        if (!cancelled) setRoutes(data);
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
  }, [pollMs]);

  return { routes, error };
}
