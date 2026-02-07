"""Project API routes."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from ..schemas.project import ProjectCreate, ProjectResponse
from ..schemas.segment import SegmentUpdate
from ..schemas.common import RunResponse
from ..repositories.project_repo import ProjectRepository
from ..repositories.file_storage import FileStorage
from ..services.pipeline_service import PipelineService
from ..services.image_service import ImageService
from ..services.story_service import StoryboardService
from ..services.subtitle_service import SubtitleService
from ..services.billing_service import billing_service
from ..schemas.subtitle import (
    SubtitleEntry,
    SubtitleStyling,
    SubtitleUpdate,
    SubtitleResponse,
    SubtitleGenerateRequest,
    get_available_fonts,
)
from ..core.logging import get_logger
from ..core.config import settings
from ..core.billing import (
    BillingContext,
    get_billing_context,
    require_can_generate,
    deduct_generation_credits,
    refund_generation_credits,
)
from ..core.auth import AuthenticatedUser, get_optional_user
from ..core.audio_utils import (
    validate_audio_format,
    get_audio_duration,
    parse_time,
    AudioValidationError,
    AudioLoadError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

# Initialize dependencies
project_repo = ProjectRepository()
file_storage = FileStorage()

def get_pipeline_service() -> PipelineService:
    return PipelineService(project_repo, file_storage)

def get_image_service() -> ImageService:
    return ImageService(project_repo=project_repo, file_storage=file_storage)

def get_story_service() -> StoryboardService:
    return StoryboardService(project_repo=project_repo)

def get_subtitle_service() -> SubtitleService:
    return SubtitleService(project_repo=project_repo, file_storage=file_storage)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    search: Optional[str] = None,
    user: Optional[AuthenticatedUser] = Depends(get_optional_user)
) -> list[dict[str, Any]]:
    """List projects (optionally filtered by user or search query)."""
    return project_repo.list_all(search=search)


@router.post("", response_model=ProjectResponse)
async def create_project(
    payload: ProjectCreate,
    user: Optional[AuthenticatedUser] = Depends(get_optional_user)
) -> dict[str, Any]:
    """Create a new project and link it to user if authenticated."""
    project = project_repo.create(payload.model_dump())
    
    if user:
        await billing_service.link_user_project(
            user_id=user.id,
            project_id=project["id"],
            title=project.get("title") or f"Project {project['id'][:8]}",
            settings=payload.model_dump()
        )
        logger.info(f"Linked new project {project['id']} to user {user.id}")
        
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> dict[str, Any]:
    """Get project details."""
    project = project_repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check for existing video render
    latest_render = file_storage.get_latest_render(project_id)
    if latest_render:
        project["video_output"] = f"/projects/{project_id}/renders/{latest_render.name}"
    
    return project


@router.post("/{project_id}/upload", response_model=RunResponse)
async def upload_audio(project_id: str, audio: UploadFile = File(...)) -> RunResponse:
    """Upload audio file for a project."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate audio format BEFORE saving
    try:
        validate_audio_format(audio.content_type, audio.filename)
    except AudioValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    project_repo.ensure_dirs(project_id)
    audio_path = file_storage.save_audio(project_id, audio.file, audio.filename or "track.wav")
    
    # Validate Duration using unified function
    try:
        duration = get_audio_duration(audio_path)
        
        max_duration_seconds = settings.max_audio_duration_minutes * 60
        if duration > max_duration_seconds:
            # Delete the file if it exceeds the limit
            try:
                if audio_path.exists():
                    audio_path.unlink()
            except Exception as delete_err:
                logger.error(f"Failed to delete rejected audio file: {delete_err}")
                
            raise HTTPException(
                status_code=400, 
                detail=f"Audio duration ({duration:.1f}s) exceeds maximum allowed ({settings.max_audio_duration_minutes} min)."
            )
            
    except AudioLoadError as e:
        # Delete invalid file
        try:
            if audio_path.exists():
                audio_path.unlink()
        except Exception as delete_err:
            logger.error(f"Failed to delete invalid audio file: {delete_err}")
        raise HTTPException(status_code=400, detail=f"Invalid audio file: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected audio validation error: {e}")
        # Keep the file but log the issue
        pass

    project_repo.update(project_id, {"status": "UPLOADED"})
    
    return RunResponse(status="OK", message="Audio uploaded")


