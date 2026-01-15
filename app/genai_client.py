from __future__ import annotations

import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google import genai


@dataclass
class GenAIConfig:
    mode: str
    api_key: str | None
    model_text: str
    model_image: str


class GenAIClient:
    def __init__(self, config: GenAIConfig) -> None:
        self.config = config
        self._client = genai.Client(api_key=config.api_key) if config.mode == "live" else None

    @classmethod
    def from_env(cls) -> "GenAIClient":
        mode = os.getenv("GENAI_MODE", "stub")
        api_key = os.getenv("GENAI_API_KEY")
        model_text = os.getenv("GENAI_TEXT_MODEL", "gemini-1.5-pro")
        model_image = os.getenv("GENAI_IMAGE_MODEL", "gemini-2.5-flash-image")
        return cls(GenAIConfig(mode=mode, api_key=api_key, model_text=model_text, model_image=model_image))

    def analyze_audio(self, source_dir: Path) -> dict[str, Any]:
        if self.config.mode != "live":
            return {
                "transcript": [
                    {"start_ms": 0, "end_ms": 10000, "text": "Demo line 1"},
                    {"start_ms": 10000, "end_ms": 20000, "text": "Demo line 2"},
                ],
                "summary": "Energetic intro with a hopeful mood.",
                "emotions": ["uplifting", "nostalgic"],
                "tempo_bpm": 120,
            }
        prompt = "Summarize the audio, return transcript with timestamps and emotions as JSON."
        response = self._client.models.generate_content(model=self.config.model_text, contents=[prompt])
        return {"raw": response.text or ""}

    def build_storyboard(self, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        if self.config.mode != "live":
            return [
                {
                    "id": "seg_001",
                    "start_ms": 0,
                    "end_ms": 10000,
                    "lyric_text": "Demo line 1",
                    "visual_intent": "Sunrise over a city skyline",
                    "mood": "uplifting",
                },
                {
                    "id": "seg_002",
                    "start_ms": 10000,
                    "end_ms": 20000,
                    "lyric_text": "Demo line 2",
                    "visual_intent": "People walking through rain with neon lights",
                    "mood": "nostalgic",
                },
            ]
        prompt = f"Build storyboard JSON segments from analysis: {analysis}"
        response = self._client.models.generate_content(model=self.config.model_text, contents=[prompt])
        return [{"raw": response.text or ""}]

    def build_prompts(self, segments: list[dict[str, Any]]) -> dict[str, Any]:
        if self.config.mode != "live":
            prompts: dict[str, Any] = {}
            for segment in segments:
                prompts[segment["id"]] = {
                    "version": 1,
                    "image_prompt": f"{segment['visual_intent']} cinematic, high detail",
                    "negative_prompt": "low quality, blurry, watermark",
                    "style_hints": "soft lighting, shallow depth of field",
                }
            return prompts
        prompt = f"Create image prompts JSON for segments: {segments}"
        response = self._client.models.generate_content(model=self.config.model_text, contents=[prompt])
        return {"raw": response.text or ""}

    def generate_image(self, prompt_payload: dict[str, Any]) -> bytes:
        if self.config.mode != "live":
            seed = random.randint(1000, 9999)
            return f"Placeholder image for {prompt_payload} seed {seed}".encode("utf-8")
        prompt = prompt_payload.get("image_prompt", "Cinematic scene")
        response = self._client.models.generate_content(model=self.config.model_image, contents=[prompt])
        return (response.text or "").encode("utf-8")
