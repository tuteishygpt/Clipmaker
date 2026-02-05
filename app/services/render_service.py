"""Video rendering service."""
from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

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
            
            # Create clips (now returns the concatenated video)
            video = self._create_clips(
                project_id, segments, prompts, project, mp
            )
            
            # clips variable is no longer a list, but we keep the name for cleanup if needed? 
            # cleanup expects clips list. Let's adjust cleanup or just pass empty list if we can't track individual clips easily anymore.
            # actually _create_clips closes local clips? No.
            # We can't easily track intermediate clips for cleanup if _create_clips swallows them.
            # But moviepy objects are usually fine if we close the main video.
            clips = [] 
            
            # video = mp.concatenate_videoclips(clips, method="compose", padding=-0.5) 
            # Concatenation is now done inside _create_clips
            
            # Add subtitles overlay if enabled and available
            if project.get("subtitles", True):
                video = self._add_subtitles(video, project_id, mp)
            
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
                threads=0,
                preset=render_preset,
                ffmpeg_params=["-crf", "23"],
            )
            
            
            render_duration = time.time() - start_time
            return output_path, render_duration
        
        finally:
            self._cleanup(video, audio_clip, clips)
    
    def render_standalone_video(
        self,
        project_id: str,
        video_path: Path,
        progress_callback: Callable[[int], None] | None = None,
    ) -> tuple[Path, float]:
        """Render video with subtitles burned in (standalone mode)."""
        start_time = time.time()
        self._ensure_pil_compatibility()
        
        import moviepy.editor as mp
        
        logger.info(f"Starting standalone render for project {project_id}")
        
        video = None
        
        try:
            # Load the source video
            video = mp.VideoFileClip(str(video_path))
            
            # Add subtitles
            video = self._add_subtitles(video, project_id, mp)
            
            # Get output path
            output_path = self.file_storage.get_next_render_path(project_id)
            
            # Render
            video.write_videofile(
                str(output_path),
                fps=video.fps or 24,
                codec="libx264",
                audio_codec="aac",
                threads=0,
                preset="fast",
                ffmpeg_params=["-crf", "23"],
            )
            
            render_duration = time.time() - start_time
            logger.info(f"Standalone render complete: {output_path}")
            return output_path, render_duration
            
        finally:
            if video:
                video.close()
    
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
    ) -> Any:
        """Create final video from segments."""
        fmt = project.get("format", "9:16")
        size = (720, 1280) if fmt == "9:16" else (1280, 720)
        
        clips = []
        # "Golden rule": Transition is a beat. Needs to be snappy.
        transition_duration = 0.4 
        
        # Transitions: 
        # "beat" -> slide/whip/zoom (dynamic)
        # "story" -> crossfade (soft) - tough to detect, so we mix them but favor dynamic.
        available_transitions = [
            "slide_left", "slide_right", "slide_up", "slide_down", 
            "zoom_in", "zoom_out",
            "crossfade"
        ]
        
        for i, seg in enumerate(segments):
            seg_id = seg.get("id") or seg.get("segment_id")
            if not seg_id:
                continue
            
            seg_id = str(seg_id)
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
            
            # Extend duration for transition overlap (except for the last clip)
            # This ensures that when we overlap by 'transition_duration', the 'useful' part
            # of the clip remains 'duration' long, keeping sync with audio.
            if i < len(segments) - 1:
                duration += transition_duration

            effect = seg.get("effect") or "random"
            if effect == "random":
                effect = random.choice([
                    "zoom_in", "zoom_out", "pan_left",
                    "pan_right", "pan_up", "pan_down"
                ])
            
            clip = self._apply_effect(img_path, duration, effect, size, mp)
            
            # Apply transition from previous clip
            if i > 0:
                transition = seg.get("transition", "random")
                if transition == "random":
                    # Heuristic: 80% dynamic ("beat"), 20% soft ("story" possibility)
                    if random.random() < 0.8:
                        transition = random.choice(["slide_left", "slide_right", "slide_up", "slide_down", "zoom_in"])
                    else:
                        transition = "crossfade"
                
                clip = self._apply_transition(clip, transition, transition_duration, size)
            
            clips.append(clip)
            
        if not clips:
             raise ValueError("No valid image segments found to render.")

        # padding must be negative of the overlap
        # Since we extended the duration of previous clips, this overlap restores the correct start time for the next clip.
        video = mp.concatenate_videoclips(clips, method="compose", padding=-transition_duration)
        # video.audio is set in the caller
        return video

    def _apply_transition(self, clip, transition_type: str, duration: float, size: tuple[int, int]):
        """Apply transition effect to the clip start with Easing."""
        w, h = size
        
        # Easing function: EaseOutExpo for "Whip" feel
        # t goes 0 -> duration. p goes 0 -> 1
        def get_p(t):
            if t >= duration: return 1.0
            if t <= 0: return 0.0
            # EaseOutCubic: 1 - (1-x)^3
            x = t / duration
            return 1.0 - (1.0 - x)**3

        if transition_type == "crossfade":
            return clip.crossfadein(duration)
        
        elif transition_type == "slide_left":
            # Slide in from Right to Center
            def pos(t):
                p = get_p(t)
                # Start at w, end at 0
                x = int(w * (1.0 - p))
                return (x, 0)
            return clip.set_position(pos)
            
        elif transition_type == "slide_right":
            # Slide in from Left to Center
            def pos(t):
                p = get_p(t)
                # Start at -w, end at 0
                x = int(-w * (1.0 - p))
                return (x, 0)
            return clip.set_position(pos)
            
        elif transition_type == "slide_up":
            # Slide in from Bottom to Center
            def pos(t):
                p = get_p(t)
                # Start at h, end at 0
                y = int(h * (1.0 - p))
                return (0, y)
            return clip.set_position(pos)
            
        elif transition_type == "slide_down":
            # Slide in from Top to Center
            def pos(t):
                p = get_p(t)
                # Start at -h, end at 0
                y = int(-h * (1.0 - p))
                return (0, y)
            return clip.set_position(pos)
        
        elif transition_type == "zoom_in":
            # Scale up from 0 to 1 (Centered)
            # Note: resize is computationally heavy per frame, but ok for 0.4s
            final_clip = clip
            
            def resize_func(t):
                if t >= duration:
                    return 1.0
                p = get_p(t)
                # Start from 0.1 to avoid strict 0 issues, go to 1.0
                return 0.1 + 0.9 * p
                
            # CompositeVideoClip usually centers the clip if sized
            # But set_position("center") is safest
            return clip.resize(resize_func).set_position("center")
        
        elif transition_type == "zoom_out":
             # Start large (2x), shrink to 1x
            def resize_func(t):
                if t >= duration:
                    return 1.0
                p = get_p(t)
                # Start 2.0, end 1.0
                return 2.0 - 1.0 * p
            
            return clip.resize(resize_func).set_position("center")

        return clip.crossfadein(duration)
    
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
        
        # Randomize zoom intensity for more dynamic feel
        zoom_level = random.uniform(0.75, 0.88)
        
        has_pan_room_x = w > (max_crop_w * 1.05)
        has_pan_room_y = h > (max_crop_h * 1.05)
        
        def make_frame(t):
            # Ease-in-out interpolation
            # p goes from 0 to 1
            linear_p = t / duration
            # Sinusoidal easing: 0.5 * (1 - cos(pi * p))
            p = 0.5 * (1.0 - np.cos(linear_p * np.pi))
            
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
            
            # High quality resize
            resized = part_img.resize((tw, th), Image.BICUBIC)
            return np.array(resized)
        
        return mp.VideoClip(make_frame, duration=duration)
    
    def _add_subtitles(self, video, project_id: str, mp):
        """Overlay subtitles on video using moviepy TextClip."""
        srt_path = self.file_storage.get_subtitles_path(project_id)
        if not srt_path:
            logger.info(f"No subtitles found for project {project_id}")
            return video
        
        styling_dict = self.file_storage.get_subtitle_styling(project_id) or {}
        
        # Parse styling
        font_family = styling_dict.get("font_family", "Arial")
        font_size = styling_dict.get("font_size", 48)
        font_color = styling_dict.get("font_color", "#FFFFFF")
        stroke_color = styling_dict.get("stroke_color", "#000000")
        stroke_width = styling_dict.get("stroke_width", 3)
        position = styling_dict.get("position", "bottom")
        margin_x = styling_dict.get("margin_x", 50)
        margin_y = styling_dict.get("margin_y", 60)
        text_align = styling_dict.get("text_align", "center")
        max_width_pct = styling_dict.get("max_width_percent", 90)
        uppercase = styling_dict.get("uppercase", False)
        bg_enabled = styling_dict.get("background_enabled", False)
        bg_color = styling_dict.get("background_color", "#000000")
        bg_opacity = styling_dict.get("background_opacity", 0.7)
        bg_padding = styling_dict.get("background_padding", 10)
        bg_radius = styling_dict.get("background_radius", 8)
        animation = styling_dict.get("animation", "none")  # none, fade, pop, typewriter
        
        # Parse highlight styling
        hl_font_color = styling_dict.get("highlight_font_color", "#FFFFFF")
        hl_bg_color = styling_dict.get("highlight_bg_color", "#6e00ff")
        hl_bg_radius = styling_dict.get("highlight_bg_radius", 8)
        hl_bg_padding = styling_dict.get("highlight_bg_padding", 8)
        hl_active_word = styling_dict.get("highlight_active_word", False)
        
        # Parse SRT file
        entries = self._parse_srt_file(srt_path)
        if not entries:
            logger.info(f"No subtitle entries parsed for project {project_id}")
            return video
        
        video_w, video_h = video.size
        max_text_width = int(video_w * max_width_pct / 100)
        
        subtitle_clips = []
        
        logger.info(f"Processing {len(entries)} subtitle entries for video ({video_w}x{video_h})")
        
        # -- Helpers for colors and font -- 
        # Parse colors
        def hex_to_rgba(hex_code, alpha=255):
            h = hex_code.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
        
        text_color = hex_to_rgba(font_color)
        outline_color = hex_to_rgba(stroke_color) if stroke_width > 0 else None
        hl_text_color_rgba = hex_to_rgba(hl_font_color)
        hl_bg_color_rgba = hex_to_rgba(hl_bg_color)
        
        # Load Font once
        from PIL import ImageFont
        font = None
        font_weight = styling_dict.get("font_weight", "bold")
        is_bold = font_weight in ("bold", "700", "black", "900")
        clean_family = font_family.replace(" ", "")
        
        base_dir = Path(__file__).resolve().parent.parent.parent
        font_dir = base_dir / "app" / "static" / "fonts"
        windows_fonts = Path("C:/Windows/Fonts")
        
        search_paths = [
            str(font_dir / f"{clean_family}.ttf"),
            str(font_dir / f"{clean_family}.otf"),
            str(font_dir / f"{clean_family}-Bold.ttf") if is_bold else str(font_dir / f"{clean_family}-Regular.ttf"),
            str(font_dir / f"{font_family}.ttf"),
            str(windows_fonts / f"{clean_family.lower()}.ttf"),
            str(windows_fonts / f"{clean_family.lower()}b.ttf") if is_bold else str(windows_fonts / f"{clean_family.lower()}.ttf"),
            str(windows_fonts / f"{font_family.lower().replace(' ', '')}.ttf"),
        ]
        
        windows_fallbacks = [
            str(windows_fonts / "arial.ttf"),
            str(windows_fonts / "arialbd.ttf") if is_bold else str(windows_fonts / "arial.ttf"),
            str(windows_fonts / "segoeui.ttf"),
            str(windows_fonts / "segoeuib.ttf") if is_bold else str(windows_fonts / "segoeui.ttf"),
            str(windows_fonts / "calibri.ttf"),
            str(windows_fonts / "calibrib.ttf") if is_bold else str(windows_fonts / "calibri.ttf"),
        ]
        
        loaded = False
        for path in search_paths:
            try:
                font = ImageFont.truetype(path, font_size)
                loaded = True
                logger.info(f"Loaded font: {path}")
                break
            except OSError:
                continue
        
        if not loaded:
            logger.warning(f"Font {font_family} not found, trying fallback")
            for path in windows_fallbacks:
                try:
                    font = ImageFont.truetype(path, font_size)
                    loaded = True
                    break
                except OSError:
                    continue
        
        if not loaded:
             font = ImageFont.load_default()

        # Iterate entries
        for idx, entry in enumerate(entries):
            text = entry["text"]
            if uppercase:
                text = text.upper()
            
            start_time = entry["start_seconds"]
            end_time = entry["end_seconds"]
            duration = end_time - start_time
            
            if duration <= 0:
                continue
            
            # Helper logic to create clip
            def create_clip(txt, dur):
                try:
                     return self._render_subtitle_image(
                        txt, font, font_size, text_color, outline_color, stroke_width,
                        hl_text_color_rgba, hl_bg_color_rgba, hl_bg_radius, hl_bg_padding,
                        max_text_width, text_align, mp
                     ).set_duration(dur)
                except Exception as e:
                     logger.warning(f"Render text error: {e}")
                     return mp.TextClip(txt=txt, fontsize=font_size, color=font_color, size=(max_text_width, None)).set_duration(dur)

            # Active Word Logic
            if hl_active_word:
                words = text.split()
                if not words: continue
                
                word_count = len(words)
                word_duration = duration / word_count
                current_start = start_time
                
                for i in range(word_count):
                    # Construct text with active word highlighted
                    chunk_words = []
                    for j, w in enumerate(words):
                        if i == j:
                            chunk_words.append(f"<h>{w}</h>")
                        else:
                            chunk_words.append(w)
                    
                    chunk_text = " ".join(chunk_words)
                    
                    clip = create_clip(chunk_text, word_duration)
                    self._position_and_add_clip(
                        clip, subtitle_clips, video_w, video_h, 
                        current_start, word_duration, 
                        position, margin_y, animation, 
                        bg_enabled, bg_color, bg_opacity, bg_padding,
                        mp
                    )
                    current_start += word_duration
            else:
                # Standard
                clip = create_clip(text, duration)
                self._position_and_add_clip(
                    clip, subtitle_clips, video_w, video_h, 
                    start_time, duration, 
                    position, margin_y, animation, 
                    bg_enabled, bg_color, bg_opacity, bg_padding,
                    mp
                )
        
        if not subtitle_clips:
            return video
        
        try:
            result = mp.CompositeVideoClip([video] + subtitle_clips)
            logger.info(f"Added {len(entries)} subtitle entries to video")
            return result
        except Exception as e:
            logger.error(f"Failed to composite subtitles: {e}")
            return video

    def _add_subtitles_deprecated(self, video, project_id: str, mp):
        """Overlay subtitles on video using moviepy TextClip."""
        srt_path = self.file_storage.get_subtitles_path(project_id)
        if not srt_path:
            logger.info(f"No subtitles found for project {project_id}")
            return video
        
        styling_dict = self.file_storage.get_subtitle_styling(project_id) or {}
        
        # Parse styling
        font_family = styling_dict.get("font_family", "Arial")
        font_size = styling_dict.get("font_size", 48)
        font_color = styling_dict.get("font_color", "#FFFFFF")
        stroke_color = styling_dict.get("stroke_color", "#000000")
        stroke_width = styling_dict.get("stroke_width", 3)
        position = styling_dict.get("position", "bottom")
        margin_x = styling_dict.get("margin_x", 50)
        margin_y = styling_dict.get("margin_y", 60)
        text_align = styling_dict.get("text_align", "center")
        max_width_pct = styling_dict.get("max_width_percent", 90)
        uppercase = styling_dict.get("uppercase", False)
        bg_enabled = styling_dict.get("background_enabled", False)
        bg_color = styling_dict.get("background_color", "#000000")
        bg_opacity = styling_dict.get("background_opacity", 0.7)
        bg_padding = styling_dict.get("background_padding", 10)
        bg_radius = styling_dict.get("background_radius", 8)
        animation = styling_dict.get("animation", "none")  # none, fade, pop, typewriter
        
        # Parse highlight styling
        hl_font_color = styling_dict.get("highlight_font_color", "#FFFFFF")
        hl_bg_color = styling_dict.get("highlight_bg_color", "#6e00ff")
        hl_bg_radius = styling_dict.get("highlight_bg_radius", 8)
        hl_bg_padding = styling_dict.get("highlight_bg_padding", 8)
        
        # Parse SRT file
        entries = self._parse_srt_file(srt_path)
        if not entries:
            logger.info(f"No subtitle entries parsed for project {project_id}")
            return video
        
        video_w, video_h = video.size
        max_text_width = int(video_w * max_width_pct / 100)
        
        subtitle_clips = []
        
        logger.info(f"Processing {len(entries)} subtitle entries for video ({video_w}x{video_h})")
        
        for idx, entry in enumerate(entries):
            text = entry["text"]
            if uppercase:
                text = text.upper()
            
            start_time = entry["start_seconds"]
            end_time = entry["end_seconds"]
            duration = end_time - start_time
            
            if duration <= 0:
                logger.warning(f"Subtitle {idx+1}: invalid duration ({start_time} -> {end_time})")
                continue
            
            logger.debug(f"Subtitle {idx+1}: {start_time:.2f}s - {end_time:.2f}s: {text[:30]}...")
            
            try:
                # Custom PIL-based text rendering to avoid ImageMagick dependency
                try:
                    # Parse colors
                    def hex_to_rgba(hex_code, alpha=255):
                        h = hex_code.lstrip('#')
                        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
                    
                    text_color = hex_to_rgba(font_color)
                    outline_color = hex_to_rgba(stroke_color) if stroke_width > 0 else None
                    
                    # Font loading with improved fallback chain
                    font = None
                    font_weight = styling_dict.get("font_weight", "bold")
                    is_bold = font_weight in ("bold", "700", "black", "900")
                    
                    # Normalize font name (e.g. "Open Sans" -> "OpenSans")
                    clean_family = font_family.replace(" ", "")
                    
                    # Calculate paths
                    base_dir = Path(__file__).resolve().parent.parent.parent  # Clipmaker root
                    font_dir = base_dir / "app" / "static" / "fonts"
                    
                    # Windows font directory
                    windows_fonts = Path("C:/Windows/Fonts")
                    
                    # Build search paths prioritizing bundled fonts, then system fonts
                    search_paths = [
                        # Bundled fonts
                        str(font_dir / f"{clean_family}.ttf"),
                        str(font_dir / f"{clean_family}.otf"),
                        str(font_dir / f"{clean_family}-Bold.ttf") if is_bold else str(font_dir / f"{clean_family}-Regular.ttf"),
                        str(font_dir / f"{font_family}.ttf"),
                        # Windows system fonts (common names)
                        str(windows_fonts / f"{clean_family.lower()}.ttf"),
                        str(windows_fonts / f"{clean_family.lower()}b.ttf") if is_bold else str(windows_fonts / f"{clean_family.lower()}.ttf"),
                        # Common Windows font variations
                        str(windows_fonts / f"{font_family.lower().replace(' ', '')}.ttf"),
                    ]
                    
                    # Add common Windows fallback fonts
                    windows_fallbacks = [
                        str(windows_fonts / "arial.ttf"),
                        str(windows_fonts / "arialbd.ttf") if is_bold else str(windows_fonts / "arial.ttf"),
                        str(windows_fonts / "segoeui.ttf"),
                        str(windows_fonts / "segoeuib.ttf") if is_bold else str(windows_fonts / "segoeui.ttf"),
                        str(windows_fonts / "calibri.ttf"),
                        str(windows_fonts / "calibrib.ttf") if is_bold else str(windows_fonts / "calibri.ttf"),
                    ]
                    
                    loaded = False
                    for path in search_paths:
                        try:
                            font = ImageFont.truetype(path, font_size)
                            loaded = True
                            logger.info(f"Loaded font: {path}")
                            break
                        except OSError:
                            continue
                    
                    # Try Windows fallbacks if primary font not found
                    if not loaded:
                        logger.warning(f"Font {font_family} not found, trying Windows fallbacks")
                        for path in windows_fallbacks:
                            try:
                                font = ImageFont.truetype(path, font_size)
                                loaded = True
                                logger.info(f"Using fallback font: {path}")
                                break
                            except OSError:
                                continue
                    
                    # Final fallback to PIL default
                    if not loaded:
                        logger.warning("All font loading failed, using PIL default")
                        font = ImageFont.load_default()
                    
                    # Text wrapping
                    hl_text_color_rgba = hex_to_rgba(hl_font_color)
                    hl_bg_color_rgba = hex_to_rgba(hl_bg_color)

                    # Tokenize text
                    tokens = []
                    parts = re.split(r'(<h>.*?</h>)', text)
                    for part in parts:
                        if part.startswith('<h>') and part.endswith('</h>'):
                            content = part[3:-4]
                            subwords = content.split()
                            for w in subwords:
                                tokens.append({'text': w, 'hl': True})
                        else:
                            subwords = part.split()
                            for w in subwords:
                                tokens.append({'text': w, 'hl': False})

                    # Measure
                    dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
                    
                    def get_width(t_str):
                        bb = dummy_draw.textbbox((0, 0), t_str, font=font)
                        return bb[2] - bb[0]
                    
                    space_w = get_width(" ")
                    if space_w == 0:
                        space_w = int(font_size * 0.25)

                    lines = []
                    current_line = []
                    current_w = 0

                    for token in tokens:
                        w = get_width(token['text'])
                        # If highlight, add padding width
                        t_w = w + (hl_bg_padding * 2 if token['hl'] else 0)
                        
                        needed = t_w + (space_w if current_line else 0)
                        
                        if current_w + needed <= max_text_width:
                            current_line.append(token)
                            current_w += needed
                        else:
                            if current_line:
                                lines.append(current_line)
                                current_line = [token]
                                current_w = t_w
                            else:
                                lines.append([token])
                                current_w = 0
                    if current_line:
                        lines.append(current_line)

                    # Calculate heights
                    # Use 'Ag' as representative for heigth
                    bbox_h = dummy_draw.textbbox((0, 0), "Ag", font=font)
                    text_height = bbox_h[3] - bbox_h[1]
                    
                    line_height = text_height + stroke_width * 2 + 10 # Base height
                    # If using highlights, ensure enough vertical space
                    step_y = max(line_height, text_height + hl_bg_padding * 2) + 5
                    
                    total_h = len(lines) * step_y + 20
                    
                    # Create Image
                    img = Image.new('RGBA', (max_text_width + 20, int(total_h)), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(img)
                    
                    y = stroke_width + 10 + hl_bg_padding # Initial offset
                    
                    for line in lines:
                        # Measure line width for alignment
                        lw = 0
                        for i, t in enumerate(line):
                            wd = get_width(t['text'])
                            if t['hl']:
                                lw += wd + hl_bg_padding * 2
                            else:
                                lw += wd
                            if i < len(line) - 1:
                                lw += space_w
                        
                        # Align
                        if text_align == 'center':
                            x = (max_text_width - lw) / 2
                        elif text_align == 'right':
                            x = max_text_width - lw
                        else:
                            x = stroke_width
                        
                        # Draw tokens
                        for i, t in enumerate(line):
                            wd = get_width(t['text'])
                            
                            if t['hl']:
                                # Draw BG
                                # Center text in bg?
                                # Highlight box
                                rx = x
                                ry = y - hl_bg_padding
                                rw = wd + hl_bg_padding * 2
                                rh = text_height + hl_bg_padding * 2 + 5 # slight adjust
                                
                                draw.rounded_rectangle(
                                    (rx, ry, rx + rw, ry + rh),
                                    radius=hl_bg_radius,
                                    fill=hl_bg_color_rgba
                                )
                                
                                # Draw text (no stroke usually)
                                draw.text((x + hl_bg_padding, y), t['text'], font=font, fill=hl_text_color_rgba)
                                x += rw
                            else:
                                # Normal
                                # Stroke
                                if stroke_width > 0:
                                    for dx in range(-stroke_width, stroke_width + 1):
                                        for dy in range(-stroke_width, stroke_width + 1):
                                            if dx*dx + dy*dy <= stroke_width*stroke_width:
                                                draw.text((x + dx, y + dy), t['text'], font=font, fill=outline_color)
                                
                                draw.text((x, y), t['text'], font=font, fill=text_color)
                                x += wd
                            
                            if i < len(line) - 1:
                                x += space_w
                                
                        y += step_y
                    
                    # Convert to numpy
                    img_np = np.array(img)
                    txt_clip = mp.ImageClip(img_np)
                    
                except Exception as pil_err:
                    logger.warning(f"PIL Text rendering failed, trying fallback: {pil_err}")
                    # Fallback to pure TextClip (might fail if no ImageMagick)
                    txt_clip = mp.TextClip(
                        txt=text,
                        fontsize=font_size,
                        font=font_family,
                        color=font_color,
                        stroke_color=stroke_color if stroke_width > 0 else None,
                        stroke_width=stroke_width,
                        method="caption",
                        align=text_align,
                        size=(max_text_width, None),
                    )
                
                # Calculate position
                # Ensure we use the clips dimensions
                clip_w, clip_h = txt_clip.size
                
                # Horizontal safety check: Resize if wider than video
                if clip_w > video_w:
                    txt_clip = txt_clip.resize(width=video_w)
                    clip_w, clip_h = txt_clip.size
                
                if position == "top":
                    y_pos = margin_y
                elif position == "middle":
                    y_pos = (video_h - clip_h) // 2
                else:  # bottom
                    y_pos = video_h - clip_h - margin_y
                
                # Vertical safety clamp
                # Ensure it never goes off screen top or bottom
                # Allow a minimum safety margin (e.g. 10px) unless margins handle it effectively
                safe_y_min = 0  # Absolute minimum top
                safe_y_max = video_h - clip_h  # Absolute minimum bottom position
                
                # Clamp y_pos
                if y_pos < safe_y_min:
                    y_pos = safe_y_min
                elif y_pos > safe_y_max:
                    y_pos = safe_y_max
                
                x_pos = (video_w - clip_w) // 2
                
                # Set timing and position
                txt_clip = txt_clip.set_start(start_time).set_duration(duration)
                txt_clip = txt_clip.set_position((x_pos, y_pos))
                
                # Apply animations
                if animation == "fade":
                    fade_duration = min(0.3, duration / 4)
                    txt_clip = txt_clip.crossfadein(fade_duration).crossfadeout(fade_duration)
                elif animation == "pop":
                    # Simple pop effect using resize
                    txt_clip = txt_clip.resize(lambda t: 1 + 0.1 * (1 - abs(t - duration/2)/(duration/2)) if t < duration else 1)
                
                # Add background if enabled
                if bg_enabled:
                    # Create semi-transparent background
                    # Use ColorClip from moviepy
                    from moviepy.video.VideoClip import ColorClip
                    bg_width = clip_w + bg_padding * 2
                    bg_height = clip_h + bg_padding * 2
                    
                    # Parse hex color
                    bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                    
                    bg_clip = ColorClip(
                        size=(bg_width, bg_height),
                        color=bg_rgb,
                    ).set_opacity(bg_opacity)
                    
                    bg_clip = bg_clip.set_start(start_time).set_duration(duration)
                    bg_x = x_pos - bg_padding
                    bg_y = y_pos - bg_padding
                    bg_clip = bg_clip.set_position((bg_x, bg_y))
                    
                    # Apply same fade to background
                    if animation == "fade":
                        bg_clip = bg_clip.crossfadein(fade_duration).crossfadeout(fade_duration)
                    
                    subtitle_clips.append(bg_clip)
                
                subtitle_clips.append(txt_clip)
                
            except Exception as e:
                logger.warning(f"Failed to create subtitle clip: {e}")
                continue
        
        if not subtitle_clips:
            return video
        
        # Composite all subtitle clips on top of video
        try:
            result = mp.CompositeVideoClip([video] + subtitle_clips)
            logger.info(f"Added {len(entries)} subtitle entries to video")
            return result
        except Exception as e:
            logger.error(f"Failed to composite subtitles: {e}")
            return video
    
    def _parse_srt_file(self, srt_path: Path) -> list[dict]:
        """Parse SRT file to list of entries with timing."""
        content = srt_path.read_text(encoding="utf-8")
        entries = []
        
        # Normalize line endings (Windows \r\n -> \n)
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Split by double newline (subtitle blocks)
        # Handle various separator patterns
        blocks = re.split(r'\n\n+', content.strip())
        
        logger.debug(f"Found {len(blocks)} subtitle blocks in SRT file")
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 2:  # Minimum: index, timing (text could be on same or next line)
                try:
                    # Find the timing line (could be first or second line)
                    timing_line_idx = -1
                    for idx, line in enumerate(lines[:3]):  # Check first 3 lines
                        if re.match(r'\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->', line.strip()):
                            timing_line_idx = idx
                            break
                    
                    if timing_line_idx == -1:
                        continue
                    
                    # Parse timing line
                    time_match = re.match(
                        r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})',
                        lines[timing_line_idx].strip()
                    )
                    if time_match:
                        start_str = time_match.group(1)
                        end_str = time_match.group(2)
                        # Text is everything after the timing line
                        text_lines = lines[timing_line_idx + 1:]
                        text = '\n'.join(text_lines).strip()
                        
                        if text:  # Only add if there's actual text
                            entries.append({
                                "start": start_str,
                                "end": end_str,
                                "start_seconds": self._srt_time_to_seconds(start_str),
                                "end_seconds": self._srt_time_to_seconds(end_str),
                                "text": text,
                            })
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse subtitle block: {e}")
                    continue
        
        logger.info(f"Parsed {len(entries)} subtitle entries from SRT file")
        return entries
    
    def _srt_time_to_seconds(self, srt_time: str) -> float:
        """Convert SRT time format to seconds."""
        srt_time = srt_time.replace(',', '.')
        parts = srt_time.split(':')
        
        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        
        return 0.0
    
    
    def _render_subtitle_image(
        self, text, font, font_size, text_color, outline_color, stroke_width,
        hl_text_color_rgba, hl_bg_color_rgba, hl_bg_radius, hl_bg_padding,
        max_text_width, text_align, mp
    ):
        """Render text to an ImageClip using PIL."""
        from PIL import Image, ImageDraw
        import numpy as np
        
        # Tokenize text
        tokens = []
        parts = re.split(r'(<h>.*?</h>)', text)
        for part in parts:
            if part.startswith('<h>') and part.endswith('</h>'):
                content = part[3:-4]
                subwords = content.split()
                for w in subwords:
                    tokens.append({'text': w, 'hl': True})
            else:
                subwords = part.split()
                for w in subwords:
                    tokens.append({'text': w, 'hl': False})

        # Measure
        dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        
        def get_width(t_str):
            bb = dummy_draw.textbbox((0, 0), t_str, font=font)
            return bb[2] - bb[0]
        
        space_w = get_width(" ")
        if space_w == 0:
            space_w = int(font_size * 0.25)

        lines = []
        current_line = []
        current_w = 0

        for token in tokens:
            w = get_width(token['text'])
            # If highlight, add padding width
            t_w = w + (hl_bg_padding * 2 if token['hl'] else 0)
            
            needed = t_w + (space_w if current_line else 0)
            
            if current_w + needed <= max_text_width:
                current_line.append(token)
                current_w += needed
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = [token]
                    current_w = t_w
                else:
                    lines.append([token])
                    current_w = 0
        if current_line:
            lines.append(current_line)

        # Calculate heights
        # Use 'Ag' as representative for heigth
        bbox_h = dummy_draw.textbbox((0, 0), "Ag", font=font)
        text_height = bbox_h[3] - bbox_h[1]
        
        line_height = text_height + stroke_width * 2 + 10 # Base height
        # If using highlights, ensure enough vertical space
        step_y = max(line_height, text_height + hl_bg_padding * 2) + 5
        
        total_h = len(lines) * step_y + 20
        
        # Create Image
        img = Image.new('RGBA', (max_text_width + 20, int(total_h)), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        y = stroke_width + 10 + hl_bg_padding # Initial offset
        
        for line in lines:
            # Measure line width for alignment
            lw = 0
            for i, t in enumerate(line):
                wd = get_width(t['text'])
                if t['hl']:
                    lw += wd + hl_bg_padding * 2
                else:
                    lw += wd
                if i < len(line) - 1:
                    lw += space_w
            
            # Align
            if text_align == 'center':
                x = (max_text_width - lw) / 2
            elif text_align == 'right':
                x = max_text_width - lw
            else:
                x = stroke_width
            
            # Draw tokens
            for i, t in enumerate(line):
                wd = get_width(t['text'])
                
                if t['hl']:
                    # Draw BG
                    rx = x
                    ry = y - hl_bg_padding
                    rw = wd + hl_bg_padding * 2
                    rh = text_height + hl_bg_padding * 2 + 5 # slight adjust
                    
                    draw.rounded_rectangle(
                        (rx, ry, rx + rw, ry + rh),
                        radius=hl_bg_radius,
                        fill=hl_bg_color_rgba
                    )
                    
                    # Draw text
                    draw.text((x + hl_bg_padding, y), t['text'], font=font, fill=hl_text_color_rgba)
                    x += rw
                else:
                    # Stroke
                    if stroke_width > 0:
                        for dx in range(-stroke_width, stroke_width + 1):
                            for dy in range(-stroke_width, stroke_width + 1):
                                if dx*dx + dy*dy <= stroke_width*stroke_width:
                                    draw.text((x + dx, y + dy), t['text'], font=font, fill=outline_color)
                    
                    draw.text((x, y), t['text'], font=font, fill=text_color)
                    x += wd
                
                if i < len(line) - 1:
                    x += space_w
                    
            y += step_y
        
        # Convert to numpy
        img_np = np.array(img)
        return mp.ImageClip(img_np)

    def _position_and_add_clip(
        self, txt_clip, subtitle_clips, video_w, video_h, 
        start_time, duration, position, margin_y, animation, 
        bg_enabled, bg_color, bg_opacity, bg_padding, mp
    ):
        """Helper to position and animate subtitle clip."""
        # Calculate position
        clip_w, clip_h = txt_clip.size
        
        # Horizontal safety check
        if clip_w > video_w:
            txt_clip = txt_clip.resize(width=video_w)
            clip_w, clip_h = txt_clip.size
        
        if position == "top":
            y_pos = margin_y
        elif position == "middle":
            y_pos = (video_h - clip_h) // 2
        else:  # bottom
            y_pos = video_h - clip_h - margin_y
        
        # Vertical safety clamp
        safe_y_min = 0
        safe_y_max = video_h - clip_h
        
        if y_pos < safe_y_min:
            y_pos = safe_y_min
        elif y_pos > safe_y_max:
            y_pos = safe_y_max
        
        x_pos = (video_w - clip_w) // 2
        
        # Set timing and position
        txt_clip = txt_clip.set_start(start_time).set_duration(duration)
        txt_clip = txt_clip.set_position((x_pos, y_pos))
        
        # Apply animations
        if animation == "fade":
            fade_duration = min(0.3, duration / 4)
            txt_clip = txt_clip.crossfadein(fade_duration).crossfadeout(fade_duration)
        elif animation == "pop":
            txt_clip = txt_clip.resize(lambda t: 1 + 0.1 * (1 - abs(t - duration/2)/(duration/2)) if t < duration else 1)
        
        # Add background if enabled
        if bg_enabled:
            from moviepy.video.VideoClip import ColorClip
            bg_width = clip_w + bg_padding * 2
            bg_height = clip_h + bg_padding * 2
            
            # Parse hex color
            bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            bg_clip = ColorClip(
                size=(bg_width, bg_height),
                color=bg_rgb,
            ).set_opacity(bg_opacity)
            
            bg_clip = bg_clip.set_start(start_time).set_duration(duration)
            bg_x = x_pos - bg_padding
            bg_y = y_pos - bg_padding
            bg_clip = bg_clip.set_position((bg_x, bg_y))
            
            if animation == "fade":
                bg_clip = bg_clip.crossfadein(fade_duration).crossfadeout(fade_duration)
            
            subtitle_clips.append(bg_clip)
        
        subtitle_clips.append(txt_clip)

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

