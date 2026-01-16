from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import random

from .genai_client import GenAIClient
from .storage import DATA_DIR, load_json, update_job, update_project, write_json


@dataclass
class PipelineContext:
    project_id: str
    project_dir: Path
    genai: GenAIClient



def _get_audio_info(project_dir: Path) -> dict[str, Any]:
    import moviepy.editor as mp
    source_dir = project_dir / "source"
    audio_files = list(source_dir.glob("track.*"))
    audio_path = next(iter(audio_files), None)
    if not audio_path:
        return {"duration": 0.0, "path": None}
    
    # We use a temporary clip to get duration
    clip = mp.AudioFileClip(str(audio_path))
    duration = clip.duration
    clip.close()
    return {"duration": duration, "path": audio_path}


def _analyze_audio_technical(audio_path: Path) -> dict[str, Any]:
    try:
        import librosa
        import numpy as np
    except ImportError:
        print("Warning: librosa or numpy not found. Skipping technical analysis.")
        return {}
    
    try:
        y, sr = librosa.load(str(audio_path), sr=None)
        
        # Tempo and Beats
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        # Energy / Volume (RMS)
        hop_length = 512
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
        
        # Simple stats
        avg_energy = float(np.mean(rms))
        max_energy = float(np.max(rms))
        
        return {
            "bpm": float(tempo),
            "beat_times": beat_times.tolist(),
            "energy_stats": {
                "avg": avg_energy,
                "max": max_energy
            }
        }
    except Exception as e:
        print(f"Technical analysis failed: {e}")
        return {}


class AudioAnalysisService:
    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        audio_info = _get_audio_info(ctx.project_dir)
        audio_path = audio_info.get("path")
        
        technical_analysis = {}
        if audio_path:
             technical_analysis = _analyze_audio_technical(audio_path)
             
        project_info = load_json(ctx.project_dir / "project.json", {})
        user_style = project_info.get("style", "cinematic")
        user_description = project_info.get("user_description", "")

        analysis = ctx.genai.analyze_audio(
            audio_path=audio_path, 
            duration=audio_info["duration"],
            technical_analysis=technical_analysis,
            user_style=user_style,
            user_description=user_description
        )
        
        analysis["total_duration"] = audio_info["duration"]
        # Merge technical stats into analysis for reference if needed
        analysis["technical_stats"] = technical_analysis
        
        write_json(ctx.project_dir / "analysis.json", analysis)
        return analysis


