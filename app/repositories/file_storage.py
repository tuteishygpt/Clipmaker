"""File storage for binary assets (images, audio, video)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from ..core.config import settings


class FileStorage:
    """Storage for binary files."""
    
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or settings.data_dir
    
    def _project_path(self, project_id: str) -> Path:
        """Get the base path for a project."""
        return self.data_dir / project_id
    
    def save_audio(self, project_id: str, file: BinaryIO, filename: str) -> Path:
        """Save an uploaded audio file."""
        source_dir = self._project_path(project_id) / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        
        extension = Path(filename).suffix or ".wav"
        target = source_dir / f"track{extension}"
        
        with target.open("wb") as buffer:
            shutil.copyfileobj(file, buffer)
        
        return target
    
    def get_audio_path(self, project_id: str) -> Path | None:
        """Get the audio file path for a project."""
        source_dir = self._project_path(project_id) / "source"
        if not source_dir.exists():
            return None
        
        for file_path in source_dir.glob("track.*"):
            return file_path
        return None
    
    def save_image(self, project_id: str, seg_id: str, version: int, data: bytes) -> Path:
        """Save a generated image."""
        images_dir = self._project_path(project_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        filename = images_dir / f"{seg_id}_v{version}.png"
        filename.write_bytes(data)
        return filename
    
    def get_image_path(self, project_id: str, image_name: str) -> Path | None:
        """Get an image file path."""
        path = self._project_path(project_id) / "images" / image_name
        return path if path.exists() else None
    
    def get_latest_render(self, project_id: str) -> Path | None:
        """Get the latest rendered video."""
        renders_dir = self._project_path(project_id) / "renders"
        if not renders_dir.exists():
            return None
        
        mp4_files = sorted(
            renders_dir.glob("*.mp4"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        return mp4_files[0] if mp4_files else None
    
    def get_render_path(self, project_id: str, render_name: str) -> Path | None:
        """Get a specific render file path."""
        path = self._project_path(project_id) / "renders" / render_name
        return path if path.exists() else None
    
    def get_next_render_path(self, project_id: str) -> Path:
        """Get the path for the next render version."""
        renders_dir = self._project_path(project_id) / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)
        
        existing = sorted(renders_dir.glob("final_v*.mp4"))
        next_version = len(existing) + 1
        return renders_dir / f"final_v{next_version}.mp4"

    def get_max_version(self, project_id: str, seg_id: str) -> int:
        """Get the highest image version for a segment."""
        images_dir = self._project_path(project_id) / "images"
        if not images_dir.exists():
            return 0
        
        max_v = 0
        prefix = f"{seg_id}_v"
        suffix = ".png"
        
        for file in images_dir.glob(f"{seg_id}_v*.png"):
            name = file.name
            try:
                # Extract N from seg_vN.png
                # name is like "segment_id_v2.png"
                # We know it ends with .png
                # We strip prefix and suffix
                
                # Careful if seg_id contains 'v', handle strictly
                if name.startswith(prefix) and name.endswith(suffix):
                    v_str = name[len(prefix):-len(suffix)]
                    v = int(v_str)
                    if v > max_v:
                        max_v = v
            except ValueError:
                continue
                
        return max_v

    # ==================== Subtitle Storage Methods ====================
    
    def save_subtitles(self, project_id: str, content: str) -> Path:
        """Save SRT content to file."""
        subs_dir = self._project_path(project_id) / "subtitles"
        subs_dir.mkdir(parents=True, exist_ok=True)
        path = subs_dir / "subtitles.srt"
        path.write_text(content, encoding="utf-8")
        return path
    
    def get_subtitles_path(self, project_id: str) -> Path | None:
        """Get path to SRT file."""
        path = self._project_path(project_id) / "subtitles" / "subtitles.srt"
        return path if path.exists() else None
    
    def save_subtitle_styling(self, project_id: str, styling: dict) -> Path:
        """Save subtitle styling config as JSON."""
        import json
        subs_dir = self._project_path(project_id) / "subtitles"
        subs_dir.mkdir(parents=True, exist_ok=True)
        path = subs_dir / "styling.json"
        path.write_text(json.dumps(styling, indent=2), encoding="utf-8")
        return path
    
    def get_subtitle_styling(self, project_id: str) -> dict | None:
        """Load subtitle styling config from JSON."""
        import json
        path = self._project_path(project_id) / "subtitles" / "styling.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None
    
    def delete_subtitles(self, project_id: str) -> None:
        """Delete all subtitle files for a project."""
        subs_dir = self._project_path(project_id) / "subtitles"
        if subs_dir.exists():
            shutil.rmtree(subs_dir)
    
    # ==================== Standalone Video Storage ====================
    
    def save_video(self, project_id: str, file: BinaryIO, filename: str) -> Path:
        """Save an uploaded video file for standalone subtitle mode."""
        source_dir = self._project_path(project_id) / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        
        extension = Path(filename).suffix or ".mp4"
        target = source_dir / f"video{extension}"
        
        with target.open("wb") as buffer:
            shutil.copyfileobj(file, buffer)
        
        return target
    
    def get_video_path(self, project_id: str) -> Path | None:
        """Get the uploaded video file path for a project."""
        source_dir = self._project_path(project_id) / "source"
        if not source_dir.exists():
            return None
        
        for file_path in source_dir.glob("video.*"):
            return file_path
        return None

