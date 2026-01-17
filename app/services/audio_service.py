"""Audio analysis service."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..clients.genai import GenAIClient
from ..repositories.project_repo import ProjectRepository
from ..repositories.file_storage import FileStorage
from ..core.logging import get_logger

logger = get_logger(__name__)


def _get_audio_duration(audio_path: Path) -> float:
    """Get audio file duration using moviepy."""
    import moviepy.editor as mp
    
    clip = mp.AudioFileClip(str(audio_path))
    duration = clip.duration
    clip.close()
    return duration


def _analyze_audio_technical(audio_path: Path) -> dict[str, Any]:
    """Perform technical audio analysis using librosa."""
    try:
        import librosa
        import numpy as np
    except ImportError:
        logger.warning("librosa or numpy not found. Skipping technical analysis.")
        return {}
    
    try:
        y, sr = librosa.load(str(audio_path), sr=None)
        
        # Tempo and Beats
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        # Energy / Volume (RMS)
        hop_length = 512
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
        
        return {
            "bpm": float(tempo),
            "beat_times": beat_times.tolist(),
            "energy_stats": {
                "avg": float(np.mean(rms)),
                "max": float(np.max(rms)),
            }
        }
    except Exception as e:
        logger.error(f"Technical analysis failed: {e}")
        return {}


class AudioAnalysisService:
    """Service for analyzing audio tracks."""
    
    def __init__(
        self,
        genai_client: GenAIClient | None = None,
        project_repo: ProjectRepository | None = None,
        file_storage: FileStorage | None = None,
    ) -> None:
        self.genai = genai_client or GenAIClient()
        self.project_repo = project_repo or ProjectRepository()
        self.file_storage = file_storage or FileStorage()
    
    def analyze(self, project_id: str) -> dict[str, Any]:
        """Analyze audio for a project."""
        # Get audio file
        audio_path = self.file_storage.get_audio_path(project_id)
        if not audio_path:
            raise FileNotFoundError(f"No audio file found for project {project_id}")
        
        # Get duration
        duration = _get_audio_duration(audio_path)
        
        # Technical analysis (librosa)
        technical_analysis = _analyze_audio_technical(audio_path)
        
        # Get project info for style and description
        project = self.project_repo.get(project_id) or {}
        user_style = project.get("style", "cinematic")
        user_description = project.get("user_description", "")
        
        # GenAI analysis
        analysis = self.genai.analyze_audio(
            audio_path=audio_path,
            duration=duration,
            technical_analysis=technical_analysis,
            user_style=user_style,
            user_description=user_description,
        )
        
        # Add metadata
        analysis["total_duration"] = duration
        analysis["technical_stats"] = technical_analysis
        
        # Save results
        self.project_repo.save_analysis(project_id, analysis)
        
        return analysis
