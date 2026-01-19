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
    ) -> dict[str, Any]:
        """Generate image prompts for all segments."""
        prompts = self.genai.build_prompts(segments, analysis)
        self.project_repo.save_prompts(project_id, prompts)
        return prompts
    
    def generate_all_images(
        self,
        project_id: str,
        prompts: dict[str, Any],
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        """Generate images for all segments in parallel."""
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
                
                # Check for exceptions raised during execution
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