@router.post("/{project_id}/run", response_model=RunResponse)
async def run_project(
    project_id: str,
    background: BackgroundTasks,
    billing: BillingContext = Depends(require_can_generate),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
) -> RunResponse:
    """
    Start the video generation pipeline.
    
    Requires authentication and sufficient credits when billing is enabled.
    Credits will be deducted based on the number of segments.
    """
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify user has minimum credits to start (e.g. 5)
    # The actual amount will be deducted in the pipeline once segments are generated
    billing.require_credits(5)
    
    # Store billing info for the pipeline
    project_repo.update(project_id, {
        "status": "RUNNING",
        "billing_user_id": billing.user.id if billing.user else None
    })
    project_repo.update_job(project_id, "pipeline", {"status": "RUNNING", "step": "queued"})
    
    background.add_task(pipeline_service.run_full_pipeline, project_id)
    
    return RunResponse(
        status="OK",
        message="Pipeline started (credits will be deducted during generation)"
    )


@router.get("/{project_id}/analysis")
async def get_analysis(project_id: str) -> dict[str, Any]:
    """Get audio analysis results. Returns empty object if not ready yet."""
    analysis = project_repo.get_analysis(project_id)
    # Return empty object instead of 404 to support progressive loading
    return analysis or {}


@router.get("/{project_id}/audio")
async def get_project_audio(project_id: str) -> FileResponse:
    """Get the project's audio file."""
    audio_path = file_storage.get_audio_path(project_id)
    if not audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    media_type = "audio/wav"
    if audio_path.suffix == ".mp3":
        media_type = "audio/mpeg"
    
    return FileResponse(audio_path, media_type=media_type)


@router.get("/{project_id}/segments")
async def get_segments(project_id: str) -> dict[str, Any]:
    """Get storyboard segments."""
    segments = project_repo.get_segments(project_id)
    if not segments:
        # Return empty list instead of 404 to support progressive loading
        return {"segments": []}
    
    # Handle malformed segments
    if isinstance(segments, list) and len(segments) == 1 and "raw" in segments[0]:
        logger.warning("Project %s has malformed segments.json", project_id)
        return {"segments": []}
    
    prompts = project_repo.get_prompts(project_id)
    enriched = []
    
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        
        seg_id = segment.get("id") or segment.get("segment_id")
        if not seg_id:
            continue
        
        segment["id"] = str(seg_id)
        prompt = prompts.get(str(seg_id), {})
        version = prompt.get("version", 1)
        
        # Add available versions info
        max_v = file_storage.get_max_version(project_id, str(seg_id))
        segment["max_version"] = max_v
        
        # Only set thumbnail if images exist
        if max_v > 0:
            # Cap version at max available to avoid 404s
            display_ver = version if version <= max_v else max_v
            segment["thumbnail"] = f"/projects/{project_id}/images/{seg_id}_v{display_ver}.png"
        else:
            segment["thumbnail"] = None
            
        segment["prompt"] = prompt
        
        enriched.append(segment)
    
    return {"segments": enriched}


@router.patch("/{project_id}/segments/{seg_id}")
async def update_segment(
    project_id: str,
    seg_id: str,
    payload: SegmentUpdate,
) -> dict[str, Any]:
    """Update a segment's properties."""
    segments = project_repo.get_segments(project_id)
    prompts = project_repo.get_prompts(project_id)
    
    if not segments:
        raise HTTPException(status_code=404, detail="Segments not found")
    
    updated_segment = None
    for segment in segments:
        if segment.get("id") == seg_id:
            if payload.visual_intent is not None:
                segment["visual_intent"] = payload.visual_intent
            if payload.effect is not None:
                segment["effect"] = payload.effect
            if payload.start_time is not None:
                segment["start_time"] = payload.start_time
            if payload.end_time is not None:
                segment["end_time"] = payload.end_time
            if payload.lyric_text is not None:
                segment["lyric_text"] = payload.lyric_text
            if payload.text is not None:
                segment["text"] = payload.text
            if payload.camera_angle is not None:
                segment["camera_angle"] = payload.camera_angle
            if payload.emotion is not None:
                segment["emotion"] = payload.emotion
            updated_segment = segment
            break
    
    if updated_segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    # Add available versions info
    max_v = file_storage.get_max_version(project_id, str(seg_id))
    updated_segment["max_version"] = max_v
    
    # Update prompts
    prompt = prompts.get(seg_id, {"version": 1})
    if payload.image_prompt is not None:
        prompt["image_prompt"] = payload.image_prompt
    if payload.negative_prompt is not None:
        prompt["negative_prompt"] = payload.negative_prompt
    if payload.style_hints is not None:
        prompt["style_hints"] = payload.style_hints
    if payload.version is not None:
        prompt["version"] = payload.version
    
    prompts[seg_id] = prompt
    
    project_repo.save_segments(project_id, segments)
    project_repo.save_prompts(project_id, prompts)
    
    return {"segment": updated_segment, "prompt": prompt}


