export interface FrameEvent {
  timestamp: string;
  description: string;
  isDangerous: boolean;
}

export interface RiskContext {
  cameraId: string;
  score: number;
  tier: "low" | "med" | "high" | "critical";
  reasons: string[];
  windowStart?: string;
  windowEnd?: string;
}

export interface AnalyzeFrameOptions {
  base64Image: string;
  transcript?: string;
  riskContext?: RiskContext;
  cameraId?: string;
}

export interface AnalyzeFrameResult {
  events: FrameEvent[];
  rawResponse: string;
  riskScoreAtTime?: number;
}

export const DETECTION_PROMPT = `Analyze this frame and determine if any of these specific dangerous situations are occurring:

1. Medical Emergencies:
- Person unconscious or lying motionless
- Person clutching chest/showing signs of heart problems
- Seizures or convulsions
- Difficulty breathing or choking

2. Falls and Injuries:
- Person falling or about to fall
- Person on the ground after a fall
- Signs of injury or bleeding
- Limping or showing signs of physical trauma

3. Distress Signals:
- Person calling for help or showing distress
- Panic attacks or severe anxiety symptoms
- Signs of fainting or dizziness
- Headache or unease
- Signs of unconsciousness

4. Violence or Threats:
- Physical altercations
- Threatening behavior
- Weapons visible

5. Suspicious Activities:
- Shoplifting
- Vandalism
- Trespassing

6. Traffic and Pedestrian Hazards:
- Near-miss between vehicles and pedestrians
- Jaywalking clusters in heavy traffic
- Vehicles running red lights or stop signs
- Blocked crosswalks or emergency lanes`;

export const OUTPUT_INSTRUCTIONS = `For each observation in this frame, emit one event with a "mm:ss" timestamp, a brief description, and an isDangerous flag. Set isDangerous=true if the event involves a fall, injury, unease, pain, accident, traffic hazard, or concerning behavior; otherwise false. If nothing concerning is visible, still emit at least one event describing the normal scene with isDangerous=false.`;

export const FRAME_EVENTS_SCHEMA = {
  type: "object",
  properties: {
    events: {
      type: "array",
      items: {
        type: "object",
        properties: {
          timestamp: { type: "string" },
          description: { type: "string" },
          isDangerous: { type: "boolean" },
        },
        required: ["timestamp", "description", "isDangerous"],
      },
    },
  },
  required: ["events"],
} as const;

export function buildPrompt(opts: AnalyzeFrameOptions): string {
  const transcriptLine = opts.transcript
    ? `\nConsider this audio transcript from the scene: "${opts.transcript}"\n`
    : "";

  const riskLine = opts.riskContext
    ? `\nContextual risk signal for this camera's location (from NYC Open Data):
- Predicted risk tier: ${opts.riskContext.tier.toUpperCase()} (score ${opts.riskContext.score.toFixed(
        2
      )})
- Reasons: ${opts.riskContext.reasons.join("; ") || "n/a"}
When risk tier is HIGH or CRITICAL, be more sensitive to subtle precursor behavior (loitering, erratic movement, sudden dispersal, near-miss pedestrian/vehicle interactions).\n`
    : "";

  return `${DETECTION_PROMPT}${transcriptLine}${riskLine}\n${OUTPUT_INSTRUCTIONS}`;
}

export function toDataUrl(input: string): string {
  if (input.startsWith("data:")) return input;
  return `data:image/jpeg;base64,${input}`;
}

export function extractJson(text: string): string {
  const codeBlockMatch = text.match(/```(?:json)?\s*({[\s\S]*?})\s*```/);
  if (codeBlockMatch) return codeBlockMatch[1];
  const rawMatch = text.match(/\{[\s\S]*\}/);
  if (rawMatch) return rawMatch[0];
  return text;
}

export interface VlmClient {
  analyzeFrame(opts: AnalyzeFrameOptions): Promise<AnalyzeFrameResult>;
  readonly backend: "lmstudio" | "nim" | "poi-brain";
}
