import os
import requests
from pathlib import Path

# Common fonts used in the app
FONTS = {
    # Montserrat (Variable font is safest import)
    "Montserrat": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
    
    # Open Sans
    "OpenSans": "https://github.com/google/fonts/raw/main/ofl/opensans/OpenSans%5Bwdth%2Cwght%5D.ttf",
    
    # Roboto
    "Roboto": "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Regular.ttf",
    
    # Inter
    "Inter": "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bslnt%2Cwght%5D.ttf",
}

def download_fonts():
    # Adjust path to point to inner Clipmaker/app/static/fonts
    target_dir = Path("Clipmaker/app/static/fonts")
    if not target_dir.parent.parent.exists():
        # Fallback if running from inside Clipmaker dir
        target_dir = Path("app/static/fonts")
        
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading fonts to {target_dir.absolute()}...")
    
    for name, url in FONTS.items():
        try:
            print(f"Fetching {name}...")
            response = requests.get(url)
            response.raise_for_status()
            
            # Save file
            file_path = target_dir / f"{name}.ttf"
            file_path.write_bytes(response.content)
            print(f"Saved {file_path}")
        except Exception as e:
            print(f"Failed to download {name}: {e}")

if __name__ == "__main__":
    download_fonts()
