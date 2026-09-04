"""Verification test script for Hybrid Subtitles Studio feature."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
clipmaker_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(clipmaker_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.repositories.project_repo import ProjectRepository
from app.repositories.file_storage import FileStorage
from app.services.render_service import _create_moviepy_logger

def run_tests():
    print("=== STARTING SUBTITLES STUDIO VERIFICATION TESTS ===")
    client = TestClient(app)
    
    # ----------------------------------------------------------------
    # TEST 1: Project creation with title and standalone_mode
    # ----------------------------------------------------------------
    print("\n--- Test 1: Project creation with title and standalone_mode ---")
    create_payload = {
        "title": "sample_video_clip.mp4",
        "format": "9:16",
        "style": "default",
        "standalone_mode": True
    }
    response = client.post("/projects", json=create_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    proj_data = response.json()
    project_id = proj_data["id"]
    assert proj_data.get("title") == "sample_video_clip.mp4", f"Title mismatch: {proj_data.get('title')}"
    assert proj_data.get("standalone_mode") is True, f"standalone_mode mismatch: {proj_data.get('standalone_mode')}"
    print(f"PASS: Project {project_id} created with title='{proj_data['title']}' and standalone_mode=True")
    
    # Verify GET /projects/{id} returns title and standalone_mode
    get_res = client.get(f"/projects/{project_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data.get("title") == "sample_video_clip.mp4"
    assert get_data.get("standalone_mode") is True
    print("PASS: GET /projects/{id} returns title and standalone_mode")

    # Verify GET /projects list filtering
    list_res = client.get("/projects?search=sample_video_clip")
    assert list_res.status_code == 200
    list_data = list_res.json()
    matching = [p for p in list_data if p["id"] == project_id]
    assert len(matching) == 1, "Failed to find project by title in list_all"
    print("PASS: GET /projects?search=... filtered by title successfully")

    # ----------------------------------------------------------------
    # TEST 2: Generate short video & test upload-video and /video endpoint
    # ----------------------------------------------------------------
    print("\n--- Test 2: Upload short video (<= 15 min) and get_video endpoint ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        short_video_path = Path(tmpdir) / "short.mp4"
        # Generate 2s synthetic test video with audio
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            "-c:v", "libx264", "-c:a", "aac",
            str(short_video_path)
        ]
        res = subprocess.run(cmd, capture_output=True)
        assert res.returncode == 0, f"FFmpeg failed: {res.stderr.decode()}"
        
        with open(short_video_path, "rb") as vf:
            upload_res = client.post(
                f"/projects/{project_id}/upload-video",
                files={"video": ("sample_video_clip.mp4", vf, "video/mp4")}
            )
        assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
        print("PASS: Short video uploaded successfully")

        # Check that GET /{id}/video serves the file
        video_serve_res = client.get(f"/projects/{project_id}/video")
        assert video_serve_res.status_code == 200
        assert "video/mp4" in video_serve_res.headers.get("content-type", "")
        assert len(video_serve_res.content) > 0
        print(f"PASS: GET /projects/{project_id}/video served {len(video_serve_res.content)} bytes")

    # ----------------------------------------------------------------
    # TEST 3: Video duration limit (> 15 minutes / 900s) rejection
    # ----------------------------------------------------------------
    print("\n--- Test 3: Video duration limit (> 15 min / 900s) rejection ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a tiny 905-second video container without encoding huge data
        # using lavfi testsrc duration=905
        long_video_path = Path(tmpdir) / "long.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=160x120:d=905:r=1",
            "-c:v", "libx264", "-preset", "ultrafast",
            str(long_video_path)
        ]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode == 0:
            with open(long_video_path, "rb") as vf:
                long_upload_res = client.post(
                    f"/projects/{project_id}/upload-video",
                    files={"video": ("long_interview.mp4", vf, "video/mp4")}
                )
            assert long_upload_res.status_code == 400, f"Expected 400, got {long_upload_res.status_code}: {long_upload_res.text}"
            assert "exceeds maximum allowed limit of 15 minutes" in long_upload_res.json().get("detail", "")
            print("PASS: Video exceeding 15 minutes correctly rejected with HTTP 400")
        else:
            print(f"SKIPPED ffmpeg long file generation: {res.stderr.decode()[:100]}")

    # ----------------------------------------------------------------
    # TEST 4: Subtitle update with Karaoke styling
    # ----------------------------------------------------------------
    print("\n--- Test 4: Subtitle update with Karaoke styling & presets ---")
    subtitles_payload = {
        "entries": [
            {
                "id": 1,
                "start_time": "00:00:00,000",
                "end_time": "00:00:02,000",
                "text": "Welcome to Subtitles Studio"
            }
        ],
        "styling": {
            "font_family": "Roboto",
            "font_size": 44,
            "font_weight": "bold",
            "font_color": "#FFFFFF",
            "stroke_color": "#000000",
            "stroke_width": 2,
            "background_enabled": True,
            "background_color": "#000000",
            "background_opacity": 0.75,
            "background_padding": 10,
            "position": "bottom",
            "highlight_active_word": True,
            "highlight_font_color": "#FFFF00",
            "highlight_bg_color": "#FF0000",
            "highlight_bg_radius": 10,
            "highlight_bg_padding": 8
        }
    }
    put_sub_res = client.put(f"/projects/{project_id}/subtitles", json=subtitles_payload)
    assert put_sub_res.status_code == 200, f"Failed to save subtitles: {put_sub_res.text}"
    sub_data = put_sub_res.json()
    assert len(sub_data["entries"]) == 1
    assert sub_data["styling"]["highlight_active_word"] is True
    assert sub_data["styling"]["highlight_font_color"] == "#FFFF00"
    assert sub_data["styling"]["highlight_bg_color"] == "#FF0000"
    print("PASS: Subtitles and Karaoke styling saved and retrieved successfully")

    # ----------------------------------------------------------------
    # TEST 5: MoviePyProgressLogger test
    # ----------------------------------------------------------------
    print("\n--- Test 5: MoviePy progress logger callback ---")
    progress_calls = []
    logger_instance = _create_moviepy_logger(lambda pct: progress_calls.append(pct))
    assert logger_instance is not None, "Logger instance was not created"
    # Simulate progress bars update
    logger_instance.state['bars']['t'] = {'index': 50, 'total': 100}
    logger_instance.callback()
    assert progress_calls == [50], f"Expected [50], got {progress_calls}"
    logger_instance.state['bars']['t'] = {'index': 100, 'total': 100}
    logger_instance.callback()
    assert progress_calls == [50, 100], f"Expected [50, 100], got {progress_calls}"
    print("PASS: MoviePyProgressLogger correctly reports progress to callback")

    # Clean up test project
    import shutil
    proj_dir = clipmaker_dir / "data" / "projects" / project_id
    if proj_dir.exists():
        shutil.rmtree(proj_dir, ignore_errors=True)
    print("PASS: Test project cleaned up successfully")

    print("\n=== ALL SUBTITLES STUDIO TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
