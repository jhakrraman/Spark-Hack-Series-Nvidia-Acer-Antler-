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

const LMSTUDIO_BASE_URL =
  process.env.LMSTUDIO_BASE_URL ?? "http://localhost:1234/v1";
const LMSTUDIO_MODEL =
  process.env.LMSTUDIO_MODEL ?? "google/gemma-4-26b-a4b";

const lmstudio = new OpenAI({
  baseURL: LMSTUDIO_BASE_URL,
  apiKey: process.env.LMSTUDIO_API_KEY ?? "local",
});

async function analyzeFrame(
  opts: AnalyzeFrameOptions
): Promise<AnalyzeFrameResult> {
  if (!opts.base64Image) throw new Error("No image data provided");

  const imageUrl = toDataUrl(opts.base64Image);
  const prompt = buildPrompt(opts);

  console.log(
    "[lmstudio] Sending frame to",
    LMSTUDIO_BASE_URL,
    "model:",
    LMSTUDIO_MODEL
  );

  let completion;
  try {
    completion = await lmstudio.chat.completions.create({
      model: LMSTUDIO_MODEL,
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
      "[lmstudio] Request failed:",
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
    };
  } catch (parseError) {
    console.error("[lmstudio] JSON parse failed:", parseError);
    return { events: [], rawResponse: text };
  }
}

export const lmstudioClient: VlmClient = {
  backend: "lmstudio",
  analyzeFrame,
};
