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
    genai_image_rpm: int = 5
    
    # Google Cloud Vertex AI
    google_genai_use_vertexai: bool = True
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    google_service_account_json: str | None = None
    google_service_account_json_b64: str | None = None
    google_application_credentials: str | None = None
    
    # Validation
    max_audio_duration_minutes: int = 10

    # Render & Storage Backends (Cloud Run / S3 / R2)
    render_backend: str = "local"  # "local", "cloud_run"
    storage_backend: str = "local"  # "local", "s3"
    gcp_project_id: str | None = None
    gcp_region: str = "us-central1"
    cloud_run_job_name: str = "clipmaker-render"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket_name: str | None = None
    
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
            genai_image_rpm=int(os.getenv("GENAI_IMAGE_RPM", "5")),
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
            render_backend=os.getenv("RENDER_BACKEND", "local").strip().lower(),
            storage_backend=os.getenv("STORAGE_BACKEND", "local").strip().lower(),
            gcp_project_id=os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_PROJECT"),
            gcp_region=os.getenv("GCP_REGION", "us-central1"),
            cloud_run_job_name=os.getenv("CLOUD_RUN_JOB_NAME", "clipmaker-render"),
            s3_endpoint_url=os.getenv("S3_ENDPOINT_URL") or os.getenv("R2_ENDPOINT_URL"),
            s3_access_key_id=os.getenv("S3_ACCESS_KEY_ID") or os.getenv("R2_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID"),
            s3_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY") or os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY"),
            s3_bucket_name=os.getenv("S3_BUCKET_NAME") or os.getenv("R2_BUCKET_NAME"),
        )
    
    @property
    def supabase_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(self.supabase_url and self.supabase_key)


# Global settings instance
settings = Settings.from_env()
