"""Clipmaker MVP - FastAPI Application Entry Point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .core.logging import setup_logging
from .api.projects import router as projects_router
from .api.web import router as web_router

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(title="Clipmaker MVP")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
app.mount("/static", StaticFiles(directory=settings.frontend_dir), name="static")

# Include routers
app.include_router(web_router)
app.include_router(projects_router)
