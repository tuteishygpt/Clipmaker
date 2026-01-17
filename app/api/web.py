"""Web routes for serving frontend."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..core.config import settings

router = APIRouter(tags=["web"])


@router.get("/")
async def index() -> FileResponse:
    """Serve the main HTML page."""
    return FileResponse(settings.frontend_dir / "index.html")
