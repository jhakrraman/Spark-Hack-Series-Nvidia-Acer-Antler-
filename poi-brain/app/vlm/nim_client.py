"""NVIDIA NIM VLM client — OpenAI-compatible endpoint hosted on the DGX."""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import List, Optional

from openai import OpenAI

from ..config import settings
from ..schemas import FrameEvent, RiskScore

log = logging.getLogger("poi.vlm")

DETECTION_PROMPT = """Analyze this traffic/street camera frame and emit events for any of these situations:

1. Medical emergencies (unconscious, seizure, chest-clutching, choking)
2. Falls and injuries (falling, on-ground, bleeding, limping)
3. Distress signals (calling for help, panic, fainting)
4. Violence or threats (altercations, weapons, aggressive behavior)
5. Suspicious activities (loitering, trespassing, vandalism)
6. Traffic and pedestrian hazards (near-miss vehicle/pedestrian, jaywalking clusters, red-light running, blocked crosswalks, vehicle stopped in travel lane)
7. Crowd anomalies (sudden dispersal, bottlenecks, pushing)
"""

OUTPUT_INSTRUCTIONS = """For each observation in this frame, emit one event with a "mm:ss" timestamp, brief description, and isDangerous flag. Set isDangerous=true for any fall, injury, unease, pain, accident, traffic hazard, or concerning behavior. If nothing concerning is visible, still emit at least one event describing the normal scene with isDangerous=false."""

FRAME_EVENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "description": {"type": "string"},
                    "isDangerous": {"type": "boolean"},
                },
                "required": ["timestamp", "description", "isDangerous"],
            },
        }
    },
    "required": ["events"],
}


def _extract_json(text: str) -> str:
    m = re.search(r"```(?:json)?\s*({[\s\S]*?})\s*```", text)
    if m:
        return m.group(1)
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return m.group(0)
    return text


class NimClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url or settings.nim_base_url
        self.model = model or settings.nim_model
        self.api_key = api_key or settings.nim_api_key
        self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def _build_prompt(
        self, transcript: str, risk_context: Optional[RiskScore]
    ) -> str:
        transcript_line = (
            f'\nAudio transcript from scene: "{transcript}"\n' if transcript else ""
        )
        risk_line = ""
        if risk_context:
            reasons = "; ".join(risk_context.reasons[:4]) or "n/a"
            risk_line = (
                f"\nContextual risk for this camera (from NYC Open Data):\n"
                f"- Predicted tier: {risk_context.tier.upper()} "
                f"(score {risk_context.score:.2f})\n"
                f"- Reasons: {reasons}\n"
                f"When tier is HIGH or CRITICAL, be more sensitive to subtle "
                f"precursor behavior (loitering, erratic movement, sudden "
                f"dispersal, near-miss pedestrian/vehicle interactions).\n"
            )
        return f"{DETECTION_PROMPT}{transcript_line}{risk_line}\n{OUTPUT_INSTRUCTIONS}"

    def analyze_frame(
        self,
        jpeg_b64: str,
        transcript: str = "",
        risk_context: Optional[RiskScore] = None,
    ) -> tuple[List[FrameEvent], str]:
        if jpeg_b64.startswith("data:"):
            image_url = jpeg_b64
        else:
            image_url = f"data:image/jpeg;base64,{jpeg_b64}"

        prompt = self._build_prompt(transcript, risk_context)
        log.debug("[nim] -> %s model=%s", self.base_url, self.model)

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                max_tokens=800,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "frame_events",
                        "schema": FRAME_EVENTS_SCHEMA,
                        "strict": True,
                    },
                },
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url},
                            },
                        ],
                    }
                ],
            )
        except Exception as err:
            log.error("[nim] request failed: %s", err)
            raise

        text = completion.choices[0].message.content or ""
        if not text:
            return [], ""

        try:
            parsed = json.loads(_extract_json(text))
            events = [FrameEvent(**e) for e in parsed.get("events", [])]
            return events, text
        except Exception as err:
            log.warning("[nim] JSON parse failed: %s", err)
            return [], text

    def warmup(self) -> None:
        """Send a 1x1 white pixel to force model load."""
        blank = base64.b64encode(
            bytes.fromhex("ffd8ffe000104a46494600010101004800480000ffdb004300080606")
            + b"\x00" * 16
        ).decode()
        try:
            self.analyze_frame(blank, transcript="")
            log.info("[nim] warmup OK")
        except Exception as err:
            log.warning("[nim] warmup failed (non-fatal): %s", err)


_client: Optional[NimClient] = None


def get_vlm_client() -> NimClient:
    global _client
    if _client is None:
        _client = NimClient()
    return _client
