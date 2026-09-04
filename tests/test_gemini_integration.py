import os
import base64
import tempfile
import unittest
from pathlib import Path

from unittest.mock import MagicMock
from gemini_integration import (
    GeminiTranscriptionAdapter,
    GeminiTranscriptionError,
    _call_with_retry,
    _clean_time,
    _is_retryable_error,
    _load_service_account_json_from_env,
    is_transcribe_model,
)


class GeminiIntegrationTests(unittest.TestCase):
    def test_loads_service_account_json_from_file_env(self):
        payload = '{"type":"service_account","project_id":"demo-project"}'

        with tempfile.TemporaryDirectory() as tmp:
            cred_path = Path(tmp) / "service-account.json"
            cred_path.write_text(payload, encoding="utf-8")

            old_json = os.environ.pop("GOOGLE_SERVICE_ACCOUNT_JSON", None)
            old_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_FILE")
            old_adc = os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
            os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_FILE"] = str(cred_path)
            try:
                self.assertEqual(_load_service_account_json_from_env(), payload)
            finally:
                if old_json is not None:
                    os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = old_json
                if old_file is not None:
                    os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_FILE"] = old_file
                else:
                    os.environ.pop("GOOGLE_SERVICE_ACCOUNT_JSON_FILE", None)
                if old_adc is not None:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = old_adc

    def test_loads_service_account_json_from_base64_env(self):
        payload = '{"type":"service_account","project_id":"demo-project"}'
        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")

        old_json = os.environ.pop("GOOGLE_SERVICE_ACCOUNT_JSON", None)
        old_b64 = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_B64")
        old_file = os.environ.pop("GOOGLE_SERVICE_ACCOUNT_JSON_FILE", None)
        old_adc = os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_B64"] = encoded
        try:
            self.assertEqual(_load_service_account_json_from_env(), payload)
        finally:
            if old_json is not None:
                os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = old_json
            if old_b64 is not None:
                os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_B64"] = old_b64
            else:
                os.environ.pop("GOOGLE_SERVICE_ACCOUNT_JSON_B64", None)
            if old_file is not None:
                os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_FILE"] = old_file
            if old_adc is not None:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = old_adc

    def test_is_transcribe_model_detection(self):
        self.assertTrue(is_transcribe_model("gemini-3.5-transcribe"))
        self.assertTrue(is_transcribe_model("gemini-3.5-transcribe-live"))
        self.assertTrue(is_transcribe_model("models/gemini-3.5-transcribe"))
        self.assertFalse(is_transcribe_model("gemini-2.5-flash"))
        self.assertFalse(is_transcribe_model("gemini-2.0-flash"))
        self.assertFalse(is_transcribe_model(""))

    def test_clean_time_formats(self):
        self.assertEqual(_clean_time(1.25), 1.25)
        self.assertEqual(_clean_time("1.25s"), 1.25)
        self.assertEqual(_clean_time("0.8S"), 0.8)
        self.assertEqual(_clean_time("00:00:05,500"), 5.5)

    def test_extract_words_from_interaction_dict(self):
        interaction = {
            "words": [
                {"word": "Прывітанне", "start_time": "0.1s", "end_time": "0.8s"},
                {"word": "свет", "start_time": "0.9s", "end_time": "1.4s"},
            ]
        }
        words = GeminiTranscriptionAdapter._extract_words_from_interaction(interaction)
        self.assertEqual(len(words), 2)
        self.assertEqual(words[0]["word"], "Прывітанне")
        self.assertEqual(words[0]["start"], 0.1)
        self.assertEqual(words[0]["end"], 0.8)
        self.assertEqual(words[1]["word"], "свет")

    def test_transcribe_adapter_routing_transcribe_model(self):
        fake_client = MagicMock()
        # Mock files.upload and interactions.create
        fake_upload = MagicMock()
        fake_upload.uri = "files/123"
        fake_upload.name = "files/123"
        fake_client.files.upload.return_value = fake_upload

        fake_interaction = {
            "words": [
                {"word": "Тэставае", "start": 0.0, "end": 0.6},
                {"word": "слова", "start": 0.65, "end": 1.2},
            ]
        }
        fake_client.interactions.create.return_value = fake_interaction

        adapter = GeminiTranscriptionAdapter(
            api_key="fake-key-12345",
            model="gemini-3.5-transcribe",
            client_factory=lambda _key: fake_client,
        )
        self.assertTrue(adapter._is_transcribe)

        # In transcribe model, refine_timestamps returns draft_srt without touching API
        draft = "1\n00:00:00,000 --> 00:00:01,000\nТэст\n"
        self.assertEqual(adapter.refine_timestamps("dummy.wav", draft, 1.0), draft)

        # Transcribe with words
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFFdummywavdata")
            temp_path = f.name

        try:
            raw_json = adapter.transcribe(temp_path, length_mode="medium")
            import json
            segments = json.loads(raw_json)
            self.assertEqual(len(segments), 1)
            self.assertEqual(segments[0]["text"], "Тэставае слова")
            self.assertTrue(fake_client.interactions.create.called)
        finally:
            os.remove(temp_path)

    def test_is_retryable_error(self):
        class MockApiErr(Exception):
            def __init__(self, code, status, msg):
                super().__init__(msg)
                self.code = code
                self.status = status

        self.assertTrue(_is_retryable_error(MockApiErr(429, "RESOURCE_EXHAUSTED", "Resource exhausted")))
        self.assertTrue(_is_retryable_error(MockApiErr(503, "UNAVAILABLE", "Service unavailable")))
        self.assertTrue(_is_retryable_error(Exception("429 RESOURCE_EXHAUSTED. {'error': {'code': 429}}")))
        self.assertTrue(_is_retryable_error(TimeoutError("Connection timed out")))
        self.assertFalse(_is_retryable_error(MockApiErr(400, "INVALID_ARGUMENT", "Bad Request")))
        self.assertFalse(_is_retryable_error(Exception("Unsupported model interaction: gemini-3.5-transcribe-preview")))
        self.assertFalse(_is_retryable_error(None))

    def test_call_with_retry_success_after_429(self):
        attempts = 0
        statuses = []

        def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise Exception("429 RESOURCE_EXHAUSTED: rate limit exceeded")
            return "ok"

        res = _call_with_retry(
            flaky,
            operation_label="flaky_test",
            status=statuses.append,
            max_retries=4,
            initial_delay=0.01,
            backoff_factor=1.5,
        )
        self.assertEqual(res, "ok")
        self.assertEqual(attempts, 3)
        self.assertEqual(len(statuses), 2)
        self.assertTrue("429" in statuses[0])

    def test_call_with_retry_non_retryable_fails_fast(self):
        attempts = 0

        def invalid_call():
            nonlocal attempts
            attempts += 1
            raise Exception("Error code: 400 - Unsupported model interaction: gemini-3.5-transcribe-preview")

        with self.assertRaises(Exception) as ctx:
            _call_with_retry(invalid_call, max_retries=5, initial_delay=0.01)
        self.assertEqual(attempts, 1)
        self.assertIn("Unsupported model interaction", str(ctx.exception))

    def test_call_with_retry_exhausted(self):
        attempts = 0

        def always_429():
            nonlocal attempts
            attempts += 1
            raise Exception("429 RESOURCE_EXHAUSTED")

        with self.assertRaises(Exception):
            _call_with_retry(always_429, max_retries=3, initial_delay=0.01)
        self.assertEqual(attempts, 3)

    def test_transcribe_words_handles_400_and_retries_429(self):
        fake_client = MagicMock()
        # interactions.create raises 400 Unsupported model interaction
        fake_client.interactions.create.side_effect = Exception(
            "Error code: 400 - {'error': {'message': 'Unsupported model interaction: gemini-3.5-transcribe-preview', 'code': 'invalid_request'}}"
        )

        # generate_content fails with 429 on attempt 1, then succeeds on attempt 2
        gen_attempts = 0

        def mock_generate_content(*args, **kwargs):
            nonlocal gen_attempts
            gen_attempts += 1
            if gen_attempts == 1:
                raise Exception("429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED'}}")
            return {
                "words": [
                    {"word": "Адноўлена", "start": 0.0, "end": 0.5},
                    {"word": "паспяхова", "start": 0.5, "end": 1.0},
                ]
            }

        fake_client.models.generate_content.side_effect = mock_generate_content

        adapter = GeminiTranscriptionAdapter(
            api_key="fake-key-12345",
            model="gemini-3.5-transcribe-preview",
            client_factory=lambda _key: fake_client,
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFFdummywavdata")
            temp_path = f.name

        try:
            status_msgs = []
            os.environ["GEMINI_RETRY_INITIAL_DELAY"] = "0.01"
            words = adapter.transcribe_words(temp_path, status=status_msgs.append)
            self.assertEqual(len(words), 2)
            self.assertEqual(words[0]["word"], "Адноўлена")
            self.assertEqual(words[1]["word"], "паспяхова")
            self.assertTrue(adapter._interactions_unsupported)
            self.assertEqual(gen_attempts, 2)
            self.assertTrue(any("429" in s for s in status_msgs))
        finally:
            os.remove(temp_path)
            os.environ.pop("GEMINI_RETRY_INITIAL_DELAY", None)

    def test_vertex_ai_bypasses_interactions_create(self):
        fake_client = MagicMock()
        fake_client.vertexai = True
        fake_client.models.generate_content.return_value = {
            "words": [{"word": "Тэст", "start": 0.0, "end": 0.5}]
        }

        adapter = GeminiTranscriptionAdapter(
            api_key="fake-key-12345",
            model="gemini-3.5-transcribe-preview",
            client_factory=lambda _key: fake_client,
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFFdummywavdata")
            temp_path = f.name

        try:
            words = adapter.transcribe_words(temp_path)
            self.assertEqual(len(words), 1)
            self.assertEqual(words[0]["word"], "Тэст")
            # interactions.create must NEVER be called on Vertex AI!
            fake_client.interactions.create.assert_not_called()
            fake_client.models.generate_content.assert_called_once()
        finally:
            os.remove(temp_path)

    def test_vertex_ai_plain_text_response_word_segmentation(self):
        fake_client = MagicMock()
        fake_client.vertexai = True

        fake_resp = MagicMock()
        fake_resp.text = "Прывітанне гэта тэставы запіс"
        fake_resp.candidates = [
            MagicMock(
                content=MagicMock(
                    parts=[MagicMock(text="Прывітанне гэта тэставы запіс", thought=False)]
                )
            )
        ]
        fake_client.models.generate_content.return_value = fake_resp

        adapter = GeminiTranscriptionAdapter(
            api_key="fake-key-12345",
            model="gemini-3.5-transcribe-preview",
            client_factory=lambda _key: fake_client,
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFFdummywavdata")
            temp_path = f.name

        try:
            words = adapter.transcribe_words(temp_path, duration_sec=4.0)
            self.assertEqual(len(words), 4)
            self.assertEqual([w["word"] for w in words], ["Прывітанне", "гэта", "тэставы", "запіс"])
            self.assertEqual(words[0]["start"], 0.0)
            self.assertEqual(words[-1]["end"], 4.0)
            fake_client.interactions.create.assert_not_called()
        finally:
            os.remove(temp_path)

    def test_model_name_normalizes_to_preview_suffix(self):
        adapter = GeminiTranscriptionAdapter(
            api_key="fake-key-12345",
            model="gemini-3.5-transcribe",
            client_factory=lambda _key: MagicMock(),
        )
        self.assertEqual(adapter._model, "gemini-3.5-transcribe-preview")

        adapter_pub = GeminiTranscriptionAdapter(
            api_key="fake-key-12345",
            model="publishers/google/models/gemini-3.5-transcribe",
            client_factory=lambda _key: MagicMock(),
        )
        self.assertEqual(adapter_pub._model, "publishers/google/models/gemini-3.5-transcribe-preview")

    def test_interactions_unsupported_cached_across_instances(self):
        GeminiTranscriptionAdapter._unsupported_interaction_models.clear()
        fake_client = MagicMock()
        fake_client.vertexai = False
        fake_client.interactions.create.side_effect = Exception(
            "Error code: 400 - Unsupported model interaction: test-model"
        )
        fake_client.models.generate_content.return_value = {
            "words": [{"word": "Слова", "start": 0.0, "end": 1.0}]
        }

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFFdummywavdata")
            temp_path = f.name

        try:
            adapter1 = GeminiTranscriptionAdapter(
                api_key="fake-key-12345",
                model="test-model",
                client_factory=lambda _key: fake_client,
            )
            adapter1.transcribe_words(temp_path)
            self.assertTrue(adapter1._interactions_unsupported)
            self.assertEqual(fake_client.interactions.create.call_count, 1)

            # Create a second adapter for the same model - it should remember and not call interactions.create again
            adapter2 = GeminiTranscriptionAdapter(
                api_key="fake-key-12345",
                model="test-model",
                client_factory=lambda _key: fake_client,
            )
            self.assertTrue(adapter2._interactions_unsupported)
            adapter2.transcribe_words(temp_path)
            # interactions.create should NOT have been called a second time
            self.assertEqual(fake_client.interactions.create.call_count, 1)
        finally:
            os.remove(temp_path)
            GeminiTranscriptionAdapter._unsupported_interaction_models.clear()

    def test_extract_words_from_json_word_timestamps(self):
        json_text = """```json
        [
            {"word": "Прывітанне", "start": 0.15, "end": 0.72},
            {"word": "дарагія", "start": 0.78, "end": 1.34},
            {"word": "сябры", "start": 1.40, "end": 1.95}
        ]
        ```"""
        words = GeminiTranscriptionAdapter._extract_words_from_text(json_text)
        self.assertEqual(len(words), 3)
        self.assertEqual(words[0]["word"], "Прывітанне")
        self.assertEqual(words[0]["start"], 0.15)
        self.assertEqual(words[0]["end"], 0.72)
        self.assertEqual(words[2]["word"], "сябры")
        self.assertEqual(words[2]["start"], 1.40)
        self.assertEqual(words[2]["end"], 1.95)

    def test_extract_words_from_inline_range_timestamps(self):
        text = "[00:00.12 - 00:00.65] Першае [00:00.70 - 00:01.25] другое слова"
        words = GeminiTranscriptionAdapter._extract_words_from_text(text)
        self.assertEqual(len(words), 3)
        self.assertEqual(words[0]["word"], "Першае")
        self.assertEqual(words[0]["start"], 0.12)
        self.assertEqual(words[0]["end"], 0.65)
        self.assertEqual(words[1]["word"], "другое")
        self.assertEqual(words[2]["word"], "слова")
        self.assertEqual(words[2]["end"], 1.25)

    def test_extract_words_from_inline_point_timestamps(self):
        text = "[00:01.20] Першае [00:01.80] другое [00:02.50]"
        words = GeminiTranscriptionAdapter._extract_words_from_text(text)
        self.assertEqual(len(words), 2)
        self.assertEqual(words[0]["word"], "Першае")
        self.assertEqual(words[0]["start"], 1.20)
        self.assertEqual(words[0]["end"], 1.80)
        self.assertEqual(words[1]["word"], "другое")
        self.assertEqual(words[1]["start"], 1.80)
        self.assertEqual(words[1]["end"], 2.50)

    def test_gemini_api_uses_interactions_create_and_files_upload(self):
        fake_client = MagicMock()
        fake_client.vertexai = False
        fake_file = MagicMock()
        fake_file.uri = "https://generativelanguage.googleapis.com/v1beta/files/test123"
        fake_file.mime_type = "audio/wav"
        fake_client.files.upload.return_value = fake_file

        fake_interaction = MagicMock()
        fake_interaction.model_dump.return_value = {
            "words": [
                {"word": "Прывітанне", "start": 0.0, "end": 0.5},
                {"word": "свет", "start": 0.5, "end": 1.0},
            ]
        }
        fake_client.interactions.create.return_value = fake_interaction

        adapter = GeminiTranscriptionAdapter(
            api_key="fake-key-12345",
            model="gemini-3.5-transcribe",
            client_factory=lambda _key: fake_client,
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFFdummywavdata")
            temp_path = f.name

        try:
            words = adapter.transcribe_words(temp_path)
            self.assertEqual(len(words), 2)
            self.assertEqual(words[0]["word"], "Прывітанне")
            self.assertEqual(words[1]["word"], "свет")
            fake_client.files.upload.assert_called_once_with(file=temp_path)
            fake_client.interactions.create.assert_called_once()
            call_kwargs = fake_client.interactions.create.call_args[1]
            self.assertEqual(call_kwargs["model"], "gemini-3.5-transcribe")
            self.assertEqual(call_kwargs["input"][0]["uri"], fake_file.uri)
        finally:
            os.remove(temp_path)

    def test_extract_words_from_audio_transcription_part(self):
        fake_response = MagicMock()
        fake_candidate = MagicMock()
        fake_part = MagicMock()
        fake_part.text = "Прывітанне свет"
        fake_part.audio_transcription = {
            "words": [
                {"text": "Прывітанне", "start_offset": "0.120s", "end_offset": "0.550s"},
                {"text": "свет", "start_offset": {"seconds": 0, "nanos": 550000000}, "end_offset": "1.000s"},
            ]
        }
        fake_candidate.content.parts = [fake_part]
        fake_response.candidates = [fake_candidate]

        words = GeminiTranscriptionAdapter._extract_words_from_interaction(fake_response)
        self.assertEqual(len(words), 2)
        self.assertEqual(words[0]["word"], "Прывітанне")
        self.assertAlmostEqual(words[0]["start"], 0.12, places=2)
        self.assertAlmostEqual(words[0]["end"], 0.55, places=2)
        self.assertEqual(words[1]["word"], "свет")
        self.assertAlmostEqual(words[1]["start"], 0.55, places=2)
        self.assertAlmostEqual(words[1]["end"], 1.00, places=2)

    def test_extract_words_from_google_cloud_notebook_schema(self):
        # Matches official Google Cloud notebook schema:
        # parts[0].audio_transcription.words where items have word, start_offset, end_offset
        class MockWordInfo:
            def __init__(self, word, start_offset, end_offset):
                self.word = word
                self.start_offset = start_offset
                self.end_offset = end_offset

        class MockAudioTranscription:
            def __init__(self, text, words):
                self.text = text
                self.words = words

        class MockPart:
            def __init__(self, audio_tx):
                self.text = None
                self.audio_transcription = audio_tx

        class MockResponse:
            def __init__(self, parts):
                self.parts = parts

        audio_tx = MockAudioTranscription(
            text="Прывітанне свет",
            words=[
                MockWordInfo("Прывітанне", "0.100s", "0.450s"),
                MockWordInfo("свет", "0.500s", "0.950s"),
            ],
        )
        resp = MockResponse(parts=[MockPart(audio_tx)])

        words = GeminiTranscriptionAdapter._extract_words_from_interaction(resp)
        self.assertEqual(len(words), 2)
        self.assertEqual(words[0]["word"], "Прывітанне")
        self.assertAlmostEqual(words[0]["start"], 0.10, places=2)
        self.assertAlmostEqual(words[0]["end"], 0.45, places=2)
        self.assertEqual(words[1]["word"], "свет")
        self.assertAlmostEqual(words[1]["start"], 0.50, places=2)
        self.assertAlmostEqual(words[1]["end"], 0.95, places=2)

        # Also test _extract_response_text extracts text from audio_transcription when part.text is None
        adapter = GeminiTranscriptionAdapter(
            api_key="fake-key",
            model="gemini-3.5-transcribe",
            client_factory=lambda _key: MagicMock(),
        )
        extracted_text = adapter._extract_response_text(resp)
        self.assertEqual(extracted_text, "Прывітанне свет")

    def test_build_system_instruction(self):
        from gemini_prompts import _build_system_instruction
        instr = _build_system_instruction(
            length_mode="medium",
            prompt_text="Custom prompt instruction",
            duration_sec=12.5,
        )
        self.assertIn("Custom prompt instruction", instr)
        self.assertIn("Audio duration constraint", instr)
        self.assertIn("Belarusian", instr)


if __name__ == "__main__":
    unittest.main()