class StoryboardService:
    def run(self, ctx: PipelineContext, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        duration = analysis.get("total_duration", 0.0)
        segments = ctx.genai.build_storyboard(analysis, total_duration=duration)
        
        # Normalize segments to perfectly fit the duration
        if segments and duration > 0:
            total_suggested = 0.0
            for seg in segments:
                s = parse_time(seg.get("start_time", 0))
                e = parse_time(seg.get("end_time", 0))
                seg["_orig_duration"] = max(0.1, e - s)
                total_suggested += seg["_orig_duration"]
            
            # Scale durations to fit exactly
            current_time = 0.0
            for i, seg in enumerate(segments):
                # Calculate proportional duration
                weight = seg.pop("_orig_duration")
                if total_suggested > 0:
                    seg_duration = (weight / total_suggested) * duration
                else:
                    seg_duration = duration / len(segments)
                
                seg["start_time"] = current_time
                # For the last segment, ensure it hits the exact end
                if i == len(segments) - 1:
                    seg["end_time"] = duration
                else:
                    seg["end_time"] = current_time + seg_duration
                
                current_time = seg["end_time"]

        write_json(ctx.project_dir / "segments.json", segments)
        return segments


class PromptFactory:
    def run(self, ctx: PipelineContext, segments: list[dict[str, Any]], analysis: dict[str, Any]) -> dict[str, Any]:
        prompts = ctx.genai.build_prompts(segments, analysis)
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


try:
    from proglog import TqdmProgressBarLogger
except ImportError:
    TqdmProgressBarLogger = object

class MoviepyProgressLogger(TqdmProgressBarLogger):
    def __init__(self, project_id: str, job_name: str, base: int, weight: int):
        if TqdmProgressBarLogger is not object:
            super().__init__()
        self.project_id = project_id
        self.job_name = job_name
        self.base = base
        self.weight = weight
        self.is_video_phase = False

    def message(self, message):
        if TqdmProgressBarLogger is not object:
            super().message(message)
        if "Writing video" in message:
            self.is_video_phase = True
        elif "Writing audio" in message:
            self.is_video_phase = False

    def callback(self, **kwargs):
        if TqdmProgressBarLogger is object:
            return
        
        if not self.is_video_phase:
             return

        try:
            best_p = 0
            if hasattr(self, 'bars'):
                for bar in self.bars.values():
                    if bar.get("total"):
                        p = (bar["index"] / bar["total"]) * 100
                        if p > best_p:
                            best_p = p
            
            if best_p > 0:
                clamped_p = min(best_p, 99)
                actual_progress = self.base + int((clamped_p / 100) * self.weight)
                update_job(self.project_id, self.job_name, {"progress": actual_progress})
        except Exception:
            pass

def parse_time(t_str: Any) -> float:
    if not t_str: return 0.0
    if isinstance(t_str, (int, float)): return float(t_str)
    
    t_str = str(t_str).replace(",", ".").strip()
    parts = t_str.split(":")
    try:
        if len(parts) == 1: # seconds
            return float(parts[0])
        if len(parts) == 2: # MM:SS
            return float(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3: # HH:MM:SS
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except ValueError:
        pass
    return 0.0


class RenderService:
    def run(self, ctx: PipelineContext, job_name: str = "render", progress_base: int = 0, progress_weight: int = 100) -> Path:
        self._ensure_pil_compatibility()
        
        logger = self._get_logger(ctx.project_id, job_name, progress_base, progress_weight)
        
        # Load data
        segments, prompts, project_info = self._load_project_data(ctx)
        
        # Prepare audio
        import moviepy.editor as mp
        audio_clip = None
        clips = []
        video = None
        
        try:
            audio_clip = self._prepare_audio(ctx.project_dir, mp)
            
            # Sync segments with audio duration for extra safety
            clips = self._create_clips(ctx, segments, prompts, project_info, mp)
            
            video = mp.concatenate_videoclips(clips, method="compose")
            video.audio = audio_clip
            
            output_path = self._render_file(ctx.project_dir, video, logger)
            return output_path
        
        finally:
            self._cleanup(video, audio_clip, clips)

    def _ensure_pil_compatibility(self):
        import PIL.Image
        if not hasattr(PIL.Image, 'ANTIALIAS'):
            PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

    def _get_logger(self, project_id: str, job_name: str, base: int, weight: int):
        if TqdmProgressBarLogger is object:
            print("Warning: proglog not found, progress bar will not be updated")
            return None
        return MoviepyProgressLogger(project_id, job_name, base, weight)

    def _load_project_data(self, ctx: PipelineContext):
        segments = load_json(ctx.project_dir / "segments.json", [])
        prompts = load_json(ctx.project_dir / "prompts.json", {})
        project_info = load_json(ctx.project_dir / "project.json", {})
        return segments, prompts, project_info

    def _prepare_audio(self, project_dir: Path, mp):
        source_dir = project_dir / "source"
        audio_files = list(source_dir.glob("track.*"))
        
        audio_path = next(iter(audio_files), None)
        if not audio_path:
            raise FileNotFoundError(f"Audio track ('track.*') not found in {source_dir}. Please upload audio first.")
            
        return mp.AudioFileClip(str(audio_path))

    def _create_clips(self, ctx: PipelineContext, segments, prompts, project_info, mp):
        fmt = project_info.get("format", "9:16")
        size = (720, 1280) if fmt == "9:16" else (1280, 720)
        
        clips = []
        images_dir = ctx.project_dir / "images"
        
        for seg in segments:
            seg_id = seg.get("id")
            if not seg_id: continue
            
            prompt = prompts.get(seg_id, {})
            version = prompt.get("version", 1)
            img_path = images_dir / f"{seg_id}_v{version}.png"
            
            if not img_path.exists():
                continue
                
            start_s = parse_time(seg.get("start_time", 0))
            end_s = parse_time(seg.get("end_time", 0))
            duration = end_s - start_s
            if duration <= 0:
                continue
                
            effect = seg.get("effect") or "random"
            if effect == "random":
                effect = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"])
            
            clip = self._apply_effect(img_path, duration, effect, size, mp)
            clips.append(clip)
            
        if not clips:
            raise ValueError("No valid image segments found to render")
            
        return clips

    def _apply_effect(self, img_path: Path, duration: float, effect: str, target_size: tuple[int, int], mp):
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            # Fallback if libraries are missing, though they are heavily expected
            return mp.ImageClip(str(img_path)).resize(target_size).set_duration(duration)

        # Open image to get dimensions and raw data
        # We assume safe to open once as we will use array in closure
        pil_img = Image.open(img_path).convert("RGB")
        w, h = pil_img.size
        # Convert to numpy array once to avoid disk I/O per frame
        img_arr = np.array(pil_img)
        
        tw, th = target_size
        
        # Calculate maximum possible crop that matches target Aspect Ratio
        if (w / h) > (tw / th):
            # Image is wider than target
            max_crop_h = h
            max_crop_w = h * (tw / th)
        else:
            # Image is taller than target
            max_crop_w = w
            max_crop_h = w * (th / tw)
            
        zoom_level = 0.85 
        
        # Determine movement capability
        has_pan_room_x = w > (max_crop_w * 1.05)
        has_pan_room_y = h > (max_crop_h * 1.05)

        def make_frame(t):
            p = t / duration
            
            # Default: Static Centered (Scale 1.0 unless we want to force zoom)
            scale = 1.0
            cx, cy = w / 2, h / 2
            
            if effect == "zoom_in":
                # From Full to Zoomed
                scale = 1.0 - (1.0 - zoom_level) * p
            
            elif effect == "zoom_out":
                # From Zoomed to Full
                scale = zoom_level + (1.0 - zoom_level) * p
                
            elif effect in ["pan_left", "pan_right"]:
                scale = 1.0 if has_pan_room_x else zoom_level
                cw = max_crop_w * scale
                
                min_cx = cw / 2
                max_cx = w - cw / 2
                
                if effect == "pan_left":
                    # Start Right, End Left
                    cx = max_cx - (max_cx - min_cx) * p
                else:
                    # Start Left, End Right
                    cx = min_cx + (max_cx - min_cx) * p
                    
            elif effect in ["pan_up", "pan_down"]:
                scale = 1.0 if has_pan_room_y else zoom_level
                ch = max_crop_h * scale
                
                min_cy = ch / 2
                max_cy = h - ch / 2
                
                if effect == "pan_up":
                    # Start Bottom, End Top
                    cy = max_cy - (max_cy - min_cy) * p
                else: 
                     # Start Top, End Bottom
                    cy = min_cy + (max_cy - min_cy) * p
            
            # Final calculation
            final_w = max_crop_w * scale
            final_h = max_crop_h * scale
            
            # Calculate coordinates
            x1 = int(cx - final_w / 2)
            y1 = int(cy - final_h / 2)
            x2 = x1 + int(final_w)
            y2 = y1 + int(final_h)
            
            # Clamp to image boundaries
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)
            
            # Handle edge case where crop is invalid
            if x2 <= x1 or y2 <= y1:
                # Return static resized frame
                aux = Image.fromarray(img_arr).resize((tw, th), Image.LANCZOS)
                return np.array(aux)

            # Crop
            part = img_arr[y1:y2, x1:x2]
            
            # Resize
            # Creating Image from array is fast enough
            part_img = Image.fromarray(part)
            resized = part_img.resize((tw, th), Image.LANCZOS)
            return np.array(resized)

        # Create VideoClip directly
        return mp.VideoClip(make_frame, duration=duration)

    def _sync_audio_video(self, video, audio_clip, clips, mp):
        # This is now redundant as StoryboardService handles it, 
        # but we keep a simplified version just in case segments are manual
        if abs(audio_clip.duration - video.duration) > 0.1:
             return video.set_duration(audio_clip.duration)
        return video

    def _render_file(self, project_dir: Path, video, logger):
        renders_dir = project_dir / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)
        
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
        return output

    def _cleanup(self, video, audio_clip, clips):
        try:
            if video: video.close()
            if audio_clip: audio_clip.close()
            for c in clips:
                c.close()
        except Exception:
            pass


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
        prompts = self._run_step("prompts", lambda: self.prompt_factory.run(self.ctx, segments, analysis))
        
        self._run_step("images", lambda: self.image_generation_service.run(self.ctx, prompts, progress_base=30, progress_weight=40))
        video_output = self._run_step("render", lambda: self.render_service.run(self.ctx, job_name="pipeline", progress_base=70, progress_weight=30))
        
        update_job(self.ctx.project_id, "pipeline", {"status": "DONE", "step": "complete", "progress": 100, "output": str(video_output)})
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
            "status": "DONE",
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
