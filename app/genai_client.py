from __future__ import annotations


import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types


import logging
import json
import re

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class GenAIConfig:
    api_key: str | None
    model_text: str
    model_image: str


class GenAIClient:
    def __init__(self, config: GenAIConfig) -> None:
        self.config = config
        self._client = genai.Client(api_key=config.api_key)

    @classmethod
    def from_env(cls) -> "GenAIClient":
        load_dotenv()
        api_key = os.getenv("GENAI_API_KEY")
        model_text = os.getenv("GENAI_TEXT_MODEL", "gemini-2.0-flash-exp")
        model_image = os.getenv("GENAI_IMAGE_MODEL", "imagen-3.0-generate-001")
        
        if api_key:
            logger.info("API token loaded successfully (length: %d)", len(api_key))
        else:
            logger.warning("API token NOT found in environment. GENAI_API_KEY is missing.")
            
        return cls(GenAIConfig(api_key=api_key, model_text=model_text, model_image=model_image))

    def _extract_json(self, text: str) -> Any:
        try:
            # Try to find JSON in code blocks
            match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            # Try to find anything that looks like JSON
            match = re.search(r"({.*}|\[.*\])", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return json.loads(text)
        except Exception as e:
            logger.error(f"Failed to parse JSON from response: {e}")
            return {"error": "Failed to parse JSON", "raw": text}

    def analyze_audio(self, source_dir: Path, duration: float = 0.0) -> dict[str, Any]:
        prompt = f"""
        Analyze the audio track in this song for create a video clip. 
        The total duration of the audio is {duration:.2f} seconds.
        Provide a summary, and a list of segments with start_time, end_time, speaker, text, and emotion.
        Make sure segments cover the entire {duration:.2f} seconds without gaps.
        Return as a JSON object.
        """
        response = self._client.models.generate_content(model=self.config.model_text, contents=[prompt])
        return self._extract_json(response.text)

    def build_storyboard(self, analysis: dict[str, Any], total_duration: float = 0.0) -> list[dict[str, Any]]:
        prompt = f"""
        Based on this analysis: {analysis}
        
        Create a storyboard as a JSON list of segments.
        The total duration MUST be EXACTLY {total_duration:.2f} seconds.
        
        Each segment MUST have:
        - id: a unique string like "seg_1", "seg_2", etc.
        - start_time: "MM:SS" (or total seconds)
        - end_time: "MM:SS" (or total seconds)
        - lyric_text: the transcript for this segment
        - visual_intent: a detailed description of what should be on screen
        - camera_angle: suggested camera shot (e.g. "Close-up", "Wide shot")
        - emotion: the detected emotion
        
        IMPORTANT: The segments MUST tile the entire {total_duration:.2f} seconds. 
        The first segment must start at 00:00. 
        The last segment must end at {total_duration:.2f}.
        No gaps, no overlaps.
        
        Return ONLY the JSON list.
        """
        response = self._client.models.generate_content(model=self.config.model_text, contents=[prompt])
        data = self._extract_json(response.text)
        if isinstance(data, dict) and "segments" in data:
            return data["segments"]
        if isinstance(data, list):
            return data
        return []

    def build_prompts(self, segments: list[dict[str, Any]]) -> dict[str, Any]:
        prompt = f"""
        For each of these segments, create a detailed image generation prompt.
        Segments: {segments}
        
        Return a JSON object where keys are the segment IDs ("seg_1", etc.) and values are objects containing:
        - image_prompt: the detailed prompt for the AI image generator
        - negative_prompt: what to avoid in the image (optional)
        - style_hints: keywords about the style (optional)
        - version: 1
        
        Return ONLY the JSON object.
        """
        response = self._client.models.generate_content(model=self.config.model_text, contents=[prompt])
        data = self._extract_json(response.text)
        if isinstance(data, dict):
            # If the LLM returned it wrapped in another key
            if "prompts" in data and isinstance(data["prompts"], dict):
                return data["prompts"]
            return data
        return {}

    def generate_image(self, prompt_payload: dict[str, Any]) -> bytes:
        prompt = prompt_payload.get("image_prompt", "Cinematic scene")
        try:
            # Check if we are using an Imagen model (legacy/specific)
            if "imagen" in self.config.model_image.lower():
                response = self._client.models.generate_images(
                    model=self.config.model_image,
                    prompt=prompt
                )
                if response.generated_images:
                    return response.generated_images[0].image.image_bytes
                return b""

            # Logic for Gemini 2.5+ Flash Image / Multimodal Generation
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            # We request only IMAGE modality effectively by ignoring text output if possible, 
            # but per user example: response_modalities=["IMAGE", "TEXT"]
            generate_content_config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            )

            # Use stream as per user example, or regular generate_content. 
            # Using stream to be safe and close to user example style.
            for chunk in self._client.models.generate_content_stream(
                model=self.config.model_image,
                contents=contents,
                config=generate_content_config,
            ):
                if (
                    chunk.candidates is None
                    or not chunk.candidates
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None
                    or not chunk.candidates[0].content.parts
                ):
                    continue
                
                part = chunk.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
            
            return b""
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            # Try to print more info if available
            return b""
