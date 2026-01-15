from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from .storage import DATA_DIR, load_json, update_job, update_project, write_json


def run_pipeline(project_id: str) -> None:
    update_job(project_id, "pipeline", {"status": "RUNNING", "step": "analysis"})
    analysis = _analyze_audio(project_id)
    update_job(project_id, "pipeline", {"status": "RUNNING", "step": "segments"})
    segments = _build_segments(project_id, analysis)
    update_job(project_id, "pipeline", {"status": "RUNNING", "step": "prompts"})
    prompts = _create_prompts(project_id, segments)
    update_job(project_id, "pipeline", {"status": "RUNNING", "step": "images"})
    _generate_images(project_id, prompts)
    update_job(project_id, "pipeline", {"status": "RUNNING", "step": "render"})
    _render_video(project_id)
    update_job(project_id, "pipeline", {"status": "DONE", "step": "complete"})
    update_project(project_id, {"status": "DONE"})


def _project_dir(project_id: str) -> Path:
    return DATA_DIR / project_id


def _analyze_audio(project_id: str) -> dict[str, Any]:
    analysis = {
        "transcript": "(demo transcript)",
        "mood": "uplifting",
        "energy": "medium",
    }
    write_json(_project_dir(project_id) / "analysis.json", analysis)
    return analysis


def _build_segments(project_id: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    segments = []
    start_ms = 0
    for index in range(3):
        end_ms = start_ms + 15000
        segments.append(
            {
                "id": f"seg_{index + 1:03d}",
                "start_ms": start_ms,
                "end_ms": end_ms,
                "lyric_text": f"Line {index + 1}",
                "visual_intent": f"Visual idea {index + 1}",
                "mood": analysis.get("mood", "neutral"),
            }
        )
        start_ms = end_ms
    write_json(_project_dir(project_id) / "segments.json", segments)
    return segments


def _create_prompts(project_id: str, segments: list[dict[str, Any]]) -> dict[str, Any]:
    prompts: dict[str, Any] = {}
    for segment in segments:
        prompts[segment["id"]] = {
            "version": 1,
            "image_prompt": f"{segment['visual_intent']} in cinematic style",
            "negative_prompt": "blurry, low quality",
            "style_hints": "soft lighting",
        }
    write_json(_project_dir(project_id) / "prompts.json", prompts)
    return prompts


def _generate_images(project_id: str, prompts: dict[str, Any]) -> None:
    images_dir = _project_dir(project_id) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    for seg_id, payload in prompts.items():
        version = payload.get("version", 1)
        filename = images_dir / f"{seg_id}_v{version}.png"
        seed = random.randint(1000, 9999)
        filename.write_bytes(
            f"Placeholder image for {seg_id} v{version} seed {seed}".encode("utf-8")
        )


def _render_video(project_id: str) -> Path:
    renders_dir = _project_dir(project_id) / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(renders_dir.glob("final_v*.mp4"))
    next_version = len(existing) + 1
    output = renders_dir / f"final_v{next_version}.mp4"
    output.write_bytes(b"Placeholder MP4 content")
    return output


def regenerate_segment(project_id: str, seg_id: str) -> dict[str, Any]:
    prompts_path = _project_dir(project_id) / "prompts.json"
    prompts = load_json(prompts_path, {})
    current = prompts.get(seg_id)
    if not current:
        raise KeyError("Segment prompt not found")
    current_version = int(current.get("version", 1))
    current["version"] = current_version + 1
    prompts[seg_id] = current
    write_json(prompts_path, prompts)
    _generate_images(project_id, {seg_id: current})
    update_job(
        project_id,
        "pipeline",
        {
            "status": "RUNNING",
            "step": "regenerate",
            "message": f"Regenerated {seg_id} v{current['version']}",
        },
    )
    return current


def render_only(project_id: str) -> Path:
    update_job(project_id, "render", {"status": "RUNNING", "step": "render"})
    output = _render_video(project_id)
    update_job(
        project_id,
        "render",
        {"status": "DONE", "step": "complete", "output": str(output)},
    )
    update_project(project_id, {"status": "DONE"})
    return output
