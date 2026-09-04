"""Google GenAI client for text and image generation via Vertex AI."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

# Ensure root backend directory is in sys.path for modules imported from CaptionsBE
_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from google import genai
from google.genai import types

from gemini_auth import (
    GeminiTranscriptionError,
    _load_service_account_json_from_env,
    _configure_adc_from_service_account_json,
    _call_with_retry,
    _is_retryable_error,
    is_transcribe_model,
)
from gemini_integration import (
    GeminiTranscriptionAdapter,
    transcribe_with_gemini,
    transcribe_words_with_gemini,
    get_last_transcribed_words,
)
from subtitle_generation import (
    transcribe_audio_to_segments,
    group_words_into_subtitles,
    _sec_to_ts,
)
from gemini_prompts import _guess_audio_mime
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class GenAIClient:
    """Client for Google Generative AI (Gemini) using Vertex AI."""
    
    def __init__(
        self,
        api_key: str | None = None,
        text_model: str | None = None,
        image_model: str | None = None,
        subtitle_model: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key or settings.genai_api_key
        self.text_model = text_model or settings.genai_text_model
        self.image_model = image_model or settings.genai_image_model
        self.subtitle_model = subtitle_model or settings.genai_subtitle_model
        
        # Vertex AI configuration
        self.service_account_json = _load_service_account_json_from_env()
        self.project = (
            settings.google_cloud_project
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GOOGLE_PROJECT")
            or ""
        ).strip()
        self.location = (
            settings.google_cloud_location
            or os.environ.get("GOOGLE_CLOUD_LOCATION")
            or os.environ.get("GOOGLE_VERTEX_LOCATION")
            or "global"
        ).strip()

        if self.service_account_json:
            self.project = _configure_adc_from_service_account_json(
                self.service_account_json,
                self.project,
            )

        if client is not None:
            self._client = client
            self.is_vertex = getattr(client, "vertexai", True) is True
        else:
            # When Service Account / ADC credentials are configured, omit api_key so SDK authenticates via Service Account
            has_service_account = bool(self.service_account_json or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
            effective_api_key = None if has_service_account else (self.api_key or None)

            # Per user requirement: All Gemini models must use Vertex AI
            self._client = genai.Client(
                vertexai=True,
                project=self.project or None,
                location=self.location,
                api_key=effective_api_key,
            )
            self.is_vertex = True
        
        logger.info(
            "GenAI client initialized via Vertex AI (project=%s, location=%s, subtitle_model=%s)",
            self.project or "<default>",
            self.location,
            self.subtitle_model,
        )

    def _normalize_model_name(self, model_name: str) -> str:
        """Normalize model name for Vertex AI (e.g. appending -preview for transcribe models)."""
        name = (model_name or "").strip()
        if name.startswith("models/"):
            name = name[len("models/"):]
        if self.is_vertex and name in ("gemini-3.5-transcribe", "publishers/google/models/gemini-3.5-transcribe"):
            return name + "-preview"
        return name

    def _call_with_retry(
        self,
        fn: Callable[[], Any],
        operation_label: str = "Gemini request",
    ) -> Any:
        """Execute callable with exponential backoff on retryable errors."""
        return _call_with_retry(fn, operation_label=operation_label)
    
    def _log_interaction(self, method: str, request: Any, response: Any) -> None:
        """Log request and response from Gemini."""
        try:
            # We don't want to log huge images in the text log
            log_response = response
            if isinstance(response, bytes):
                log_response = f"<binary data: {len(response)} bytes>"
            elif hasattr(response, "text"):
                log_response = response.text
            
            response_len = len(str(log_response))
            display_response = str(log_response)
            if response_len > 2000:
                display_response = display_response[:2000] + f" ... <truncated, total {response_len} chars>"

            logger.info("-" * 40)
            logger.info(f"GEMINI INTERACTION: {method}")
            logger.info(f"REQUEST:\n{request}")
            logger.info(f"RESPONSE (Length: {response_len}):\n{display_response}")
            logger.info("-" * 40)
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")

    def _extract_json(self, text: str) -> Any:
        """Extract JSON from model response text."""
        try:
            # 1. Try to find JSON in code blocks
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)
            
            text = text.strip()
            
            # 2. Simple attempt
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            
            # 3. Handle Truncated List: Starts with [ but doesn't end with ]
            if text.startswith("[") and not text.endswith("]"):
                # Try appending ]
                try:
                    return json.loads(text + "]")
                except json.JSONDecodeError:
                    pass
                # Try removing trailing comma/junk and appending ]
                # Find the last closing brace }
                last_brace = text.rfind("}")
                if last_brace != -1:
                    truncated = text[:last_brace+1] + "]"
                    try:
                        return json.loads(truncated)
                    except json.JSONDecodeError:
                        pass

            # 4. Regex fallback (be careful with {})
            # Prefer full array match
            match = re.search(r"(\[.*\])", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 5. Regex for object
            match = re.search(r"({.*})", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            
            # 6. If it looks like a list content "obj}, {obj", wrap it
            if "},{" in text:
                # Try to wrap in brackets
                try:
                    return json.loads(f"[{text}]")
                except json.JSONDecodeError:
                    pass
            
            raise ValueError("Could not extract valid JSON")
            
        except Exception as e:
            logger.error(f"Failed to parse JSON from response: {e}")
            return {"error": "Failed to parse JSON", "raw": text}
    
    def _upload_file(self, path: Path) -> Any:
        """Upload a file to GenAI and wait for processing (used for Developer API fallback)."""
        if self.is_vertex:
            raise RuntimeError("Vertex AI does not use Files API. Pass audio bytes via types.Part.from_bytes.")

        if not self.api_key or not str(self.api_key).strip():
            raise RuntimeError(
                "Gemini API key is missing. Please set GENAI_API_KEY in Clipmaker/.env"
            )

        try:
            logger.info(f"Uploading file: {path}")
            file_ref = self._client.files.upload(file=str(path))
            
            # Wait for processing
            while file_ref.state.name == "PROCESSING":
                time.sleep(1)
                file_ref = self._client.files.get(name=file_ref.name)
            
            if file_ref.state.name == "FAILED":
                logger.error("File processing failed in Gemini.")
                raise RuntimeError("File processing failed in Gemini.")
            
            logger.info(f"File uploaded and processed: {file_ref.name}")
            return file_ref
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            err_str = str(e)
            if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                raise RuntimeError(
                    "Gemini API key is invalid or expired. Please update GENAI_API_KEY in Clipmaker/.env (get a valid key at https://aistudio.google.com/apikey)"
                ) from e
            if "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str:
                raise RuntimeError(
                    "Gemini API quota exceeded. Please check your rate limits or billing in Google AI Studio."
                ) from e
            raise RuntimeError(f"Failed to upload audio file to Gemini: {e}") from e
    
    def transcribe_audio_for_subtitles(
        self,
        audio_path: Path,
        language: str = "auto",
        min_words: int = 1,
        max_words: int = 10,
        return_words: bool = False,
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Transcribe audio to timestamped subtitle segments via Vertex AI.
        
        Args:
            audio_path: Path to the audio file.
            language: Language code or 'auto' for auto-detection.
            min_words: Minimum words per subtitle segment.
            max_words: Maximum words per subtitle segment.
            return_words: If True, returns a tuple of (entries, words).
            
        Returns:
            List of dicts with 'start', 'end' (SRT format), and 'text' keys,
            or tuple of (entries, words) if return_words=True.
        """
        model_name = self._normalize_model_name(self.subtitle_model)
        logger.info(f"Transcribing subtitles with model={model_name} (Vertex AI: {self.is_vertex})")

        # 1. Dedicated Gemini 3.5 Transcribe model (gemini-3.5-transcribe / gemini-3.5-transcribe-preview)
        if is_transcribe_model(model_name):
            adapter = GeminiTranscriptionAdapter(
                api_key=self.api_key,
                model=model_name,
                client_factory=lambda _key: self._client,
            )
            words = adapter.transcribe_words(str(audio_path), language=language)
            try:
                import gemini_integration
                gemini_integration._last_transcribed_words = words
            except Exception:
                pass

            if max_words <= 3:
                length_mode = "short"
            elif max_words >= 10:
                length_mode = "long"
            else:
                length_mode = "medium"

            max_chars = 24 if max_words <= 3 else (40 if max_words <= 6 else 75)

            segments = group_words_into_subtitles(
                words=words,
                length_mode=length_mode,
                max_chars=max_chars,
            )

            result_entries = []
            for seg in segments:
                result_entries.append({
                    "start": _sec_to_ts(seg["start"]),
                    "end": _sec_to_ts(seg["end"]),
                    "text": str(seg["text"]).strip(),
                })
            if return_words:
                return result_entries, words
            return result_entries

        # 2. General LLM fallback for non-transcribe models
        mime = _guess_audio_mime(str(audio_path))
        if self.is_vertex:
            audio_part = types.Part.from_bytes(
                data=Path(audio_path).read_bytes(),
                mime_type=mime,
            )
        else:
            file_ref = self._upload_file(audio_path)
            if not file_ref:
                raise RuntimeError("Failed to upload audio file for transcription")
            audio_part = types.Part.from_uri(
                file_uri=file_ref.uri,
                mime_type=file_ref.mime_type,
            )
        
        language_instruction = ""
        if language != "auto":
            language_instruction = f"The audio is in {language}. Transcribe in that language."
        else:
            language_instruction = "Detect the language automatically and transcribe in the original language."
        
        system_instruction_text = f"""
        You are an expert lyrics synchronizer and audio transcriber suitable for karaoke creation. Your task is to generate precise, synchronized subtitles for the provided SONG audio.

        LANGUAGE INSTRUCTION: {language_instruction}

        TIMING & FORMATTING (CRITICAL FOR MUSIC):
        1. Precision (Vocal Attack): The "start" time must correspond exactly to the millisecond the vocal cords engage (the attack of the first syllable). Do not include the instrumental intro breath before the word.
        2. End Times: The "end" time must mark exactly where the vocal stops. Do not extend the segment into the instrumental tail or reverb.
        3. Instrumental Sections: If there are instrumental solos, breaks, or intros/outros with NO vocals, do NOT generate any segments. Leave gaps in the timeline.
        4. Format: Use standard SRT time format HH:MM:SS,mmm. ALWAYS include milliseconds and use a COMMA (,) as the separator.

        TEXT & SEGMENTATION RULES:
        1. Lyrical Phrasing: Segment the text based on MUSICAL PHRASING and lyrical lines, not just sentence structure.
           - It is acceptable to have short segments (e.g., 1-2 words) if they act as a distinct call-out or ad-lib.
           - Do NOT break a continuous sung phrase in the middle just to satisfy word counts unless it is extremely long (>10 seconds).
        2. Constraints:
           - Target roughly {min_words} to {max_words} words per segment, BUT prioritize the natural rhythm of the song.
        3. Content: Transcribe ONLY spoken/sung words. 
           - NO non-verbal tags like [Music], [Guitar Solo], [Applause].
           - Include ad-libs (e.g., "Yeah", "Ooh") and background vocals if they are prominent.
        4. Acoustic Truth: Transcribe exactly what is heard in THIS audio file. Do not correct grammar or insert lyrics from the original studio version if the singer skips them or changes them in this recording.

        ### ONE-SHOT EXAMPLE (Strictly follow this JSON format and logic):

        Input: [Audio of a song with a pause between lines]
        Output:
        [
          {{
            "start": "00:00:12,450",
            "end": "00:00:14,200",
            "text": "Is this the real life?"
          }},
          {{
            "start": "00:00:14,300",
            "end": "00:00:16,100",
            "text": "Is this just fantasy?"
          }},
          {{
            "start": "00:00:19,500",
            "end": "00:00:22,000",
            "text": "Caught in a landslide"
          }}
        ]
        (Note: Notice the gap between 16,100 and 19,500 where instrumental music plays – no segment is generated there).

        OUTPUT FORMAT: 
        Return a strictly valid JSON array matching the schema above.
        Do not wrap the JSON in markdown blocks (no ```json). Return raw JSON string only.
        """

        try:
            logger.info(f"Generating subtitles using model: {model_name}")
            
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        audio_part,
                        types.Part.from_text(text="Transcribe the audio file using the provided system instructions."),
                    ],
                ),
            ]

            generate_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        required=["text", "start", "end"],
                        properties={
                            "text": types.Schema(
                                type=types.Type.STRING,
                            ),
                            "start": types.Schema(
                                type=types.Type.STRING,
                            ),
                            "end": types.Schema(
                                type=types.Type.STRING,
                            ),
                        },
                    ),
                ),
                temperature=0.0,
                max_output_tokens=8192,
                system_instruction=[
                    types.Part.from_text(text=system_instruction_text),
                ],
            )

            response = self._call_with_retry(
                lambda: self._client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=generate_config,
                ),
                operation_label="transcribe_audio_for_subtitles",
            )
            
            logger.info("Model raw response begin:")
            try:
                logger.info(response.text)
            except Exception as e:
                logger.error(f"Could not read response text: {e}")
            logger.info("Model raw response end.")

            self._log_interaction(
                "transcribe_audio_for_subtitles", 
                f"Audio transcription request using model: {model_name}", 
                response
            )
            
            # With structured output, response.text should be valid JSON
            result = self._extract_json(response.text)
            
            final_entries: list[dict[str, Any]] = []
            # 1. Direct List
            if isinstance(result, list):
                final_entries = result
            elif isinstance(result, dict):
                # 2. Known keys
                for key in ["subtitles", "entries", "segments", "data", "results"]:
                    if key in result and isinstance(result[key], list):
                        final_entries = result[key]
                        break
                
                # 3. Single object fallback (if model returned just one segment as an object)
                if not final_entries and "start" in result and "text" in result:
                    final_entries = [result]

                # 4. Deep search: Look for ANY list value that contains subtitle-like objects
                if not final_entries:
                    for value in result.values():
                        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                            # Check if the first item has at least 'text' or 'start'
                            if "text" in value[0] or "start" in value[0]:
                                final_entries = value
                                break

            if not final_entries:
                logger.warning(f"Unexpected transcription result format: {type(result)} - {result}")

            if return_words:
                return final_entries, []
            return final_entries
                
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            raise
    
    def analyze_audio(
        self,
        audio_path: Path | None,
        duration: float = 0.0,
        technical_analysis: dict | None = None,
        user_style: str = "cinematic",
        user_description: str = "",
        character_description: str = "",
        use_batch: bool = False,
    ) -> dict[str, Any] | str:
        """Analyze audio track for video clip creation."""
        audio_part = None
        if audio_path and Path(audio_path).exists():
            try:
                if self.is_vertex:
                    mime = _guess_audio_mime(str(audio_path))
                    audio_part = types.Part.from_bytes(
                        data=Path(audio_path).read_bytes(),
                        mime_type=mime,
                    )
                else:
                    audio_part = self._upload_file(Path(audio_path))
            except Exception as e:
                logger.warning(f"Audio attachment failed for clip analysis, continuing without audio: {e}")
        
        tech_context = ""
        if technical_analysis:
            tech_context = f"\nTechnical Analysis Data (librosa):\n{json.dumps(technical_analysis, indent=2)}\n"
        
        prompt = f"""
        Analyze the audio track in this song to create a PROFESSIONAL music video plan.
        The total duration of the audio is {duration:.2f} seconds.
        
        USER REQUEST / PLOT DESCRIPTION:
        "{user_description}"
        (The narrative, metaphors, and events MUST follow this description if provided. If empty, invent a creative one).
        
        The user has requested the visual style: "{user_style}".

        CHARACTER DESCRIPTION:
        "{character_description}"
        (If provided, this character MUST be the protagonist of the video).
        
        {tech_context}
        
        EDITING RULES (CRITICAL):
        1. RHYTHM IS KING: Cut to the beat. Visuals must sync with the audio.
        2. SONG STRUCTURE: You MUST identify the sections: Intro, Verse, Pre-Chorus, Chorus, Bridge, Outro.
        3. PACING BY SECTION:
           - Verses: Longer, cinematic shots. Focus on storytelling.
           - Choruses: FAST cuts. Short, rhythmic clips. "Micro-series" of shots on beats. High energy.
           - Transitions: 1-2 distinct "accent" shots with strong movement/impact.
        4. MARKERS: Place keyframes on strong beats (kick/snare, drops).
        
        Please provide:
        1. A summary of the song's energy, mood, and style.
        2. A "global_visual_narrative": A single, cohesive visual metaphor or story concept.
           - MUST be a concrete visual idea (e.g. "A cyberpunk detective walking through neon rain", NOT just "A journey of self-discovery").
           - Should evolve from beginning to end.
        3. A "visual_style_anchor": A specific, consistent visual style description BASED ON "{user_style}".
           - Include lighting, color palette, and texture (e.g. "Cinematic lighting, teal and orange palette, film grain").
        4. A "video_plan": A structured plan containing "scenes".
        
        "video_plan" structure:
        {{
          "scenes": [
            {{
              "start_time": float,
              "end_time": float,
              "section_type": "Intro" | "Verse" | "Chorus" | "Bridge" | "Outro",
              "description": "Visual description of the scene",
              "energy_level": float (0.0 to 1.0),
              "keyframes": [
                {{
                  "time": float,
                  "type": "cut" | "zoom" | "shake" | "beat",
                  "description": "Short note",
                  "parameters": {{}}
                }}
              ]
            }}
          ]
        }}
        
        Instructions for Scenes:
        - Segments have NO GAPS and NO OVERLAPS.
        - Cover exactly 0.0 to {duration:.2f}.
        - The pacing MUST follow the structure (Verse=Slow, Chorus=Fast).
        - Use the technical analysis (Drops, Downbeats) to align scene changes and keyframes.
        
        Return as a JSON object with keys: "summary", "global_visual_narrative", "visual_style_anchor", "video_plan", "segments" (legacy support, map scenes to segments if needed or keep separate).
        """
        
        contents = [prompt]
        if audio_part:
            contents.append(audio_part)
        
        if use_batch:
            # Construct a request body suitable for Batch API
            batch_parts = [{"text": prompt}]
            if audio_part:
                batch_parts.append(audio_part)
            
            return {
                "contents": [{"role": "user", "parts": batch_parts}]
            }

        logger.info("Sending audio analysis request to Gemini...")
        response = self._call_with_retry(
            lambda: self._client.models.generate_content(
                model=self._normalize_model_name(self.text_model),
                contents=contents,
            ),
            operation_label="analyze_audio",
        )
        self._log_interaction("analyze_audio", contents, response)
        return self._extract_json(response.text)
    
    def build_storyboard(
        self,
        analysis: dict[str, Any],
        total_duration: float = 0.0,
        use_batch: bool = False,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Build storyboard segments from analysis."""
        prompt = f"""
        Based on this analysis: {analysis}
        
        Create a storyboard as a JSON list of segments.
        The total duration MUST be EXACTLY {total_duration:.2f} seconds.
        
        Follow the "global_visual_narrative" defined in the analysis. The video must feel like a cohesive film with a clear Narrative Arc (Beginning, Development, Climax).
        
        VISUAL STORYTELLING:
        - Don't just list random images. Connect them.
        - Use cinematographic terms (Wide Shot, Close Up, Dolly Zoom, Tracking Shot).
        - Describe lighting and movement in EVERY segment.
        
        PACING & RHYTHM RULES (STRICT):
        1. RHYTHM IS KING: Align cuts with the music's rhythm.
        2. VERSES / INTRO = Cinematic, Longer Shots (4-8s). Focus on storytelling and establishing atmosphere.
        3. CHORUSES / DROPS = Fast Cuts, High Energy (0.5s-2s). Flash different angles/actions on beats. "Micro-series" of shots.
        4. TRANSITIONS = Accent shots (fast zooms/whips) on section changes.
        5. Match the "energy_level" of the music. If the rhythm "sits", even simple pan/zoom looks professional.
        
        Each segment MUST have:
        - id: a unique string like "seg_1", "seg_2", etc.
        - start_time: "MM:SS" (or total seconds)
        - end_time: "MM:SS" (or total seconds)
        - lyric_text: the transcript for this segment
        - visual_intent: a detailed description of what should be on screen, following the global narrative and current intensity.
        - camera_angle: suggested camera shot (e.g. "Close-up", "Wide shot", "Drone shot")
        - emotion: the detected emotion
        - effect: "zoom_in" | "zoom_out" | "pan_left" | "pan_right" | "pan_up" | "pan_down" (Verse = smooth pans, Chorus = fast zooms)
        - transition: "cut" | "crossfade" | "slide_left" | "slide_right" | "zoom_in" (High Energy = slide/zoom, Low Energy = crossfade)
        
        IMPORTANT: The segments MUST tile the entire {total_duration:.2f} seconds. 
        The first segment must start at 00:00. 
        The last segment must end at {total_duration:.2f}.
        No gaps, no overlaps.
        
        Return ONLY the JSON list.
        """
        
        if use_batch:
            return {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}]
            }

        response = self._call_with_retry(
            lambda: self._client.models.generate_content(
                model=self._normalize_model_name(self.text_model),
                contents=[prompt],
            ),
            operation_label="build_storyboard",
        )
        self._log_interaction("build_storyboard", [prompt], response)
        data = self._extract_json(response.text)
        
        if isinstance(data, dict) and "segments" in data:
            return data["segments"]
        if isinstance(data, list):
            return data
        return []
    
    def build_prompts(
        self,
        segments: list[dict[str, Any]],
        analysis: dict[str, Any] | None = None,
        use_batch: bool = False,
    ) -> dict[str, Any]:
        """Build image generation prompts for segments."""
        style_anchor = ""
        if analysis and "visual_style_anchor" in analysis:
            style_anchor = analysis["visual_style_anchor"]
        
        prompt = f"""
        For each of these segments, create a detailed image generation prompt.
        
        Global Style Anchor: "{style_anchor}" 
        (YOU MUST APPEND THIS EXACT STYLE DESCRIPTION TO EVERY SINGLE PROMPT TO ENSURE CONSISTENCY).
        
        QUALITY BOOSTERS (Include these invisibly in the style):
        "8k resolution, cinematic lighting, photorealistic, intricate detail, sharp focus, masterpiece"
        (Unless the user style explicitly contradicts this, e.g. "pixel art").

        CHARACTER CONSISTENCY:
        Character Description: "{analysis.get('character_description', '')}"
        (If the character appears, they MUST match this description. If the scene allows, feature this character).
        
        Segments: {segments}
        
        Return a JSON object where keys are the segment IDs ("seg_1", etc.) and values are objects containing:
        - image_prompt: the detailed prompt for the AI image generator. MUST include the Style Anchor and Visual Intent.
        - negative_prompt: "blurry, low quality, distorted, bad anatomy, text, watermark, signature, ugly"
        - style_hints: keywords about the style (optional)
        
        Return ONLY the JSON object.
        """
        
        if use_batch:
            return {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}]
            }

        response = self._call_with_retry(
            lambda: self._client.models.generate_content(
                model=self._normalize_model_name(self.text_model),
                contents=[prompt],
            ),
            operation_label="build_prompts",
        )
        self._log_interaction("build_prompts", [prompt], response)
        data = self._extract_json(response.text)
        
        if isinstance(data, dict):
            if "prompts" in data and isinstance(data["prompts"], dict):
                return data["prompts"]
            return data
        return {}
    
    def generate_image(self, prompt_payload: dict[str, Any]) -> bytes:
        """Generate an image from a prompt via Vertex AI."""
        prompt = prompt_payload.get("image_prompt", "Cinematic scene")
        
        try:
            image_mod = self._normalize_model_name(self.image_model)
            # Check if we are using an Imagen model
            if "imagen" in image_mod.lower():
                response = self._call_with_retry(
                    lambda: self._client.models.generate_images(
                        model=image_mod,
                        prompt=prompt,
                    ),
                    operation_label="generate_image (Imagen)",
                )
                self._log_interaction("generate_image (Imagen)", prompt, "<Image response generated>")
                if response.generated_images:
                    return response.generated_images[0].image.image_bytes
                return b""
            
            # Logic for Gemini Flash Image / Multimodal Generation
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            )
            
            total_bytes = b""
            stream = self._call_with_retry(
                lambda: self._client.models.generate_content_stream(
                    model=image_mod,
                    contents=contents,
                    config=generate_content_config,
                ),
                operation_label="generate_image (Multimodal Stream)",
            )
            for chunk in stream:
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
                    total_bytes += part.inline_data.data
            
            self._log_interaction("generate_image (Multimodal Stream)", prompt, f"<Generated {len(total_bytes)} bytes>")
            return total_bytes
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return b""

    def create_batch_job(
        self,
        dataset_name: str,
        source: str | Path,
        dest: str | None = None,
        model_name: str | None = None,
    ) -> Any | None:
        """Create a batch prediction job exclusively via Vertex AI.
        
        Args:
            dataset_name: Display name for the batch job.
            source: GCS URI ('gs://path/to/data.jsonl'), BigQuery URI ('bq://...'),
                    or local .jsonl path (auto-uploaded if GCS bucket configured).
            dest: Destination GCS URI ('gs://path/to/output') for batch results.
            model_name: Target model (e.g. "gemini-2.5-flash"). Defaults to self.text_model.
            
        Returns:
            The created batch job object.
        """
        if not self.is_vertex:
            raise RuntimeError("create_batch_job is supported exclusively via Vertex AI.")

        model = self._normalize_model_name(model_name or self.text_model)
        source_str = str(source).strip()

        # Vertex AI requires GCS URI or BigQuery URI
        if not (source_str.startswith("gs://") or source_str.startswith("bq://")):
            gcs_bucket = (
                os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")
                or os.getenv("GCS_BUCKET")
                or ""
            ).strip()
            source_path = Path(source_str)
            if gcs_bucket and source_path.is_file():
                try:
                    from google.cloud import storage
                    storage_client = storage.Client(project=self.project or None)
                    bucket_clean = gcs_bucket.replace("gs://", "").strip("/")
                    bucket = storage_client.bucket(bucket_clean)
                    blob_name = f"batch_inputs/{dataset_name}_{source_path.name}"
                    blob = bucket.blob(blob_name)
                    blob.upload_from_filename(str(source_path))
                    source_str = f"gs://{bucket.name}/{blob_name}"
                    logger.info(f"Uploaded batch input file to GCS: {source_str}")
                except Exception as gcs_err:
                    logger.error(f"Failed to auto-upload {source_str} to GCS bucket {gcs_bucket}: {gcs_err}")
                    raise ValueError(
                        f"Vertex AI Batch API requires a GCS URI ('gs://...'). "
                        f"Auto-upload of local file failed: {gcs_err}"
                    ) from gcs_err
            else:
                raise ValueError(
                    f"Vertex AI Batch API requires a Google Cloud Storage URI ('gs://bucket/data.jsonl') "
                    f"or BigQuery URI ('bq://...'). Files API is not supported on Vertex AI. Provided: '{source_str}'"
                )

        config_kwargs: dict[str, Any] = {"display_name": dataset_name}
        if dest:
            config_kwargs["dest"] = dest

        config = (
            types.CreateBatchJobConfig(**config_kwargs)
            if types is not None and hasattr(types, "CreateBatchJobConfig")
            else None
        )

        logger.info(f"Creating Vertex AI batch job '{dataset_name}' for model {model} from {source_str}")
        try:
            batch_job = self._call_with_retry(
                lambda: self._client.batches.create(
                    model=model,
                    src=source_str,
                    config=config,
                ),
                operation_label=f"Vertex AI batches.create ({dataset_name})",
            )
            logger.info(f"Vertex AI batch job created: {getattr(batch_job, 'name', batch_job)}")
            return batch_job
        except Exception as e:
            logger.error(f"Failed to create Vertex AI batch job: {e}")
            raise

    def get_batch_job(self, job_name: str) -> Any | None:
        """Get the status of a batch job."""
        try:
            return self._client.batches.get(name=job_name)
        except Exception as e:
            logger.error(f"Failed to get batch job {job_name}: {e}")
            return None

    def list_batch_jobs(self, limit: int = 50) -> list[Any]:
        """List recent batch jobs."""
        try:
            return list(self._client.batches.list(page_size=limit))
        except Exception as e:
            logger.error(f"Failed to list batch jobs: {e}")
            return []

    def cancel_batch_job(self, job_name: str) -> Any | None:
        """Cancel a batch job."""
        try:
            # SDK might have .cancel() on the job object or client.batches.cancel(name=...)
            # Looking at common patterns: client.batches.cancel(name=...)
            return self._client.batches.cancel(name=job_name)
        except Exception as e:
            logger.error(f"Failed to cancel batch job {job_name}: {e}")
            return None

