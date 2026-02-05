"""Subtitle-related Pydantic schemas."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# Popular fonts bundled with the application
BUNDLED_FONTS = [
    # Sans-serif (modern, clean)
    "Montserrat",
    "Inter",
    "Roboto",
    "Open Sans",
    "Lato",
    "Poppins",
    "Nunito",
    "Raleway",
    "Ubuntu",
    "Oswald",
    "Source Sans Pro",
    "Fira Sans",
    "Work Sans",
    "DM Sans",
    "Quicksand",
    "Mulish",
    "Barlow",
    "Outfit",
    "Manrope",
    "Urbanist",
    # Serif (elegant, traditional)
    "Playfair Display",
    "Merriweather",
    "Lora",
    "PT Serif",
    "Libre Baskerville",
    "Crimson Text",
    "Source Serif Pro",
    # Display & decorative
    "Bebas Neue",
    "Anton",
    "Righteous",
    "Lobster",
    "Pacifico",
    "Permanent Marker",
    "Abril Fatface",
    "Russo One",
    "Bangers",
    "Concert One",
    "Bungee",
    "Black Ops One",
    # Monospace (code-like)
    "Fira Code",
    "JetBrains Mono",
    "Source Code Pro",
    "Roboto Mono",
    # Bold & impact
    "Impact",
    "Arial Black",
    "Futura",
    "Archivo Black",
    "Teko",
]


class SubtitleEntry(BaseModel):
    """Single subtitle entry with timing and text."""
    id: int
    start_time: str = Field(..., description="SRT format: 00:00:01,000")
    end_time: str = Field(..., description="SRT format: 00:00:03,500")
    text: str


class SubtitleStyling(BaseModel):
    """Subtitle styling configuration."""
    font_family: str = Field(default="Montserrat", description="Font family name")
    font_size: int = Field(default=48, ge=16, le=120, description="Font size in pixels")
    font_weight: str = Field(default="bold", description="Font weight: normal, bold, black")
    font_color: str = Field(default="#FFFFFF", description="Text color in hex")
    stroke_color: str = Field(default="#000000", description="Outline color in hex")
    stroke_width: int = Field(default=3, ge=0, le=10, description="Outline width in pixels")
    shadow_color: str = Field(default="#000000", description="Shadow color in hex")
    shadow_offset: int = Field(default=2, ge=0, le=10, description="Shadow offset in pixels")
    background_enabled: bool = Field(default=False, description="Enable background box")
    background_color: str = Field(default="#000000", description="Background box color")
    background_opacity: float = Field(default=0.7, ge=0, le=1, description="Background opacity")
    background_padding: int = Field(default=12, ge=0, le=50, description="Background padding")
    background_radius: int = Field(default=8, ge=0, le=30, description="Background border radius")
    position: str = Field(default="bottom", description="Position: top, middle, bottom")
    margin_x: int = Field(default=50, ge=0, le=200, description="Horizontal margin in pixels")
    margin_y: int = Field(default=60, ge=0, le=300, description="Vertical margin in pixels")
    text_align: str = Field(default="center", description="Text alignment: left, center, right")
    max_width_percent: int = Field(default=90, ge=50, le=100, description="Max text width as % of video width")
    uppercase: bool = Field(default=False, description="Convert text to uppercase")
    animation: str = Field(default="none", description="Animation: none, fade, pop, typewriter")


class SubtitleUpdate(BaseModel):
    """Update request for subtitles."""
    entries: Optional[list[SubtitleEntry]] = None
    styling: Optional[SubtitleStyling] = None


class SubtitleResponse(BaseModel):
    """Response containing subtitles data."""
    entries: list[SubtitleEntry]
    styling: SubtitleStyling
    srt_content: Optional[str] = None
    
    class Config:
        extra = "allow"


class SubtitleGenerateRequest(BaseModel):
    """Request to generate subtitles."""
    language: str = Field(default="auto", description="Language code or 'auto' for detection")
    min_words: int = Field(default=1, ge=1, le=10, description="Minimum words per subtitle segment")
    max_words: int = Field(default=10, ge=1, le=20, description="Maximum words per subtitle segment")


class FontInfo(BaseModel):
    """Font information for frontend."""
    name: str
    category: str  # sans-serif, serif, display, monospace


def get_available_fonts() -> list[FontInfo]:
    """Get list of available fonts with categories."""
    categories = {
        "sans-serif": [
            "Montserrat", "Inter", "Roboto", "Open Sans", "Lato", "Poppins",
            "Nunito", "Raleway", "Ubuntu", "Oswald", "Source Sans Pro", "Fira Sans",
            "Work Sans", "DM Sans", "Quicksand", "Mulish", "Barlow", "Outfit",
            "Manrope", "Urbanist"
        ],
        "serif": [
            "Playfair Display", "Merriweather", "Lora", "PT Serif",
            "Libre Baskerville", "Crimson Text", "Source Serif Pro"
        ],
        "display": [
            "Bebas Neue", "Anton", "Righteous", "Lobster", "Pacifico",
            "Permanent Marker", "Abril Fatface", "Russo One", "Bangers",
            "Concert One", "Bungee", "Black Ops One", "Impact", "Arial Black",
            "Futura", "Archivo Black", "Teko"
        ],
        "monospace": [
            "Fira Code", "JetBrains Mono", "Source Code Pro", "Roboto Mono"
        ]
    }
    
    fonts = []
    for category, font_names in categories.items():
        for name in font_names:
            fonts.append(FontInfo(name=name, category=category))
    
    return fonts
