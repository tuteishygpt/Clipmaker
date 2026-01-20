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

    def generate(self, project_id: str, analysis: dict[str, Any], use_batch: bool = True) -> list[dict[str, Any]]:
        """Generate storyboard segments from analysis."""
        duration = analysis.get("total_duration", 0.0)

        # Generate segments via GenAI
        if not use_batch:
            segments = self.genai.build_storyboard(analysis, total_duration=duration, use_batch=False)
        else:
            # --- Batch Mode ---
            from .batch_service import BatchService
            batch_service = BatchService()
            
            req_body = self.genai.build_storyboard(analysis, total_duration=duration, use_batch=True)
            
            job_result = batch_service.submit_batch_job(
                requests=[req_body],
                model_name=self.genai.text_model,
                job_name=f"Storyboard-{project_id}"
            )
            
            job_name = job_result.get("job_id")
            if not job_name:
                raise RuntimeError("Failed to submit batch job for storyboard")
            
            batch_service.wait_for_job(job_name)
            
            results = batch_service.download_results(job_name)
            if not results:
                raise RuntimeError("Batch storyboard failed to return results")
            
            # BatchService.download_results now returns the parsed content directly
            data = results[0]
            
            # If data is string (extraction failed or was raw text), try to extract JSON
            if isinstance(data, dict) and "text" in data and "custom_id" in data:
                # This suggests it wasn't parsed as JSON in the service
                data = self.genai._extract_json(data["text"])
            
            # If it's still a string, try extract again (redundant but safe)
            if isinstance(data, str):
                data = self.genai._extract_json(data)
            
            if isinstance(data, dict) and "segments" in data:
                segments = data["segments"]
            elif isinstance(data, list):
                segments = data
            else:
                logger.warning(f"Unexpected storyboard structure: {type(data)}")
                segments = []

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
        """Normalize segment times to exactly fit the duration with rhythmic awareness."""
        MAX_DURATION = 6.0  # Maximum length for a single segment
        MIN_DURATION = 0.5  # Minimum length
        
        # Calculate original durations
        total_suggested = 0.0
        for seg in segments:
            s = _parse_time(seg.get("start_time", 0))
            e = _parse_time(seg.get("end_time", 0))
            seg_duration = max(0.1, e - s)
            # Cap original duration if it's too long
            seg_duration = min(seg_duration, MAX_DURATION * 1.5) 
            seg["_orig_duration"] = seg_duration
            total_suggested += seg_duration

        # Calculate scaling factor
        scale_factor = duration / total_suggested if total_suggested > 0 else 1.0
        logger.info(f"Normalizing {len(segments)} segments: total_suggested={total_suggested:.2f}s, "
                    f"target_duration={duration:.2f}s, scale_factor={scale_factor:.3f}")

        # Technical stats
        tech_stats = analysis.get("technical_stats", {}) or {}
        beat_times = tech_stats.get("beat_times", [])
        beat_strengths = tech_stats.get("beat_strengths", [])
        onset_times = tech_stats.get("onset_times", [])
        beat_confidence = float(tech_stats.get("beat_confidence") or 0.0)
        bpm = float(tech_stats.get("bpm") or 0.0)

        # Create localized strength map
        beat_strength_map = {}
        if beat_times and beat_strengths and len(beat_times) == len(beat_strengths):
            beat_strength_map = dict(zip(beat_times, beat_strengths))
        elif beat_times:
            beat_strength_map = {b: 0.5 for b in beat_times}

        # Structural points
        structural_points = []
        for seg in analysis.get("segments", []) or []:
            structural_points.append(_parse_time(seg.get("start_time", 0)))
            structural_points.append(_parse_time(seg.get("end_time", 0)))
        structural_points = sorted({t for t in structural_points if 0.0 <= t <= duration})

        # Timing mode
        if beat_times and beat_confidence >= 0.4:
            timing_mode = "beat-driven"
        elif beat_times and beat_confidence >= 0.15:
            timing_mode = "beat-assisted"
        else:
            timing_mode = "structure-driven"

        beat_grid = sorted({0.0, *beat_times, duration}) if beat_times else [0.0, duration]
        
        def _get_strength(t: float) -> float:
            return beat_strength_map.get(t, 0.0)

        def _nearest_time(target: float, candidates: list[float]) -> float:
            if not candidates: return target
            return min(candidates, key=lambda x: abs(x - target))

        def _snap_to_beat(time_value: float) -> float:
            if not beat_grid: return time_value
            return _nearest_time(time_value, beat_grid)

        def _select_smart_beat_end(start_time: float, ideal_end: float, remaining_segments: int, seg_idx: int) -> float:
            if not beat_grid: return ideal_end
            
            # Constraints
            min_end = start_time + MIN_DURATION
            max_end = min(start_time + MAX_DURATION, duration - (remaining_segments * MIN_DURATION))
            
            candidates = [b for b in beat_grid if b >= min_end and b <= max_end]
            if not candidates:
                return min(max_end, duration)

            # Window for search
            window = 2.0
            window_candidates = [c for c in candidates if abs(c - ideal_end) <= window]
            if not window_candidates:
                return _nearest_time(ideal_end, candidates)
            
            best_t = window_candidates[0]
            best_score = -1.0
            
            # Rhythm context (look for 4-beat or 8-beat patterns if BPM is known)
            beat_duration = 60.0 / bpm if bpm > 20 else 0.5
            
            for t in window_candidates:
                dist = abs(t - ideal_end)
                dist_score = 1.0 - (dist / window)
                strength = _get_strength(t)
                
                # Rhythm score: favor intervals that match 2, 4, 8 beats
                rhythm_score = 0.0
                if beat_duration > 0:
                    elapsed = t - start_time
                    beats_elapsed = elapsed / beat_duration
                    # 1.0 if perfectly aligned with a multiple of 1, 2, or 4 beats
                    alignment = 1.0 - (abs(beats_elapsed - round(beats_elapsed)) / 0.5)
                    rhythm_score = alignment * 0.2
                    
                    # Bonus for "round" numbers of beats (4, 8, 16)
                    if abs(beats_elapsed - 4.0) < 0.2 or abs(beats_elapsed - 8.0) < 0.2:
                        rhythm_score += 0.3
                    elif abs(beats_elapsed - 2.0) < 0.2:
                        rhythm_score += 0.1

                # Weighted score
                score = 0.3 * dist_score + 0.5 * strength + 0.2 * rhythm_score
                
                # Structural match bonus
                if any(abs(t - sp) < 0.15 for sp in structural_points):
                     score += 0.4
                
                if score > best_score:
                    best_score = score
                    best_t = t
            
            return best_t

        # Normalization Loop
        current_time = 0.0
        num_segments = len(segments)
        if num_segments == 0: return []

        # Dynamics: if track is too long for the number of segments, 
        # we must increase our effective maximum to avoid a huge last segment.
        ideal_avg = duration / num_segments
        effective_max = max(MAX_DURATION, ideal_avg * 1.3)
        
        for i, seg in enumerate(segments):
            orig_dur = seg.pop("_orig_duration")
            # Proportional target vs dynamic max
            seg_duration = min(orig_dur * scale_factor, effective_max)
            seg_duration = max(MIN_DURATION, seg_duration)
            
            remaining = num_segments - i - 1

            # Precision snapping for start_time
            if timing_mode == "beat-driven":
                # Only snap if we aren't at the very start
                if current_time > 0:
                    current_time = _snap_to_beat(current_time)
            
            seg["start_time"] = current_time

            if i == num_segments - 1:
                # Check if the last segment is too long
                last_dur = duration - current_time
                if last_dur > effective_max * 1.5 and num_segments > 1:
                    logger.warning(f"Last segment {seg.get('id')} is very long ({last_dur:.2f}s). "
                                   f"Avg should be {ideal_avg:.2f}s.")
                seg["end_time"] = duration
                continue

            # Target end time
            ideal_end = current_time + seg_duration
            
            # Recalculate remaining average to see if we are falling behind
            rem_time = duration - ideal_end
            if remaining > 0:
                rem_avg = rem_time / remaining
                # If we are falling behind (leaving too much for later), 
                # we should stretch current segment towards the new average
                if rem_avg > effective_max:
                    ideal_end += (rem_avg - effective_max) * 0.5

            if timing_mode == "beat-driven":
                actual_end = _select_smart_beat_end(current_time, ideal_end, remaining, i)
            elif timing_mode == "beat-assisted":
                beat_end = _select_smart_beat_end(current_time, ideal_end, remaining, i)
                actual_end = (0.2 * ideal_end) + (0.8 * beat_end)
                actual_end = _snap_to_beat(actual_end)
            else:
                actual_end = min(ideal_end, duration - (remaining * MIN_DURATION))
                
            # Final safety
            actual_end = max(actual_end, current_time + MIN_DURATION)
            actual_end = min(actual_end, duration - (remaining * MIN_DURATION))
            
            seg["end_time"] = actual_end
            current_time = actual_end

        # Post-process: Gaps removal
        for i in range(len(segments) - 1):
            segments[i+1]["start_time"] = segments[i]["end_time"]
            
        logger.info(f"Rhythmic normalization complete. Avg: {ideal_avg:.2f}s, EffMax: {effective_max:.2f}s")
        return segments
