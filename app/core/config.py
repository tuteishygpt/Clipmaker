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
    
    # GenAI & Vertex AI
    genai_api_key: str | None = None
    genai_text_model: str = "gemini-2.5-flash"
    genai_image_model: str = "gemini-2.5-flash-image"
    genai_subtitle_model: str = "gemini-3.5-transcribe"
    genai_text_mode: str = "standard"
    genai_image_mode: str = "standard"
    
    # Google Cloud Vertex AI
    google_genai_use_vertexai: bool = True
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    google_service_account_json: str | None = None
    google_service_account_json_b64: str | None = None
    google_application_credentials: str | None = None
    
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
        use_vertex_env = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", os.getenv("VERTEXAI", "true")).strip().lower()
        use_vertex = use_vertex_env not in ("0", "false", "no")
        return cls(
            genai_api_key=os.getenv("GENAI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("gemini") or os.getenv("gembeh"),
            genai_text_model=os.getenv("GENAI_TEXT_MODEL", "gemini-2.5-flash"),
            genai_image_model=os.getenv("GENAI_IMAGE_MODEL", "gemini-2.5-flash-image"),
            genai_subtitle_model=os.getenv("GENAI_SUBTITLE_MODEL") or os.getenv("mod", "gemini-3.5-transcribe"),
            genai_text_mode=os.getenv("GENAI_TEXT_MODE", "standard"),
            genai_image_mode=os.getenv("GENAI_IMAGE_MODE", "standard"),
            google_genai_use_vertexai=use_vertex,
            google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_PROJECT"),
            google_cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_VERTEX_LOCATION") or "global",
            google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
            google_service_account_json_b64=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64"),
            google_application_credentials=os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_FILE"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY"),
            supabase_jwt_secret=(os.getenv("SUPABASE_JWT_SECRET") or "").strip().strip('"').strip("'"),
            supabase_jwt_public_key=(os.getenv("SUPABASE_JWT_PUBLIC_KEY") or "").replace("\\n", "\n").strip().strip('"').strip("'"),
            base_dir=base_dir,
            data_dir=Path(os.getenv("PROJECTS_DATA_DIR")) if os.getenv("PROJECTS_DATA_DIR") else base_dir / "data" / "projects",
            frontend_dir=base_dir / "frontend-react" / "dist",
        )
    
    @property
    def supabase_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(self.supabase_url and self.supabase_key)


# Global settings instance
settings = Settings.from_env()
