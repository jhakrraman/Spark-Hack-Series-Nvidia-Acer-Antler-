import { Buffer } from "buffer"

const DEFAULT_BASE_URL = "https://webcams.nyctmc.org/api"

export const NYCTMC_API_BASE_URL = process.env.NYCTMC_API_BASE_URL ?? DEFAULT_BASE_URL

const CAMERAS_ENDPOINT = `${NYCTMC_API_BASE_URL}/cameras`

export interface NyctmcCamera {
  id: string
  name: string
  area?: string | null
  latitude: number | null
  longitude: number | null
  imageUrl: string
}

interface RawNyctmcCamera {
  id?: string
  name?: string
  camera_name?: string
  location?: string
  area?: string
  borough?: string
  latitude?: number | string
  lat?: number | string
  longitude?: number | string
  lon?: number | string
  imageUrl?: string
  url?: string
}

function toNumber(value?: string | number | null): number | null {
  if (value === null || value === undefined) return null
  if (typeof value === "number") return Number.isFinite(value) ? value : null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function normalizeCamera(raw: RawNyctmcCamera): NyctmcCamera | null {
  if (!raw?.id) return null

  const name = raw.name ?? raw.camera_name ?? raw.location ?? "Unnamed Camera"
  const imageUrl = raw.imageUrl ?? raw.url ?? `${CAMERAS_ENDPOINT}/${raw.id}/image`

  return {
    id: raw.id,
    name,
    area: raw.area ?? raw.borough ?? null,
    latitude: toNumber(raw.latitude ?? raw.lat),
    longitude: toNumber(raw.longitude ?? raw.lon),
    imageUrl,
  }
}

async function fetchJson<T>(input: string): Promise<T> {
  const response = await fetch(input, {
    cache: "no-store",
    next: { revalidate: 0 },
    headers: {
      Accept: "application/json",
    },
  })

  if (!response.ok) {
    throw new Error(`NYCTMC request failed: ${response.status} ${response.statusText}`)
  }

  return (await response.json()) as T
}

export async function fetchNyctmcCameras(limit = 0): Promise<NyctmcCamera[]> {
  const payload = await fetchJson<RawNyctmcCamera[] | { cameras: RawNyctmcCamera[] }>(CAMERAS_ENDPOINT)
  const rawList = Array.isArray(payload) ? payload : payload.cameras ?? []
  const normalized = rawList
    .map(normalizeCamera)
    .filter((camera): camera is NyctmcCamera => Boolean(camera))

  if (typeof limit === "number" && limit > 0) {
    return normalized.slice(0, limit)
  }

  return normalized
}

export async function fetchNyctmcFrame(cameraId: string): Promise<{ base64Image: string; contentType: string }> {
  if (!cameraId) {
    throw new Error("cameraId is required to fetch NYCTMC frame")
  }

  const imageUrl = `${CAMERAS_ENDPOINT}/${cameraId}/image?ts=${Date.now()}`
  const response = await fetch(imageUrl, {
    cache: "no-store",
    next: { revalidate: 0 },
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch NYCTMC frame for camera ${cameraId}: ${response.status}`)
  }

  const arrayBuffer = await response.arrayBuffer()
  const contentType = response.headers.get("content-type") ?? "image/jpeg"
  const base64Image = Buffer.from(arrayBuffer).toString("base64")

  return { base64Image, contentType }
}
