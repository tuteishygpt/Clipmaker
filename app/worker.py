from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
import tempfile
import time

from .core.config import settings
from .core.logging import get_logger, setup_logging
from .repositories.file_storage import FileStorage
from .repositories.project_repo import ProjectRepository
from .services.pipeline_service import PipelineService
from .services.render_service import RenderService

logger = get_logger(__name__)


async def run_worker(project_id: str, mode: str = "render") -> None:
    """Run the worker in the specified mode for project_id."""
    logger.info(f"Worker started: project_id={project_id}, mode={mode}, storage_backend={settings.storage_backend}")

    try:
        if settings.storage_backend == "s3":
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_data_dir = Path(temp_dir) / "data" / "projects"
                project_dir = temp_data_dir / project_id
                project_dir.mkdir(parents=True, exist_ok=True)

                file_storage = FileStorage(data_dir=temp_data_dir)
                project_repo = ProjectRepository(data_dir=temp_data_dir)

                # 1. Download manifest and assets from S3/R2
                logger.info(f"Downloading assets for project {project_id} from S3/R2...")
                file_storage.download_project_assets(project_id, project_dir)
                project_repo.load_manifest_from_storage(project_id, project_dir)

                # 2. Render locally inside temp directory
                output_path: Path | None = None
                duration: float = 0.0

                if mode == "render":
                    logger.info(f"Executing storyboard render for project {project_id}...")
                    render_service = RenderService(project_repo, file_storage)
                    output_path, duration = render_service.render(project_id)

                elif mode == "standalone":
                    logger.info(f"Executing standalone render for project {project_id}...")
                    video_path = file_storage.get_video_path(project_id)
                    if not video_path or not video_path.exists():
                        raise FileNotFoundError(f"Video file not found for standalone render in {project_dir}")
                    render_service = RenderService(project_repo, file_storage)
                    output_path, duration = render_service.render_standalone_video(project_id, video_path)

                elif mode == "pipeline":
                    logger.info(f"Executing pipeline for project {project_id}...")
                    pipeline_service = PipelineService(project_repo, file_storage)
                    result_path = await pipeline_service.run_full_pipeline(project_id)
                    output_path = Path(result_path) if result_path else None
                    duration = 0.0

                else:
                    raise ValueError(f"Unknown worker mode: {mode}")

                # 3. Upload rendered MP4 back to S3/R2
                if output_path and output_path.exists():
                    logger.info(f"Uploading render result {output_path.name} to S3/R2...")
                    s3_key = file_storage.upload_render_result(project_id, output_path)
                    logger.info(f"Upload complete: {s3_key}")

                    project_repo.update(project_id, {
                        "status": "DONE",
                        "video_output": f"/projects/{project_id}/rendered-video",
                    })
                    project_repo.update_job(project_id, "render", {
                        "status": "DONE",
                        "progress": 100,
                        "output": s3_key,
                        "output_path": s3_key,
                        "render_duration_seconds": round(duration, 1),
                    })
                    project_repo.save_manifest_to_storage(project_id)

        else:
            # Local filesystem fallback
            file_storage = FileStorage()
            project_repo = ProjectRepository()

            if mode == "render":
                pipeline_service = PipelineService(project_repo, file_storage)
                await pipeline_service.render_only(project_id)

            elif mode == "standalone":
                video_path = file_storage.get_video_path(project_id)
                if not video_path or not video_path.exists():
                    raise FileNotFoundError(f"Video file not found for standalone render: project {project_id}")
                render_service = RenderService(project_repo, file_storage)
                project_repo.update_job(project_id, "render", {"status": "RUNNING", "progress": 0})
                output_path, duration = render_service.render_standalone_video(project_id, video_path)
                project_repo.update_job(project_id, "render", {
                    "status": "DONE",
                    "progress": 100,
                    "output_path": str(output_path),
                    "output": str(output_path),
                    "render_duration": duration,
                })
                project_repo.update(project_id, {
                    "status": "DONE",
                    "video_output": f"/projects/{project_id}/renders/{output_path.name}",
                })

            elif mode == "pipeline":
                pipeline_service = PipelineService(project_repo, file_storage)
                await pipeline_service.run_full_pipeline(project_id)

            else:
                raise ValueError(f"Unknown worker mode: {mode}")

        logger.info(f"Worker successfully finished processing project {project_id} (mode={mode})")

    except Exception as exc:
        logger.error(f"Worker execution failed for project {project_id}: {exc}", exc_info=True)
        # Attempt to record failure in project repo
        try:
            repo = ProjectRepository()
            repo.update_job(project_id, "render", {
                "status": "FAILED",
                "error": str(exc),
            })
            repo.update(project_id, {"status": "FAILED"})
        except Exception:
            pass
        sys.exit(1)


def main() -> None:
    """CLI entry point for worker."""
    setup_logging()
    parser = argparse.ArgumentParser(description="Studio worker")
    parser.add_argument("--project_id", required=True, help="Project ID to process")
    parser.add_argument(
        "--mode",
        choices=["render", "standalone", "pipeline"],
        default="render",
        help="Worker mode: render, standalone, or pipeline (default: render)",
    )
    args = parser.parse_args()
    asyncio.run(run_worker(project_id=args.project_id, mode=args.mode))


if __name__ == "__main__":
    main()
