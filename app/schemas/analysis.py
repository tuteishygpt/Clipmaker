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
    downbeats: List[float] = []
    bars: List[Dict[str, Any]] = []
    phrases: List[Dict[str, Any]] = []
    drops: List[float] = []
    emotion_curve: List[Dict[str, float]] = []



class VideoKeyframe(BaseModel):
    """A specific point in time with visual instructions."""
    time: float
    type: str  # "cut", "zoom", "shake", "beat"
    description: str = ""
    parameters: Dict[str, Any] = {}


class VideoScene(BaseModel):
    """A visual scene corresponding to an audio section."""
    start_time: float
    end_time: float
    description: str = ""
    energy_level: float = 0.5
    keyframes: List[VideoKeyframe] = []


class VideoPlan(BaseModel):
    """Structured plan for video generation."""
    scenes: List[VideoScene] = []
    
    
class AudioAnalysis(BaseModel):
    """Full audio analysis result."""
    summary: str = ""
    global_visual_narrative: str = ""
    visual_style_anchor: str = ""
    segments: List[AnalysisSegment] = []
    total_duration: float = 0.0
    technical_stats: Optional[TechnicalStats] = None
    video_plan: Optional[VideoPlan] = None
    
    class Config:
        extra = "allow"
