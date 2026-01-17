"""Project repository for managing project data."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .json_repo import JsonRepository
from ..core.config import settings


def _utc_now() -> str:
    """Get current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


class ProjectRepository:
    """Repository for project CRUD operations."""
    
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or settings.data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_repo(self, project_id: str) -> JsonRepository:
        """Get a JsonRepository for a specific project."""
        return JsonRepository(self.data_dir / project_id)
    
    def ensure_dirs(self, project_id: str) -> dict[str, Path]:
        """Ensure all project directories exist."""
        project_dir = self.data_dir / project_id
        dirs = {
            "project": project_dir,
            "source": project_dir / "source",
            "images": project_dir / "images",
            "renders": project_dir / "renders",
            "jobs": project_dir / "jobs",
        }
        for folder in dirs.values():
            folder.mkdir(parents=True, exist_ok=True)
        return dirs
    
    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a new project."""
        project_id = uuid.uuid4().hex
        self.ensure_dirs(project_id)
        
        project_data = {
            "id": project_id,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "status": "NEW",
            "format": payload.get("format", "9:16"),
            "style": payload.get("style", "cinematic"),
            "subtitles": payload.get("subtitles", True),
            "user_description": payload.get("user_description", ""),
        }
        
        repo = self._get_repo(project_id)
        repo.save("project.json", project_data)
        return project_data
    
    def get(self, project_id: str) -> dict[str, Any] | None:
        """Get a project by ID."""
        repo = self._get_repo(project_id)
        if not repo.exists("project.json"):
            return None
        return repo.load("project.json", {})
    
    def update(self, project_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update project fields."""
        updates["updated_at"] = _utc_now()
        repo = self._get_repo(project_id)
        return repo.update("project.json", updates)
    
    def exists(self, project_id: str) -> bool:
        """Check if a project exists."""
        return self._get_repo(project_id).exists("project.json")
    
    def list_all(self) -> list[dict[str, Any]]:
        """List all projects, sorted by updated_at descending."""
        projects = []
        if not self.data_dir.exists():
            return projects
        
        for project_dir in self.data_dir.iterdir():
            if project_dir.is_dir():
                repo = JsonRepository(project_dir)
                if repo.exists("project.json"):
                    project = repo.load("project.json", {})
                    if project:
                        projects.append(project)
        
        projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return projects
    
    # Analysis
    def save_analysis(self, project_id: str, analysis: dict[str, Any]) -> None:
        """Save audio analysis results."""
        self._get_repo(project_id).save("analysis.json", analysis)
    
    def get_analysis(self, project_id: str) -> dict[str, Any] | None:
        """Get audio analysis results."""
        repo = self._get_repo(project_id)
        if not repo.exists("analysis.json"):
            return None
        return repo.load("analysis.json", {})
    
    # Segments
    def save_segments(self, project_id: str, segments: list[dict[str, Any]]) -> None:
        """Save storyboard segments."""
        self._get_repo(project_id).save("segments.json", segments)
    
    def get_segments(self, project_id: str) -> list[dict[str, Any]]:
        """Get storyboard segments."""
        return self._get_repo(project_id).load("segments.json", [])
    
    def update_segment(self, project_id: str, seg_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a specific segment."""
        repo = self._get_repo(project_id)
        segments = repo.load("segments.json", [])
        
        for segment in segments:
            if segment.get("id") == seg_id:
                segment.update(updates)
                repo.save("segments.json", segments)
                return segment
        return None
    
    # Prompts
    def save_prompts(self, project_id: str, prompts: dict[str, Any]) -> None:
        """Save image prompts."""
        self._get_repo(project_id).save("prompts.json", prompts)
    
    def get_prompts(self, project_id: str) -> dict[str, Any]:
        """Get image prompts."""
        return self._get_repo(project_id).load("prompts.json", {})
    
    def update_prompt(self, project_id: str, seg_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a specific prompt."""
        repo = self._get_repo(project_id)
        prompts = repo.load("prompts.json", {})
        
        if seg_id not in prompts:
            prompts[seg_id] = {"version": 1}
        
        prompts[seg_id].update(updates)
        repo.save("prompts.json", prompts)
        return prompts[seg_id]
    
    # Jobs
    def update_job(self, project_id: str, job_name: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update job status."""
        updates["updated_at"] = _utc_now()
        repo = self._get_repo(project_id)
        return repo.update(f"jobs/{job_name}.json", updates)
    
    def get_jobs(self, project_id: str) -> dict[str, Any]:
        """Get all job statuses."""
        jobs_dir = self.data_dir / project_id / "jobs"
        jobs = {}
        
        if jobs_dir.exists():
            repo = JsonRepository(jobs_dir)
            for job_file in jobs_dir.glob("*.json"):
                jobs[job_file.stem] = repo.load(job_file.name, {})
        
        return jobs
