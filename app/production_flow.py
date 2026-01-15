from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Deque, Iterable
from uuid import uuid4

from .genai_client import GenAIClient


class ProjectState(str, Enum):
    uploaded = "UPLOADED"
    analyzing = "ANALYZING"
    analyzed = "ANALYZED"
    storyboarding = "STORYBOARDING"
    storyboarded = "STORYBOARDED"
    prompting = "PROMPTING"
    prompted = "PROMPTED"
    generating_assets = "GENERATING_ASSETS"
    assets_ready = "ASSETS_READY"
    rendering = "RENDERING"
    done = "DONE"
    failed = "FAILED"


@dataclass
class Project:
    id: str
    title: str
    audio_uri: str | None = None
    state: ProjectState = ProjectState.uploaded
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AudioAnalysis:
    project_id: str
    transcript: list[dict[str, Any]]
    emotions: list[str]
    energy_curve: list[dict[str, Any]]
    summary: str
    diarization: list[dict[str, Any]] | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Segment:
    id: str
    project_id: str
    start_ms: int
    end_ms: int
    lyric_line: str | None
    visual_intent: str
    shot_type: str
    mood: str
    style_id: str


@dataclass
class PromptPayload:
    segment_id: str
    version: int
    image_prompt: str
    negative_prompt: str
    consistency_hints: str


@dataclass
class Asset:
    segment_id: str
    version: int
    uri: str
    model: str
    seed: int
    prompt_hash: str
    created_at: datetime = field(default_factory=datetime.utcnow)


class InMemoryDB:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}
        self.analyses: dict[str, AudioAnalysis] = {}
        self.segments: dict[str, list[Segment]] = {}
        self.prompts: dict[str, list[PromptPayload]] = {}
        self.assets: dict[str, list[Asset]] = {}

    def create_project(self, title: str) -> Project:
        project_id = str(uuid4())
        project = Project(id=project_id, title=title)
        self.projects[project_id] = project
        return project

    def update_project_state(self, project_id: str, state: ProjectState) -> None:
        project = self.projects[project_id]
        project.state = state
        project.updated_at = datetime.utcnow()


class InMemoryQueue:
    def __init__(self) -> None:
        from collections import deque

        self._queue: Deque[Job] = deque()

    def enqueue(self, job: "Job") -> None:
        self._queue.append(job)

    def run_next(self) -> bool:
        if not self._queue:
            return False
        job = self._queue.popleft()
        job.handler(job.payload)
        return True

    def drain(self) -> None:
        while self.run_next():
            continue


@dataclass
class Job:
    name: str
    payload: dict[str, Any]
    handler: Callable[[dict[str, Any]], None]


class ObjectStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def put(self, key: str, content: bytes) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return f"storage://{key}"


class AudioAnalysisService:
    def __init__(self, genai: GenAIClient) -> None:
        self.genai = genai

    def analyze(self, audio_uri: str) -> dict[str, Any]:
        return self.genai.analyze_audio(Path(audio_uri.replace("storage://", "")))


class StoryboardService:
    def __init__(self, genai: GenAIClient) -> None:
        self.genai = genai

    def create_segments(self, analysis: AudioAnalysis) -> list[Segment]:
        segments_raw = self.genai.build_storyboard(
            {
                "transcript": analysis.transcript,
                "emotions": analysis.emotions,
                "summary": analysis.summary,
            }
        )
        segments: list[Segment] = []
        for index, segment in enumerate(segments_raw, start=1):
            segments.append(
                Segment(
                    id=segment.get("id", f"seg_{index:03d}"),
                    project_id=analysis.project_id,
                    start_ms=int(segment.get("start_ms", 0)),
                    end_ms=int(segment.get("end_ms", 0)),
                    lyric_line=segment.get("lyric_line") or segment.get("lyric_text"),
                    visual_intent=segment.get("visual_intent", ""),
                    shot_type=segment.get("shot_type", "wide"),
                    mood=segment.get("mood", "neutral"),
                    style_id=segment.get("style_id", "default"),
                )
            )
        return segments


class PromptFactory:
    def __init__(self, genai: GenAIClient) -> None:
        self.genai = genai

    def build_prompts(self, segments: Iterable[Segment]) -> list[PromptPayload]:
        prompts_raw = self.genai.build_prompts([segment.__dict__ for segment in segments])
        prompts: list[PromptPayload] = []
        for segment in segments:
            payload = prompts_raw.get(segment.id, {})
            prompts.append(
                PromptPayload(
                    segment_id=segment.id,
                    version=int(payload.get("version", 1)),
                    image_prompt=payload.get("image_prompt", segment.visual_intent),
                    negative_prompt=payload.get("negative_prompt", ""),
                    consistency_hints=payload.get("consistency_hints", ""),
                )
            )
        return prompts


class ImageGenerationService:
    def __init__(self, genai: GenAIClient, storage: ObjectStorage) -> None:
        self.genai = genai
        self.storage = storage

    def generate(self, prompt: PromptPayload) -> Asset:
        image_bytes = self.genai.generate_image(
            {
                "image_prompt": prompt.image_prompt,
                "negative_prompt": prompt.negative_prompt,
                "consistency_hints": prompt.consistency_hints,
                "version": prompt.version,
            }
        )
        key = f"assets/{prompt.segment_id}_v{prompt.version}.png"
        uri = self.storage.put(key, image_bytes)
        seed = hash((prompt.segment_id, prompt.version)) % 10_000
        prompt_hash = str(hash((prompt.image_prompt, prompt.negative_prompt)))
        return Asset(
            segment_id=prompt.segment_id,
            version=prompt.version,
            uri=uri,
            model=self.genai.config.model_image,
            seed=seed,
            prompt_hash=prompt_hash,
        )


