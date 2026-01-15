from __future__ import annotations

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

import shutil
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .pipeline import regenerate_segment, render_only, run_pipeline
from .schemas import ProjectCreate, ProjectResponse, RunResponse, SegmentUpdate
from .storage import (
    DATA_DIR,
    create_project,
    ensure_project_dirs,
    load_json,
    project_exists,
    update_job,
    update_project,
    write_json,
    list_projects,
)

app = FastAPI(title="Clipmaker MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.get("/projects", response_model=list[ProjectResponse])
async def list_projects_endpoint() -> list[dict[str, Any]]:
    return list_projects()


@app.post("/projects", response_model=ProjectResponse)
async def create_project_endpoint(payload: ProjectCreate) -> dict[str, Any]:
    return create_project(payload.model_dump())


@app.post("/projects/{project_id}/upload", response_model=RunResponse)
async def upload_audio(project_id: str, audio: UploadFile = File(...)) -> RunResponse:
    if not project_exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    paths = ensure_project_dirs(project_id)
    extension = Path(audio.filename or "track.wav").suffix or ".wav"
    target = paths["source"] / f"track{extension}"
    with target.open("wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
    update_project(project_id, {"status": "UPLOADED"})
    return RunResponse(status="OK", message="Audio uploaded")


@app.post("/projects/{project_id}/run", response_model=RunResponse)
async def run_project(project_id: str, background: BackgroundTasks) -> RunResponse:
    if not project_exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    update_project(project_id, {"status": "RUNNING"})
    update_job(project_id, "pipeline", {"status": "RUNNING", "step": "queued"})
    background.add_task(run_pipeline, project_id)
    return RunResponse(status="OK", message="Pipeline started")


@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> dict[str, Any]:
    project_path = DATA_DIR / project_id / "project.json"
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    return load_json(project_path, {})


@app.get("/projects/{project_id}/audio")
async def get_project_audio(project_id: str) -> FileResponse:
    source_dir = DATA_DIR / project_id / "source"
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    # Find any file starting with track.
    for file_path in source_dir.glob("track.*"):
        media_type = "audio/wav"
        if file_path.suffix == ".mp3":
            media_type = "audio/mpeg"
        # Add other types if necessary
        return FileResponse(file_path, media_type=media_type)
    raise HTTPException(status_code=404, detail="Audio not found")


@app.get("/projects/{project_id}/segments")
async def get_segments(project_id: str) -> dict[str, Any]:
    segments_path = DATA_DIR / project_id / "segments.json"
    prompts_path = DATA_DIR / project_id / "prompts.json"
    if not segments_path.exists():
        raise HTTPException(status_code=404, detail="Segments not ready")
    
    segments = load_json(segments_path, [])
    # If segments is just a dict with raw data (old format), try to fix it or return empty
    if isinstance(segments, list) and len(segments) == 1 and "raw" in segments[0]:
        # This is the corrupted case we saw
        logging.warning("Project %s has malformed segments.json", project_id)
        # We could try to re-parse it here, but it's better to just return what we can
        # For now, let's treat it as empty to avoid crash
        return {"segments": []}

    prompts = load_json(prompts_path, {})
    enriched = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        seg_id = segment.get("id")
        if not seg_id:
            # Try to use segment_id if present
            seg_id = segment.get("segment_id")
            if seg_id:
                segment["id"] = str(seg_id)
                seg_id = str(seg_id)
            else:
                continue
        
        prompt = prompts.get(seg_id, {})
        version = prompt.get("version", 1)
        segment["thumbnail"] = f"/projects/{project_id}/images/{seg_id}_v{version}.png"
        segment["prompt"] = prompt
        enriched.append(segment)
    return {"segments": enriched}


@app.patch("/projects/{project_id}/segments/{seg_id}")
async def update_segment(project_id: str, seg_id: str, payload: SegmentUpdate) -> dict[str, Any]:
    segments_path = DATA_DIR / project_id / "segments.json"
    prompts_path = DATA_DIR / project_id / "prompts.json"
    segments = load_json(segments_path, [])
    prompts = load_json(prompts_path, {})
    if not segments:
        raise HTTPException(status_code=404, detail="Segments not found")
    updated_segment = None
    for segment in segments:
        if segment["id"] == seg_id:
            if payload.visual_intent is not None:
                segment["visual_intent"] = payload.visual_intent
            updated_segment = segment
            break
    if updated_segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    prompt = prompts.get(seg_id, {"version": 1})
    if payload.image_prompt is not None:
        prompt["image_prompt"] = payload.image_prompt
    if payload.negative_prompt is not None:
        prompt["negative_prompt"] = payload.negative_prompt
    if payload.style_hints is not None:
        prompt["style_hints"] = payload.style_hints
    prompts[seg_id] = prompt
    write_json(segments_path, segments)
    write_json(prompts_path, prompts)
    return {"segment": updated_segment, "prompt": prompt}


@app.post("/projects/{project_id}/segments/{seg_id}/regenerate")
async def regenerate_scene(project_id: str, seg_id: str) -> dict[str, Any]:
    try:
        prompt = regenerate_segment(project_id, seg_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Segment not found")
    return {"segment_id": seg_id, "prompt": prompt}


@app.post("/projects/{project_id}/render", response_model=RunResponse)
async def render_project(project_id: str, background: BackgroundTasks) -> RunResponse:
    if not project_exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    background.add_task(render_only, project_id)
    return RunResponse(status="OK", message="Render started")


@app.get("/projects/{project_id}/jobs")
async def get_jobs(project_id: str) -> dict[str, Any]:
    jobs_dir = DATA_DIR / project_id / "jobs"
    if not jobs_dir.exists():
        raise HTTPException(status_code=404, detail="Jobs not found")
    jobs = {}
    for job_file in jobs_dir.glob("*.json"):
        jobs[job_file.stem] = load_json(job_file, {})
    return {"jobs": jobs}


@app.get("/projects/{project_id}/images/{image_name}")
async def get_image(project_id: str, image_name: str) -> FileResponse:
    image_path = DATA_DIR / project_id / "images" / image_name
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)


@app.get("/projects/{project_id}/renders/{render_name}")
async def get_render(project_id: str, render_name: str) -> FileResponse:
    render_path = DATA_DIR / project_id / "renders" / render_name
    if not render_path.exists():
        raise HTTPException(status_code=404, detail="Render not found")
    return FileResponse(render_path)
