"""Pipeline orchestrator service."""
from __future__ import annotations

from typing import Any, Callable

from ..clients.genai import GenAIClient
from ..repositories.project_repo import ProjectRepository
from ..repositories.file_storage import FileStorage
from .audio_service import AudioAnalysisService
from .story_service import StoryboardService
from .image_service import ImageService
from .render_service import RenderService
from ..core.logging import get_logger

logger = get_logger(__name__)


class PipelineService:
    """Orchestrates the full video generation pipeline."""
    
    def __init__(
        self,
        project_repo: ProjectRepository | None = None,
        file_storage: FileStorage | None = None,
        genai_client: GenAIClient | None = None,
    ) -> None:
        self.project_repo = project_repo or ProjectRepository()
        self.file_storage = file_storage or FileStorage()
        self.genai = genai_client or GenAIClient()
        
        # Initialize services
        self.audio_service = AudioAnalysisService(
            self.genai, self.project_repo, self.file_storage
        )
        self.story_service = StoryboardService(self.genai, self.project_repo)
        self.image_service = ImageService(
            self.genai, self.project_repo, self.file_storage
        )
        self.render_service = RenderService(self.project_repo, self.file_storage)
    
    def run_full_pipeline(self, project_id: str) -> str:
        """Run the complete video generation pipeline."""
        try:
            # Step 1: Audio Analysis
            self._update_job(project_id, "pipeline", {
                "status": "RUNNING", "step": "analysis", "progress": 5
            })
            analysis = self._run_step(
                project_id, "analysis",
                lambda: self.audio_service.analyze(project_id)
            )
            
            # Step 2: Storyboard Generation
            self._update_job(project_id, "pipeline", {
                "status": "RUNNING", "step": "segments", "progress": 15
            })
            segments = self._run_step(
                project_id, "segments",
                lambda: self.story_service.generate(project_id, analysis)
            )
            
            # Step 3: Prompt Generation
            self._update_job(project_id, "pipeline", {
                "status": "RUNNING", "step": "prompts", "progress": 25
            })
            prompts = self._run_step(
                project_id, "prompts",
                lambda: self.image_service.generate_prompts(
                    project_id, segments, analysis
                )
            )
            
            # Step 4: Image Generation
            def image_progress(p: int):
                self._update_job(project_id, "pipeline", {
                    "progress": 30 + int(p * 0.4)
                })
            
            self._run_step(
                project_id, "images",
                lambda: self.image_service.generate_all_images(
                    project_id, prompts, image_progress
                )
            )
            
            # Step 5: Video Rendering
            self._update_job(project_id, "pipeline", {
                "status": "RUNNING", "step": "render", "progress": 70
            })
            
            def render_progress(p: int):
                self._update_job(project_id, "pipeline", {
                    "progress": 70 + int(p * 0.3)
                })
            
            output_path, render_duration = self._run_step(
                project_id, "render",
                lambda: self.render_service.render(project_id, render_progress)
            )
            
            # Complete
            self._update_job(project_id, "pipeline", {
                "status": "DONE",
                "step": "complete",
                "progress": 100,
                "output": str(output_path),
                "render_duration_seconds": round(render_duration, 1),
            })
            self.project_repo.update(project_id, {"status": "DONE"})
            
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self._update_job(project_id, "pipeline", {
                "status": "FAILED", "error": str(e)
            })
            self.project_repo.update(project_id, {"status": "FAILED"})
            raise
    
    def render_only(self, project_id: str) -> str:
        """Run only the rendering step."""
        try:
            self._update_job(project_id, "render", {
                "status": "RUNNING", "step": "render", "progress": 0
            })
            
            def render_progress(p: int):
                self._update_job(project_id, "render", {
                    "progress": p
                })
            
            output_path, render_duration = self.render_service.render(project_id, render_progress)
            
            self._update_job(project_id, "render", {
                "status": "DONE",
                "step": "complete",
                "progress": 100,
                "output": str(output_path),
                "render_duration_seconds": round(render_duration, 1),
            })
            self.project_repo.update(project_id, {"status": "DONE"})
            
            return str(output_path)
        
        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"Render failed: {error_msg}")
            self._update_job(project_id, "render", {
                "status": "FAILED", "error": error_msg
            })
            self.project_repo.update(project_id, {"status": "FAILED"})
            raise
    
    def _run_step(
        self,
        project_id: str,
        step: str,
        action: Callable[[], Any],
        attempts: int = 2,
    ) -> Any:
        """Run a pipeline step with retry logic."""
        last_error = None
        
        for attempt in range(1, attempts + 1):
            self._update_job(project_id, "pipeline", {
                "status": "RUNNING", "step": step, "attempt": attempt
            })
            try:
                return action()
            except Exception as exc:
                last_error = exc
                self._update_job(project_id, "pipeline", {
                    "status": "RETRYING",
                    "step": step,
                    "attempt": attempt,
                    "error": str(exc),
                })
        
        self._update_job(project_id, "pipeline", {
            "status": "FAILED", "step": step, "error": str(last_error)
        })
        self.project_repo.update(project_id, {"status": "FAILED"})
        raise last_error or RuntimeError(f"Pipeline step failed: {step}")
    
    def _update_job(self, project_id: str, job_name: str, updates: dict[str, Any]) -> None:
        """Update job status."""
        self.project_repo.update_job(project_id, job_name, updates)
