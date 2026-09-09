"""Image generation service."""
from __future__ import annotations

from typing import Any, Callable

from ..clients.genai import GenAIClient
from ..repositories.project_repo import ProjectRepository
from ..repositories.file_storage import FileStorage
from ..core.logging import get_logger

logger = get_logger(__name__)


class ImageService:
    """Service for generating images for segments."""
    
    def __init__(
        self,
        genai_client: GenAIClient | None = None,
        project_repo: ProjectRepository | None = None,
        file_storage: FileStorage | None = None,
    ) -> None:
        self.genai = genai_client or GenAIClient()
        self.project_repo = project_repo or ProjectRepository()
        self.file_storage = file_storage or FileStorage()
    
    def generate_prompts(
        self,
        project_id: str,
        segments: list[dict[str, Any]],
        analysis: dict[str, Any],
        use_batch: bool = True
    ) -> dict[str, Any]:
        """Generate image prompts for all segments."""
        project = self.project_repo.get(project_id) or {}
        project_format = project.get("format") or analysis.get("format", "9:16")
        if analysis and "format" not in analysis:
            analysis["format"] = project_format

        if not use_batch:
            prompts = self.genai.build_prompts(segments, analysis, use_batch=False)
        else:
            # --- Batch Mode ---
            from .batch_service import BatchService
            batch_service = BatchService()
            
            req_body = self.genai.build_prompts(segments, analysis, use_batch=True)
            
            job_result = batch_service.submit_batch_job(
                requests=[req_body],
                model_name=self.genai.text_model,
                job_name=f"Prompts-{project_id}"
            )
            
            job_name = job_result.get("job_id")
            if not job_name:
                raise RuntimeError("Failed to submit batch job for prompts")
            
            batch_service.wait_for_job(job_name)
            
            results = batch_service.download_results(job_name)
            if not results:
                raise RuntimeError("Batch prompts failed to return results")
            
            # Parse response - results now contains raw JSONL entries
            raw_item = results[0]
            response_data = raw_item.get("response", {})
            candidates = response_data.get("candidates", [])
            
            text_content = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        text_content += part["text"]
            
            if text_content:
                prompts = self.genai._extract_json(text_content)
            else:
                # Fallback if structure is different
                prompts = raw_item.get("response", raw_item)

            # Unify structure if needed
            if isinstance(prompts, dict) and "prompts" in prompts:
                 prompts = prompts["prompts"]

        # Ensure version and aspect ratio exist for local tracking
        for seg_id, data in prompts.items():
            if not isinstance(data, dict):
                continue
            max_v = self.file_storage.get_max_version(project_id, seg_id)
            cur_v = data.get("version", 0)
            # If an image for this segment already exists on disk, advance to next version
            data["version"] = (max_v + 1) if max_v > 0 else (cur_v or 1)
            if "aspect_ratio" not in data:
                data["aspect_ratio"] = project_format
            if "format" not in data:
                data["format"] = project_format

        self.project_repo.save_prompts(project_id, prompts)
        return prompts
    
    def generate_all_images(
        self,
        project_id: str,
        prompts: dict[str, Any],
        progress_callback: Callable[[int], None] | None = None,
        use_batch: bool = True,
        force: bool = False,
    ) -> None:
        """
        Generate images for all segments.
        
        Args:
            project_id: The project ID.
            prompts: Dictionary mapping segment IDs to prompt payloads.
            progress_callback: Callback for progress updates (0-100).
            use_batch: If True, uses Gemini Batch API. If False, uses parallel direct requests.
            force: If True, regenerates images even if they already exist on disk.
        """
        if not prompts:
            return

        if not use_batch:
            self._generate_images_interactive(project_id, prompts, progress_callback, force=force)
            return

        # --- Batch Mode ---
        from .batch_service import BatchService
        batch_service = BatchService()
        
        project = self.project_repo.get(project_id) or {}
        project_format = project.get("format", "9:16")
        
        logger.info(f"Starting BATCH image generation for project {project_id} with {len(prompts)} prompts (format: {project_format})")
        if progress_callback:
            progress_callback(5)

        # 1. Prepare requests
        batch_requests = []
        for seg_id, payload in prompts.items():
            prompt_text = payload.get("image_prompt", "")
            aspect_ratio = payload.get("aspect_ratio") or payload.get("format") or project_format
            
            # Construct the request body for generateContent
            # We need to match the structure expected by the model for image generation
            # If using Gemini with response_modalities=["IMAGE"]:
            request_body = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt_text}]
                    }
                ],
                "generationConfig": {
                    "response_modalities": ["IMAGE"],
                    "imageConfig": {
                        "aspectRatio": aspect_ratio
                    }
                }
            }
            
            batch_requests.append({
                "custom_id": seg_id, # Track which segment this is
                "method": "generateContent",
                "request": request_body
            })

        # 2. Submit Batch Job
        model_name = self.genai.image_model
        job_result = batch_service.submit_batch_job(
            requests=batch_requests,
            model_name=model_name,
            job_name=f"Images-{project_id}"
        )
        
        job_name = job_result.get("job_id")
        if not job_name:
            logger.error("Failed to submit batch job, falling back to interactive mode")
            self._generate_images_interactive(project_id, prompts, progress_callback)
            return

        logger.info(f"Batch job submitted: {job_name}. Waiting for completion...")
        
        # 3. Poll for completion
        state = batch_service.wait_for_job(job_name)

        if state != "SUCCEEDED":
            logger.error(f"Batch job finished with state {state}")
            # If failed, we might want to try interactive or just fail?
            # For now, let's try to download whatever succeeded.

        # 4. Download and Process Results
        results = batch_service.download_results(job_name)
        logger.info(f"Downloaded {len(results)} results from batch job")
        
        processed_count = 0
        for item in results:
            try:
                # item structure: {custom_id: ..., response: { ... }}
                seg_id = item.get("custom_id")
                response_data = item.get("response", {})
                
                # Check for errors in individual request
                if "error" in response_data:
                    logger.error(f"Error for segment {seg_id}: {response_data['error']}")
                    continue
                
                # Extract image bytes
                # The response follows the REST API structure for GenerateContentResponse
                # candidates[0].content.parts[0].inlineData.data (base64)
                
                import base64
                
                candidates = response_data.get("candidates", [])
                if not candidates:
                    continue
                    
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    continue
                    
                inline_data = parts[0].get("inlineData", {})
                b64_data = inline_data.get("data")
                
                if b64_data:
                    image_bytes = base64.b64decode(b64_data)
                    
                    # Determine version
                    # We might need to look up current version or just assume 1 if not present
                    # payload = prompts.get(seg_id, {})
                    # version = payload.get("version", 1)
                    # Simplified: Always save as version 1 for batch init, or check generic logic
                    version = 1 
                    if seg_id in prompts:
                        version = prompts[seg_id].get("version", 1)
                        
                    self.file_storage.save_image(project_id, seg_id, version, image_bytes)
                    processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process batch result item: {e}")

        logger.info(f"Successfully saved {processed_count} images from batch.")
        if progress_callback:
            progress_callback(100)

    def _generate_images_interactive(
        self,
        project_id: str,
        prompts: dict[str, Any],
        progress_callback: Callable[[int], None] | None = None,
        force: bool = False,
    ) -> None:
        """Generate images for all segments with strict RPM pacing (e.g. Tier 1: 5 RPM) and retry logic."""
        import time
        from ..core.config import settings

        project = self.project_repo.get(project_id) or {}
        project_format = project.get("format", "9:16")

        total = len(prompts)
        completed = 0
        rpm = getattr(settings, "genai_image_rpm", 5) or 5
        # 60s / 5 RPM = 12.0s per request + 0.5s safety buffer = 12.5s interval
        interval = (60.0 / max(rpm, 1)) + 0.5
        logger.info(f"Generating images for {total} segments (format: {project_format}, RPM limit: {rpm}, pacing interval: {interval:.1f}s, force: {force})")

        last_request_time = 0.0

        def _pace():
            nonlocal last_request_time
            if last_request_time > 0:
                elapsed = time.time() - last_request_time
                if elapsed < interval:
                    sleep_time = interval - elapsed
                    logger.info(f"Pacing ({rpm} RPM): waiting {sleep_time:.1f}s before next image request...")
                    time.sleep(sleep_time)
            last_request_time = time.time()

        def _generate_single(seg_id: str, payload: dict[str, Any], max_retries: int = 3) -> bool:
            version = payload.get("version", 1)
            if "aspect_ratio" not in payload:
                payload["aspect_ratio"] = project_format
            if "format" not in payload:
                payload["format"] = project_format
            
            # Check if valid image already exists on disk (avoid redundant generation only if not force)
            if not force:
                existing_img = self.file_storage.get_image_path(project_id, f"{seg_id}_v{version}.png")
                if existing_img and existing_img.exists() and existing_img.stat().st_size > 1000:
                    logger.info(f"Image for {seg_id} v{version} already exists ({existing_img.stat().st_size} bytes), skipping")
                    return True

            for attempt in range(1, max_retries + 1):
                _pace()
                try:
                    image_bytes = self.genai.generate_image(payload)
                    if image_bytes and len(image_bytes) > 0:
                        self.file_storage.save_image(project_id, seg_id, version, image_bytes)
                        logger.info(f"Successfully generated image for {seg_id} v{version}")
                        return True
                    logger.warning(f"Attempt {attempt}/{max_retries} returned empty image for {seg_id}")
                except Exception as e:
                    logger.error(f"Attempt {attempt}/{max_retries} error for {seg_id}: {e}")
                
                if attempt < max_retries:
                    time.sleep(3.0 * attempt)

            logger.error(f"All {max_retries} attempts failed to generate image for {seg_id}")
            return False

        # Pass 1: Sequential paced generation
        for seg_id, payload in prompts.items():
            ok = _generate_single(seg_id, payload)
            completed += 1
            if progress_callback:
                progress = int((completed / total) * 90)
                progress_callback(progress)

        # Pass 2: Retry any still-missing images
        missing_items = []
        for seg_id, payload in prompts.items():
            version = payload.get("version", 1)
            img_path = self.file_storage.get_image_path(project_id, f"{seg_id}_v{version}.png")
            if not img_path or not img_path.exists() or img_path.stat().st_size == 0:
                missing_items.append((seg_id, payload))

        if missing_items:
            logger.warning(f"{len(missing_items)} images missing after pass 1. Starting sequential retry pass...")
            for seg_id, payload in missing_items:
                ok = _generate_single(seg_id, payload, max_retries=3)
                if not ok:
                    logger.error(f"Permanent failure generating image for segment {seg_id}")

        # Final check: Ensure every segment has an image
        still_missing = []
        for seg_id, payload in prompts.items():
            version = payload.get("version", 1)
            img_path = self.file_storage.get_image_path(project_id, f"{seg_id}_v{version}.png")
            if not img_path or not img_path.exists() or img_path.stat().st_size == 0:
                still_missing.append(seg_id)

        if still_missing:
            raise RuntimeError(
                f"Failed to generate images for {len(still_missing)} segments: {', '.join(still_missing[:5])}. "
                f"Please check quota or retry."
            )

        if progress_callback:
            progress_callback(100)
    
    def regenerate_segment(self, project_id: str, seg_id: str) -> dict[str, Any]:
        """Regenerate image for a single segment."""
        # Fetch current segment data to ensure we use updated descriptions
        segments = self.project_repo.get_segments(project_id)
        if not segments:
            raise KeyError(f"Segments for project {project_id} not found")
            
        current_segment = next((s for s in segments if s.get("id") == seg_id), None)
        if not current_segment:
            raise KeyError(f"Segment {seg_id} not found")
        
        # Log segment details
        seg_text = current_segment.get('lyric_text', current_segment.get('text', 'NO TEXT'))
        logger.info(f"[REGENERATE_SEGMENT] Found segment with text: '{seg_text[:50]}...'")

        project = self.project_repo.get(project_id) or {}
        project_format = project.get("format", "9:16")

        # Fetch analysis for context (style, character, format)
        analysis = self.project_repo.get_analysis(project_id) or {}
        analysis["format"] = project_format
        if project.get("character_description"):
            analysis["character_description"] = project["character_description"]
        if project.get("style"):
            analysis["style"] = project["style"]
        if project.get("user_description"):
            analysis["user_description"] = project["user_description"]
        
        # Log for debugging
        style = analysis.get('visual_style_anchor') or analysis.get('style', 'NO STYLE')
        logger.info(f"[REGENERATE_SEGMENT] project_id={project_id}, seg_id={seg_id}, format={project_format}, style='{style[:50]}...'")
        
        # Get existing prompt data for version tracking
        prompts = self.project_repo.get_prompts(project_id)
        old_prompt_data = prompts.get(seg_id, {})
        max_v = self.file_storage.get_max_version(project_id, seg_id)
        cur_v = int(old_prompt_data.get("version", 1))
        new_version = max(max_v, cur_v) + 1
        
        # Re-build prompt using the (potentially updated) segment description
        # We pass a list containing just this segment
        new_prompts_map = self.genai.build_prompts([current_segment], analysis)
        new_prompt_data = new_prompts_map.get(seg_id)
        
        if not new_prompt_data:
            logger.warning(f"Failed to rebuild prompt for {seg_id}, using old prompt")
            new_prompt_data = old_prompt_data
        
        new_prompt_data["version"] = new_version
        new_prompt_data["aspect_ratio"] = project_format
        new_prompt_data["format"] = project_format
        
        # Save updated prompt
        self.project_repo.update_prompt(project_id, seg_id, new_prompt_data)
        
        # Generate new image
        image_bytes = self.genai.generate_image(new_prompt_data)
        if image_bytes:
            self.file_storage.save_image(
                project_id, seg_id, new_version, image_bytes
            )
        else:
             logger.error(f"Failed to generate image bytes for {seg_id}")
        
        return new_prompt_data

    def regenerate_prompt_only(self, project_id: str, seg_id: str) -> dict[str, Any]:
        """Regenerate only the prompt for a segment (no image generation)."""
        # Fetch current segment data
        segments = self.project_repo.get_segments(project_id)
        if not segments:
            raise KeyError(f"Segments for project {project_id} not found")
            
        current_segment = next((s for s in segments if s.get("id") == seg_id), None)
        if not current_segment:
            raise KeyError(f"Segment {seg_id} not found")

        project = self.project_repo.get(project_id) or {}
        project_format = project.get("format", "9:16")

        # Fetch analysis for context
        analysis = self.project_repo.get_analysis(project_id) or {}
        analysis["format"] = project_format
        if project.get("character_description"):
            analysis["character_description"] = project["character_description"]
        if project.get("style"):
            analysis["style"] = project["style"]
        if project.get("user_description"):
            analysis["user_description"] = project["user_description"]
        
        # Get existing prompt data for version tracking
        prompts = self.project_repo.get_prompts(project_id)
        old_prompt_data = prompts.get(seg_id, {})
        # Keep same version since we're only updating the prompt text
        current_version = int(old_prompt_data.get("version", 1))
        
        # Re-build prompt
        new_prompts_map = self.genai.build_prompts([current_segment], analysis)
        new_prompt_data = new_prompts_map.get(seg_id)
        
        if not new_prompt_data:
            logger.warning(f"Failed to rebuild prompt for {seg_id}")
            raise RuntimeError(f"Failed to rebuild prompt for {seg_id}")
        
        # Preserve version and set aspect ratio
        new_prompt_data["version"] = current_version
        new_prompt_data["aspect_ratio"] = project_format
        new_prompt_data["format"] = project_format
        
        # Save updated prompt
        self.project_repo.update_prompt(project_id, seg_id, new_prompt_data)
        
        logger.info(f"Regenerated prompt only for {seg_id}")
        return new_prompt_data

    def regenerate_image_only(self, project_id: str, seg_id: str) -> dict[str, Any]:
        """Regenerate only the image using existing prompt (new version)."""
        project = self.project_repo.get(project_id) or {}
        project_format = project.get("format", "9:16")

        # Get existing prompt data
        prompts = self.project_repo.get_prompts(project_id)
        prompt_data = prompts.get(seg_id)
        
        if not prompt_data:
            raise KeyError(f"Prompt for segment {seg_id} not found")
        
        if not prompt_data.get("image_prompt"):
            raise ValueError(f"No image_prompt found for segment {seg_id}")
        
        # Increment version for new image
        max_v = self.file_storage.get_max_version(project_id, seg_id)
        cur_v = int(prompt_data.get("version", 1))
        new_version = max(max_v, cur_v) + 1
        prompt_data["version"] = new_version
        prompt_data["aspect_ratio"] = project_format
        prompt_data["format"] = project_format
        
        # Save updated version
        self.project_repo.update_prompt(project_id, seg_id, prompt_data)
        
        # Generate new image
        image_bytes = self.genai.generate_image(prompt_data)
        if image_bytes:
            self.file_storage.save_image(
                project_id, seg_id, new_version, image_bytes
            )
            logger.info(f"Regenerated image only for {seg_id} as v{new_version} (format: {project_format})")
        else:
            logger.error(f"Failed to generate image bytes for {seg_id}")
            raise RuntimeError(f"Failed to generate image for {seg_id}")
        
        return prompt_data
