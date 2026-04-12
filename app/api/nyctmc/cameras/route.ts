import { NextResponse } from "next/server"
import { fetchNyctmcCameras } from "@/lib/nyctmc"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const limitParam = searchParams.get("limit")
  const limit = limitParam ? Number(limitParam) : 0

  try {
    const cameras = await fetchNyctmcCameras(Number.isFinite(limit) ? limit : 0)
    return NextResponse.json({ cameras })
  } catch (error) {
    console.error("Failed to load NYCTMC cameras", error)
    return NextResponse.json(
      { error: "Failed to load NYCTMC cameras" },
      { status: 502 }
    )
  }
}
