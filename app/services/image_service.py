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
        """Generate images for all segments."""
        total = len(prompts)
        
        for i, (seg_id, payload) in enumerate(prompts.items()):
            if progress_callback:
                progress = int((i / total) * 100)
                progress_callback(progress)
            
            version = payload.get("version", 1)
            image_bytes = self.genai.generate_image(payload)
            
            if image_bytes:
                self.file_storage.save_image(project_id, seg_id, version, image_bytes)
            else:
                logger.warning(f"Failed to generate image for {seg_id}")
        
        if progress_callback:
            progress_callback(100)
    
    def regenerate_segment(self, project_id: str, seg_id: str) -> dict[str, Any]:
        """Regenerate image for a single segment."""
        prompts = self.project_repo.get_prompts(project_id)
        
        if seg_id not in prompts:
            raise KeyError(f"Segment {seg_id} not found in prompts")
        
        current = prompts[seg_id]
        current_version = int(current.get("version", 1))
        current["version"] = current_version + 1
        
        # Save updated version
        self.project_repo.update_prompt(project_id, seg_id, current)
        
        # Generate new image
        image_bytes = self.genai.generate_image(current)
        if image_bytes:
            self.file_storage.save_image(
                project_id, seg_id, current["version"], image_bytes
            )
        
        return current
