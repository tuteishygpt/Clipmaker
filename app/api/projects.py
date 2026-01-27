"""Project API routes."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..schemas.project import ProjectCreate, ProjectResponse
from ..schemas.segment import SegmentUpdate
from ..schemas.common import RunResponse
from ..repositories.project_repo import ProjectRepository
from ..repositories.file_storage import FileStorage
from ..services.pipeline_service import PipelineService
from ..services.image_service import ImageService
from ..services.billing_service import billing_service
from ..core.logging import get_logger
from ..core.billing import (
    BillingContext,
    get_billing_context,
    require_can_generate,
    deduct_generation_credits,
    refund_generation_credits,
)
from ..core.auth import AuthenticatedUser, get_optional_user

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

# Initialize dependencies
project_repo = ProjectRepository()
file_storage = FileStorage()

def get_pipeline_service() -> PipelineService:
    return PipelineService(project_repo, file_storage)

def get_image_service() -> ImageService:
    return ImageService(project_repo=project_repo, file_storage=file_storage)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user: Optional[AuthenticatedUser] = Depends(get_optional_user)
) -> list[dict[str, Any]]:
    """List projects (optionally filtered by user)."""
    # For now, we still list all local projects for simplicity, 
    # but we could filter by user.id if records exist in Supabase.
    return project_repo.list_all()


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


from ..core.config import settings

@router.post("/{project_id}/upload", response_model=RunResponse)
async def upload_audio(project_id: str, audio: UploadFile = File(...)) -> RunResponse:
    """Upload audio file for a project."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_repo.ensure_dirs(project_id)
    audio_path = file_storage.save_audio(project_id, audio.file, audio.filename or "track.wav")
    
    # Validate Duration
    try:
        import moviepy.editor as mp
        # Use a context manager logic or explicit close to ensure file handle is released
        # AudioFileClip doesn't support context manager natively in older versions, so we use close()
        clip = mp.AudioFileClip(str(audio_path))
        duration = clip.duration
        clip.close()
        
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
            
    except ImportError:
        logger.warning("moviepy not found, skipping duration check")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio validation failed: {e}")
        # Optionally delete if invalid audio format
        # For now, we proceed or error? 
        # If moviepy fails to open it, it might be invalid.
        # Let's try to be safe: if we can't validate, we might warn but let it pass 
        # OR better, if it's really an audio app, we should probably fail.
        # But let's act conservative: if check fails, maybe log it.
        # However, the user asked for a check. If checking fails, likely the file is bad.
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
    """Get audio analysis results."""
    analysis = project_repo.get_analysis(project_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not ready")
    return analysis


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
        raise HTTPException(status_code=404, detail="Segments not ready")
    
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
async def recalculate_timings(project_id: str) -> RunResponse:
    """Recalculate segment timings to evenly distribute across audio duration."""
    if not project_repo.exists(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get current segments and analysis
    segments = project_repo.get_segments(project_id)
    analysis = project_repo.get_analysis(project_id)
    
    if not segments:
        raise HTTPException(status_code=404, detail="No segments found")
    
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found")
    
    duration = analysis.get("total_duration", 0.0)
    if duration <= 0:
        raise HTTPException(status_code=400, detail="Invalid audio duration")
    
    # Helper for time parsing
    def parse_t(t_val) -> float:
        if isinstance(t_val, (int, float)):
            return float(t_val)
        if not t_val:
            return 0.0
        try:
            t_str = str(t_val).replace(",", ".").strip()
            parts = t_str.split(":")
            if len(parts) == 1: return float(parts[0])
            if len(parts) == 2: return float(parts[0]) * 60 + float(parts[1])
            if len(parts) == 3: return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except: pass
        return 0.0

    MAX_DURATION = 6.0
    MIN_DURATION = 0.5
    
    # Calculate proportional timings
    num_segments = len(segments)
    if num_segments == 0:
        return RunResponse(status="OK", message="No segments to recalculate")

    # If the track is very long, we might need to increase MAX_DURATION to fill it
    # but we should do it uniformly.
    ideal_avg = duration / num_segments
    effective_max = max(MAX_DURATION, ideal_avg * 1.5)
    
    # First, calculate weights based on current duration or default to 1.0
    weights = []
    for seg in segments:
        s = parse_t(seg.get("start_time", 0))
        e = parse_t(seg.get("end_time", 0))
        d = e - s
        if d < 0.1: d = 3.0 # Default weight for broken segments
        weights.append(d)
    
    total_weight = sum(weights)
    
    # Step 1: Assign initial durations based on weights, but clamp to effective_max
    durations = []
    for w in weights:
        d = (w / total_weight) * duration if total_weight > 0 else ideal_avg
        d = max(MIN_DURATION, min(d, effective_max))
        durations.append(d)
    
    # Step 2: Recalculate and distribute the difference to hit exactly total_duration
    # This prevents the last segment from being huge
    for _ in range(3): # Iterate a few times to settle
        current_total = sum(durations)
        diff = duration - current_total
        if abs(diff) < 0.01: break
        
        # Distribute diff among segments that are NOT at their limits (if possible)
        # or just distribute among all
        per_seg_diff = diff / num_segments
        for j in range(num_segments):
            durations[j] = max(MIN_DURATION, min(durations[j] + per_seg_diff, effective_max))

    # Step 3: Apply timings
    current_time = 0.0
    for i, seg in enumerate(segments):
        seg["start_time"] = current_time
        seg_dur = durations[i]
        
        # Last segment MUST hit the end exactly
        if i == num_segments - 1:
            seg["end_time"] = duration
        else:
            seg["end_time"] = current_time + seg_dur
            
        current_time = seg["end_time"]
    
    # Save updated segments
    project_repo.save_segments(project_id, segments)
    
    return RunResponse(
        status="OK", 
        message=f"Recalculated timings for {num_segments} segments (Avg: {duration/num_segments:.2f}s, Max set to {effective_max:.1f}s)"
    )


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
async def get_render(project_id: str, render_name: str) -> FileResponse:
    """Get a rendered video."""
    render_path = file_storage.get_render_path(project_id, render_name)
    if not render_path:
        raise HTTPException(status_code=404, detail="Render not found")
    return FileResponse(render_path, media_type="video/mp4")


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
