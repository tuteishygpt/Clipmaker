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

        # Ensure version exists for local tracking
        for seg_id, data in prompts.items():
            if "version" not in data:
                data["version"] = 1

        self.project_repo.save_prompts(project_id, prompts)
        return prompts
    
    def generate_all_images(
        self,
        project_id: str,
        prompts: dict[str, Any],
        progress_callback: Callable[[int], None] | None = None,
        use_batch: bool = True
    ) -> None:
        """
        Generate images for all segments.
        
        Args:
            project_id: The project ID.
            prompts: Dictionary mapping segment IDs to prompt payloads.
            progress_callback: Callback for progress updates (0-100).
            use_batch: If True, uses Gemini Batch API. If False, uses parallel direct requests.
        """
        if not prompts:
            return

        if not use_batch:
            self._generate_images_interactive(project_id, prompts, progress_callback)
            return

        # --- Batch Mode ---
        from .batch_service import BatchService
        batch_service = BatchService()
        
        logger.info(f"Starting BATCH image generation for project {project_id} with {len(prompts)} prompts")
        if progress_callback:
            progress_callback(5)

        # 1. Prepare requests
        batch_requests = []
        for seg_id, payload in prompts.items():
            prompt_text = payload.get("image_prompt", "")
            
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
                    "response_modalities": ["IMAGE"]
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
    ) -> None:
        """Generate images for all segments in parallel (Interactive/Threaded)."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        total = len(prompts)
        completed = 0
        
        def _generate_task(item):
            seg_id, payload = item
            version = payload.get("version", 1)
            try:
                image_bytes = self.genai.generate_image(payload)
                if image_bytes:
                    self.file_storage.save_image(project_id, seg_id, version, image_bytes)
                    return True
                else:
                    logger.warning(f"Failed to generate image for {seg_id}")
                    return False
            except Exception as e:
                logger.error(f"Exception generating image for {seg_id}: {e}")
                return False

        # Run up to 5 generations in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_generate_task, item) for item in prompts.items()]
            
            for future in as_completed(futures):
                completed += 1
                if progress_callback:
                    progress = int((completed / total) * 100)
                    progress_callback(progress)
                
                try:
                    future.result()
                except Exception as e:
                     logger.error(f"Task failed with error: {e}")

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

        # Fetch analysis for context (style, character)
        analysis = self.project_repo.get_analysis(project_id) or {}
        
        # Get existing prompt data for version tracking
        prompts = self.project_repo.get_prompts(project_id)
        old_prompt_data = prompts.get(seg_id, {})
        new_version = int(old_prompt_data.get("version", 1)) + 1
        
        # Re-build prompt using the (potentially updated) segment description
        # We pass a list containing just this segment
        new_prompts_map = self.genai.build_prompts([current_segment], analysis)
        new_prompt_data = new_prompts_map.get(seg_id)
        
        if not new_prompt_data:
            logger.warning(f"Failed to rebuild prompt for {seg_id}, using old prompt")
            new_prompt_data = old_prompt_data
            # Should at least update the prompt text if we can't rebuild fully?
            # ideally build_prompts works.
        
        new_prompt_data["version"] = new_version
        
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