@router.post("/{project_id}/segments/{seg_id}/regenerate")
async def regenerate_scene(
    project_id: str,
    seg_id: str,
    billing: BillingContext = Depends(require_can_generate),
    image_service: ImageService = Depends(get_image_service)
) -> dict[str, Any]:
    """
    Regenerate image for a segment.
    
    Requires 1 credit per regeneration.
    """
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Deduct 1 credit for regeneration
    transaction_id = await deduct_generation_credits(
        billing,
        amount=1,
        description=f"Regenerate segment {seg_id}",
        reference_id=f"{project_id}:{seg_id}"
    )
    
    try:
        logger.info(f"[REGENERATE] Starting regeneration: project_id={project_id}, seg_id={seg_id}")
        prompt = image_service.regenerate_segment(project_id, seg_id)
        
        project_repo.update_job(project_id, "pipeline", {
            "status": "DONE",
            "step": "regenerate",
            "message": f"Regenerated {seg_id} v{prompt.get('version', 1)}",
        })
        
        return {
            "segment_id": seg_id,
            "prompt": prompt,
            "credits_used": 1,
            "transaction_id": transaction_id
        }
    except KeyError:
        # Refund on error
        await refund_generation_credits(
            billing, amount=1, transaction_id=transaction_id,
            reason=f"Segment {seg_id} not found - refund"
        )
        raise HTTPException(status_code=404, detail="Segment not found")
    except Exception as e:
        # Refund on any generation error
        await refund_generation_credits(
            billing, amount=1, transaction_id=transaction_id,
            reason=f"Regeneration failed: {str(e)}"
        )
        logger.error(f"Regeneration failed for {seg_id}: {e}")
        raise HTTPException(status_code=500, detail="Regeneration failed")


@router.post("/{project_id}/segments/{seg_id}/regenerate-prompt")
async def regenerate_prompt(
    project_id: str,
    seg_id: str,
    billing: BillingContext = Depends(require_can_generate),
    image_service: ImageService = Depends(get_image_service)
) -> dict[str, Any]:
    """
    Regenerate only the prompt for a segment.
    
    This operation is inexpensive, but we might still want to track it.
    For now, let's treat it as free or very cheap.
    Let's make it free since it doesn't use the image generation model cost, 
    only text generation which is negligible compared to image.
    """
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        prompt = image_service.regenerate_prompt_only(project_id, seg_id)
        
        project_repo.update_job(project_id, "pipeline", {
            "status": "DONE",
            "step": "regenerate-prompt",
            "message": f"Regenerated prompt for {seg_id}",
        })
        
        return {
            "segment_id": seg_id,
            "prompt": prompt,
            "credits_used": 0
        }
    except Exception as e:
        logger.error(f"Prompt regeneration failed for {seg_id}: {e}")
        raise HTTPException(status_code=500, detail="Prompt regeneration failed")


