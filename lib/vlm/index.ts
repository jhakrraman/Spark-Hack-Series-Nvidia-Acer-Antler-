import type { VlmClient } from "./shared";
import { lmstudioClient } from "./lmstudio-client";
import { nimClient } from "./nim-client";
import { poiBrainClient } from "./poi-brain-client";

export * from "./shared";

type Backend = "lmstudio" | "nim" | "poi-brain";

function resolveBackend(): Backend {
  const raw = (process.env.POI_VLM_BACKEND ?? "").toLowerCase();
  if (raw === "nim") return "nim";
  if (raw === "poi-brain" || raw === "poibrain" || raw === "dgx") return "poi-brain";
  return "lmstudio";
}

export function getVlmClient(): VlmClient {
  switch (resolveBackend()) {
    case "nim":
      return nimClient;
    case "poi-brain":
      return poiBrainClient;
    default:
      return lmstudioClient;
  }
}
