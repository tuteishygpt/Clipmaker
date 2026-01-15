from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .genai_client import GenAIClient
from .storage import DATA_DIR, load_json, update_job, update_project, write_json


@dataclass
class PipelineContext:
    project_id: str
    project_dir: Path
    genai: GenAIClient


class AudioAnalysisService:
    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        analysis = ctx.genai.analyze_audio(ctx.project_dir / "source")
        write_json(ctx.project_dir / "analysis.json", analysis)
        return analysis


class StoryboardService:
    def run(self, ctx: PipelineContext, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        segments = ctx.genai.build_storyboard(analysis)
        write_json(ctx.project_dir / "segments.json", segments)
        return segments


class PromptFactory:
    def run(self, ctx: PipelineContext, segments: list[dict[str, Any]]) -> dict[str, Any]:
        prompts = ctx.genai.build_prompts(segments)
        write_json(ctx.project_dir / "prompts.json", prompts)
        return prompts


class ImageGenerationService:
    def run(self, ctx: PipelineContext, prompts: dict[str, Any]) -> None:
        images_dir = ctx.project_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        for seg_id, payload in prompts.items():
            version = payload.get("version", 1)
            filename = images_dir / f"{seg_id}_v{version}.png"
            image_bytes = ctx.genai.generate_image(payload)
            filename.write_bytes(image_bytes)


class RenderService:
    def run(self, ctx: PipelineContext) -> Path:
        renders_dir = ctx.project_dir / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(renders_dir.glob("final_v*.mp4"))
        next_version = len(existing) + 1
        output = renders_dir / f"final_v{next_version}.mp4"
        output.write_bytes(b"Placeholder MP4 content")
        return output


class PipelineOrchestrator:
    def __init__(self, ctx: PipelineContext) -> None:
        self.ctx = ctx
        self.analysis_service = AudioAnalysisService()
        self.storyboard_service = StoryboardService()
        self.prompt_factory = PromptFactory()
        self.image_generation_service = ImageGenerationService()
        self.render_service = RenderService()

    def run(self) -> None:
        analysis = self._run_step("analysis", lambda: self.analysis_service.run(self.ctx))
        segments = self._run_step("segments", lambda: self.storyboard_service.run(self.ctx, analysis))
        prompts = self._run_step("prompts", lambda: self.prompt_factory.run(self.ctx, segments))
        self._run_step("images", lambda: self.image_generation_service.run(self.ctx, prompts))
        self._run_step("render", lambda: self.render_service.run(self.ctx))
        update_job(self.ctx.project_id, "pipeline", {"status": "DONE", "step": "complete"})
        update_project(self.ctx.project_id, {"status": "DONE"})

    def _run_step(self, step: str, action: Callable[[], Any], attempts: int = 2) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            update_job(
                self.ctx.project_id,
                "pipeline",
                {"status": "RUNNING", "step": step, "attempt": attempt},
            )
            try:
                return action()
            except Exception as exc:  # noqa: BLE001 - keep pipeline alive in MVP
                last_error = exc
                update_job(
                    self.ctx.project_id,
                    "pipeline",
                    {
                        "status": "RETRYING",
                        "step": step,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
        update_job(
            self.ctx.project_id,
            "pipeline",
            {"status": "FAILED", "step": step, "error": str(last_error)},
        )
        update_project(self.ctx.project_id, {"status": "FAILED"})
        raise last_error or RuntimeError(f"Pipeline step failed: {step}")


def run_pipeline(project_id: str) -> None:
    ctx = PipelineContext(
        project_id=project_id,
        project_dir=_project_dir(project_id),
        genai=GenAIClient.from_env(),
    )
    PipelineOrchestrator(ctx).run()


def _project_dir(project_id: str) -> Path:
    return DATA_DIR / project_id


def regenerate_segment(project_id: str, seg_id: str) -> dict[str, Any]:
    ctx = PipelineContext(
        project_id=project_id,
        project_dir=_project_dir(project_id),
        genai=GenAIClient.from_env(),
    )
    prompts_path = ctx.project_dir / "prompts.json"
    prompts = load_json(prompts_path, {})
    current = prompts.get(seg_id)
    if not current:
        raise KeyError("Segment prompt not found")
    current_version = int(current.get("version", 1))
    current["version"] = current_version + 1
    prompts[seg_id] = current
    write_json(prompts_path, prompts)
    ImageGenerationService().run(ctx, {seg_id: current})
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
    ctx = PipelineContext(
        project_id=project_id,
        project_dir=_project_dir(project_id),
        genai=GenAIClient.from_env(),
    )
    update_job(project_id, "render", {"status": "RUNNING", "step": "render"})
    output = RenderService().run(ctx)
    update_job(
        project_id,
        "render",
        {"status": "DONE", "step": "complete", "output": str(output)},
    )
    update_project(project_id, {"status": "DONE"})
    return output
