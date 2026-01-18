"""Segment-related Pydantic schemas."""
from __future__ import annotations

from typing import Optional, List, Any
from pydantic import BaseModel, Field


class SegmentBase(BaseModel):
    """Base segment schema."""
    id: str
    start_time: float
    end_time: float
    lyric_text: str = ""
    visual_intent: str = ""
    camera_angle: str = ""
    emotion: str = ""
    effect: Optional[str] = None


class SegmentResponse(SegmentBase):
    """Segment with additional computed fields for API response."""
    thumbnail: Optional[str] = None
    prompt: Optional[dict] = None


class SegmentUpdate(BaseModel):
    """Schema for updating a segment."""
    start_time: Optional[Any] = None
    end_time: Optional[Any] = None
    lyric_text: Optional[str] = None
    text: Optional[str] = None
    visual_intent: Optional[str] = None
    camera_angle: Optional[str] = None
    emotion: Optional[str] = None
    image_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    style_hints: Optional[str] = None
    effect: Optional[str] = None


class SegmentsResponse(BaseModel):
    """Response containing list of segments."""
    segments: List[SegmentResponse]


class PromptPayload(BaseModel):
    """Prompt data for a segment."""
    image_prompt: str
    negative_prompt: str = ""
    style_hints: str = ""
    version: int = 1
