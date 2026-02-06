"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


@dataclass
class Settings:
    """Application settings."""
    
    # GenAI
    genai_api_key: str | None = None
    genai_text_model: str = "gemini-2.5-flash"
    genai_image_model: str = "gemini-2.5-flash-image"
    genai_subtitle_model: str = "gemini-2.5-flash"
    genai_text_mode: str = "standard"
    genai_image_mode: str = "standard"
    
    # Validation
    max_audio_duration_minutes: int = 10
    
    # Supabase
    supabase_url: str | None = None
    supabase_key: str | None = None  # Service role key for backend
    supabase_jwt_secret: str | None = None
    supabase_jwt_public_key: str | None = None
    
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
            genai_subtitle_model=os.getenv("GENAI_SUBTITLE_MODEL", "gemini-2.5-flash"),
            genai_text_mode=os.getenv("GENAI_TEXT_MODE", "standard"),
            genai_image_mode=os.getenv("GENAI_IMAGE_MODE", "standard"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY"),
            supabase_jwt_secret=(os.getenv("SUPABASE_JWT_SECRET") or "").strip().strip('"').strip("'"),
            supabase_jwt_public_key=(os.getenv("SUPABASE_JWT_PUBLIC_KEY") or "").replace("\\n", "\n").strip().strip('"').strip("'"),
            base_dir=base_dir,
            data_dir=base_dir / "data" / "projects",
            frontend_dir=base_dir / "frontend-react" / "dist",
        )
    
    @property
    def supabase_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(self.supabase_url and self.supabase_key)


# Global settings instance
settings = Settings.from_env()
