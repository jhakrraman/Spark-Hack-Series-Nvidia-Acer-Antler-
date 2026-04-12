"use client";

import { useEffect, useState } from "react";
import { openRiskStream } from "@/lib/risk/client";
import type { RiskScore } from "@/types";

export function useRiskStream() {
  const [risksByCamera, setRisks] = useState<Record<string, RiskScore>>({});
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const es = openRiskStream(
      (risk) => {
        setRisks((prev) => ({ ...prev, [risk.cameraId]: risk }));
        setConnected(true);
      },
      () => setConnected(false)
    );
    return () => es?.close();
  }, []);

  return { risksByCamera, connected };
}
