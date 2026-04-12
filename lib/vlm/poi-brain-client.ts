import {
  AnalyzeFrameOptions,
  AnalyzeFrameResult,
  VlmClient,
} from "./shared";

const POI_BRAIN_URL =
  process.env.POI_BRAIN_URL ?? "http://localhost:8080";

async function analyzeFrame(
  opts: AnalyzeFrameOptions
): Promise<AnalyzeFrameResult> {
  if (!opts.base64Image) throw new Error("No image data provided");

  const body = {
    cameraId: opts.cameraId,
    frameJpegB64: opts.base64Image.replace(/^data:image\/\w+;base64,/, ""),
    transcript: opts.transcript ?? "",
  };

  const res = await fetch(`${POI_BRAIN_URL}/frames/analyze`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`poi-brain analyze failed ${res.status}: ${text}`);
  }

  const data = await res.json();
  return {
    events: Array.isArray(data.events) ? data.events : [],
    rawResponse: JSON.stringify(data),
    riskScoreAtTime: data.riskScoreAtTime,
  };
}

export const poiBrainClient: VlmClient = {
  backend: "poi-brain",
  analyzeFrame,
};
