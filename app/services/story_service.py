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
        suggested_durations: list[float] = []
        for seg in segments:
            s = _parse_time(seg.get("start_time", 0))
            e = _parse_time(seg.get("end_time", 0))
            seg_duration = max(0.1, e - s)
            seg["_orig_duration"] = seg_duration
            suggested_durations.append(seg_duration)
            total_suggested += seg_duration

        # Get beat/onset times and confidence for snapping
        beat_times: list[float] = []
        onset_times: list[float] = []
        beat_confidence = 0.0
        if "technical_stats" in analysis:
            tech_stats = analysis["technical_stats"] or {}
            beat_times = tech_stats.get("beat_times", [])
            onset_times = tech_stats.get("onset_times", [])
            beat_confidence = float(tech_stats.get("beat_confidence") or 0.0)

        # Structural peaks derived from analysis segments
        structural_points = []
        for seg in analysis.get("segments", []) or []:
            structural_points.append(_parse_time(seg.get("start_time", 0)))
            structural_points.append(_parse_time(seg.get("end_time", 0)))
        structural_points = sorted({t for t in structural_points if 0.0 <= t <= duration})

        # Timing mode selection
        if beat_times and beat_confidence >= 0.66:
            timing_mode = "beat-driven"
        elif beat_times and beat_confidence >= 0.33:
            timing_mode = "beat-assisted"
        else:
            timing_mode = "structure-driven"

        beat_grid = sorted({0.0, *beat_times, duration}) if beat_times else [0.0, duration]
        beat_intervals = [
            beat_grid[i + 1] - beat_grid[i] for i in range(len(beat_grid) - 1)
            if beat_grid[i + 1] - beat_grid[i] > 0
        ]
        beat_interval = median(beat_intervals) if beat_intervals else 0.5

        if structural_points:
            structural_intervals = [
                structural_points[i + 1] - structural_points[i]
                for i in range(len(structural_points) - 1)
                if structural_points[i + 1] - structural_points[i] > 0
            ]
            structural_median = median(structural_intervals) if structural_intervals else 3.0
            min_seconds = max(1.5, 0.6 * structural_median)
            max_seconds = min(6.0, 1.8 * structural_median)
        else:
            min_seconds = 1.5
            max_seconds = 6.0

        min_beats = 2
        max_beats = 24

        def _nearest_time(target: float, candidates: list[float]) -> float:
            return min(candidates, key=lambda x: abs(x - target))

        def _snap_to_beat(time_value: float) -> float:
            if not beat_grid:
                return time_value
            return _nearest_time(time_value, beat_grid)

        def _beat_index(time_value: float) -> int:
            if not beat_grid:
                return 0
            return min(range(len(beat_grid)), key=lambda i: abs(beat_grid[i] - time_value))

        def _select_beat_end(start_time: float, ideal_end: float) -> float:
            if not beat_grid:
                return ideal_end
            start_idx = _beat_index(start_time)
            min_idx = min(start_idx + min_beats, len(beat_grid) - 1)
            max_idx = min(start_idx + max_beats, len(beat_grid) - 1)
            candidate_indices = range(min_idx, max_idx + 1)
            candidates = [beat_grid[i] for i in candidate_indices]
            if not candidates:
                return beat_grid[-1]
            return _nearest_time(ideal_end, candidates)

        def _apply_onset_adjustment(beat_end: float) -> float:
            if not onset_times:
                return beat_end
            window = 0.2
            nearby = [t for t in onset_times if abs(t - beat_end) <= window]
            if not nearby:
                return beat_end
            return _nearest_time(beat_end, nearby)

        # Apply timing based on mode with minimal adjustments
        current_time = 0.0

        for i, seg in enumerate(segments):
            weight = seg.pop("_orig_duration")
            if total_suggested > 0:
                seg_duration = weight
            else:
                seg_duration = duration / len(segments)

            if timing_mode in {"beat-driven", "beat-assisted"}:
                current_time = _snap_to_beat(current_time)

            seg["start_time"] = current_time

            if i == len(segments) - 1:
                seg["end_time"] = duration
                current_time = seg["end_time"]
                continue

            ideal_end = current_time + seg_duration

            if timing_mode == "beat-driven":
                actual_end = _select_beat_end(current_time, ideal_end)
            elif timing_mode == "beat-assisted":
                beat_end = _select_beat_end(current_time, ideal_end)
                actual_end = _apply_onset_adjustment(beat_end)
            else:
                actual_end = ideal_end
                if structural_points:
                    candidates = [
                        t for t in structural_points
                        if current_time + min_seconds <= t <= current_time + max_seconds
                    ]
                    if candidates:
                        actual_end = _nearest_time(ideal_end, candidates)
                actual_end = max(current_time + min_seconds, actual_end)
                actual_end = min(current_time + max_seconds, actual_end)

            actual_end = min(actual_end, duration)
            if actual_end <= current_time:
                actual_end = min(current_time + min_seconds, duration)

            seg["end_time"] = actual_end
            current_time = seg["end_time"]

        # Hard-fix end time without global rescaling
        if segments:
            segments[-1]["end_time"] = duration
            if segments[-1]["start_time"] >= duration:
                min_segment = min_seconds if timing_mode == "structure-driven" else max(
                    min_beats * beat_interval, 0.5
                )
                if len(segments) > 1:
                    prev = segments[-2]
                    prev_end = max(prev["start_time"] + min_segment, duration - min_segment)
                    prev["end_time"] = min(prev_end, duration - min_segment)
                    segments[-1]["start_time"] = prev["end_time"]
                else:
                    segments[-1]["start_time"] = max(0.0, duration - min_segment)

        return segments
