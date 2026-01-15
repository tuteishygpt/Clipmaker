# Clipmaker MVP

Minimal MVP scaffold for the "song → scenes → images → clip" workflow described in the concept and architecture notes.

## Features
- FastAPI backend with JSON-file storage (no DB/Redis).
- Background pipeline that generates placeholder analysis, segments, prompts, images, and renders.
- Simple frontend to create projects, upload audio, run pipeline, inspect scenes, and render video.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000` to use the UI.

## Project storage

Generated assets and JSON files live under `data/projects/<project_id>/` and follow the layout from `architektura_MVP.md`.
