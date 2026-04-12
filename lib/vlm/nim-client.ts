import OpenAI from "openai";
import {
  AnalyzeFrameOptions,
  AnalyzeFrameResult,
  FRAME_EVENTS_SCHEMA,
  VlmClient,
  buildPrompt,
  extractJson,
  toDataUrl,
} from "./shared";

const NIM_BASE_URL =
  process.env.NIM_BASE_URL ?? "http://localhost:8000/v1";
const NIM_MODEL =
  process.env.NIM_MODEL ?? "meta/llama-3.2-11b-vision-instruct";
const NIM_API_KEY = process.env.NIM_API_KEY ?? "nim";

const nim = new OpenAI({
  baseURL: NIM_BASE_URL,
  apiKey: NIM_API_KEY,
});

async function analyzeFrame(
  opts: AnalyzeFrameOptions
): Promise<AnalyzeFrameResult> {
  if (!opts.base64Image) throw new Error("No image data provided");

  const imageUrl = toDataUrl(opts.base64Image);
  const prompt = buildPrompt(opts);

  console.log(
    "[nim] Sending frame to",
    NIM_BASE_URL,
    "model:",
    NIM_MODEL,
    opts.cameraId ? `camera=${opts.cameraId}` : ""
  );

  let completion;
  try {
    completion = await nim.chat.completions.create({
      model: NIM_MODEL,
      temperature: 0.1,
      max_tokens: 800,
      response_format: {
        type: "json_schema",
        json_schema: {
          name: "frame_events",
          schema: FRAME_EVENTS_SCHEMA as unknown as Record<string, unknown>,
          strict: true,
        },
      },
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: prompt },
            { type: "image_url", image_url: { url: imageUrl } },
          ],
        },
      ],
    });
  } catch (err) {
    const anyErr = err as { status?: number; message?: string; error?: unknown };
    console.error(
      "[nim] Request failed:",
      anyErr.status ?? "?",
      anyErr.message,
      anyErr.error
    );
    throw err;
  }

  const choice = completion.choices?.[0];
  const text = choice?.message?.content ?? "";
  if (!text) return { events: [], rawResponse: "" };

  try {
    const parsed = JSON.parse(extractJson(text));
    return {
      events: Array.isArray(parsed.events) ? parsed.events : [],
      rawResponse: text,
      riskScoreAtTime: opts.riskContext?.score,
    };
  } catch (parseError) {
    console.error("[nim] JSON parse failed:", parseError);
    return { events: [], rawResponse: text };
  }
}

export const nimClient: VlmClient = {
  backend: "nim",
  analyzeFrame,
};
