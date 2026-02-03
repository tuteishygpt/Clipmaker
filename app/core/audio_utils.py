"""Audio utilities: validation, duration, time parsing."""
from __future__ import annotations

from pathlib import Path
from typing import Union

from .logging import get_logger

logger = get_logger(__name__)

# Supported audio MIME types
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/mpeg",       # MP3
    "audio/mp3",        # MP3 alternative
    "audio/wav",        # WAV
    "audio/x-wav",      # WAV alternative
    "audio/wave",       # WAV alternative
    "audio/ogg",        # OGG
    "audio/flac",       # FLAC
    "audio/x-flac",     # FLAC alternative
    "audio/aac",        # AAC
    "audio/m4a",        # M4A
    "audio/x-m4a",      # M4A alternative
    "audio/mp4",        # M4A/MP4 audio
}

# Supported file extensions (fallback validation)
ALLOWED_AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".mp4", ".wma"
}


class AudioValidationError(Exception):
    """Raised when audio validation fails."""
    pass


class AudioLoadError(Exception):
    """Raised when audio file cannot be loaded for processing."""
    pass


def validate_audio_format(content_type: str | None, filename: str | None) -> bool:
    """
    Validate audio file format by MIME type and extension.
    
    Args:
        content_type: MIME type from upload
        filename: Original filename
        
    Returns:
        True if valid
        
    Raises:
        AudioValidationError: If format is not supported
    """
    # Check MIME type
    if content_type and content_type.lower() in ALLOWED_AUDIO_MIME_TYPES:
        return True
    
    # Fallback to extension check
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in ALLOWED_AUDIO_EXTENSIONS:
            logger.warning(
                f"MIME type '{content_type}' not recognized, but extension '{ext}' is valid"
            )
            return True
    
    # Neither MIME nor extension is valid
    raise AudioValidationError(
        f"Unsupported audio format. MIME: '{content_type}', File: '{filename}'. "
        f"Supported formats: MP3, WAV, OGG, FLAC, AAC, M4A"
    )


def get_audio_duration(audio_path: Path) -> float:
    """
    Get audio file duration in seconds.
    
    Uses moviepy for reliable duration detection across formats.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Duration in seconds
        
    Raises:
        AudioLoadError: If file cannot be loaded
    """
    try:
        import moviepy.editor as mp
        
        clip = mp.AudioFileClip(str(audio_path))
        duration = clip.duration
        clip.close()
        return duration
        
    except Exception as e:
        logger.error(f"Failed to get audio duration for {audio_path}: {e}")
        raise AudioLoadError(f"Cannot read audio file: {e}")


def parse_time(value: Union[str, int, float, None]) -> float:
    """
    Parse time value to seconds.
    
    Handles various formats:
    - float/int: returned as-is
    - "SS" or "SS.ms": seconds
    - "MM:SS" or "MM:SS.ms": minutes and seconds
    - "HH:MM:SS" or "HH:MM:SS.ms": hours, minutes, seconds
    
    Args:
        value: Time value in various formats
        
    Returns:
        Time in seconds as float
    """
    if value is None:
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    try:
        # Normalize string
        t_str = str(value).replace(",", ".").strip()
        
        # Handle empty string
        if not t_str:
            return 0.0
        
        parts = t_str.split(":")
        
        if len(parts) == 1:
            # Just seconds
            return float(parts[0])
        elif len(parts) == 2:
            # MM:SS
            minutes, seconds = parts
            return float(minutes) * 60 + float(seconds)
        elif len(parts) == 3:
            # HH:MM:SS
            hours, minutes, seconds = parts
            return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
        else:
            logger.warning(f"Unexpected time format: {value}")
            return 0.0
            
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse time value '{value}': {e}")
        return 0.0


def format_time(seconds: float, include_ms: bool = False) -> str:
    """
    Format seconds to MM:SS or MM:SS.ms string.
    
    Args:
        seconds: Time in seconds
        include_ms: Whether to include milliseconds
        
    Returns:
        Formatted time string
    """
    if seconds < 0:
        seconds = 0
    
    minutes = int(seconds // 60)
    secs = seconds % 60
    
    if include_ms:
        return f"{minutes:02d}:{secs:05.2f}"
    else:
        return f"{minutes:02d}:{int(secs):02d}"
