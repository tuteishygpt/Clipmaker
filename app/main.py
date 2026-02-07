"""Studio MVP - FastAPI Application Entry Point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .core.logging import setup_logging
from .api.projects import router as projects_router
from .api.cabinet import router as cabinet_router
from .api.web import router as web_router

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(title="Studio MVP")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hukflow.com",
        "https://www.hukflow.com",
        "http://hukflow.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend assets)
# We mount /assets to point to dist/assets
app.mount("/assets", StaticFiles(directory=settings.frontend_dir / "assets"), name="assets")

# Mount project files (videos, images, etc.)
# This allows serving generated videos and images from /projects/{project_id}/...
if settings.data_dir.exists():
    app.mount("/projects", StaticFiles(directory=settings.data_dir), name="projects")

# Include routers
app.include_router(web_router)
app.include_router(projects_router)
app.include_router(cabinet_router)
