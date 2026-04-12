"use server";

import { getVlmClient } from "@/lib/vlm";
import type { FrameEvent, RiskContext } from "@/lib/vlm/shared";

export type VideoEvent = FrameEvent;

export async function detectEvents(
  base64Image: string,
  transcript: string = "",
  cameraId?: string,
  riskContext?: RiskContext
): Promise<{ events: VideoEvent[]; rawResponse: string; riskScoreAtTime?: number }> {
  console.log("Starting frame analysis (realtime stream)...");
  try {
    return await getVlmClient().analyzeFrame({
      base64Image,
      transcript,
      cameraId,
      riskContext,
    });
  } catch (error) {
    console.error("Error in detectEvents:", error);
    throw error;
  }
}
