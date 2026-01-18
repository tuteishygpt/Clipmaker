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

        # Onset Detection
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)

        # Beat confidence estimation
        tempo_stability = 0.0
        if len(beat_times) > 2:
            intervals = np.diff(beat_times)
            mean_interval = float(np.mean(intervals))
            if mean_interval > 0:
                tempo_stability = float(
                    max(0.0, 1.0 - min(1.0, float(np.std(intervals)) / mean_interval))
                )

        beat_strength = 0.0
        # Per-beat strength
        beat_per_strength = []
        if len(beat_frames) > 0 and len(onset_env) > 0:
            # Ensure beat_frames are within bounds
            valid_mask = beat_frames < len(onset_env)
            valid_beat_frames = beat_frames[valid_mask]
            
            if len(valid_beat_frames) > 0:
                # Raw strengths at beat locations
                raw_strengths = onset_env[valid_beat_frames]
                # Normalize relative to max energy in the track
                max_env = float(np.max(onset_env)) + 1e-6
                beat_per_strength = (raw_strengths / max_env).tolist()
                
                # Update global beat strength metric
                beat_strength = float(np.mean(beat_per_strength))

        beat_confidence = float(
            max(0.0, min(1.0, 0.6 * tempo_stability + 0.4 * beat_strength))
        )

        # Energy / Volume (RMS)
        hop_length = 512
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]

        return {
            "bpm": float(tempo),
            "beat_times": beat_times.tolist(),
            "beat_strengths": beat_per_strength,
            "onset_times": onset_times.tolist(),
            "beat_confidence": beat_confidence,
            "tempo_stability": tempo_stability,
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
        character_description = project.get("character_description", "")
        
        # GenAI analysis
        analysis = self.genai.analyze_audio(
            audio_path=audio_path,
            duration=duration,
            technical_analysis=technical_analysis,
            user_style=user_style,
            user_description=user_description,
            character_description=character_description,
        )
        
        # Add metadata
        analysis["total_duration"] = duration
        analysis["total_duration"] = duration
        analysis["technical_stats"] = technical_analysis
        analysis["character_description"] = character_description
        
        # Save results
        self.project_repo.save_analysis(project_id, analysis)
        
        return analysis