@router.post("/{project_id}/segments/{seg_id}/regenerate-image")
async def regenerate_image_only(
    project_id: str,
    seg_id: str,
    billing: BillingContext = Depends(require_can_generate),
    image_service: ImageService = Depends(get_image_service)
) -> dict[str, Any]:
    """
    Regenerate only the image for a segment using existng prompt.
    
    Requires 1 credit.
    """
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Deduct 1 credit for regeneration
    transaction_id = await deduct_generation_credits(
        billing,
        amount=1,
        description=f"Regenerate image {seg_id}",
        reference_id=f"{project_id}:{seg_id}:img"
    )
    
    try:
        prompt = image_service.regenerate_image_only(project_id, seg_id)
        
        project_repo.update_job(project_id, "pipeline", {
            "status": "DONE",
            "step": "regenerate-image",
            "message": f"Regenerated image {seg_id} v{prompt.get('version', 1)}",
        })
        
        return {
            "segment_id": seg_id,
            "prompt": prompt,
            "credits_used": 1,
            "transaction_id": transaction_id
        }
    except Exception as e:
        # Refund on any generation error
        await refund_generation_credits(
            billing, amount=1, transaction_id=transaction_id,
            reason=f"Regeneration failed: {str(e)}"
        )
        logger.error(f"Image regeneration failed for {seg_id}: {e}")
        raise HTTPException(status_code=500, detail="Image regeneration failed")


@router.post("/{project_id}/recalculate-timings", response_model=RunResponse)
async def recalculate_timings(
    project_id: str,
    story_service: StoryboardService = Depends(get_story_service)
) -> RunResponse:
    """Recalculate segment timings to evenly distribute across audio duration using RHYTHMIC analysis."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get current segments and analysis
    segments = project_repo.get_segments(project_id)
    analysis = project_repo.get_analysis(project_id)
    
    if not segments:
        return RunResponse(status="SKIPPED", message="No segments to recalculate")
    
    if not analysis:
        return RunResponse(status="SKIPPED", message="Analysis not ready yet")
    
    duration = analysis.get("total_duration", 0.0)
    if duration <= 0:
        return RunResponse(status="SKIPPED", message="Invalid audio duration")
    
    # 1. Recover original intentions based on text density or Keep current length as 'suggested'
    # The normalize_segments function expects '_orig_duration' or looks at start/end
    # We should prep the segments so they have 'start_time' and 'end_time' which they already do.
    # normalize_segments calculates 'suggested' duration from current s/e.
    
    # 2. Run Smart Rhythmic Normalization
    try:
        updated_segments = story_service.normalize_segments(segments, duration, analysis)
        
        # 3. Save updated segments
        project_repo.save_segments(project_id, updated_segments)
        
        return RunResponse(
            status="OK", 
            message=f"Recalculated timings with Beat Sync for {len(updated_segments)} segments."
        )
    except Exception as e:
        logger.error(f"Recalculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Recalculation failed: {e}")


@router.post("/{project_id}/render", response_model=RunResponse)
async def render_project(
    project_id: str,
    background: BackgroundTasks,
    billing: BillingContext = Depends(get_billing_context),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
) -> RunResponse:
    """
    Start video rendering.
    
    Rendering is free (no additional credits), but still tracks the user.
    """
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Log who initiated the render (for analytics)
    if billing.user:
        logger.info(f"User {billing.user.id} started render for {project_id}")
    
    background.add_task(pipeline_service.render_only, project_id)
    
    return RunResponse(status="OK", message="Render started")


@router.get("/{project_id}/jobs")
async def get_jobs(project_id: str) -> dict[str, Any]:
    """Get job statuses."""
    jobs = project_repo.get_jobs(project_id)
    if not jobs:
        raise HTTPException(status_code=404, detail="Jobs not found")
    return {"jobs": jobs}


@router.get("/{project_id}/images/{image_name}")
async def get_image(project_id: str, image_name: str) -> FileResponse:
    """Get a generated image."""
    image_path = file_storage.get_image_path(project_id, image_name)
    if not image_path:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)


@router.get("/{project_id}/renders/{render_name}")
async def get_render(project_id: str, render_name: str, request: Request):
    """Stream a rendered video with Range request support for seeking."""
    import os
    
    render_path = file_storage.get_render_path(project_id, render_name)
    if not render_path:
        raise HTTPException(status_code=404, detail="Render not found")
    
    file_size = os.path.getsize(render_path)
    
    # Parse Range header
    range_header = request.headers.get("range")
    
    if range_header:
        # Parse "bytes=start-end" format
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1
        
        # Clamp to valid range
        start = max(0, start)
        end = min(end, file_size - 1)
        content_length = end - start + 1
        
        def iter_file():
            with open(render_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                chunk_size = 1024 * 1024  # 1MB chunks
                while remaining > 0:
                    to_read = min(chunk_size, remaining)
                    data = f.read(to_read)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
        
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": "video/mp4",
        }
        
        return StreamingResponse(
            iter_file(),
            status_code=206,
            headers=headers,
            media_type="video/mp4"
        )
    else:
        # No Range header - return full file with Accept-Ranges
        def iter_full_file():
            with open(render_path, "rb") as f:
                chunk_size = 1024 * 1024  # 1MB chunks
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    yield data
        
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": "video/mp4",
        }
        
        return StreamingResponse(
            iter_full_file(),
            status_code=200,
            headers=headers,
            media_type="video/mp4"
        )


@router.get("/{project_id}/download")
async def download_project_video(project_id: str) -> FileResponse:
    """Download the latest rendered video."""
    video_path = file_storage.get_latest_render(project_id)
    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=video_path.name,
        headers={"Content-Type": "video/mp4"},
    )


# ==================== Subtitle Endpoints ====================

@router.post("/{project_id}/subtitles/generate", response_model=SubtitleResponse)
async def generate_subtitles(
    project_id: str,
    request: SubtitleGenerateRequest = SubtitleGenerateRequest(),
    subtitle_service: SubtitleService = Depends(get_subtitle_service)
) -> SubtitleResponse:
    """Generate subtitles from audio using Gemini 3.0 Flash."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    audio_path = file_storage.get_audio_path(project_id)
    if not audio_path:
        raise HTTPException(status_code=400, detail="No audio file uploaded")
    
    # Auto-adjust settings for vertical videos
    project = project_repo.get(project_id)
    if project and project.get("format") == "9:16":
        # For vertical videos, we limit max words to 5 for better readability
        # unless the user specifically requested a very small number (which is unlikely to be < 5 anyway)
        # But here we enforce the max limit of 5 as requested.
        if request.max_words > 5:
            logger.info(f"Auto-adjusting max_words from {request.max_words} to 5 for vertical video (9:16)")
            request.max_words = 5
    
    from fastapi.concurrency import run_in_threadpool
    
    try:
        entries = await run_in_threadpool(
            subtitle_service.transcribe_audio,
            project_id=project_id,
            language=request.language,
            min_words=request.min_words,
            max_words=request.max_words,
        )
        
        # Get styling (default or existing)
        styling_dict = file_storage.get_subtitle_styling(project_id)
        styling = SubtitleStyling(**(styling_dict or {}))
        
        return SubtitleResponse(
            entries=entries,
            styling=styling,
            srt_content=subtitle_service.get_srt_content(project_id),
        )
    except Exception as e:
        logger.error(f"Subtitle generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Subtitle generation failed: {str(e)}")


