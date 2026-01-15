from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    format: str = Field(default="9:16")
    style: str = Field(default="cinematic")
    subtitles: bool = Field(default=True)


class ProjectResponse(BaseModel):
    id: str
    created_at: str
    updated_at: str
    status: str
    format: str
    style: str
    subtitles: bool


class SegmentUpdate(BaseModel):
    visual_intent: Optional[str] = None
    image_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    style_hints: Optional[str] = None


class RunResponse(BaseModel):
    status: str
    message: str
