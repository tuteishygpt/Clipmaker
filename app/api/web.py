"""Web routes for serving frontend."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..core.config import settings

router = APIRouter(tags=["web"])


class ShowcaseItem(BaseModel):
    """A showcase video item for the landing page."""
    id: str
    title: str
    format: str  # "9:16", "16:9", "1:1"
    style: str
    video_url: str
    thumbnail_url: Optional[str] = None


@router.get("/")
async def index() -> FileResponse:
    """Serve the main HTML page."""
    return FileResponse(settings.frontend_dir / "index.html")


@router.get("/showcase", response_model=List[ShowcaseItem])
async def get_showcase_videos() -> List[ShowcaseItem]:
    """
    Get a list of showcase videos for the landing page.
    
    Returns up to 6 completed projects with rendered videos.
    """
    showcase_items = []
    projects_dir = settings.data_dir
    
    if not projects_dir.exists():
        return []
    
    # Scan for projects with completed renders
    for project_folder in projects_dir.iterdir():
        if not project_folder.is_dir():
            continue
            
        project_json = project_folder / "project.json"
        renders_dir = project_folder / "renders"
        
        if not project_json.exists() or not renders_dir.exists():
            continue
        
        # Find the latest render
        renders = list(renders_dir.glob("final_v*.mp4"))
        if not renders:
            continue
            
        # Sort by version number to get the latest
        renders.sort(key=lambda x: int(x.stem.split("_v")[1]), reverse=True)
        latest_render = renders[0]
        
        try:
            with open(project_json, "r", encoding="utf-8") as f:
                project_data = json.load(f)
        except Exception:
            continue
        
        # Skip if not completed
        if project_data.get("status") != "DONE":
            continue
        
        project_id = project_data.get("id", project_folder.name)
        
        # Generate a title from description or use default
        description = project_data.get("user_description", "")
        if description:
            title = description[:50].strip()
            if len(description) > 50:
                title += "..."
        else:
            title = f"Video #{len(showcase_items) + 1}"
        
        # Check for a preview image
        images_dir = project_folder / "images"
        thumbnail_url = None
        if images_dir.exists():
            preview_images = list(images_dir.glob("seg_*_v*.png"))
            if preview_images:
                # Get first segment's latest version as thumbnail
                preview_images.sort()
                thumbnail_url = f"/projects/{project_id}/images/{preview_images[0].name}"
        
        showcase_items.append(ShowcaseItem(
            id=project_id,
            title=title,
            format=project_data.get("format", "16:9"),
            style=project_data.get("style", "cinematic"),
            video_url=f"/projects/{project_id}/renders/{latest_render.name}",
            thumbnail_url=thumbnail_url
        ))
        
        # Limit to 6 items
        if len(showcase_items) >= 6:
            break
    
    return showcase_items