@router.post("/{project_id}/subtitles/import", response_model=SubtitleResponse)
async def import_subtitles(
    project_id: str,
    srt_file: UploadFile = File(...),
    subtitle_service: SubtitleService = Depends(get_subtitle_service)
) -> SubtitleResponse:
    """Import SRT file."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not srt_file.filename or not srt_file.filename.lower().endswith('.srt'):
        raise HTTPException(status_code=400, detail="File must be a .srt file")
    
    try:
        entries = subtitle_service.import_srt(
            project_id=project_id,
            file=srt_file.file,
            filename=srt_file.filename,
        )
        
        styling_dict = file_storage.get_subtitle_styling(project_id)
        styling = SubtitleStyling(**(styling_dict or {}))
        
        return SubtitleResponse(
            entries=entries,
            styling=styling,
            srt_content=subtitle_service.get_srt_content(project_id),
        )
    except Exception as e:
        logger.error(f"SRT import failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse SRT file: {str(e)}")


@router.get("/{project_id}/subtitles", response_model=SubtitleResponse)
async def get_subtitles(
    project_id: str,
    subtitle_service: SubtitleService = Depends(get_subtitle_service)
) -> SubtitleResponse:
    """Get current subtitles."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    result = subtitle_service.load_subtitles(project_id)
    if not result:
        # Return empty response if no subtitles exist
        return SubtitleResponse(
            entries=[],
            styling=SubtitleStyling(),
            srt_content=None,
        )
    
    return result


