"""Analysis-related Pydantic schemas."""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class AnalysisSegment(BaseModel):
    """A segment from audio analysis."""
    start_time: float
    end_time: float
    speaker: str = ""
    text: str = ""
    emotion: str = ""
    instrumentation: str = ""
    section_type: str = ""
    acoustic_environment: str = ""


class TechnicalStats(BaseModel):
    """Technical audio analysis from librosa."""
    bpm: Optional[float] = None
    beat_times: List[float] = []
    beat_strengths: List[float] = []  # Normalized strength at each beat
    onset_times: List[float] = []
    beat_confidence: Optional[float] = None
    tempo_stability: Optional[float] = None
    energy_stats: Dict[str, float] = {}


class AudioAnalysis(BaseModel):
    """Full audio analysis result."""
    summary: str = ""
    global_visual_narrative: str = ""
    visual_style_anchor: str = ""
    segments: List[AnalysisSegment] = []
    total_duration: float = 0.0
    technical_stats: Optional[TechnicalStats] = None
    
    class Config:
        extra = "allow"
