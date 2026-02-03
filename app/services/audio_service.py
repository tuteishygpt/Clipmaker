"""Audio analysis service."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..clients.genai import GenAIClient
from ..repositories.project_repo import ProjectRepository
from ..repositories.file_storage import FileStorage
from ..core.logging import get_logger
from ..core.audio_utils import get_audio_duration, AudioLoadError

logger = get_logger(__name__)


def _analyze_rhythm_madmom(audio_path: str) -> dict[str, Any]:
    """
    Analyze rhythm using madmom (beats, downbeats, bars).
    """
    try:
        from madmom.features.beats import RNNBeatProcessor, DBNBeatTrackingProcessor
        from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor
    except ImportError:
        logger.warning("madmom not installed. Skipping advanced rhythm analysis.")
        return {}
    except Exception as e:
        logger.error(f"Failed to import madmom: {e}")
        return {}

    try:
        # 1. Beat Tracking (RNN + DBN)
        proc = DBNBeatTrackingProcessor(fps=100)
        act = RNNBeatProcessor()(audio_path)
        beat_times = proc(act)

        # 2. Downbeat Tracking (Bar segmentation)
        # RNNDownBeatProcessor returns columns: [beat_prob, downbeat_prob]
        proc_down = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)
        act_down = RNNDownBeatProcessor()(audio_path)
        downbeat_times = proc_down(act_down)
        
        # downbeat_times is usually a 2D array: [time, beat_number]
        # We want just the times where beat_number == 1 (the downbeat)
        
        # Parse downbeats and bars
        downbeats = []
        bars = []
        
        # madmom returns [time, beat_index]
        # beat_index is 1-based (1, 2, 3, 4...)
        
        current_bar_start = 0.0
        current_measure_beats = []
        
        for i, row in enumerate(downbeat_times):
            t = float(row[0])
            b_idx = int(row[1])
            
            if b_idx == 1:
                downbeats.append(t)
                # If we have a previous bar, close it
                if i > 0:
                    bars.append({
                        "start": current_bar_start,
                        "end": t,
                        "duration": t - current_bar_start,
                        "beats": current_measure_beats
                    })
                current_bar_start = t
                current_measure_beats = [t]
            else:
                current_measure_beats.append(t)

        return {
            "madmom_beats": [float(row[0]) for row in downbeat_times],
            "downbeats": downbeats,
            "bars": bars
        }

    except Exception as e:
        logger.error(f"madmom analysis failed: {e}")
        return {}


def _analyze_audio_technical(audio_path: Path) -> dict[str, Any]:
    """
    Perform technical audio analysis using librosa and madmom.
    
    Returns empty dict if libraries unavailable or analysis fails.
    Raises AudioLoadError for unrecoverable file issues.
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        logger.warning("librosa or numpy not found. Skipping technical analysis.")
        return {}

    try:
        # Load audio (mono for technical analysis)
        y, sr = librosa.load(str(audio_path), sr=None)
        
        # --- 1. Basic Rhythm (Librosa Fallback) ---
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        # --- 2. Advanced Rhythm (Madmom) ---
        rhythm_stats = _analyze_rhythm_madmom(str(audio_path))
        
        # Prefer madmom beats if available
        final_beats = rhythm_stats.get("madmom_beats", beat_times.tolist())
        downbeats = rhythm_stats.get("downbeats", [])
        bars = rhythm_stats.get("bars", [])
        
        # --- 3. Spectral & Frequency Analysis ---
        # Spectral Centroid (Brightness)
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)
        avg_brightness = float(np.mean(cent))
        
        # Frequency Bands Energy (Bass, Mid, High)
        # STFT
        S = np.abs(librosa.stft(y))
        
        # Define approximate bins for sr/2 frequency range
        # bass: 20-250Hz, mid: 250-4000Hz, high: 4000Hz+
        nyquist = sr / 2
        bin_hz = nyquist / S.shape[0]
        
        bass_bound = int(250 / bin_hz)
        mid_bound = int(4000 / bin_hz)
        
        bass_energy = np.mean(S[:bass_bound, :])
        mid_energy = np.mean(S[bass_bound:mid_bound, :])
        high_energy = np.mean(S[mid_bound:, :])
        
        # --- 4. Drop/Impact Detection ---
        # Onset Strength
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_times = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr)
        
        # Calculate energy delta (derivative of RMS)
        rms = librosa.feature.rms(y=y)[0]
        rms_delta = np.diff(rms, prepend=0)
        
        # Find drops: High energy + High onset strength + Sudden increase
        # Simple heuristic: Look for peaks in rms_delta * onset_env (resampled)
        
        # Resample onset_env to match rms length if needed, or vice-versa
        # Librosa features usually align if computed similarly. 
        # onset_strength hop_length defaults to 512, rms defaults to 512.
        
        # Detect 'Impacts' where energy jumps significantly
        threshold = np.std(rms_delta) * 2.5
        impact_frames = np.where(rms_delta > threshold)[0]
        impact_times = librosa.frames_to_time(impact_frames, sr=sr, hop_length=512)
        
        # Filter impacts to only keep significant ones (spaced out)
        drops = []
        if len(impact_times) > 0:
            last_impact = -10.0
            for t in impact_times:
                if t - last_impact > 2.0: # Minimum 2 seconds between "drops"
                    drops.append(float(t))
                    last_impact = t
        
        # --- 5. Emotion Curve (Valence/Arousal Approximation) ---
        # This is hard without a trained model like wav2vec or similar.
        # We will approximate Arousal with Energy (RMS) and Valence with major/minor estimation or brightness
        # This is a very rough heuristic for visualization drivers
        
        emotion_curve = []
        # Downsample for curve (e.g., 1 point per second)
        curve_res = 1.0 # seconds
        total_dur = librosa.get_duration(y=y, sr=sr)
        for t_curr in np.arange(0, total_dur, curve_res):
            # Extract simple features for this second
            t_idx = int(t_curr * sr)
            t_end_idx = int((t_curr + curve_res) * sr)
            chunk = y[t_idx:t_end_idx]
            if len(chunk) == 0: continue
            
            e_rms = np.mean(chunk**2)**0.5
            e_cent = np.mean(librosa.feature.spectral_centroid(y=chunk, sr=sr)) if len(chunk) > 512 else 0
            
            # Normalize roughly
            arousal = min(1.0, e_rms * 5) # Amplify RMS
            valence = min(1.0, e_cent / 5000) # Brightness = Happiness? (Simple heuristic)
            
            emotion_curve.append({
                "time": float(t_curr),
                "arousal": float(arousal),
                "valence": float(valence),
                "tension": float(arousal * 0.8 + (1.0 - valence) * 0.2)
            })

        # --- Statistics ---
        beat_confidence = 0.0 # TODO: Calculate properly if needed
        
        return {
            "bpm": float(tempo),
            "beat_times": final_beats,
            "beat_strengths": [], # Populated if needed
            "onset_times": librosa.frames_to_time(librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr), sr=sr).tolist(),
            "beat_confidence": beat_confidence,
            "tempo_stability": 0.0,
            "energy_stats": {
                "avg": float(np.mean(rms)),
                "max": float(np.max(rms)),
                "bass": float(bass_energy),
                "mid": float(mid_energy),
                "high": float(high_energy)
            },
            "downbeats": downbeats,
            "bars": bars,
            "drops": drops,
            "emotion_curve": emotion_curve
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

    def _generate_video_plan(self, technical_stats: dict[str, Any], duration: float) -> dict[str, Any]:
        """Generate a procedural video plan based on technical analysis."""
        scenes = []
        
        # 1. Create Scenes from Bars
        bars = technical_stats.get("bars", [])
        if bars:
            # Group bars into phrases (e.g. 4 bars)
            bars_per_scene = 4
            for i in range(0, len(bars), bars_per_scene):
                chunk = bars[i:i + bars_per_scene]
                start = chunk[0]["start"]
                end = chunk[-1]["end"]
                
                scenes.append({
                    "start_time": float(start),
                    "end_time": float(end),
                    "description": f"Scene {len(scenes) + 1} (Bars {i+1}-{i+len(chunk)})",
                    "energy_level": 0.5, # Placeholder
                    "keyframes": []
                })
        else:
            # Fallback: 4-second chunks
            chunk_dur = 4.0
            t = 0.0
            while t < duration:
                end_t = min(duration, t + chunk_dur)
                scenes.append({
                    "start_time": float(t),
                    "end_time": float(end_t),
                    "description": f"Scene {len(scenes) + 1}",
                    "energy_level": 0.5,
                    "keyframes": []
                })
                t += chunk_dur

        # 2. Add Keyframes from Drops
        drops = technical_stats.get("drops", [])
        
        for scene in scenes:
            s_start = scene["start_time"]
            s_end = scene["end_time"]
            
            # Drops -> Camera Shake / Impact
            for drop_t in drops:
                if s_start <= drop_t < s_end:
                    scene["keyframes"].append({
                        "time": drop_t,
                        "type": "shake",
                        "description": "Drop impact",
                        "parameters": {"intensity": 1.0}
                    })
            
        return {"scenes": scenes}
    
    def analyze(self, project_id: str, use_batch: bool = True) -> dict[str, Any]:
        """Analyze audio for a project."""
        # Get audio file
        audio_path = self.file_storage.get_audio_path(project_id)
        if not audio_path:
            raise FileNotFoundError(f"No audio file found for project {project_id}")
        
        # Get duration using unified function
        duration = get_audio_duration(audio_path)
        
        # Technical analysis (librosa)
        technical_analysis = _analyze_audio_technical(audio_path)
        
        # Get project info for style and description
        project = self.project_repo.get(project_id) or {}
        user_style = project.get("style", "cinematic")
        user_description = project.get("user_description", "")
        character_description = project.get("character_description", "")
        
        # GenAI analysis logic
        if not use_batch:
            analysis = self.genai.analyze_audio(
                audio_path=audio_path,
                duration=duration,
                technical_analysis=technical_analysis,
                user_style=user_style,
                user_description=user_description,
                character_description=character_description,
                use_batch=False
            )
        else:
            # --- Batch Mode ---
            from .batch_service import BatchService
            batch_service = BatchService()
            
            # 1. Construct the request part
            req_body = self.genai.analyze_audio(
                audio_path=audio_path,
                duration=duration,
                technical_analysis=technical_analysis,
                user_style=user_style,
                user_description=user_description,
                character_description=character_description,
                use_batch=True
            )
            
            # 2. Submit Batch Job
            job_result = batch_service.submit_batch_job(
                requests=[req_body],
                model_name=self.genai.text_model,
                job_name=f"Analysis-{project_id}"
            )
            
            job_name = job_result.get("job_id")
            if not job_name:
                raise RuntimeError("Failed to submit batch job for analysis")
            
            # 3. Wait for completion
            batch_service.wait_for_job(job_name)
            
            # 4. Process Results
            results = batch_service.download_results(job_name)
            if not results:
                raise RuntimeError("Batch analysis failed to return results")
            
            # Parse response - BatchService returns parsed content directly now
            data = results[0]
            if isinstance(data, dict) and "text" in data and "custom_id" in data:
                # Was wrapped as text
                analysis = self.genai._extract_json(data["text"])
            elif isinstance(data, str):
                 analysis = self.genai._extract_json(data)
            else:
                 analysis = data
        
        # Add metadata
        analysis["total_duration"] = duration
        analysis["technical_stats"] = technical_analysis
        analysis["character_description"] = character_description
        
        # Handle Video Plan
        # 1. Procedural plan (always good for Drops/Beats)
        procedural_plan = self._generate_video_plan(technical_analysis, duration)
        
        # 2. Check if AI generated a plan
        if "video_plan" in analysis and analysis["video_plan"]:
            # Trust AI for Scenes, but inject technical Keyframes (drops) if missing
            ai_plan = analysis["video_plan"]
            
            # Ensure structure matches our schema (basic check)
            if isinstance(ai_plan, dict) and "scenes" in ai_plan:
                # Merge procedural keyframes (drops) into AI scenes
                # This ensures we get the "Creative" scenes from AI + "Technical" sync from code
                
                # Get drops from procedural
                drops = technical_analysis.get("drops", [])
                
                for scene in ai_plan["scenes"]:
                    # Type conversion safety
                    s_start = float(scene.get("start_time", 0.0))
                    s_end = float(scene.get("end_time", 0.0))
                    if "keyframes" not in scene:
                        scene["keyframes"] = []
                        
                    # Add drops if they fall in this scene
                    for drop_t in drops:
                        if s_start <= drop_t < s_end:
                            # Check if duplicate keyframe exists nearby
                            has_drop = any(
                                abs(float(k.get("time", 0)) - drop_t) < 0.5 and k.get("type") == "shake" 
                                for k in scene["keyframes"]
                            )
                            if not has_drop:
                                scene["keyframes"].append({
                                    "time": drop_t,
                                    "type": "shake",
                                    "description": "Drop impact (Technical)",
                                    "parameters": {"intensity": 1.0}
                                })
                
                analysis["video_plan"] = ai_plan
                
                # SYNC: Update legacy 'segments' to match the 'video_plan' scenes
                # This ensures the Frontend UI (which uses segments) shows the exact same timing/cuts
                new_segments = []
                for scene in ai_plan["scenes"]:
                    # Create a segment that mirrors the scene
                    new_segments.append({
                        "start_time": float(scene.get("start_time", 0.0)),
                        "end_time": float(scene.get("end_time", 0.0)),
                        "text": scene.get("description", ""), # Use description as text/visual intent
                        "section_type": "scene", # Generic type
                        "emotion": "", # Placeholder, could be extracted if we asked AI
                        "speaker": "",
                        "instrumentation": "",
                        "acoustic_environment": ""
                    })
                
                # If we have valid new segments, overwrite the legacy ones
                if new_segments:
                    analysis["segments"] = new_segments
                    
            else:
                # Malformed AI plan, fallback
                analysis["video_plan"] = procedural_plan
        else:
            # No AI plan, use procedural
            analysis["video_plan"] = procedural_plan
        
        # Save results
        self.project_repo.save_analysis(project_id, analysis)
        
        return analysis