@router.put("/{project_id}/subtitles", response_model=SubtitleResponse)
async def update_subtitles(
    project_id: str,
    payload: SubtitleUpdate,
    subtitle_service: SubtitleService = Depends(get_subtitle_service)
) -> SubtitleResponse:
    """Update subtitle entries and/or styling."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    if payload.entries is not None:
        subtitle_service.update_entries(project_id, payload.entries)
    
    if payload.styling is not None:
        subtitle_service.update_styling(project_id, payload.styling)
    
    # Return updated state
    result = subtitle_service.load_subtitles(project_id)
    if not result:
        return SubtitleResponse(
            entries=[],
            styling=SubtitleStyling(),
            srt_content=None,
        )
    
    return result


@router.get("/{project_id}/subtitles/download")
async def download_srt(project_id: str) -> FileResponse:
    """Download SRT file."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    srt_path = file_storage.get_subtitles_path(project_id)
    if not srt_path:
        raise HTTPException(status_code=404, detail="Subtitles not found")
    
    return FileResponse(
        path=srt_path,
        media_type="application/x-subrip",
        filename="subtitles.srt",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )


@router.delete("/{project_id}/subtitles")
async def delete_subtitles(
    project_id: str,
    subtitle_service: SubtitleService = Depends(get_subtitle_service)
) -> dict[str, str]:
    """Delete all subtitles for a project."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    subtitle_service.delete_subtitles(project_id)
    return {"status": "OK", "message": "Subtitles deleted"}


@router.get("/meta/fonts")
async def list_fonts() -> dict[str, Any]:
    """Get list of available fonts for subtitles."""
    fonts = get_available_fonts()
    return {
        "fonts": [f.model_dump() for f in fonts],
        "total": len(fonts),
    }


# ==================== Standalone Video Endpoints ====================

@router.post("/{project_id}/upload-video", response_model=RunResponse)
async def upload_video_standalone(
    project_id: str,
    video: UploadFile = File(...)
) -> RunResponse:
    """Upload video for standalone subtitle mode."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate video format
    valid_types = ['video/mp4', 'video/quicktime', 'video/webm', 'video/avi', 'video/x-msvideo']
    if video.content_type not in valid_types:
        raise HTTPException(status_code=400, detail="Invalid video format")
    
    project_repo.ensure_dirs(project_id)
    
    # Save video to project
    video_path = file_storage.save_video(project_id, video.file, video.filename or "video.mp4")
    
    # Also extract audio for transcription
    try:
        import subprocess
        audio_path = video_path.parent / "track.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
            str(audio_path)
        ], capture_output=True, check=True)
        logger.info(f"Extracted audio to {audio_path}")
    except Exception as e:
        logger.warning(f"Could not extract audio from video: {e}")
    
    project_repo.update(project_id, {"status": "VIDEO_UPLOADED", "standalone_mode": True})
    
    return RunResponse(status="OK", message="Video uploaded")


@router.post("/{project_id}/render-standalone", response_model=RunResponse)
async def render_standalone(
    project_id: str,
    background: BackgroundTasks,
    pipeline_service: PipelineService = Depends(get_pipeline_service)
) -> RunResponse:
    """Render video with subtitles only (standalone mode)."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    video_path = file_storage.get_video_path(project_id)
    if not video_path:
        raise HTTPException(status_code=400, detail="No video uploaded")
    
    srt_path = file_storage.get_subtitles_path(project_id)
    if not srt_path:
        raise HTTPException(status_code=400, detail="No subtitles available")
    
    async def render_with_subtitles():
        from ..services.render_service import RenderService
        render_service = RenderService(project_repo, file_storage)
        
        project_repo.update_job(project_id, "render", {"status": "RUNNING", "progress": 0})
        
        try:
            # Use standard render with video source instead of segments
            output_path, duration = render_service.render_standalone_video(
                project_id=project_id,
                video_path=video_path,
            )
            
            project_repo.update_job(project_id, "render", {
                "status": "DONE",
                "progress": 100,
                "output_path": str(output_path),
                "render_duration": duration
            })
            
        except Exception as e:
            logger.error(f"Standalone render failed: {e}")
            project_repo.update_job(project_id, "render", {
                "status": "ERROR",
                "message": str(e)
            })
    
    background.add_task(render_with_subtitles)
    
    return RunResponse(status="OK", message="Standalone render started")

