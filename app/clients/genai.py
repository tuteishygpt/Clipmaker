"""Google GenAI client for text and image generation."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class GenAIClient:
    """Client for Google Generative AI (Gemini)."""
    
    def __init__(
        self,
        api_key: str | None = None,
        text_model: str | None = None,
        image_model: str | None = None,
        subtitle_model: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.genai_api_key
        self.text_model = text_model or settings.genai_text_model
        self.image_model = image_model or settings.genai_image_model
        self.subtitle_model = subtitle_model or settings.genai_subtitle_model
        
        self._client = genai.Client(api_key=self.api_key)
        
        if self.api_key:
            logger.info("GenAI client initialized (API key length: %d)", len(self.api_key))
        else:
            logger.warning("GenAI client initialized without API key!")
    
    def _log_interaction(self, method: str, request: Any, response: Any) -> None:
        """Log request and response from Gemini."""
        try:
            # We don't want to log huge images in the text log
            log_response = response
            if isinstance(response, bytes):
                log_response = f"<binary data: {len(response)} bytes>"
            elif hasattr(response, "text"):
                log_response = response.text
            
            logger.info("-" * 40)
            logger.info(f"GEMINI INTERACTION: {method}")
            logger.info(f"REQUEST:\n{request}")
            logger.info(f"RESPONSE:\n{log_response}")
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
    
    def _upload_file(self, path: Path) -> Any | None:
        """Upload a file to GenAI and wait for processing."""
        try:
            logger.info(f"Uploading file: {path}")
            # Fix: The SDK expects 'file' instead of 'path'
            file_ref = self._client.files.upload(file=str(path))
            
            # Wait for processing
            while file_ref.state.name == "PROCESSING":
                time.sleep(1)
                file_ref = self._client.files.get(name=file_ref.name)
            
            if file_ref.state.name == "FAILED":
                logger.error("File processing failed in Gemini.")
                return None
            
            logger.info(f"File uploaded and processed: {file_ref.name}")
            return file_ref
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return None
    
    def transcribe_audio_for_subtitles(
        self,
        audio_path: Path,
        language: str = "auto",
        min_words: int = 1,
        max_words: int = 10,
    ) -> list[dict[str, Any]]:
        """Transcribe audio to timestamped subtitle segments.
        
        Args:
            audio_path: Path to the audio file.
            language: Language code or 'auto' for auto-detection.
            min_words: Minimum words per subtitle segment.
            max_words: Maximum words per subtitle segment.
            
        Returns:
            List of dicts with 'start', 'end' (SRT format), and 'text' keys.
        """
        file_ref = self._upload_file(audio_path)
        if not file_ref:
            raise RuntimeError("Failed to upload audio file for transcription")
        
        language_instruction = ""
        if language != "auto":
            language_instruction = f"The audio is in {language}. Transcribe in that language."
        else:
            language_instruction = "Detect the language automatically and transcribe in the original language."
        
        system_instruction = f"""
        You are an expert video subtitler and audio engineer. Your task is to create PIXEL-PERFECT SYNCHRONIZED subtitles for the provided audio.
        
        CRITICAL TIMING INSTRUCTIONS (READ CAREFULLY):
        1. **PHONEME-LEVEL ALIGNMENT**: Listen for the exact start of the *first distinct sound* of a spoken phrase. That is your `start` time.
        2. **GAP HANDLING**: If there is a silence >= 0.5s between phrases, CLOSE the previous subtitle entry before the silence begins. Do NOT blindly bridge gaps unless the speech is continuous.
        3. **NO OVERLAP**: `start` of "Phrase B" must be >= `end` of "Phrase A".
        4. **PRECISION**: Use the waveform data internally (if possible) to align to the millisecond.
        
        SRT FORMATTING (STRICT):
        - `HH:MM:SS,mmm` (e.g., `00:00:01,534`). 
        - Comma separator is MANDATORY.
        
        TEXT RULES:
        1. **Word Count Constraints**:
           - **Minimum Words**: {min_words} words per line.
           - **Maximum Words**: {max_words} words per line. 
           - **Exceptions**: If a natural pause/silence occurs, you CAN break the line even if it has fewer words.
        2. **NO NON-VERBAL TAGS**: Do NOT include labels like [Music], [Applause], [Silence], or [Instrumental]. Output ONLY the spoken words (lyrics or speech). If there is no speech, return nothing.
        3. **Split Logic**: Prioritize splitting at natural grammatical boundaries if possible, but STRICTLY adhere to the max word count.
        
        CRITICAL:
        - You MUST transcribe the audio FROM BEGINNING TO END.
        - Do NOT summarize. Do NOT skip parts.
        - Do NOT stop until the audio file ends. 
        - If the audio is long, continue transcribing until the very last second.
        
        OUTPUT REQUIREMENT:
        Return a strictly valid JSON array of objects.
        """
        
        user_prompt = f"""
        Transcribe the attached audio file.
        {language_instruction}
        """
        
        try:
            # Define schema for structured output
            subtitle_schema = types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "start": types.Schema(
                            type=types.Type.STRING,
                            description="Start time in SRT format (HH:MM:SS,mmm)"
                        ),
                        "end": types.Schema(
                            type=types.Type.STRING,
                            description="End time in SRT format (HH:MM:SS,mmm)"
                        ),
                        "text": types.Schema(
                            type=types.Type.STRING,
                            description="Transcribed text"
                        ),
                    },
                    required=["start", "end", "text"]
                )
            )

            # Use Gemini 3.0 Flash for best transcription quality
            generate_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=subtitle_schema,
                temperature=0.0,
                max_output_tokens=8192,
                system_instruction=system_instruction
            )

            response = self._client.models.generate_content(
                model=self.subtitle_model,
                contents=[user_prompt, file_ref],
                config=generate_config
            )
            self._log_interaction("transcribe_audio_for_subtitles", "Audio transcription request", response)
            
            # With structured output, response.text should be valid JSON
            result = self._extract_json(response.text)
            
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "subtitles" in result:
                return result["subtitles"]
            elif isinstance(result, dict) and "entries" in result:
                return result["entries"]
            else:
                logger.warning(f"Unexpected transcription result format: {type(result)}")
                return []
                
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
        file_ref = None
        if audio_path and audio_path.exists():
            file_ref = self._upload_file(audio_path)
        
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
        if file_ref:
            # For Batch API, we need the resource name in a specific format if we construct manually.
            # But here we are building for direct generate_content first.
            contents.append(file_ref)
        
        if use_batch:
            # Construct a request body suitable for Batch API
            # Batch API requires a list of parts in 'contents'
            batch_parts = [{"text": prompt}]
            if file_ref:
                batch_parts.append({
                    "file_data": {
                        "file_uri": file_ref.uri,
                        "mime_type": file_ref.mime_type
                    }
                })
            
            return {
                "contents": [{"role": "user", "parts": batch_parts}]
            }

        logger.info("Sending audio analysis request to Gemini...")
        response = self._client.models.generate_content(
            model=self.text_model,
            contents=contents
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

        response = self._client.models.generate_content(
            model=self.text_model,
            contents=[prompt]
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

        response = self._client.models.generate_content(
            model=self.text_model,
            contents=[prompt]
        )
        self._log_interaction("build_prompts", [prompt], response)
        data = self._extract_json(response.text)
        
        if isinstance(data, dict):
            if "prompts" in data and isinstance(data["prompts"], dict):
                return data["prompts"]
            return data
        return {}
    
    def generate_image(self, prompt_payload: dict[str, Any]) -> bytes:
        """Generate an image from a prompt."""
        prompt = prompt_payload.get("image_prompt", "Cinematic scene")
        
        try:
            # Check if we are using an Imagen model
            if "imagen" in self.image_model.lower():
                response = self._client.models.generate_images(
                    model=self.image_model,
                    prompt=prompt
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
            for chunk in self._client.models.generate_content_stream(
                model=self.image_model,
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
                    total_bytes += part.inline_data.data
            
            self._log_interaction("generate_image (Multimodal Stream)", prompt, f"<Generated {len(total_bytes)} bytes>")
            return total_bytes
            
            self._log_interaction("generate_image (Multimodal Stream)", prompt, f"<Generated {len(total_bytes)} bytes>")
            return total_bytes
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return b""

    def create_batch_job(
        self,
        dataset_name: str,
        source_file_path: Path,
        model_name: str | None = None,
    ) -> Any | None:
        """
        Create a batch job using a local JSONL file.
        
        Args:
            dataset_name: A display name for the batch job.
            source_file_path: Path to the local .jsonl file containing requests.
            model_name: Target model (e.g. "gemini-1.5-flash-002"). Defaults to self.text_model.
            
        Returns:
            The created batch job object or None if failed.
        """
        try:
            model = model_name or self.text_model
            logger.info(f"Creating batch job '{dataset_name}' for model {model} from {source_file_path}")
            
            # 1. Upload the file
            # Batch API requires a specific file upload or referencing a file.
            # Usually we use client.files.upload and then reference it.
            # Or client.batches.create might accept a local path depending on SDK version.
            # Assuming standard Google GenAI SDK flow:
            
            # Fix: Use 'file' param and explicit mime_type for JSONL files
            # Reverting to application/json as it's standard, and using 'dataset' param in create
            file_ref = self._client.files.upload(
                file=str(source_file_path),
                config={"mime_type": "application/json"}
            )
            logger.info(f"Uploaded batch file: {file_ref.name}")
            
            # Wait for file to be processed (ACTIVE state)
            while file_ref.state.name == "PROCESSING":
                time.sleep(1)
                file_ref = self._client.files.get(name=file_ref.name)

            if file_ref.state.name == "FAILED":
                raise RuntimeError(f"Batch file processing failed: {file_ref.error.message if hasattr(file_ref, 'error') else 'Unknown error'}")

            logger.info(f"Batch file ready: {file_ref.name} (State: {file_ref.state.name})")

            # 2. Create the batch job
            # The 'src' parameter implies GCS. For File API, we should use 'dataset'.
            batch_job = self._client.batches.create(
                model=model,
                dataset=file_ref.name,
                config=types.CreateBatchJobConfig(
                    display_name=dataset_name
                )
            )
            
            logger.info(f"Batch job created: {batch_job.name} (State: {batch_job.state})")
            return batch_job
            
        except Exception as e:
            logger.error(f"Failed to create batch job: {e}")
            return None

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

