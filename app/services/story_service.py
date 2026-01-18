"""Storyboard generation service."""
from __future__ import annotations

from statistics import median
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
            seg_duration = max(0.1, e - s)
            seg["_orig_duration"] = seg_duration
            total_suggested += seg_duration

        # Get beat/onset times and strength
        beat_times: list[float] = []
        beat_strengths: list[float] = []
        onset_times: list[float] = []
        beat_confidence = 0.0
        if "technical_stats" in analysis:
            tech_stats = analysis["technical_stats"] or {}
            beat_times = tech_stats.get("beat_times", [])
            beat_strengths = tech_stats.get("beat_strengths", [])
            onset_times = tech_stats.get("onset_times", [])
            beat_confidence = float(tech_stats.get("beat_confidence") or 0.0)

        # Create localized strength map
        beat_strength_map = {}
        if beat_times and beat_strengths and len(beat_times) == len(beat_strengths):
            beat_strength_map = dict(zip(beat_times, beat_strengths))
        elif beat_times:
             # Default strength if missing
            beat_strength_map = {b: 0.5 for b in beat_times}

        # Structural peaks derived from analysis segments
        structural_points = []
        for seg in analysis.get("segments", []) or []:
            structural_points.append(_parse_time(seg.get("start_time", 0)))
            structural_points.append(_parse_time(seg.get("end_time", 0)))
        structural_points = sorted({t for t in structural_points if 0.0 <= t <= duration})

        # Timing mode selection
        if beat_times and beat_confidence >= 0.4:  # Lowered threshold slightly
            timing_mode = "beat-driven"
        elif beat_times and beat_confidence >= 0.2:
            timing_mode = "beat-assisted"
        else:
            timing_mode = "structure-driven"

        beat_grid = sorted({0.0, *beat_times, duration}) if beat_times else [0.0, duration]
        
        # Helper functionality
        def _get_strength(t: float) -> float:
            return beat_strength_map.get(t, 0.0)

        def _nearest_time(target: float, candidates: list[float]) -> float:
            return min(candidates, key=lambda x: abs(x - target))

        def _snap_to_beat(time_value: float) -> float:
            if not beat_grid:
                return time_value
            # Snap to nearest beat
            return _nearest_time(time_value, beat_grid)

        def _select_smart_beat_end(start_time: float, ideal_end: float) -> float:
            """Smartly select end beat based on strength and proximity."""
            if not beat_grid:
                return ideal_end
            
            # Find closest beat index to ideal_end
            candidates = [b for b in beat_grid if b > start_time + 0.5]
            if not candidates:
                return beat_grid[-1]
            
            # Window of interest: +/- 1.5 seconds around ideal_end
            window = 1.5
            window_candidates = [c for c in candidates if abs(c - ideal_end) <= window]
            
            if not window_candidates:
                return _nearest_time(ideal_end, candidates)
            
            # Score candidates
            best_t = window_candidates[0]
            best_score = -1.0
            
            for t in window_candidates:
                dist = abs(t - ideal_end)
                dist_score = 1.0 - (dist / window)  # 0 to 1
                strength = _get_strength(t)
                
                # Weighted score: prioritize strong beats significantly
                score = 0.4 * dist_score + 0.6 * strength
                
                # Bonus for exact structural matches (if any)
                if any(abs(t - sp) < 0.1 for sp in structural_points):
                     score += 0.3
                
                if score > best_score:
                    best_score = score
                    best_t = t
            
            return best_t

        # Calculate segments
        current_time = 0.0
        
        for i, seg in enumerate(segments):
            weight = seg.pop("_orig_duration")
            if total_suggested > 0:
                seg_duration = weight
            else:
                seg_duration = duration / len(segments)

            # Snap start time
            if timing_mode in {"beat-driven", "beat-assisted"}:
                current_time = _snap_to_beat(current_time)
            
            seg["start_time"] = current_time

            # Last segment fix
            if i == len(segments) - 1:
                seg["end_time"] = duration
                continue

            ideal_end = current_time + seg_duration

            if timing_mode == "beat-driven":
                actual_end = _select_smart_beat_end(current_time, ideal_end)
            elif timing_mode == "beat-assisted":
                # Check nearest beat
                beat_end = _select_smart_beat_end(current_time, ideal_end)
                # Check nearest onset
                if onset_times:
                    onset_candidates = [o for o in onset_times if abs(o - beat_end) < 0.2]
                    if onset_candidates:
                        beat_end = _nearest_time(beat_end, onset_candidates)
                actual_end = beat_end
            else:
                # Structure driven fallback
                actual_end = ideal_end
                
            # Validations
            actual_end = max(actual_end, current_time + 0.5)
            actual_end = min(actual_end, duration)
            
            seg["end_time"] = actual_end
            current_time = actual_end

        # Final sanity check for gaps/overlaps
        for i in range(len(segments) - 1):
            segments[i+1]["start_time"] = segments[i]["end_time"]
            
        return segments
