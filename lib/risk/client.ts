import type {
  Camera,
  ForecastStats,
  HazardCategory,
  HazardCategoryId,
  Heatmap,
  PatrolRoute,
  RiskScore,
} from "@/types";

/**
 * Browser-side risk client.
 *
 * All requests go through the Next.js `/api/risk/*` proxy routes (which in
 * turn talk to poi-brain server-side). This keeps CORS out of the picture
 * for the judging-room browser path — the only thing the browser needs to
 * reach is Next.js itself, and the proxy handles the hop to the DGX.
 *
 * Server-side code (e.g. a server action that wanted to call poi-brain
 * directly) should use POI_BRAIN_URL via getJsonDirect() below.
 */

const PROXY_BASE = "/api/risk";

const DIRECT_BASE =
  typeof process !== "undefined"
    ? process.env.POI_BRAIN_URL ?? "http://localhost:8080"
    : "http://localhost:8080";

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${PROXY_BASE}${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    throw new Error(`poi-brain proxy ${path} ${res.status}: ${await res.text()}`);
  }
  return (await res.json()) as T;
}

export async function fetchCameras(): Promise<Camera[]> {
  return getJson<Camera[]>("/cameras");
}

export async function fetchHeatmap(
  resolution = 9,
  category: HazardCategoryId = "all",
  hourOfWeek?: number
): Promise<Heatmap> {
  const params = new URLSearchParams({
    resolution: String(resolution),
    category,
  });
  if (hourOfWeek !== undefined) {
    params.set("hour_of_week", String(hourOfWeek));
  }
  return getJson<Heatmap>(`/heatmap?${params.toString()}`);
}

export async function fetchCategories(): Promise<HazardCategory[]> {
  return getJson<HazardCategory[]>("/categories");
}

export async function fetchCameraRisk(
  cameraId: string
): Promise<RiskScore | null> {
  try {
    return await getJson<RiskScore>(
      `/camera/${encodeURIComponent(cameraId)}`
    );
  } catch {
    return null;
  }
}

export async function fetchForecastStats(
  category: HazardCategoryId = "all"
): Promise<ForecastStats> {
  return getJson<ForecastStats>(`/stats?category=${category}`);
}

export async function fetchPatrolRoutes(): Promise<PatrolRoute[]> {
  return getJson<PatrolRoute[]>("/routes");
}

/**
 * SSE subscriptions bypass the proxy — EventSource can't be easily forwarded
 * through a Next.js route handler. These talk directly to poi-brain using
 * the NEXT_PUBLIC_POI_BRAIN_URL env var. Dev-time only; for the DGX demo set
 * NEXT_PUBLIC_POI_BRAIN_URL to the reachable DGX address.
 */
const SSE_BASE =
  process.env.NEXT_PUBLIC_POI_BRAIN_URL ?? "http://localhost:8080";

export function openRiskStream(
  onMessage: (risk: RiskScore) => void,
  onError?: (ev: Event) => void
): EventSource | null {
  if (typeof window === "undefined") return null;
  const es = new EventSource(`${SSE_BASE}/risk/stream`);
  es.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data));
    } catch (err) {
      console.error("[risk-stream] parse error", err);
    }
  };
  if (onError) es.onerror = onError;
  return es;
}

export function openCameraStream(
  onMessage: (
    msg: {
      cameraId: string;
      latestThumbB64?: string;
      latestEvents?: Array<{
        timestamp: string;
        description: string;
        isDangerous: boolean;
      }>;
      riskScoreAtTime?: number;
    }
  ) => void
): EventSource | null {
  if (typeof window === "undefined") return null;
  const es = new EventSource(`${SSE_BASE}/cameras/stream`);
  es.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data));
    } catch (err) {
      console.error("[camera-stream] parse error", err);
    }
  };
  return es;
}

export const POI_BRAIN_BASE_URL = DIRECT_BASE;
