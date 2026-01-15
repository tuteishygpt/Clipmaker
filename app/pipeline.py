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
    def run(self, ctx: PipelineContext, prompts: dict[str, Any], progress_base: int = 0, progress_weight: int = 0) -> None:
        images_dir = ctx.project_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        total = len(prompts)
        for i, (seg_id, payload) in enumerate(prompts.items()):
            if progress_weight > 0:
                progress = progress_base + int((i / total) * progress_weight)
                update_job(ctx.project_id, "pipeline", {"progress": progress})
            
            version = payload.get("version", 1)
            filename = images_dir / f"{seg_id}_v{version}.png"
            image_bytes = ctx.genai.generate_image(payload)
            filename.write_bytes(image_bytes)
        
        if progress_weight > 0:
            update_job(ctx.project_id, "pipeline", {"progress": progress_base + progress_weight})


class RenderService:
    def run(self, ctx: PipelineContext, job_name: str = "render", progress_base: int = 0, progress_weight: int = 100) -> Path:
        import PIL.Image
        if not hasattr(PIL.Image, 'ANTIALIAS'):
            PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
            
        import moviepy.editor as mp
        
        logger = None
        try:
            from proglog import TqdmProgressBarLogger

            class MoviepyProgressLogger(TqdmProgressBarLogger):
                def __init__(self, project_id, job_name, base, weight):
                    super().__init__()
                    self.project_id = project_id
                    self.job_name = job_name
                    self.base = base
                    self.weight = weight

                def callback(self, **kwargs):
                    try:
                        best_progress = 0
                        for bar in self.bars.values():
                            if bar.get('total'):
                                p = int((bar['index'] / bar['total']) * 100)
                                if p > best_progress:
                                    best_progress = p
                        
                        if best_progress > 0:
                            actual_progress = self.base + int((best_progress / 100) * self.weight)
                            update_job(self.project_id, self.job_name, {"progress": actual_progress})
                    except Exception:
                        pass

            logger = MoviepyProgressLogger(ctx.project_id, job_name, progress_base, progress_weight)
        except ImportError:
            print("Warning: proglog not found, progress bar will not be updated")
        
        renders_dir = ctx.project_dir / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)
        
        segments = load_json(ctx.project_dir / "segments.json", [])
        prompts = load_json(ctx.project_dir / "prompts.json", {})
        project_info = load_json(ctx.project_dir / "project.json", {})
        
        # Audio file
        source_dir = ctx.project_dir / "source"
        audio_files = list(source_dir.glob("track.*"))
        
        audio_path = next(iter(audio_files), None)
        if not audio_path:
            raise FileNotFoundError(f"Audio track ('track.*') not found in {source_dir}. Please upload audio first.")
            
        audio_clip = mp.AudioFileClip(str(audio_path))
        
        # Determine format (9:16 or 16:9)
        fmt = project_info.get("format", "9:16")
        if fmt == "9:16":
            size = (720, 1280)
        else:
            size = (1280, 720)
            
        clips = []
        images_dir = ctx.project_dir / "images"
        
        def parse_time(t_str: str) -> float:
            if not t_str: return 0.0
            parts = t_str.split(":")
            if len(parts) == 2: # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3: # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return float(t_str)

        for seg in segments:
            seg_id = seg.get("id")
            if not seg_id: continue
            
            prompt = prompts.get(seg_id, {})
            version = prompt.get("version", 1)
            img_path = images_dir / f"{seg_id}_v{version}.png"
            
            if not img_path.exists():
                continue
                
            start_s = parse_time(seg.get("start_time", "00:00"))
            end_s = parse_time(seg.get("end_time", "00:00"))
            duration = end_s - start_s
            if duration <= 0:
                continue
                
            clip = mp.ImageClip(str(img_path)).set_duration(duration).resize(size)
            clips.append(clip)
            
        if not clips:
            raise ValueError("No valid image segments found to render")
            
        video = mp.concatenate_videoclips(clips, method="compose")
        video.audio = audio_clip
        
        existing = sorted(renders_dir.glob("final_v*.mp4"))
        next_version = len(existing) + 1
        output = renders_dir / f"final_v{next_version}.mp4"
        
        video.write_videofile(
            str(output), 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            logger=logger
        )
        
        # Close clips to free resources
        video.close()
        audio_clip.close()
        for c in clips:
            c.close()
            
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
        update_job(self.ctx.project_id, "pipeline", {"status": "RUNNING", "step": "analysis", "progress": 5})
        analysis = self._run_step("analysis", lambda: self.analysis_service.run(self.ctx))
        
        update_job(self.ctx.project_id, "pipeline", {"status": "RUNNING", "step": "segments", "progress": 15})
        segments = self._run_step("segments", lambda: self.storyboard_service.run(self.ctx, analysis))
        
        update_job(self.ctx.project_id, "pipeline", {"status": "RUNNING", "step": "prompts", "progress": 25})
        prompts = self._run_step("prompts", lambda: self.prompt_factory.run(self.ctx, segments))
        
        self._run_step("images", lambda: self.image_generation_service.run(self.ctx, prompts, progress_base=30, progress_weight=40))
        self._run_step("render", lambda: self.render_service.run(self.ctx, job_name="pipeline", progress_base=70, progress_weight=30))
        
        update_job(self.ctx.project_id, "pipeline", {"status": "DONE", "step": "complete", "progress": 100})
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
    try:
        ctx = PipelineContext(
            project_id=project_id,
            project_dir=_project_dir(project_id),
            genai=GenAIClient.from_env(),
        )
        update_job(project_id, "render", {"status": "RUNNING", "step": "render", "progress": 0})
        output = RenderService().run(ctx, job_name="render", progress_base=0, progress_weight=100)
        update_job(
            project_id,
            "render",
            {"status": "DONE", "step": "complete", "output": str(output), "progress": 100},
        )
        update_project(project_id, {"status": "DONE"})
        return output
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"Render failed: {error_msg}")
        update_job(project_id, "render", {"status": "FAILED", "error": error_msg})
        update_project(project_id, {"status": "FAILED"})
        raise
