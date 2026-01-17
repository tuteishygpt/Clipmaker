"""Storyboard generation service."""
from __future__ import annotations

from typing import Any

from ..clients.genai import GenAIClient
from ..repositories.project_repo import ProjectRepository
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
        if len(parts) == 1:  # seconds
            return float(parts[0])
        if len(parts) == 2:  # MM:SS
            return float(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:  # HH:MM:SS
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except ValueError:
        pass
    
    return 0.0


class StoryboardService:
    """Service for generating video storyboard."""
    
    def __init__(
        self,
        genai_client: GenAIClient | None = None,
        project_repo: ProjectRepository | None = None,
    ) -> None:
        self.genai = genai_client or GenAIClient()
        self.project_repo = project_repo or ProjectRepository()
    
    def generate(self, project_id: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate storyboard segments from analysis."""
        duration = analysis.get("total_duration", 0.0)
        
        # Generate segments via GenAI
        segments = self.genai.build_storyboard(analysis, total_duration=duration)
        
        # Normalize segments to perfectly fit the duration
        if segments and duration > 0:
            segments = self._normalize_segments(segments, duration, analysis)
        
        # Save results
        self.project_repo.save_segments(project_id, segments)
        
        return segments
    
    def _normalize_segments(
        self,
        segments: list[dict[str, Any]],
        duration: float,
        analysis: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Normalize segment times to exactly fit the duration."""
        # Calculate original durations
        total_suggested = 0.0
        for seg in segments:
            s = _parse_time(seg.get("start_time", 0))
            e = _parse_time(seg.get("end_time", 0))
            seg["_orig_duration"] = max(0.1, e - s)
            total_suggested += seg["_orig_duration"]
        
        # Get beat times for snapping
        beat_times = []
        if "technical_stats" in analysis:
            beat_times = analysis["technical_stats"].get("beat_times", [])
        
        # Scale durations to fit exactly
        current_time = 0.0
        
        for i, seg in enumerate(segments):
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
                ideal_end = current_time + seg_duration
                actual_end = ideal_end
                
                # Beat Snapping Logic
                if beat_times:
                    valid_beats = [
                        b for b in beat_times
                        if current_time + 1.0 < b < duration - 1.0
                    ]
                    
                    if valid_beats:
                        closest_beat = min(valid_beats, key=lambda x: abs(x - ideal_end))
                        
                        # Tolerance: only snap if within 1.5 seconds
                        if abs(closest_beat - ideal_end) < 1.5:
                            actual_end = closest_beat
                
                seg["end_time"] = actual_end
            
            current_time = seg["end_time"]
        
        return segments
