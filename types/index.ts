export type RiskTier = "low" | "med" | "high" | "critical";

export type HazardCategoryId =
  | "all"
  | "violent"
  | "property"
  | "public_order"
  | "traffic_hazard"
  | "environmental";

export interface HazardCategory {
  id: HazardCategoryId;
  label: string;
  description: string;
}

export interface CategoryScore {
  score: number;
  tier: RiskTier;
  count: number;
}

export type ModelCoverage = "full" | "partial" | "none";

export interface Camera {
  id: string;
  name: string;
  location: string;
  address: string;
  thumbnail: string;
  videoUrl?: string;
  snapshotUrl?: string;
  latLng?: [number, number];
  precinctId?: string;
  h3Cell?: string;
  borough?: string;
  modelCoverage?: ModelCoverage;
  online?: boolean;
}

export interface Location {
  id: string;
  name: string;
  cameras: Camera[];
}

export interface RetrievedIncident {
  incidentId: string;
  summary: string;
  distanceM: number;
  daysAgo: number;
  category?: string;
}

export interface Event {
  id: string;
  camera: Camera;
  type: string;
  timestamp: Date;
  thumbnail?: string;
  description?: string;
  isDangerous?: boolean;
  riskScoreAtTime?: number;
  retrievedContext?: RetrievedIncident[];
  priorityScore?: number;
}

export interface BoundingBoxData {
  video_info: {
    name: string;
    width: number;
    height: number;
    fps: number;
    total_frames: number;
    frame_interval: number;
  };
  frames: {
    [frameNumber: string]: {
      boxes: [number, number, number, number][];
      confidences: number[];
      is_keyframe: boolean;
    };
  };
}

export interface RiskScore {
  cameraId: string;
  score: number;
  tier: RiskTier;
  reasons: string[];
  windowStart: string;
  windowEnd: string;
  modelVersion: string;
}

export interface HexCell {
  h3Index: string;
  score: number;
  tier: RiskTier;
  contributingFactors?: Record<string, number>;
  incidentCountForecast?: number;
  categories?: Record<string, CategoryScore>;
}

export interface Heatmap {
  resolution: number;
  cells: HexCell[];
  generatedAt: string;
  windowStart: string;
  windowEnd: string;
}

export interface Precinct {
  id: string;
  name: string;
  centroidLatLng: [number, number];
  riskScore?: number;
  tier?: RiskTier;
}

export interface PredictionWindow {
  windowStart: string;
  windowEnd: string;
  granularityMinutes: number;
  incidentCountForecast: number;
  confidenceInterval: [number, number];
}

export interface ForecastStats {
  predictedNext24h: number;
  highestRiskPrecinct: Precinct | null;
  modelVersion: string;
  generatedAt: string;
  hottestHexes: HexCell[];
}

export interface PatrolWaypoint {
  latLng: [number, number];
  etaSeconds: number;
  cameraId?: string;
}

export interface PatrolRoute {
  unitId: string;
  waypoints: PatrolWaypoint[];
  totalRiskCovered: number;
  solverMetadata: {
    solveMs: number;
    objective: number;
    solverBackend: "cuopt" | "greedy";
  };
}
