"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Application settings."""
    
    # GenAI
    genai_api_key: str | None = None
    genai_text_model: str = "gemini-2.5-flash"
    genai_image_model: str = "gemini-2.5-flash-image"
    genai_text_mode: str = "standard"
    genai_image_mode: str = "standard"
    
    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = base_dir / "data" / "projects"
    frontend_dir: Path = base_dir / "frontend"
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        return cls(
            genai_api_key=os.getenv("GENAI_API_KEY"),
            genai_text_model=os.getenv("GENAI_TEXT_MODEL", "gemini-2.5-flash"),
            genai_image_model=os.getenv("GENAI_IMAGE_MODEL", "gemini-2.5-flash-image"),
            genai_text_mode=os.getenv("GENAI_TEXT_MODE", "standard"),
            genai_image_mode=os.getenv("GENAI_IMAGE_MODE", "standard"),
            base_dir=base_dir,
            data_dir=base_dir / "data" / "projects",
            frontend_dir=base_dir / "frontend",
        )


# Global settings instance
settings = Settings.from_env()
