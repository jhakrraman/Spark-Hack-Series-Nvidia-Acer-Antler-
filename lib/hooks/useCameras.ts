"use client";

import { useEffect, useState } from "react";
import { fetchCameras } from "@/lib/risk/client";
import { locations as fallbackLocations } from "@/lib/data";
import type { Camera } from "@/types";

export function useCameras() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [source, setSource] = useState<"poi-brain" | "fallback">("fallback");
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const live = await fetchCameras();
        if (cancelled) return;
        if (Array.isArray(live) && live.length > 0) {
          setCameras(live);
          setSource("poi-brain");
          return;
        }
        throw new Error("empty camera list");
      } catch (err) {
        if (cancelled) return;
        setError(err as Error);
        setCameras(fallbackLocations.flatMap((l) => l.cameras));
        setSource("fallback");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { cameras, source, error };
}
