"""Download and install all BUNDLED_FONTS into app/static/fonts."""
import os
import re
import urllib.request
import urllib.parse
from pathlib import Path

# Paths
ROOT_DIR = Path("d:/googlePRJ/clipmaker/Clipmaker").resolve()
STATIC_FONTS_DIR = ROOT_DIR / "app" / "static" / "fonts"
ALT_STATIC_FONTS_DIR = Path("d:/googlePRJ/clipmaker/app/static/fonts").resolve()
STATIC_FONTS_DIR.mkdir(parents=True, exist_ok=True)
ALT_STATIC_FONTS_DIR.mkdir(parents=True, exist_ok=True)

WINDOWS_FONTS = Path("C:/Windows/Fonts")

# Fonts list from app/schemas/subtitle.py
BUNDLED_FONTS = [
    # Sans-serif
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
    # Serif
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
    # Monospace
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
    # Classic
    "Arial",
]

# System font mappings
SYSTEM_FONT_MAP = {
    "Impact": ["impact.ttf"],
    "Arial Black": ["ariblk.ttf"],
    "Arial": ["arial.ttf", "arialbd.ttf"],
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"

def download_font_variant(family: str, weight_label: str, weight_num: int) -> bool:
    clean_fam = family.replace(" ", "")
    target_file = STATIC_FONTS_DIR / f"{clean_fam}-{weight_label}.ttf"
    if target_file.exists() and target_file.stat().st_size > 1000:
        return True

    query = family.replace(" ", "+")
    css_url = f"https://fonts.googleapis.com/css2?family={query}:wght@{weight_num}"
    try:
        req = urllib.request.Request(css_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=8) as resp:
            css = resp.read().decode("utf-8")
        
        src_match = re.search(r"src:\s*url\((https://[^)]+)\)", css)
        if src_match:
            font_url = src_match.group(1)
            f_req = urllib.request.Request(font_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(f_req, timeout=10) as font_resp:
                font_bytes = font_resp.read()
            if len(font_bytes) > 1000:
                target_file.write_bytes(font_bytes)
                print(f"  [OK] Downloaded {family} ({weight_label}): {len(font_bytes)} bytes")
                return True
    except Exception:
        pass
    return False

def copy_system_font(family: str) -> bool:
    clean_fam = family.replace(" ", "")
    files = SYSTEM_FONT_MAP.get(family, [])
    found = False
    for filename in files:
        src = WINDOWS_FONTS / filename
        if src.exists():
            dst = STATIC_FONTS_DIR / f"{clean_fam}-{filename}"
            if not dst.exists():
                dst.write_bytes(src.read_bytes())
                print(f"  [OK] Copied system font {filename} -> {dst.name}")
            # Also copy bare name
            bare_dst = STATIC_FONTS_DIR / filename
            if not bare_dst.exists():
                bare_dst.write_bytes(src.read_bytes())
            found = True
    return found

def main():
    print(f"Starting check and download for {len(BUNDLED_FONTS)} fonts...")
    success_count = 0

    for font_name in BUNDLED_FONTS:
        print(f"\nChecking {font_name}...")
        clean_name = font_name.replace(" ", "")

        # Check system fonts first
        if font_name in SYSTEM_FONT_MAP:
            if copy_system_font(font_name):
                success_count += 1
                continue

        # Try downloading Regular (400), Bold (700), Black (900)
        got_any = False
        for label, weight in [("Regular", 400), ("Bold", 700), ("Black", 900)]:
            if download_font_variant(font_name, label, weight):
                got_any = True

        if not got_any:
            # Try single font without weight specifier
            try:
                query = font_name.replace(" ", "+")
                css_url = f"https://fonts.googleapis.com/css2?family={query}"
                req = urllib.request.Request(css_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    css = resp.read().decode("utf-8")
                src_match = re.search(r"src:\s*url\((https://[^)]+)\)", css)
                if src_match:
                    font_url = src_match.group(1)
                    target_file = STATIC_FONTS_DIR / f"{clean_name}-Regular.ttf"
                    f_req = urllib.request.Request(font_url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(f_req, timeout=10) as font_resp:
                        font_bytes = font_resp.read()
                    if len(font_bytes) > 1000:
                        target_file.write_bytes(font_bytes)
                        print(f"  [OK] Downloaded {font_name} (Default): {len(font_bytes)} bytes")
                        got_any = True
            except Exception as e:
                print(f"  [WARN] Could not fetch {font_name}: {e}")

        if got_any:
            success_count += 1

    # Sync all files to ALT_STATIC_FONTS_DIR
    import shutil
    for f in STATIC_FONTS_DIR.glob("*.ttf"):
        shutil.copy2(f, ALT_STATIC_FONTS_DIR / f.name)
    for f in STATIC_FONTS_DIR.glob("*.otf"):
        shutil.copy2(f, ALT_STATIC_FONTS_DIR / f.name)

    print(f"\nDone! Total fonts in static/fonts: {len(list(STATIC_FONTS_DIR.glob('*.*')))} files.")
    print(f"Successfully configured {success_count}/{len(BUNDLED_FONTS)} font families.")

if __name__ == "__main__":
    main()
