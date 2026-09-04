import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure Clipmaker root is in sys.path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.clients.genai import GenAIClient
from app.services.subtitle_service import SubtitleService
from app.repositories.file_storage import FileStorage
from app.repositories.project_repo import ProjectRepository


class VertexSubtitleServiceTests(unittest.TestCase):
    def test_genai_client_vertex_ai_default(self):
        fake_client = MagicMock()
        fake_client.vertexai = True

        client = GenAIClient(
            api_key="fake-key",
            subtitle_model="gemini-3.5-transcribe",
            client=fake_client,
        )
        self.assertTrue(client.is_vertex)
        self.assertEqual(client._normalize_model_name("gemini-3.5-transcribe"), "gemini-3.5-transcribe-preview")
        self.assertEqual(client._normalize_model_name("gemini-2.5-flash"), "gemini-2.5-flash")

    def test_transcribe_audio_for_subtitles_via_vertex_35(self):
        fake_client = MagicMock()
        fake_client.vertexai = True
        fake_client.models.generate_content.return_value = {
            "words": [
                {"word": "Прывітанне", "start": 0.0, "end": 0.5},
                {"word": "дарагія", "start": 0.55, "end": 1.0},
                {"word": "сябры", "start": 1.05, "end": 1.5},
            ]
        }

        genai_client = GenAIClient(
            api_key="fake-key",
            subtitle_model="gemini-3.5-transcribe",
            client=fake_client,
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFFdummywavdata")
            temp_path = Path(f.name)

        try:
            entries = genai_client.transcribe_audio_for_subtitles(
                audio_path=temp_path,
                language="be",
                max_words=5,
            )
            self.assertGreater(len(entries), 0)
            self.assertIn("Прывітанне", entries[0]["text"])
            self.assertIn("-->", entries[0]["start"] + " --> " + entries[0]["end"])
            # Vertex AI models.generate_content called directly (Interactions API bypassed)
            fake_client.models.generate_content.assert_called_once()
        finally:
            if temp_path.exists():
                os.remove(temp_path)

    def test_subtitle_service_full_flow(self):
        fake_client = MagicMock()
        fake_client.vertexai = True
        fake_client.models.generate_content.return_value = {
            "words": [
                {"word": "Спяваем", "start": 0.0, "end": 0.8},
                {"word": "разам", "start": 0.85, "end": 1.4},
            ]
        }

        genai_client = GenAIClient(
            api_key="fake-key",
            subtitle_model="gemini-3.5-transcribe",
            client=fake_client,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = FileStorage(data_dir=Path(tmp_dir))
            project_id = "test_project_123"

            # Create dummy audio in project directory
            source_dir = Path(tmp_dir) / project_id / "source"
            source_dir.mkdir(parents=True, exist_ok=True)
            dummy_audio = source_dir / "track.wav"
            dummy_audio.write_bytes(b"RIFFdummywavdata")

            service = SubtitleService(
                genai_client=genai_client,
                file_storage=storage,
            )

            entries = service.transcribe_audio(
                project_id=project_id,
                language="be",
                max_words=5,
            )

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].text, "Спяваем разам")
            self.assertEqual(entries[0].start_time, "00:00:00,000")
            self.assertEqual(entries[0].end_time, "00:00:01,400")

            # Check that SRT was saved
            srt_path = storage.get_subtitles_path(project_id)
            self.assertIsNotNone(srt_path)
            self.assertTrue(srt_path.exists())
            srt_content = srt_path.read_text(encoding="utf-8")
            self.assertIn("Спяваем разам", srt_content)

            # Check that words.json was saved
            words = storage.get_subtitle_words(project_id)
            self.assertIsNotNone(words)
            self.assertEqual(len(words), 2)
            self.assertEqual(words[0]["word"], "Спяваем")

    def test_subtitle_service_preserves_long_duration(self):
        """Ensure subtitles longer than 20 seconds are NOT corrupted by legacy heuristics."""
        fake_client = MagicMock()
        fake_client.vertexai = True
        fake_client.transcribe_audio_for_subtitles.return_value = (
            [
                {
                    "start": "00:01:10,000",
                    "end": "00:01:35,000",
                    "text": "Доўгі музычны альбо паэтычны фрагмент",
                }
            ],
            [
                {"word": "Доўгі", "start": 70.0, "end": 71.0},
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = FileStorage(data_dir=Path(tmp_dir))
            project_id = "test_long_duration"
            source_dir = Path(tmp_dir) / project_id / "source"
            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "track.wav").write_bytes(b"RIFFdummy")

            service = SubtitleService(
                genai_client=fake_client,
                file_storage=storage,
            )

            entries = service.transcribe_audio(project_id=project_id)
            self.assertEqual(len(entries), 1)
            # Must remain 00:01:10 -> 00:01:35 (25 seconds duration)
            self.assertEqual(entries[0].start_time, "00:01:10,000")
            self.assertEqual(entries[0].end_time, "00:01:35,000")

    def test_create_batch_job_vertex_ai(self):
        """Test Vertex AI-only batch prediction job creation."""
        fake_client = MagicMock()
        fake_client.vertexai = True
        mock_job = MagicMock()
        mock_job.name = "projects/test/locations/global/batchPredictionJobs/123"
        fake_client.batches.create.return_value = mock_job

        genai_client = GenAIClient(
            api_key="fake-key",
            client=fake_client,
        )

        # 1. Success with GCS URI
        job = genai_client.create_batch_job(
            dataset_name="test_job",
            source="gs://my-bucket/inputs.jsonl",
            dest="gs://my-bucket/output/",
        )
        self.assertIsNotNone(job)
        fake_client.batches.create.assert_called_once()
        call_kwargs = fake_client.batches.create.call_args[1]
        self.assertEqual(call_kwargs["src"], "gs://my-bucket/inputs.jsonl")

        # 2. Rejection of local file when no GCS bucket configured
        with self.assertRaises(ValueError):
            genai_client.create_batch_job(
                dataset_name="test_job_fail",
                source="local_requests.jsonl",
            )

        # 3. Rejection if not in Vertex AI mode
        genai_client.is_vertex = False
        with self.assertRaises(RuntimeError):
            genai_client.create_batch_job(
                dataset_name="test_job_fail_non_vertex",
                source="gs://my-bucket/inputs.jsonl",
            )


if __name__ == "__main__":
    unittest.main()