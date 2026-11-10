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
            "title": payload.get("title") or f"Project {project_id[:8]}",
            "standalone_mode": payload.get("standalone_mode", False),
            "format": payload.get("format", "9:16"),
            "style": payload.get("style", "cinematic"),
            "subtitles": payload.get("subtitles", True),
            "user_description": payload.get("user_description", ""),
            "character_description": payload.get("character_description", ""),
            "render_preset": payload.get("render_preset", "fast"),
        }
        
        repo = self._get_repo(project_id)
        repo.save("project.json", project_data)
        if settings.storage_backend == "s3":
            try:
                self.save_manifest_to_storage(project_id)
            except Exception:
                pass
        return project_data
    
    def get(self, project_id: str) -> dict[str, Any] | None:
        """Get a project by ID."""
        repo = self._get_repo(project_id)
        if not repo.exists("project.json") and settings.storage_backend == "s3":
            try:
                self.load_manifest_from_storage(project_id)
            except Exception:
                pass
        if not repo.exists("project.json"):
            return None
        return repo.load("project.json", {})
    
    def update(self, project_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update project fields."""
        updates["updated_at"] = _utc_now()
        repo = self._get_repo(project_id)
        res = repo.update("project.json", updates)
        if settings.storage_backend == "s3":
            try:
                self.save_manifest_to_storage(project_id)
            except Exception:
                pass
        return res
    
    def exists(self, project_id: str) -> bool:
        """Check if a project exists."""
        if self._get_repo(project_id).exists("project.json"):
            return True
        if settings.storage_backend == "s3":
            try:
                self.load_manifest_from_storage(project_id)
                return self._get_repo(project_id).exists("project.json")
            except Exception:
                return False
        return False
    
    def list_all(self, search: str | None = None, standalone: bool | None = None) -> list[dict[str, Any]]:
        """List all projects, sorted by updated_at descending, optionally filtered by search and standalone mode."""
        if settings.storage_backend == "s3":
            try:
                from .file_storage import FileStorage
                storage = FileStorage(self.data_dir)
                client = storage.get_s3_client()
                resp = client.list_objects_v2(
                    Bucket=settings.s3_bucket_name,
                    Prefix="projects/",
                    Delimiter="/"
                )
                for prefix_obj in resp.get("CommonPrefixes", []):
                    prefix = prefix_obj.get("Prefix", "")
                    parts = prefix.strip("/").split("/")
                    if len(parts) == 2:
                        p_id = parts[1]
                        if not (self.data_dir / p_id / "project.json").exists():
                            try:
                                self.load_manifest_from_storage(p_id)
                            except Exception:
                                pass
            except Exception:
                pass

        projects = []
        if not self.data_dir.exists():
            return projects
        
        search_lower = search.lower() if search else None
        
        for project_dir in self.data_dir.iterdir():
            if project_dir.is_dir():
                repo = JsonRepository(project_dir)
                if repo.exists("project.json"):
                    project = repo.load("project.json", {})
                    if not project:
                        continue
                    
                    # Standalone filter
                    if standalone is not None:
                        is_standalone = bool(project.get("standalone_mode", False))
                        if is_standalone != standalone:
                            continue

                    # Search filtering
                    if search_lower:
                        project_id = str(project.get("id", "")).lower()
                        title = str(project.get("title", "")).lower()
                        description = str(project.get("user_description", "")).lower()
                        if search_lower not in project_id and search_lower not in title and search_lower not in description:
                            continue
                            
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
        
        # In S3 mode: If jobs missing locally or render job is RUNNING/PENDING,
        # refresh from S3 manifest to pick up updates written by remote worker.
        render_status = jobs.get("render", {}).get("status")
        if settings.storage_backend == "s3" and (not jobs or render_status in ("RUNNING", "PENDING", None)):
            try:
                manifest = self.load_manifest_from_storage(project_id, force_refresh=True)
                s3_jobs = manifest.get("jobs", {})
                if isinstance(s3_jobs, dict) and s3_jobs:
                    jobs_dir.mkdir(parents=True, exist_ok=True)
                    jrepo = JsonRepository(jobs_dir)
                    for k, v in s3_jobs.items():
                        # Update if remote worker reached a terminal state or has newer info
                        if k not in jobs or v.get("status") in ("DONE", "FAILED", "ERROR") or v.get("updated_at", "") > jobs[k].get("updated_at", ""):
                            jobs[k] = v
                            jrepo.save(f"{k}.json", v)
            except Exception:
                pass
        
        return jobs

    # ==================== Manifest Export / Import ====================

    def export_manifest(self, project_id: str) -> dict[str, Any]:
        """Export project, segments, prompts, and analysis into a unified manifest."""
        project = self.get(project_id) or {}
        segments = self.get_segments(project_id)
        prompts = self.get_prompts(project_id)
        analysis = self.get_analysis(project_id)
        
        # Read local jobs directly to avoid recursion
        jobs_dir = self.data_dir / project_id / "jobs"
        jobs = {}
        if jobs_dir.exists():
            repo = JsonRepository(jobs_dir)
            for job_file in jobs_dir.glob("*.json"):
                jobs[job_file.stem] = repo.load(job_file.name, {})
        
        manifest = {
            "version": "1.0",
            "project_id": project_id,
            "project": project,
            "segments": segments,
            "prompts": prompts,
            "analysis": analysis,
            "jobs": jobs,
            "exported_at": _utc_now(),
        }
        return manifest

    def save_manifest_to_storage(self, project_id: str) -> dict[str, Any]:
        """Save project manifest locally and upload to S3/R2 if storage_backend == 's3'."""
        import json
        manifest = self.export_manifest(project_id)
        project_dir = self.data_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = project_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        if settings.storage_backend == "s3":
            from .file_storage import FileStorage
            storage = FileStorage(self.data_dir)
            s3_key = f"projects/{project_id}/manifest.json"
            try:
                storage.upload_file(manifest_path, s3_key, content_type="application/json")
            except Exception:
                pass
            
            # Also upload individual json metadata files if present
            for fname in ["project.json", "segments.json", "prompts.json", "analysis.json"]:
                fpath = project_dir / fname
                if fpath.exists():
                    try:
                        storage.upload_file(fpath, f"projects/{project_id}/{fname}", content_type="application/json")
                    except Exception:
                        pass
            
            # Also upload job status files
            jobs_dir = project_dir / "jobs"
            if jobs_dir.exists():
                for jpath in jobs_dir.glob("*.json"):
                    try:
                        storage.upload_file(jpath, f"projects/{project_id}/jobs/{jpath.name}", content_type="application/json")
                    except Exception:
                        pass
        return manifest

    def load_manifest_from_storage(self, project_id: str, target_dir: Path | None = None, force_refresh: bool = False) -> dict[str, Any]:
        """Load manifest from S3/R2 or local storage and populate project files in target_dir."""
        import json
        base_dir = Path(target_dir) if target_dir else (self.data_dir / project_id)
        base_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = base_dir / "manifest.json"

        if settings.storage_backend == "s3" and (force_refresh or not manifest_file.exists()):
            from .file_storage import FileStorage
            storage = FileStorage(self.data_dir)
            try:
                storage.download_file(f"projects/{project_id}/manifest.json", manifest_file)
            except Exception:
                try:
                    storage.download_file(f"{project_id}/manifest.json", manifest_file)
                except Exception:
                    pass

        if not manifest_file.exists():
            if (base_dir / "project.json").exists():
                return self.export_manifest(project_id)
            raise FileNotFoundError(f"Manifest not found for project {project_id}")

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

        repo = JsonRepository(base_dir)
        if manifest.get("project") and (force_refresh or not repo.exists("project.json")):
            repo.save("project.json", manifest["project"])
        if manifest.get("segments") is not None and (force_refresh or not repo.exists("segments.json")):
            repo.save("segments.json", manifest["segments"])
        if manifest.get("prompts") is not None and (force_refresh or not repo.exists("prompts.json")):
            repo.save("prompts.json", manifest["prompts"])
        if manifest.get("analysis") is not None and (force_refresh or not repo.exists("analysis.json")):
            repo.save("analysis.json", manifest["analysis"])
        if manifest.get("jobs") and isinstance(manifest["jobs"], dict):
            jobs_dir = base_dir / "jobs"
            jobs_dir.mkdir(parents=True, exist_ok=True)
            jrepo = JsonRepository(jobs_dir)
            for jname, jdata in manifest["jobs"].items():
                if force_refresh or not jrepo.exists(f"{jname}.json"):
                    jrepo.save(f"{jname}.json", jdata)

        return manifest
