from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "projects"


def ensure_project_dirs(project_id: str) -> dict[str, Path]:
    project_dir = DATA_DIR / project_id
    source_dir = project_dir / "source"
    images_dir = project_dir / "images"
    renders_dir = project_dir / "renders"
    jobs_dir = project_dir / "jobs"
    for folder in (project_dir, source_dir, images_dir, renders_dir, jobs_dir):
        folder.mkdir(parents=True, exist_ok=True)
    return {
        "project": project_dir,
        "source": source_dir,
        "images": images_dir,
        "renders": renders_dir,
        "jobs": jobs_dir,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    project_id = uuid.uuid4().hex
    paths = ensure_project_dirs(project_id)
    project_data = {
        "id": project_id,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "status": "NEW",
        "format": payload.get("format", "9:16"),
        "style": payload.get("style", "cinematic"),
        "subtitles": payload.get("subtitles", True),
    }
    write_json(paths["project"] / "project.json", project_data)
    return project_data


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def update_project(project_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    paths = ensure_project_dirs(project_id)
    project_path = paths["project"] / "project.json"
    project_data = load_json(project_path, {})
    project_data.update(updates)
    project_data["updated_at"] = _utc_now()
    write_json(project_path, project_data)
    return project_data


def project_exists(project_id: str) -> bool:
    return (DATA_DIR / project_id / "project.json").exists()


def job_path(project_id: str, job_name: str) -> Path:
    return DATA_DIR / project_id / "jobs" / f"{job_name}.json"


def update_job(project_id: str, job_name: str, updates: dict[str, Any]) -> dict[str, Any]:
    path = job_path(project_id, job_name)
    job_data = load_json(path, {"status": "PENDING"})
    job_data.update(updates)
    job_data["updated_at"] = _utc_now()
    write_json(path, job_data)
    return job_data
