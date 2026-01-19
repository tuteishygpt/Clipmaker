"""Video rendering service."""
from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any, Callable

from ..repositories.project_repo import ProjectRepository
from ..repositories.file_storage import FileStorage
from ..core.logging import get_logger

logger = get_logger(__name__)


def _parse_time(t_str: Any) -> float:
    """Parse time string or number to float seconds."""
    if not t_str:
        return 0.0
    if isinstance(t_str, (int, float)):
        return float(t_str)
    
    t_str = str(t_str).replace(",", ".").strip()
    parts = t_str.split(":")
    
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except ValueError:
        pass
    
    return 0.0


class RenderService:
    """Service for rendering final video."""
    
    def __init__(
        self,
        project_repo: ProjectRepository | None = None,
        file_storage: FileStorage | None = None,
    ) -> None:
        self.project_repo = project_repo or ProjectRepository()
        self.file_storage = file_storage or FileStorage()
    
    def render(
        self,
        project_id: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> tuple[Path, float]:
        """Render video for a project. Returns (output_path, render_duration_seconds)."""
        start_time = time.time()
        self._ensure_pil_compatibility()
        
        import moviepy.editor as mp
        
        try:
            from proglog import ProgressBarLogger
            class MoviePyProgressLogger(ProgressBarLogger):
                def __init__(self, cb):
                    super().__init__()
                    self.cb = cb
                    self.last_pct = -1
                def callback(self, **changes):
                    bars = self.state.get('bars', {})
                    if not bars: return
                    # Prioritize 't' bar (main rendering bar)
                    main_bar = bars.get('t') or next(iter(bars.values()), None)
                    if main_bar and main_bar.get('total'):
                        pct = min(int(100 * main_bar['index'] / main_bar['total']), 100)
                        if pct != self.last_pct:
                            self.cb(pct)
                            self.last_pct = pct
            
            logger_obj = MoviePyProgressLogger(progress_callback) if progress_callback else None
        except (ImportError, Exception):
            logger_obj = None

        # Load data
        segments = self.project_repo.get_segments(project_id)
        prompts = self.project_repo.get_prompts(project_id)
        project = self.project_repo.get(project_id) or {}
        
        # Prepare audio
        audio_path = self.file_storage.get_audio_path(project_id)
        if not audio_path:
            raise FileNotFoundError("Audio track not found")
        
        audio_clip = None
        clips = []
        video = None
        
        try:
            audio_clip = mp.AudioFileClip(str(audio_path))
            
            # Create clips
            clips = self._create_clips(
                project_id, segments, prompts, project, mp
            )
            
            if not clips:
                raise ValueError("No valid image segments found to render. This usually means image generation failed. Check logs for details.")
            
            video = mp.concatenate_videoclips(clips, method="compose")
            video.audio = audio_clip
            
            # Render
            output_path = self.file_storage.get_next_render_path(project_id)
            
            # Get render preset from project settings
            render_preset = project.get("render_preset", "fast")
            if render_preset not in ("fast", "veryfast", "ultrafast"):
                render_preset = "fast"
            
            video.write_videofile(
                str(output_path),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                logger=logger_obj,
                threads=4,
                preset=render_preset,
            )
            
            render_duration = time.time() - start_time
            return output_path, render_duration
        
        finally:
            self._cleanup(video, audio_clip, clips)
    
    def _ensure_pil_compatibility(self) -> None:
        """Ensure PIL compatibility with moviepy."""
        import PIL.Image
        if not hasattr(PIL.Image, 'ANTIALIAS'):
            PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
    
    def _create_clips(
        self,
        project_id: str,
        segments: list[dict[str, Any]],
        prompts: dict[str, Any],
        project: dict[str, Any],
        mp,
    ) -> list:
        """Create video clips from segments."""
        fmt = project.get("format", "9:16")
        size = (720, 1280) if fmt == "9:16" else (1280, 720)
        
        clips = []
        
        for seg in segments:
            seg_id = seg.get("id")
            if not seg_id:
                continue
            
            prompt = prompts.get(seg_id, {})
            version = prompt.get("version", 1)
            
            img_path = self.file_storage.get_image_path(
                project_id, f"{seg_id}_v{version}.png"
            )
            if not img_path:
                logger.warning(f"Missing image for segment {seg_id} (version {version})")
                continue
            
            start_s = _parse_time(seg.get("start_time", 0))
            end_s = _parse_time(seg.get("end_time", 0))
            duration = end_s - start_s
            
            if duration <= 0:
                continue
            
            effect = seg.get("effect") or "random"
            if effect == "random":
                effect = random.choice([
                    "zoom_in", "zoom_out", "pan_left",
                    "pan_right", "pan_up", "pan_down"
                ])
            
            clip = self._apply_effect(img_path, duration, effect, size, mp)
            clips.append(clip)
        
        return clips
    
    def _apply_effect(
        self,
        img_path: Path,
        duration: float,
        effect: str,
        target_size: tuple[int, int],
        mp,
    ):
        """Apply Ken Burns effect to an image."""
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            return mp.ImageClip(str(img_path)).resize(target_size).set_duration(duration)
        
        pil_img = Image.open(img_path).convert("RGB")
        w, h = pil_img.size
        img_arr = np.array(pil_img)
        
        tw, th = target_size
        
        # Calculate maximum possible crop that matches target AR
        if (w / h) > (tw / th):
            max_crop_h = h
            max_crop_w = h * (tw / th)
        else:
            max_crop_w = w
            max_crop_h = w * (th / tw)
        
        zoom_level = 0.85
        has_pan_room_x = w > (max_crop_w * 1.05)
        has_pan_room_y = h > (max_crop_h * 1.05)
        
        def make_frame(t):
            p = t / duration
            
            scale = 1.0
            cx, cy = w / 2, h / 2
            
            if effect == "zoom_in":
                scale = 1.0 - (1.0 - zoom_level) * p
            elif effect == "zoom_out":
                scale = zoom_level + (1.0 - zoom_level) * p
            elif effect in ["pan_left", "pan_right"]:
                scale = 1.0 if has_pan_room_x else zoom_level
                cw = max_crop_w * scale
                min_cx = cw / 2
                max_cx = w - cw / 2
                
                if effect == "pan_left":
                    cx = max_cx - (max_cx - min_cx) * p
                else:
                    cx = min_cx + (max_cx - min_cx) * p
            elif effect in ["pan_up", "pan_down"]:
                scale = 1.0 if has_pan_room_y else zoom_level
                ch = max_crop_h * scale
                min_cy = ch / 2
                max_cy = h - ch / 2
                
                if effect == "pan_up":
                    cy = max_cy - (max_cy - min_cy) * p
                else:
                    cy = min_cy + (max_cy - min_cy) * p
            
            final_w = max_crop_w * scale
            final_h = max_crop_h * scale
            
            x1 = max(0, int(cx - final_w / 2))
            y1 = max(0, int(cy - final_h / 2))
            x2 = min(w, x1 + int(final_w))
            y2 = min(h, y1 + int(final_h))
            
            if x2 <= x1 or y2 <= y1:
                aux = Image.fromarray(img_arr).resize((tw, th), Image.BICUBIC)
                return np.array(aux)
            
            part = img_arr[y1:y2, x1:x2]
            part_img = Image.fromarray(part)
            resized = part_img.resize((tw, th), Image.BICUBIC)
            return np.array(resized)
        
        return mp.VideoClip(make_frame, duration=duration)
    
    def _cleanup(self, video, audio_clip, clips) -> None:
        """Clean up moviepy resources."""
        try:
            if video:
                video.close()
            if audio_clip:
                audio_clip.close()
            for c in clips:
                c.close()
        except Exception:
            pass
