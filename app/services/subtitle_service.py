"""Subtitle service for transcription and management."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, BinaryIO

from ..clients.genai import GenAIClient
from ..repositories.project_repo import ProjectRepository
from ..repositories.file_storage import FileStorage
from ..schemas.subtitle import (
    SubtitleEntry,
    SubtitleStyling,
    SubtitleResponse,
    BUNDLED_FONTS,
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class SubtitleService:
    """Service for subtitle transcription and management."""
    
    def __init__(
        self,
        genai_client: GenAIClient | None = None,
        project_repo: ProjectRepository | None = None,
        file_storage: FileStorage | None = None,
    ) -> None:
        self.genai_client = genai_client or GenAIClient()
        self.project_repo = project_repo or ProjectRepository()
        self.file_storage = file_storage or FileStorage()
    
    def transcribe_audio(
        self,
        project_id: str,
        language: str = "auto",
        min_words: int = 1,
        max_words: int = 10,
    ) -> list[SubtitleEntry]:
        """Transcribe audio to subtitle entries using Gemini 3.0 Flash."""
        audio_path = self.file_storage.get_audio_path(project_id)
        if not audio_path:
            raise FileNotFoundError(f"Audio file not found for project {project_id}")
        
        # Call GenAI to transcribe
        raw_entries = self.genai_client.transcribe_audio_for_subtitles(
            audio_path=audio_path,
            language=language,
            min_words=min_words,
            max_words=max_words,
        )
        
        # Convert to SubtitleEntry objects
        entries = []
        for i, entry in enumerate(raw_entries, start=1):
            # Normalize timestamps to allow loose AI output to be saved correctly
            start_norm = self.seconds_to_srt_time(self.srt_time_to_seconds(entry["start"]))
            end_norm = self.seconds_to_srt_time(self.srt_time_to_seconds(entry["end"]))
            
            # Clean text: remove double newlines which might break SRT format
            clean_text = entry["text"].replace("\r\n", "\n").replace("\n\n", "\n").strip()
            
            entries.append(SubtitleEntry(
                id=i,
                start_time=start_norm,
                end_time=end_norm,
                text=clean_text,
            ))
        
        # Save as SRT
        self._save_entries_as_srt(project_id, entries)
        
        # Initialize default styling if not exists
        if not self.file_storage.get_subtitle_styling(project_id):
            self._save_styling(project_id, SubtitleStyling())
        
        return entries
    
    def _save_entries_as_srt(self, project_id: str, entries: list[SubtitleEntry]) -> Path:
        """Save subtitle entries as SRT file."""
        srt_blocks = []
        for entry in entries:
            # Build each SRT block
            block = f"{entry.id}\n{entry.start_time} --> {entry.end_time}\n{entry.text}"
            srt_blocks.append(block)
        
        # Join blocks with double newline (standard SRT format)
        srt_content = "\n\n".join(srt_blocks)
        # Ensure file ends with newline
        if srt_content and not srt_content.endswith("\n"):
            srt_content += "\n"
        
        return self.file_storage.save_subtitles(project_id, srt_content)
    
    def _save_styling(self, project_id: str, styling: SubtitleStyling) -> Path:
        """Save subtitle styling configuration."""
        return self.file_storage.save_subtitle_styling(project_id, styling.model_dump())
    
    def load_subtitles(self, project_id: str) -> SubtitleResponse | None:
        """Load subtitles from storage."""
        srt_path = self.file_storage.get_subtitles_path(project_id)
        if not srt_path:
            return None
        
        entries = self._parse_srt(srt_path)
        styling_dict = self.file_storage.get_subtitle_styling(project_id)
        styling = SubtitleStyling(**(styling_dict or {}))
        srt_content = srt_path.read_text(encoding="utf-8")
        
        return SubtitleResponse(
            entries=entries,
            styling=styling,
            srt_content=srt_content,
        )
    
    def _parse_srt(self, srt_path: Path) -> list[SubtitleEntry]:
        """Parse SRT file to subtitle entries."""
        content = srt_path.read_text(encoding="utf-8")
        entries = []
        
        # Normalize line endings (Windows \r\n -> \n)
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Split by double newline (subtitle blocks)
        blocks = re.split(r'\n\n+', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 2:  # Minimum: index/timing, text
                try:
                    # Find the timing line (could be first or second line)
                    timing_line_idx = -1
                    for idx, line in enumerate(lines[:3]):  # Check first 3 lines
                        # Relaxed regex: \d{1,2} for hours/mins/secs
                        if re.match(r'\d{1,2}:\d{1,2}:\d{1,2}[,\.]\d{1,3}\s*-->', line.strip()):
                            timing_line_idx = idx
                            break
                    
                    if timing_line_idx == -1:
                        continue
                    
                    # Try to get entry ID from the line before timing (if exists)
                    entry_id = len(entries) + 1
                    if timing_line_idx > 0:
                        try:
                            entry_id = int(lines[0].strip())
                        except ValueError:
                            pass
                    
                    # Relaxed regex capture
                    time_match = re.match(
                        r'(\d{1,2}:\d{1,2}:\d{1,2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{1,2}:\d{1,2}[,\.]\d{1,3})',
                        lines[timing_line_idx].strip()
                    )
                    if time_match:
                        # We should normalize these when reading too, just in case
                        start_time = self.seconds_to_srt_time(self.srt_time_to_seconds(time_match.group(1)))
                        end_time = self.seconds_to_srt_time(self.srt_time_to_seconds(time_match.group(2)))
                        
                        text_lines = lines[timing_line_idx + 1:]
                        text = '\n'.join(text_lines).strip()
                        
                        if text:  # Only add if there's actual text
                            entries.append(SubtitleEntry(
                                id=entry_id,
                                start_time=start_time,
                                end_time=end_time,
                                text=text,
                            ))
                except (ValueError, IndexError):
                    continue
        
        return entries
    
    def import_srt(self, project_id: str, file: BinaryIO, filename: str) -> list[SubtitleEntry]:
        """Import SRT file from upload."""
        content = file.read().decode("utf-8")
        
        # Save the raw SRT content
        self.file_storage.save_subtitles(project_id, content)
        
        # Parse and return entries
        srt_path = self.file_storage.get_subtitles_path(project_id)
        entries = self._parse_srt(srt_path)
        
        # Initialize default styling if not exists
        if not self.file_storage.get_subtitle_styling(project_id):
            self._save_styling(project_id, SubtitleStyling())
        
        return entries
    
    def update_entries(self, project_id: str, entries: list[SubtitleEntry]) -> None:
        """Update subtitle entries and save as SRT."""
        self._save_entries_as_srt(project_id, entries)
    
    def update_styling(self, project_id: str, styling: SubtitleStyling) -> None:
        """Update subtitle styling configuration."""
        self._save_styling(project_id, styling)
    
    def get_srt_content(self, project_id: str) -> str | None:
        """Get raw SRT file content."""
        srt_path = self.file_storage.get_subtitles_path(project_id)
        if srt_path:
            return srt_path.read_text(encoding="utf-8")
        return None
    
    def delete_subtitles(self, project_id: str) -> None:
        """Delete all subtitle files for a project."""
        self.file_storage.delete_subtitles(project_id)
    
    @staticmethod
    def get_available_fonts() -> list[str]:
        """Get list of available fonts."""
        return BUNDLED_FONTS.copy()
    
    @staticmethod
    def srt_time_to_seconds(srt_time: str) -> float:
        """Convert SRT time format to seconds.
        
        Format: 00:00:01,000 -> 1.0
        """
        if isinstance(srt_time, (int, float)):
            return float(srt_time)

        srt_time = str(srt_time).replace(',', '.')
        parts = srt_time.split(':')
        
        if len(parts) == 3:
            try:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            except ValueError:
                pass
        
        if len(parts) == 2:
            try:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            except ValueError:
                pass
                
        if len(parts) == 1:
            try:
                return float(parts[0])
            except ValueError:
                pass
        
        return 0.0
    
    @staticmethod
    def seconds_to_srt_time(seconds: float) -> str:
        """Convert seconds to SRT time format.
        
        Format: 1.5 -> 00:00:01,500
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millis = int((secs % 1) * 1000)
        secs = int(secs)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
