export type { FrameEvent, AnalyzeFrameOptions, AnalyzeFrameResult } from "./vlm/shared";
export { getVlmClient } from "./vlm";

import { getVlmClient } from "./vlm";
import type { AnalyzeFrameOptions, AnalyzeFrameResult } from "./vlm/shared";

export async function analyzeFrame(
  opts: AnalyzeFrameOptions
): Promise<AnalyzeFrameResult> {
  return getVlmClient().analyzeFrame(opts);
}
