"""File storage for binary assets (images, audio, video)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO, Any

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class FileStorage:
    """Storage for binary files supporting local filesystem and S3/R2."""
    
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or settings.data_dir
        self._s3_client: Any = None
    
    # ==================== Cloud (S3/R2) Methods ====================

    def get_s3_client(self) -> Any:
        """Get or initialize boto3 S3 client."""
        if self._s3_client is not None:
            return self._s3_client
            
        import boto3
        from botocore.config import Config

        is_r2 = bool(settings.s3_endpoint_url and "r2.cloudflarestorage.com" in settings.s3_endpoint_url)
        region = "auto" if is_r2 else "us-east-1"

        self._s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )
        return self._s3_client

    def upload_file(self, local_path: Path | str, s3_key: str, content_type: str | None = None) -> str:
        """Upload a local file to S3/R2."""
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"Local file not found for S3 upload: {path}")
        
        extra_args: dict[str, Any] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        else:
            suffix = path.suffix.lower()
            if suffix == ".mp4":
                extra_args["ContentType"] = "video/mp4"
            elif suffix == ".png":
                extra_args["ContentType"] = "image/png"
            elif suffix in (".wav", ".mp3"):
                extra_args["ContentType"] = "audio/wav" if suffix == ".wav" else "audio/mpeg"
            elif suffix == ".json":
                extra_args["ContentType"] = "application/json"
            elif suffix == ".srt":
                extra_args["ContentType"] = "text/plain; charset=utf-8"

        client = self.get_s3_client()
        client.upload_file(
            Filename=str(path),
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            ExtraArgs=extra_args if extra_args else None,
        )
        logger.info(f"Uploaded file to s3://{settings.s3_bucket_name}/{s3_key}")
        return s3_key

    def download_file(self, s3_key: str, local_target_path: Path | str) -> Path:
        """Download an S3 object to local target path."""
        target = Path(local_target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        client = self.get_s3_client()
        client.download_file(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Filename=str(target),
        )
        logger.info(f"Downloaded s3://{settings.s3_bucket_name}/{s3_key} -> {target}")
        return target

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned GET URL for an S3 object."""
        client = self.get_s3_client()
        return client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": s3_key,
            },
            ExpiresIn=expires_in,
        )

    def get_presigned_put_url(self, s3_key: str, content_type: str = "video/mp4", expires_in: int = 3600) -> str:
        """Generate a presigned PUT URL for direct upload to S3/R2."""
        client = self.get_s3_client()
        return client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )

    def get_source_video_s3_key(self, project_id: str) -> str | None:
        """Find source video S3 key if present."""
        if not settings.s3_bucket_name:
            return None
        client = self.get_s3_client()
        for ext in [".mp4", ".mov", ".webm", ".avi"]:
            s3_key = f"projects/{project_id}/source/video{ext}"
            try:
                client.head_object(Bucket=settings.s3_bucket_name, Key=s3_key)
                return s3_key
            except Exception:
                continue
        return None

    def download_project_assets(self, project_id: str, target_dir: Path | str) -> list[Path]:
        """Download all files for a project from S3/R2 to target_dir."""
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        client = self.get_s3_client()

        prefixes = [f"projects/{project_id}/", f"{project_id}/"]
        downloaded: list[Path] = []

        for prefix in prefixes:
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=settings.s3_bucket_name, Prefix=prefix):
                contents = page.get("Contents", [])
                for obj in contents:
                    key = obj.get("Key", "")
                    if not key or key.endswith("/"):
                        continue
                    rel_path = key[len(prefix):]
                    local_dest = target_path / rel_path
                    self.download_file(key, local_dest)
                    downloaded.append(local_dest)
            if downloaded:
                break

        return downloaded

    def upload_render_result(self, project_id: str, local_video_path: Path | str) -> str:
        """Upload a rendered video to S3 and return the S3 key."""
        path = Path(local_video_path)
        s3_key = f"projects/{project_id}/renders/{path.name}"
        self.upload_file(path, s3_key, content_type="video/mp4")
        return s3_key

    def get_render_s3_key(self, project_id: str, render_name: str) -> str:
        """Get standard S3 key for a specific render."""
        return f"projects/{project_id}/renders/{render_name}"

    def get_latest_render_key(self, project_id: str) -> str | None:
        """Find the latest render S3 key for a project."""
        if not settings.s3_bucket_name:
            return None
        client = self.get_s3_client()
        prefixes = [f"projects/{project_id}/renders/", f"{project_id}/renders/"]
        candidates: list[tuple[Any, str]] = []
        for prefix in prefixes:
            try:
                resp = client.list_objects_v2(Bucket=settings.s3_bucket_name, Prefix=prefix)
                for obj in resp.get("Contents", []):
                    key = obj.get("Key", "")
                    if key.endswith(".mp4"):
                        candidates.append((obj.get("LastModified"), key))
            except Exception as e:
                logger.warning(f"Error querying S3 renders with prefix {prefix}: {e}")
            if candidates:
                break
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    # ==================== Local Storage Methods ====================

    def _project_path(self, project_id: str) -> Path:
        """Get the base path for a project."""
        return self.data_dir / project_id
    
    def save_audio(self, project_id: str, file: BinaryIO, filename: str) -> Path:
        """Save an uploaded audio file."""
        source_dir = self._project_path(project_id) / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        
        extension = Path(filename).suffix or ".wav"
        target = source_dir / f"track{extension}"
        
        with target.open("wb") as buffer:
            shutil.copyfileobj(file, buffer)
        
        if settings.storage_backend == "s3":
            try:
                self.upload_file(target, f"projects/{project_id}/source/{target.name}")
            except Exception as e:
                logger.warning(f"Failed to upload audio to S3: {e}")

        return target
    
    def get_audio_path(self, project_id: str) -> Path | None:
        """Get the audio file path for a project."""
        source_dir = self._project_path(project_id) / "source"
        if source_dir.exists():
            for file_path in source_dir.glob("track.*"):
                return file_path
        
        if settings.storage_backend == "s3":
            client = self.get_s3_client()
            for ext in [".wav", ".mp3"]:
                s3_key = f"projects/{project_id}/source/track{ext}"
                try:
                    client.head_object(Bucket=settings.s3_bucket_name, Key=s3_key)
                    local_target = source_dir / f"track{ext}"
                    self.download_file(s3_key, local_target)
                    return local_target
                except Exception:
                    continue
        return None
    
    def save_image(self, project_id: str, seg_id: str, version: int, data: bytes) -> Path:
        """Save a generated image."""
        images_dir = self._project_path(project_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        filename = images_dir / f"{seg_id}_v{version}.png"
        filename.write_bytes(data)

        if settings.storage_backend == "s3":
            try:
                self.upload_file(filename, f"projects/{project_id}/images/{filename.name}")
            except Exception as e:
                logger.warning(f"Failed to upload image to S3: {e}")

        return filename
    
    def get_image_path(self, project_id: str, image_name: str) -> Path | None:
        """Get an image file path."""
        path = self._project_path(project_id) / "images" / image_name
        return path if path.exists() else None
    
    def get_latest_render(self, project_id: str) -> Path | None:
        """Get the latest rendered video."""
        renders_dir = self._project_path(project_id) / "renders"
        if not renders_dir.exists():
            return None
        
        mp4_files = sorted(
            renders_dir.glob("*.mp4"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        return mp4_files[0] if mp4_files else None
    
    def get_render_path(self, project_id: str, render_name: str) -> Path | None:
        """Get a specific render file path."""
        path = self._project_path(project_id) / "renders" / render_name
        return path if path.exists() else None
    
    def get_next_render_path(self, project_id: str) -> Path:
        """Get the path for the next render version."""
        renders_dir = self._project_path(project_id) / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)
        
        existing = sorted(renders_dir.glob("final_v*.mp4"))
        next_version = len(existing) + 1
        return renders_dir / f"final_v{next_version}.mp4"

    def get_max_version(self, project_id: str, seg_id: str) -> int:
        """Get the highest image version for a segment."""
        images_dir = self._project_path(project_id) / "images"
        if not images_dir.exists():
            return 0
        
        max_v = 0
        prefix = f"{seg_id}_v"
        suffix = ".png"
        
        for file in images_dir.glob(f"{seg_id}_v*.png"):
            name = file.name
            try:
                if name.startswith(prefix) and name.endswith(suffix):
                    v_str = name[len(prefix):-len(suffix)]
                    v = int(v_str)
                    if v > max_v:
                        max_v = v
            except ValueError:
                continue
                
        return max_v

    # ==================== Subtitle Storage Methods ====================
    
    def save_subtitles(self, project_id: str, content: str) -> Path:
        """Save SRT content to file."""
        subs_dir = self._project_path(project_id) / "subtitles"
        subs_dir.mkdir(parents=True, exist_ok=True)
        path = subs_dir / "subtitles.srt"
        path.write_text(content, encoding="utf-8")

        if settings.storage_backend == "s3":
            try:
                self.upload_file(path, f"projects/{project_id}/subtitles/{path.name}")
            except Exception as e:
                logger.warning(f"Failed to upload subtitles to S3: {e}")

        return path
    
    def get_subtitles_path(self, project_id: str) -> Path | None:
        """Get path to SRT file."""
        subs_dir = self._project_path(project_id) / "subtitles"
        path = subs_dir / "subtitles.srt"
        if path.exists():
            return path
        if settings.storage_backend == "s3":
            try:
                self.download_file(f"projects/{project_id}/subtitles/subtitles.srt", path)
                return path
            except Exception:
                pass
        return None
    
    def save_subtitle_styling(self, project_id: str, styling: dict) -> Path:
        """Save subtitle styling config as JSON."""
        import json
        subs_dir = self._project_path(project_id) / "subtitles"
        subs_dir.mkdir(parents=True, exist_ok=True)
        path = subs_dir / "styling.json"
        path.write_text(json.dumps(styling, indent=2), encoding="utf-8")

        if settings.storage_backend == "s3":
            try:
                self.upload_file(path, f"projects/{project_id}/subtitles/{path.name}")
            except Exception as e:
                logger.warning(f"Failed to upload subtitle styling to S3: {e}")

        return path
    
    def get_subtitle_styling(self, project_id: str) -> dict | None:
        """Load subtitle styling config from JSON."""
        import json
        subs_dir = self._project_path(project_id) / "subtitles"
        path = subs_dir / "styling.json"
        if not path.exists() and settings.storage_backend == "s3":
            try:
                self.download_file(f"projects/{project_id}/subtitles/styling.json", path)
            except Exception:
                pass
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None
    
    def save_subtitle_words(self, project_id: str, words: list[dict]) -> Path:
        """Save word-level timestamps as JSON."""
        import json
        subs_dir = self._project_path(project_id) / "subtitles"
        subs_dir.mkdir(parents=True, exist_ok=True)
        path = subs_dir / "words.json"
        path.write_text(json.dumps(words, indent=2, ensure_ascii=False), encoding="utf-8")

        if settings.storage_backend == "s3":
            try:
                self.upload_file(path, f"projects/{project_id}/subtitles/{path.name}")
            except Exception as e:
                logger.warning(f"Failed to upload subtitle words to S3: {e}")

        return path

    def get_subtitle_words(self, project_id: str) -> list[dict] | None:
        """Load word-level timestamps from JSON."""
        import json
        subs_dir = self._project_path(project_id) / "subtitles"
        path = subs_dir / "words.json"
        if not path.exists() and settings.storage_backend == "s3":
            try:
                self.download_file(f"projects/{project_id}/subtitles/words.json", path)
            except Exception:
                pass
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def delete_subtitles(self, project_id: str) -> None:
        """Delete all subtitle files for a project."""
        subs_dir = self._project_path(project_id) / "subtitles"
        if subs_dir.exists():
            shutil.rmtree(subs_dir)
    
    # ==================== Standalone Video Storage ====================
    
    def save_video(self, project_id: str, file: BinaryIO, filename: str) -> Path:
        """Save an uploaded video file for standalone subtitle mode."""
        source_dir = self._project_path(project_id) / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        
        extension = Path(filename).suffix or ".mp4"
        target = source_dir / f"video{extension}"
        
        with target.open("wb") as buffer:
            shutil.copyfileobj(file, buffer)

        if settings.storage_backend == "s3":
            try:
                self.upload_file(target, f"projects/{project_id}/source/{target.name}")
            except Exception as e:
                logger.warning(f"Failed to upload video to S3: {e}")
        
        return target
    
    def get_video_path(self, project_id: str) -> Path | None:
        """Get the video file path for a project (source video or rendered output)."""
        source_dir = self._project_path(project_id) / "source"
        if source_dir.exists():
            for file_path in source_dir.glob("video.*"):
                return file_path
        
        # If not present locally and in S3 mode, download from S3
        if settings.storage_backend == "s3":
            client = self.get_s3_client()
            for ext in [".mp4", ".mov", ".webm", ".avi"]:
                s3_key = f"projects/{project_id}/source/video{ext}"
                try:
                    client.head_object(Bucket=settings.s3_bucket_name, Key=s3_key)
                    local_target = source_dir / f"video{ext}"
                    self.download_file(s3_key, local_target)
                    return local_target
                except Exception:
                    continue

        # Fallback to latest render if available (e.g. for Studio-generated projects)
        return self.get_latest_render(project_id)
