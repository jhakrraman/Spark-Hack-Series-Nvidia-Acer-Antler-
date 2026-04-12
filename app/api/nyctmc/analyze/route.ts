import { NextResponse } from "next/server"
import { fetchNyctmcFrame } from "@/lib/nyctmc"
import { analyzeFrame } from "@/lib/lmstudio"

export async function POST(request: Request) {
  try {
    const { cameraId, transcript } = await request.json()

    if (!cameraId || typeof cameraId !== "string") {
      return NextResponse.json({ error: "cameraId is required" }, { status: 400 })
    }

    const { base64Image } = await fetchNyctmcFrame(cameraId)
    const result = await analyzeFrame({ base64Image, transcript })

    return NextResponse.json(result)
  } catch (error) {
    console.error("Failed to analyze NYCTMC frame", error)
    return NextResponse.json({ error: "Failed to analyze NYCTMC frame" }, { status: 500 })
  }
}
