"use server";

import { getVlmClient } from "@/lib/vlm";
import type { FrameEvent } from "@/lib/vlm/shared";

export type VideoEvent = FrameEvent;

export async function detectEvents(
  base64Image: string
): Promise<{ events: VideoEvent[]; rawResponse: string }> {
  console.log("Starting frame analysis (upload)...");
  try {
    return await getVlmClient().analyzeFrame({ base64Image });
  } catch (error) {
    console.error("Error in detectEvents:", error);
    throw error;
  }
}
