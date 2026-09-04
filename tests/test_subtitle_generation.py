import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure Clipmaker root is in sys.path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from subtitle_generation import (
    group_words_into_subtitles,
    model_response_to_srt,
    read_srt_file,
)


class SubtitleGenerationTests(unittest.TestCase):
    def test_json_model_response_becomes_srt_text(self):
        raw = (
            '[{"start": "00:00:00,000", "end": "00:00:01,500", '
            '"text": "Прывітанне ўсім"}]'
        )

        srt_text, segments = model_response_to_srt(raw, duration_sec=5.0)

        self.assertEqual(len(segments), 1)
        self.assertIn("1\n00:00:00,000 --> 00:00:01,500\nПрывітанне ўсім", srt_text)

    def test_read_srt_file_preserves_imported_subtitles(self):
        content = "1\n00:00:00,000 --> 00:00:01,000\nГатовы субцітр\n"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "imported.srt"
            path.write_text(content, encoding="utf-8")

            self.assertEqual(read_srt_file(str(path)), content)

    def test_group_words_short_mode(self):
        words = [
            {"word": "Слова", "start": 0.0, "end": 0.4},
            {"word": "адзін", "start": 0.45, "end": 0.8},
            {"word": "слова", "start": 0.85, "end": 1.2},
            {"word": "два", "start": 1.25, "end": 1.6},
        ]
        segments = group_words_into_subtitles(words, length_mode="short")
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["text"], "Слова адзін")
        self.assertEqual(segments[1]["text"], "слова два")
        self.assertEqual(segments[0]["start"], "00:00:00,000")
        self.assertEqual(segments[0]["end"], "00:00:00,800")

    def test_group_words_pause_split(self):
        words = [
            {"word": "Першы", "start": 0.0, "end": 0.5},
            {"word": "фрагмент.", "start": 0.55, "end": 1.0},
            # 1.5-second pause
            {"word": "Другі", "start": 2.5, "end": 3.0},
            {"word": "фрагмент.", "start": 3.05, "end": 3.5},
        ]
        segments = group_words_into_subtitles(words, length_mode="medium")
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["text"], "Першы фрагмент.")
        self.assertEqual(segments[1]["text"], "Другі фрагмент.")
        self.assertEqual(segments[1]["start"], "00:00:02,500")

    def test_group_words_with_seconds_suffix_and_duration_capping(self):
        words = [
            {"word": "Прывітанне", "start_time": "1.0s", "end_time": "1.8s"},
            {"word": "свет", "start_time": "1.85s", "end_time": "2.5s"},
            {"word": "пасля", "start_time": "10.0s", "end_time": "10.5s"},
        ]
        # audio duration is 5.0 seconds -> 3rd word should be discarded
        segments = group_words_into_subtitles(words, length_mode="medium", duration_sec=5.0)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["text"], "Прывітанне свет")
        self.assertEqual(segments[0]["start"], "00:00:01,000")
        self.assertEqual(segments[0]["end"], "00:00:02,500")

    def test_transcribe_pipeline_routing(self):
        from unittest.mock import patch
        from subtitle_generation import transcribe_audio_to_segments

        sample_json = '[{"start": "00:00:00,000", "end": "00:00:02,000", "text": "Прывітанне"}]'

        # 1. When is_transcribe_model is True -> second pass is NOT called
        with (
            patch("subtitle_generation._validate"),
            patch("subtitle_generation._get_duration_sec", return_value=5.0),
            patch("subtitle_generation.transcribe_with_gemini", return_value=sample_json),
            patch("subtitle_generation.is_transcribe_model", return_value=True),
            patch("subtitle_generation._refine_segments_second_pass") as mock_second_pass,
        ):
            segs = transcribe_audio_to_segments("fake.wav")
            self.assertEqual(len(segs), 1)
            mock_second_pass.assert_not_called()

        # 2. When is_transcribe_model is False -> second pass IS called (legacy mode)
        with (
            patch("subtitle_generation._validate"),
            patch("subtitle_generation._get_duration_sec", return_value=5.0),
            patch("subtitle_generation.transcribe_with_gemini", return_value=sample_json),
            patch("subtitle_generation.is_transcribe_model", return_value=False),
            patch(
                "subtitle_generation._refine_segments_second_pass",
                return_value=[{"start": 0.0, "end": 2.0, "text": "Прывітанне"}],
            ) as mock_second_pass,
        ):
            segs = transcribe_audio_to_segments("fake.wav")
            self.assertEqual(len(segs), 1)
            mock_second_pass.assert_called_once()

    def test_transcribe_pipeline_quota_fallback(self):
        from unittest.mock import patch
        from gemini_integration import GeminiTranscriptionError
        from subtitle_generation import transcribe_audio_to_segments

        sample_legacy_json = '[{"start": "00:00:00,000", "end": "00:00:02,000", "text": "Рэзервовы тэкст"}]'

        def mock_transcribe_with_gemini(path, status=None, length_mode="medium", duration_sec=None, model=None, **kwargs):
            if model and "transcribe" in model:
                raise GeminiTranscriptionError(
                    "Vertex AI transcription failed (gemini-3.5-transcribe-preview): 429 RESOURCE_EXHAUSTED"
                )
            return sample_legacy_json

        status_msgs = []
        with (
            patch("subtitle_generation._validate"),
            patch("subtitle_generation._get_duration_sec", return_value=5.0),
            patch("subtitle_generation.transcribe_with_gemini", side_effect=mock_transcribe_with_gemini),
            patch(
                "subtitle_generation._refine_segments_second_pass",
                return_value=[{"start": 0.0, "end": 2.0, "text": "Рэзервовы тэкст"}],
            ) as mock_second_pass,
        ):
            segs = transcribe_audio_to_segments(
                "fake.wav",
                status=status_msgs.append,
                model="gemini-3.5-transcribe-preview",
            )
            self.assertEqual(len(segs), 1)
            self.assertEqual(segs[0]["text"], "Рэзервовы тэкст")
            mock_second_pass.assert_called_once()
            self.assertTrue(any("вычарпана" in s for s in status_msgs))

    def test_subtitle_process_result_tuple_behavior(self):
        from subtitle_generation import SegmentList, SubtitleProcessResult

        words = [{"word": "Прывітанне", "start": 0.0, "end": 0.5}]
        segs = SegmentList([{"start": 0.0, "end": 0.5, "text": "Прывітанне"}], words=words, duration_sec=5.0)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs.words, words)
        self.assertEqual(segs.duration_sec, 5.0)

        res = SubtitleProcessResult("dummy_srt_content", "dummy.srt", words=words, duration_sec=5.0)
        self.assertIsInstance(res, tuple)
        self.assertEqual(len(res), 2)
        content, path = res
        self.assertEqual(content, "dummy_srt_content")
        self.assertEqual(path, "dummy.srt")
        self.assertEqual(res.words, words)
        self.assertEqual(res.duration_sec, 5.0)

    def test_default_model_is_gemini_35_transcribe(self):
        from app.core.config import settings
        self.assertIn("transcribe", settings.genai_subtitle_model)

    def test_instant_length_rebuild_from_cached_words(self):
        words = [
            {"word": "Першае", "start": 0.0, "end": 0.4},
            {"word": "другое", "start": 0.45, "end": 0.8},
            {"word": "трэцяе", "start": 0.85, "end": 1.2},
            {"word": "чацвёртае", "start": 1.25, "end": 1.6},
        ]
        short_segs = group_words_into_subtitles(words, length_mode="short")
        medium_segs = group_words_into_subtitles(words, length_mode="medium")
        long_segs = group_words_into_subtitles(words, length_mode="long")

        self.assertEqual(len(short_segs), 2)
        self.assertEqual(len(medium_segs), 1)
        self.assertEqual(len(long_segs), 1)
        self.assertEqual(short_segs[0]["text"], "Першае другое")
        self.assertEqual(medium_segs[0]["text"], "Першае другое трэцяе чацвёртае")


if __name__ == "__main__":
    unittest.main()