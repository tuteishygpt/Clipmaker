"""Project-related Pydantic schemas."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    format: str = Field(default="9:16", description="Video format ratio")
    style: str = Field(default="cinematic", description="Visual style preset")
    subtitles: bool = Field(default=True, description="Whether to include subtitles")
    user_description: str = Field(default="", description="User's description of the clip idea")
    character_description: str = Field(default="", description="Description of the consistent character")
    render_preset: str = Field(default="fast", description="Encoding preset: fast, veryfast, ultrafast")


class ProjectResponse(BaseModel):
    """Schema for project API responses."""
    id: str
    created_at: str
    updated_at: str
    status: str
    format: str
    style: str
    subtitles: bool
    user_description: str = ""
    character_description: str = ""
    render_preset: str = "fast"
    video_output: Optional[str] = None
    
    class Config:
        extra = "allow"


class ProjectUpdate(BaseModel):
    """Schema for updating project fields."""
    format: Optional[str] = None
    style: Optional[str] = None
    subtitles: Optional[bool] = None
    user_description: Optional[str] = None
    character_description: Optional[str] = None
    status: Optional[str] = None
    render_preset: Optional[str] = None
