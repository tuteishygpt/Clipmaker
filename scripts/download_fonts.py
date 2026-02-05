#!/usr/bin/env python3
"""
Download Google Fonts for subtitle rendering.
This ensures consistency between frontend preview and backend render.
"""

import os
import sys
import urllib.request
from pathlib import Path

# Popular fonts to download
FONTS_TO_DOWNLOAD = {
    # Sans-serif (most popular for subtitles)
    "Montserrat": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf",
    "Inter": "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Bold.otf",
    "Roboto": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
    "OpenSans": "https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Bold.ttf",
    "Poppins": "https://github.com/itfoundry/Poppins/raw/master/products/Poppins-Bold.ttf",
    "Outfit": "https://github.com/AshitaCreatives/Outfit/raw/master/fonts/ttf/Outfit-Bold.ttf",
    # Display fonts
    "BebasNeue": "https://github.com/googlefonts/BebasNeue/raw/main/fonts/BebasNeue-Regular.ttf",
    "Anton": "https://github.com/googlefonts/AntonFont/raw/main/fonts/Anton-Regular.ttf",
    "Bangers": "https://github.com/googlefonts/bangers/raw/main/fonts/Bangers-Regular.ttf",
    "RussoOne": "https://github.com/AnyWhichWay/RussoOne/raw/master/RussoOne-Regular.ttf",
    # Serif
    "PlayfairDisplay": "https://github.com/googlefonts/Playfair/raw/main/fonts/Playfair%5Bopsz%2Cwdth%2Cwght%5D.ttf",
    "Merriweather": "https://github.com/SorkinType/Merriweather/raw/master/fonts/ttf/Merriweather-Bold.ttf",
    "Lora": "https://github.com/cyrealtype/Lora-Cyrillic/raw/master/fonts/otf/Lora-Bold.otf",
    # Monospace
    "FiraCode": "https://github.com/tonsky/FiraCode/raw/master/distr/ttf/FiraCode-Bold.ttf",
    "JetBrainsMono": "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Bold.ttf",
}

# Alternative: Direct Google Fonts API URLs (more reliable)
GOOGLE_FONTS_API = {
    "Montserrat": "Montserrat:wght@700",
    "Inter": "Inter:wght@700",
    "Roboto": "Roboto:wght@700",
    "Open+Sans": "Open+Sans:wght@700",
    "Poppins": "Poppins:wght@700",
    "Outfit": "Outfit:wght@700",
    "Bebas+Neue": "Bebas+Neue",
    "Anton": "Anton",
    "Bangers": "Bangers",
    "Russo+One": "Russo+One",
    "Playfair+Display": "Playfair+Display:wght@700",
    "Merriweather": "Merriweather:wght@700",
    "Lora": "Lora:wght@700",
    "Fira+Code": "Fira+Code:wght@700",
    "JetBrains+Mono": "JetBrains+Mono:wght@700",
}


def get_font_dir() -> Path:
    """Get the fonts directory path."""
    # This script is in scripts/, fonts are in app/static/fonts/
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    font_dir = base_dir / "app" / "static" / "fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    return font_dir


def download_font(name: str, url: str, font_dir: Path) -> bool:
    """Download a single font file."""
    # Determine extension from URL
    ext = ".ttf"
    if url.endswith(".otf"):
        ext = ".otf"
    
    target_path = font_dir / f"{name}{ext}"
    
    if target_path.exists():
        print(f"  ✓ {name} already exists")
        return True
    
    try:
        print(f"  ↓ Downloading {name}...")
        # Add user agent to avoid blocks
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
        
        with open(target_path, "wb") as f:
            f.write(data)
        
        print(f"  ✓ {name} downloaded ({len(data) // 1024} KB)")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to download {name}: {e}")
        return False


def main():
    print("🔤 Downloading fonts for Clipmaker subtitle rendering...\n")
    
    font_dir = get_font_dir()
    print(f"Target directory: {font_dir}\n")
    
    success_count = 0
    fail_count = 0
    
    for name, url in FONTS_TO_DOWNLOAD.items():
        if download_font(name, url, font_dir):
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\n{'='*50}")
    print(f"✓ Downloaded: {success_count}")
    print(f"✗ Failed: {fail_count}")
    
    if fail_count > 0:
        print("\n⚠ Some fonts failed to download. The system will use fallback fonts.")
        print("  You can manually download missing fonts from fonts.google.com")
    else:
        print("\n✓ All fonts downloaded successfully!")
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
