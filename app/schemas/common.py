"""Common response schemas."""
from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel


class RunResponse(BaseModel):
    """Generic response for async operations."""
    status: str
    message: str


class JobStatus(BaseModel):
    """Job status information."""
    status: str
    step: str = ""
    progress: int = 0
    error: Optional[str] = None
    output: Optional[str] = None
    updated_at: Optional[str] = None


class JobsResponse(BaseModel):
    """Response containing job statuses."""
    jobs: Dict[str, JobStatus]
