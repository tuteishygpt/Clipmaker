from __future__ import annotations


import os
import random
import time
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
        model_text = os.getenv("GENAI_TEXT_MODEL", "gemini-2.5-flash")
        model_image = os.getenv("GENAI_IMAGE_MODEL", "gemini-2.5-flash-image")
        
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

    def analyze_audio(self, audio_path: Path | None, duration: float = 0.0, technical_analysis: dict = None, user_style: str = "cinematic", user_description: str = "") -> dict[str, Any]:
        file_ref = None
        if audio_path and audio_path.exists():
            try:
                # Upload the file
                logger.info(f"Uploading audio file: {audio_path}")
                file_ref = self._client.files.upload(path=str(audio_path))
                
                # Wait for processing
                while file_ref.state.name == "PROCESSING":
                    time.sleep(1)
                    file_ref = self._client.files.get(name=file_ref.name)
                
                if file_ref.state.name == "FAILED":
                    logger.error("Audio file processing failed in Gemini.")
                    file_ref = None
                else:
                    logger.info(f"Audio file uploaded and processed: {file_ref.name}")
                    
            except Exception as e:
                logger.error(f"Failed to upload audio file: {e}")
                file_ref = None

        tech_context = ""
        if technical_analysis:
            tech_context = f"\nTechnical Analysis Data (librosa):\n{json.dumps(technical_analysis, indent=2)}\n"

        prompt = f"""
        Analyze the audio track in this song to create a video clip. 
        The total duration of the audio is {duration:.2f} seconds.
        
        USER REQUEST / PLOT DESCRIPTION:
        "{user_description}"
        (This is the most important instruction. The narrative, metaphors, and events MUST follow this description if provided. If empty, invent a creative one).
        
        The user has requested the visual style: "{user_style}".
        
        {tech_context}
        
        Please provide:
        1. A summary of the song's energy, mood, and style.
        2. A "global_visual_narrative": A single, cohesive visual metaphor or story concept (e.g. "journey of an abandoned robot" or "a cyber-gothic dance in rain") that will persist throughout the video. If the user provided a plot description, adapt it here.
        3. A "visual_style_anchor": A specific, consistent visual style description BASED ON "{user_style}" (e.g. if user said "Anime", generate "90s Cyberpunk Anime, high contrast").
        4. A list of segments that cover the ENTIRE duration ({duration:.2f}s).
        
        For each segment, identify:
        - start_time and end_time (0.0 to {duration:.2f})
        - speaker (if vocals generally)
        - text (lyrics)
        - emotion
        - instrumentation (e.g. "guitar solo", "heavy drums", "minimal synth")
        - section_type (e.g. "intro", "verse", "chorus", "bridge", "drop", "climax", "outro")
        - acoustic_environment (e.g. "studio", "live hall", "lo-fi", "underwater", "echoey")
        
        Ensure:
        - Segments have NO GAPS and NO OVERLAPS.
        - The sequence covers exactly from 0.0 to {duration:.2f}.
        - Use the Technical Analysis (BPM, Energy) to align segments with beats and intense moments if possible.
        
        Return as a JSON object with keys: "summary", "global_visual_narrative", "visual_style_anchor", "segments".
        """
        
        contents = [prompt]
        if file_ref:
            contents.append(file_ref)
            
        logger.info("Sending analysis request to Gemini...")
        response = self._client.models.generate_content(
            model=self.config.model_text, 
            contents=contents
        )
        return self._extract_json(response.text)

    def build_storyboard(self, analysis: dict[str, Any], total_duration: float = 0.0) -> list[dict[str, Any]]:
        prompt = f"""
        Based on this analysis: {analysis}
        
        Create a storyboard as a JSON list of segments.
        The total duration MUST be EXACTLY {total_duration:.2f} seconds.
        
        Follow the "global_visual_narrative" defined in the analysis. The video must feel like a cohesive film with a clear Narrative Arc (Beginning, Development, Climax).
        
        Crucial: React to changes in music intensity (from technical analysis stats or section_type) by changing the INTENSITY of the plot/visuals. 
        - If the music builds up (climax/drop), the visuals must become more massive, dynamic, or fast-paced.
        - If the music is calm, the visuals should be steady and atmospheric.
        
        PACING INSTRUCTION:
        - The user wants a dynamic video with MANY segments.
        - Aim for segment durations between 2 and 5 seconds for most parts.
        - Only use longer segments (up to 8s) for very slow, atmospheric parts.
        - Avoid creating few long segments. We need a high "segment density".
        
        Each segment MUST have:
        - id: a unique string like "seg_1", "seg_2", etc.
        - start_time: "MM:SS" (or total seconds)
        - end_time: "MM:SS" (or total seconds)
        - lyric_text: the transcript for this segment
        - visual_intent: a detailed description of what should be on screen, following the global narrative and current intensity.
        - camera_angle: suggested camera shot (e.g. "Close-up", "Wide shot", "Drone shot")
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

    def build_prompts(self, segments: list[dict[str, Any]], analysis: dict[str, Any] | None = None) -> dict[str, Any]:
        style_anchor = ""
        if analysis and "visual_style_anchor" in analysis:
            style_anchor = analysis["visual_style_anchor"]
            
        prompt = f"""
        For each of these segments, create a detailed image generation prompt.
        
        Global Style Anchor: "{style_anchor}" 
        (YOU MUST APPEND THIS EXACT STYLE DESCRIPTION TO EVERY SINGLE PROMPT TO ENSURE CONSISTENCY).
        
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