class RenderService:
    def render(self, project: Project, assets: list[Asset]) -> str:
        filename = f"renders/{project.id}/final.mp4"
        return f"storage://{filename}"


class ProductionPipeline:
    def __init__(self, db: InMemoryDB, queue: InMemoryQueue, storage: ObjectStorage, genai: GenAIClient) -> None:
        self.db = db
        self.queue = queue
        self.storage = storage
        self.genai = genai
        self.audio_service = AudioAnalysisService(genai)
        self.storyboard_service = StoryboardService(genai)
        self.prompt_factory = PromptFactory(genai)
        self.image_service = ImageGenerationService(genai, storage)
        self.render_service = RenderService()

    def upload_audio(self, project_id: str, audio_bytes: bytes, extension: str = ".wav") -> None:
        key = f"projects/{project_id}/source/track{extension}"
        uri = self.storage.put(key, audio_bytes)
        project = self.db.projects[project_id]
        project.audio_uri = uri
        self.db.update_project_state(project_id, ProjectState.uploaded)
        self.queue.enqueue(
            Job(
                name="ANALYZE_AUDIO",
                payload={"project_id": project_id, "audio_uri": uri},
                handler=self._handle_analyze_audio,
            )
        )

    def _handle_analyze_audio(self, payload: dict[str, Any]) -> None:
        project_id = payload["project_id"]
        self.db.update_project_state(project_id, ProjectState.analyzing)
        raw = self.audio_service.analyze(payload["audio_uri"])
        analysis = AudioAnalysis(
            project_id=project_id,
            transcript=raw.get("transcript", []),
            emotions=raw.get("emotions", []),
            energy_curve=raw.get("energy_curve", []),
            summary=raw.get("summary", ""),
            diarization=raw.get("diarization"),
        )
        self.db.analyses[project_id] = analysis
        self.db.update_project_state(project_id, ProjectState.analyzed)
        self.queue.enqueue(
            Job(
                name="STORYBOARD",
                payload={"project_id": project_id},
                handler=self._handle_storyboard,
            )
        )

    def _handle_storyboard(self, payload: dict[str, Any]) -> None:
        project_id = payload["project_id"]
        self.db.update_project_state(project_id, ProjectState.storyboarding)
        analysis = self.db.analyses[project_id]
        segments = self.storyboard_service.create_segments(analysis)
        self.db.segments[project_id] = segments
        self.db.update_project_state(project_id, ProjectState.storyboarded)
        self.queue.enqueue(
            Job(
                name="PROMPT_FACTORY",
                payload={"project_id": project_id},
                handler=self._handle_prompt_factory,
            )
        )

    def _handle_prompt_factory(self, payload: dict[str, Any]) -> None:
        project_id = payload["project_id"]
        self.db.update_project_state(project_id, ProjectState.prompting)
        segments = self.db.segments[project_id]
        prompts = self.prompt_factory.build_prompts(segments)
        self.db.prompts[project_id] = prompts
        self.db.update_project_state(project_id, ProjectState.prompted)
        for prompt in prompts:
            self.queue.enqueue(
                Job(
                    name="GENERATE_IMAGE",
                    payload={"project_id": project_id, "segment_id": prompt.segment_id},
                    handler=self._handle_generate_image,
                )
            )

    def _handle_generate_image(self, payload: dict[str, Any]) -> None:
        project_id = payload["project_id"]
        segment_id = payload["segment_id"]
        self.db.update_project_state(project_id, ProjectState.generating_assets)
        prompts = {prompt.segment_id: prompt for prompt in self.db.prompts[project_id]}
        asset = self.image_service.generate(prompts[segment_id])
        self.db.assets.setdefault(project_id, []).append(asset)
        if len(self.db.assets[project_id]) == len(self.db.prompts[project_id]):
            self.db.update_project_state(project_id, ProjectState.assets_ready)
            self.queue.enqueue(
                Job(
                    name="RENDER",
                    payload={"project_id": project_id},
                    handler=self._handle_render,
                )
            )

    def _handle_render(self, payload: dict[str, Any]) -> None:
        project_id = payload["project_id"]
        self.db.update_project_state(project_id, ProjectState.rendering)
        project = self.db.projects[project_id]
        assets = self.db.assets.get(project_id, [])
        render_uri = self.render_service.render(project, assets)
        project.updated_at = datetime.utcnow()
        project.state = ProjectState.done
        project.audio_uri = render_uri

    def regenerate_segment(self, project_id: str, segment_id: str) -> PromptPayload:
        prompts = self.db.prompts[project_id]
        updated: PromptPayload | None = None
        for prompt in prompts:
            if prompt.segment_id == segment_id:
                prompt.version += 1
                updated = prompt
                break
        if updated is None:
            raise KeyError("Segment not found")
        asset = self.image_service.generate(updated)
        self.db.assets.setdefault(project_id, []).append(asset)
        return updated

