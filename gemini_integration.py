"""Google Gemini transcription integration for API-key-based Express Mode.

Public wrappers expected by app.py:
- transcribe_with_gemini(path, status, length_mode, duration_sec=None)
- refine_timestamps_with_gemini(path, draft_srt, duration_sec, status)
"""

from __future__ import annotations

import json
import base64
import logging
import os
from typing import Any, Callable, Optional

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover
    genai = None
    types = None

from gemini_auth import (
    GeminiTranscriptionError,
    _call_with_retry,
    _is_retryable_error,
    _clean_time,
    is_transcribe_model,
    _load_service_account_json_from_env,
    _load_local_env,
    _configure_adc_from_service_account_json,
    _validate_api_key_format,
)
from gemini_prompts import (
    _build_duration_instruction,
    _get_format_instruction,
    _build_system_instruction,
    _build_timestamp_refinement_instruction,
    _guess_audio_mime,
)
from gemini_word_extraction import (
    _extract_words_from_text,
    _extract_words_from_steps,
    _extract_words_from_interaction,
)

logger = logging.getLogger(__name__)

_last_transcribed_words: list[dict] | None = None

class GeminiTranscriptionAdapter:
    """Adapter around Vertex AI Gemini for subtitle generation."""

    provider_name = "gemini"
    _unsupported_interaction_models: set[str] = set()

    @property
    def _interactions_unsupported(self) -> bool:
        return self._model in self._unsupported_interaction_models

    @_interactions_unsupported.setter
    def _interactions_unsupported(self, val: bool) -> None:
        if val:
            self._unsupported_interaction_models.add(self._model)
        else:
            self._unsupported_interaction_models.discard(self._model)

    def __init__(
        self,
        api_key: Optional[str],
        model: str,
        prompt_text: str = "",
        client_factory: Optional[Callable[[str], Any]] = None,
    ) -> None:
        if genai is None or types is None:
            raise GeminiTranscriptionError(
                "google-genai library is not available. Install google-genai."
            )

        self._service_account_json = _load_service_account_json_from_env()
        self._api_key = api_key or (
            os.environ.get("gemini")
            or os.environ.get("gembeh")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        self._prompt_text = prompt_text or ""
        model_clean = model.strip()
        if model_clean.startswith("models/"):
            model_clean = model_clean[len("models/"):]
        if model_clean in ("gemini-3.5-transcribe", "publishers/google/models/gemini-3.5-transcribe"):
            model_clean += "-preview"
        self._model = model_clean
        self._project = (
            os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GOOGLE_PROJECT")
            or ""
        ).strip()
        self._location = (
            os.environ.get("GOOGLE_CLOUD_LOCATION")
            or os.environ.get("GOOGLE_CLOUD_REGION")
            or os.environ.get("GOOGLE_VERTEX_LOCATION")
            or "global"
        ).strip()

        if self._service_account_json:
            self._project = _configure_adc_from_service_account_json(
                self._service_account_json,
                self._project,
            )
        elif not self._api_key and not (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or self._project):
            raise GeminiTranscriptionError(
                "GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SERVICE_ACCOUNT_JSON_B64, "
                "GOOGLE_SERVICE_ACCOUNT_JSON_FILE, GOOGLE_APPLICATION_CREDENTIALS, "
                "gemini, gembeh, GOOGLE_API_KEY, or GEMINI_API_KEY is not configured."
            )

        if self._api_key:
            _validate_api_key_format(self._api_key)

        if not self._model:
            raise GeminiTranscriptionError(
                "Model name is empty. Set env var 'mod', for example: gemini-2.5-flash"
            )

        self._is_transcribe = is_transcribe_model(self._model)
        self._client_factory = client_factory or self._default_client_factory
        self._client = self._client_factory(self._api_key)

    def _call_with_retry(
        self,
        fn: Callable[[], Any],
        *,
        operation_label: str = "API request",
        status: Optional[Callable[[str], None]] = None,
        max_retries: Optional[int] = None,
        initial_delay: Optional[float] = None,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
    ) -> Any:
        return _call_with_retry(
            fn,
            operation_label=operation_label,
            status=status,
            max_retries=max_retries,
            initial_delay=initial_delay,
            backoff_factor=backoff_factor,
            max_delay=max_delay,
        )

    def _default_client_factory(self, api_key: Optional[str]) -> Any:
        use_vertex = (
            os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").strip().lower() not in ("0", "false", "no")
            and os.getenv("VERTEXAI", "true").strip().lower() not in ("0", "false", "no")
        )
        if use_vertex or self._service_account_json or self._project:
            has_service_account = bool(self._service_account_json or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
            effective_key = None if has_service_account else (api_key or None)
            return genai.Client(
                vertexai=True,
                project=self._project or None,
                location=self._location,
                api_key=effective_key,
            )

        # Standard Gemini Developer API (ai.google.dev per official documentation)
        return genai.Client(api_key=api_key)

    def _build_user_content(
        self,
        audio_bytes: bytes,
        mime: str,
        extra_text: str | None = None,
    ) -> "types.Content":
        parts = []

        if extra_text and extra_text.strip():
            parts.append(types.Part.from_text(text=extra_text.strip()))

        parts.append(types.Part.from_bytes(data=audio_bytes, mime_type=mime))

        return types.Content(role="user", parts=parts)

    def _get_max_output_tokens(self) -> int:
        raw = os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "65536").strip()

        try:
            value = int(raw)
        except ValueError:
            logger.warning("Invalid GEMINI_MAX_OUTPUT_TOKENS=%r; using 65536", raw)
            value = 65536

        return max(2048, min(value, 65536))

    def _new_generate_config(self, **kwargs: Any) -> "types.GenerateContentConfig":
        try:
            return types.GenerateContentConfig(**kwargs)
        except Exception as exc:
            if "max_output_tokens" in kwargs:
                logger.warning(
                    "GenerateContentConfig rejected max_output_tokens; retrying without it: %s",
                    exc,
                )
                kwargs = dict(kwargs)
                kwargs.pop("max_output_tokens", None)
                return types.GenerateContentConfig(**kwargs)

            raise

    def _make_generate_config(
        self,
        system_instruction: str,
        *,
        response_mime_type: str | None = "application/json",
        thinking_budget: int | None = -1,
    ) -> "types.GenerateContentConfig":
        kwargs: dict[str, Any] = {
            "temperature": 0.0,
            "system_instruction": system_instruction,
            "max_output_tokens": self._get_max_output_tokens(),
        }

        if response_mime_type:
            kwargs["response_mime_type"] = response_mime_type

        if thinking_budget is not None:
            kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=thinking_budget
            )

        return self._new_generate_config(**kwargs)

    def _extract_response_text(
        self,
        response: Any,
        *,
        attempt_name: str = "",
        raise_on_empty: bool = True,
    ) -> str:
        # 1. First inspect candidates/parts directly.
        # This handles both part.text and part.audio_transcription.text, and prevents
        # the SDK's response.text property from logging "Warning: there are non-text parts in the response".
        pieces: list[str] = []
        has_non_text_parts = False

        parts_to_scan = []
        parts_val = getattr(response, "parts", None)
        if isinstance(parts_val, (list, tuple)) and parts_val:
            parts_to_scan.extend(parts_val)
        else:
            candidates = getattr(response, "candidates", None) or []
            if isinstance(candidates, (list, tuple)):
                for cand in candidates:
                    content = getattr(cand, "content", None)
                    if content:
                        cand_parts = getattr(content, "parts", None)
                        if isinstance(cand_parts, (list, tuple)):
                            parts_to_scan.extend(cand_parts)

        for part in parts_to_scan:
            if bool(getattr(part, "thought", False)):
                continue

            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                pieces.append(part_text.strip())
            else:
                # Check audio_transcription per Google Cloud gemini_3_5_transcribe sample
                at = getattr(part, "audio_transcription", None)
                if at is not None:
                    has_non_text_parts = True
                    at_text = getattr(at, "text", None) or (at.get("text") if isinstance(at, dict) else None)
                    if isinstance(at_text, str) and at_text.strip():
                        pieces.append(at_text.strip())

        if pieces:
            return "\n".join(pieces).strip()

        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            try:
                return json.dumps(parsed, ensure_ascii=False)
            except Exception:
                logger.debug("Could not JSON-dump response.parsed", exc_info=True)

        if not has_non_text_parts:
            try:
                direct_text = getattr(response, "text", None)
                if isinstance(direct_text, str) and direct_text.strip():
                    return direct_text.strip()
            except Exception:
                pass

        text = "\n".join(pieces).strip()

        if text:
            return text

        summary = self._summarize_empty_response(response)
        logger.error(
            "Gemini returned no visible text. attempt=%s summary=%s",
            attempt_name,
            summary,
        )

        if raise_on_empty:
            raise GeminiTranscriptionError(
                "Gemini returned an empty visible response. "
                f"Attempt={attempt_name}. Details: {summary}"
            )

        return ""

    def _summarize_empty_response(self, response: Any) -> str:
        details: dict[str, Any] = {}

        prompt_feedback = getattr(response, "prompt_feedback", None)

        if prompt_feedback is not None:
            details["prompt_feedback"] = self._safe_model_dump(prompt_feedback)

        usage_metadata = getattr(response, "usage_metadata", None)

        if usage_metadata is not None:
            details["usage_metadata"] = self._safe_model_dump(usage_metadata)

        candidates_info: list[dict[str, Any]] = []
        candidates = getattr(response, "candidates", None) or []

        for idx, cand in enumerate(candidates):
            info: dict[str, Any] = {"index": idx}

            for attr in ("finish_reason", "finish_message"):
                value = getattr(cand, attr, None)

                if value is not None:
                    info[attr] = str(value)

            safety = getattr(cand, "safety_ratings", None)

            if safety is not None:
                info["safety_ratings"] = self._safe_model_dump(safety)

            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) or []
            info["part_count"] = len(parts)
            candidates_info.append(info)

        details["candidates"] = candidates_info

        try:
            return json.dumps(details, ensure_ascii=False, default=str)[:4000]
        except Exception:
            return str(details)[:4000]

    def _safe_model_dump(self, obj: Any, visited: dict[int, Any] = None) -> Any:
        if visited is None:
            visited = {}
            
        obj_id = id(obj)
        if obj_id in visited:
            return "<cycle>"
        visited[obj_id] = obj
        
        try:
            if hasattr(obj, "model_dump"):
                return obj.model_dump(exclude_none=True)

            if hasattr(obj, "to_json_dict"):
                return obj.to_json_dict()

            if isinstance(obj, list):
                return [self._safe_model_dump(x, visited) for x in obj]

            if isinstance(obj, tuple):
                return tuple(self._safe_model_dump(x, visited) for x in obj)

            if isinstance(obj, dict):
                return {k: self._safe_model_dump(v, visited) for k, v in obj.items()}
        except Exception:
            pass

        return str(obj)

    def _looks_truncated_json_text(self, text: str) -> bool:
        stripped = text.strip()

        if not stripped:
            return False

        try:
            json.loads(stripped)
            return False
        except json.JSONDecodeError:
            pass

        json_like = (
            stripped.startswith("[")
            or stripped.startswith("{")
            or '"start"' in stripped
            or '"end"' in stripped
            or '"text"' in stripped
        )

        if not json_like:
            return False

        if stripped[-1] not in "]}":
            return True

        if stripped.count("[") > stripped.count("]"):
            return True

        if stripped.count("{") > stripped.count("}"):
            return True

        return False

    def _generate_content_text(
        self,
        *,
        contents: list[Any],
        system_instruction: str,
        operation_label: str,
        status: Optional[Callable[[str], None]] = None,
    ) -> str:
        attempts: list[tuple[str, "types.GenerateContentConfig", bool]] = [
            (
                f"{operation_label}:json_dynamic_thinking",
                self._make_generate_config(
                    system_instruction,
                    response_mime_type="application/json",
                    thinking_budget=-1,
                ),
                False,
            ),
            (
                f"{operation_label}:json_no_thinking",
                self._make_generate_config(
                    system_instruction,
                    response_mime_type="application/json",
                    thinking_budget=0,
                ),
                False,
            ),
            (
                f"{operation_label}:plain_no_thinking",
                self._make_generate_config(
                    system_instruction,
                    response_mime_type=None,
                    thinking_budget=0,
                ),
                False,
            ),
            (
                f"{operation_label}:stream_json_no_thinking",
                self._make_generate_config(
                    system_instruction,
                    response_mime_type="application/json",
                    thinking_budget=0,
                ),
                True,
            ),
        ]

        empty_summaries: list[str] = []
        truncated_outputs: list[str] = []
        last_error: Exception | None = None

        for attempt_idx, (attempt_name, config, use_stream) in enumerate(attempts, 1):
            if status is not None and attempt_idx > 1:
                status(
                    "Gemini вярнуў пусты або няпоўны адказ; паўтараем запыт "
                    f"({attempt_idx}/{len(attempts)}) …"
                )

            try:
                if use_stream:
                    text = self._call_with_retry(
                        lambda: self._generate_stream_text(
                            contents=contents,
                            config=config,
                            attempt_name=attempt_name,
                        ),
                        operation_label=f"Gemini {attempt_name}",
                        status=status,
                    )
                else:
                    response = self._call_with_retry(
                        lambda: self._client.models.generate_content(
                            model=self._model,
                            contents=contents,
                            config=config,
                        ),
                        operation_label=f"Gemini {attempt_name}",
                        status=status,
                    )
                    text = self._extract_response_text(
                        response,
                        attempt_name=attempt_name,
                        raise_on_empty=False,
                    )

                text = text.strip()

                if text:
                    if self._looks_truncated_json_text(text):
                        logger.warning(
                            "Gemini returned a likely truncated JSON response on attempt %s. chars=%s. Retrying.",
                            attempt_name,
                            len(text),
                        )
                        truncated_outputs.append(text)
                        continue

                    if attempt_idx > 1:
                        logger.warning(
                            "Gemini succeeded after fallback attempt: %s",
                            attempt_name,
                        )

                    return text

                empty_summaries.append(attempt_name)

            except Exception as exc:  # pragma: no cover
                last_error = exc
                logger.exception("Gemini attempt failed: %s", attempt_name)

        if truncated_outputs:
            best = max(truncated_outputs, key=len)
            logger.error(
                "All Gemini attempts returned truncated JSON. Returning longest partial response for salvage. chars=%s",
                len(best),
            )
            return best

        message = (
            "Gemini returned no visible subtitle text after retries. "
            f"Empty attempts: {', '.join(empty_summaries) or 'none'}."
        )

        if last_error is not None:
            message += f" Last error: {last_error}"

        raise GeminiTranscriptionError(message)

    def _generate_stream_text(
        self,
        *,
        contents: list[Any],
        config: "types.GenerateContentConfig",
        attempt_name: str,
    ) -> str:
        chunks: list[str] = []

        stream = self._client.models.generate_content_stream(
            model=self._model,
            contents=contents,
            config=config,
        )

        for chunk in stream:
            chunk_text = self._extract_response_text(
                chunk,
                attempt_name=attempt_name,
                raise_on_empty=False,
            )

            if chunk_text:
                chunks.append(chunk_text)

        return "".join(chunks).strip()

    def _store_transcribed_words(self, words: list[dict]) -> list[dict]:
        global _last_transcribed_words
        self.last_words = words
        _last_transcribed_words = words
        return words

    def transcribe_words(
        self,
        path: str,
        status: Optional[Callable[[str], None]] = None,
        duration_sec: Optional[float] = None,
        language: Optional[str] = None,
    ) -> list[dict]:
        mime = _guess_audio_mime(path)
        with open(path, "rb") as af:
            audio_bytes = af.read()

        if status is not None:
            status("Распазнаем аўдыё праз Vertex AI gemini-3.5-transcribe …")

        transcribe_mode = os.getenv("TRANSCRIBE_MODE", "verbatim").strip()
        mode_payload: Any = transcribe_mode
        if transcribe_mode == "verbatim":
            mode_payload = {
                "type": "verbatim",
                "timestamp_granularities": ["word"],
            }

        if language and language != "auto":
            if language.lower() in ("be", "bel", "by"):
                lang_codes = ["be-BY"]
            elif language.lower() in ("ru", "rus"):
                lang_codes = ["ru-RU"]
            elif language.lower() in ("en", "eng"):
                lang_codes = ["en-US"]
            else:
                lang_codes = [language]
        else:
            lang_codes_env = os.getenv("TRANSCRIBE_LANGUAGE_CODES", os.getenv("LANGUAGE_CODES", "be-BY")).strip()
            lang_codes = [c.strip() for c in lang_codes_env.split(",") if c.strip()] or ["be-BY"]

        generation_config: dict[str, Any] = {
            "transcription_config": {
                "language_codes": lang_codes,
                "word_level_timestamps": True,
                "mode": mode_payload,
            }
        }

        custom_vocab_raw = os.getenv("CUSTOM_VOCABULARY", "").strip()
        if custom_vocab_raw:
            vocab_list = [v.strip() for v in custom_vocab_raw.split(",") if v.strip()]
            if vocab_list:
                generation_config["transcription_config"]["custom_vocabulary"] = vocab_list[:1000]

        # Check whether the client is configured for Vertex AI
        is_vertex = getattr(self._client, "vertexai", False) is True

        call_model = self._model
        if is_vertex:
            if call_model in ("gemini-3.5-transcribe", "publishers/google/models/gemini-3.5-transcribe"):
                call_model = call_model + "-preview"
        else:
            if call_model.endswith("-preview"):
                call_model = call_model[:-len("-preview")]

        # Prepare audio input
        audio_input = None
        uploaded_file = None
        if not is_vertex and hasattr(self._client, "files") and hasattr(self._client.files, "upload"):
            try:
                logger.info("Uploading audio via client.files.upload (per ai.google.dev): %s", path)
                uploaded_file = self._client.files.upload(file=path)
                if uploaded_file and hasattr(uploaded_file, "uri"):
                    audio_input = {
                        "type": "audio",
                        "uri": uploaded_file.uri,
                        "mime_type": getattr(uploaded_file, "mime_type", mime) or mime,
                    }
            except Exception as up_exc:
                logger.info("Files upload skipped or failed (%s); using inline base64", up_exc)

        if audio_input is None:
            b64_data = base64.b64encode(audio_bytes).decode("ascii")
            audio_input = {"type": "audio", "data": b64_data, "mime_type": mime}

        # 1. First attempt: Interactions API (per https://ai.google.dev/gemini-api/docs/transcribe)
        if not is_vertex and not self._interactions_unsupported:
            generation_configs = [
                {
                    "transcription_config": {
                        "language_codes": ["be-BY"],
                        "mode": "VERBATIM",
                        "word_level_timestamps": True,
                    }
                },
                {
                    "transcription_config": {
                        "language_codes": ["be-BY"],
                        "mode": {
                            "type": "VERBATIM",
                            "timestamp_granularities": ["word"],
                        },
                    }
                },
                None,
            ]
            for gen_cfg in generation_configs:
                try:
                    logger.info("Calling client.interactions.create with model=%s", call_model)
                    kwargs: dict[str, Any] = {
                        "model": call_model,
                        "input": [audio_input],
                    }
                    if gen_cfg is not None:
                        kwargs["generation_config"] = gen_cfg

                    interaction = self._call_with_retry(
                        lambda: self._client.interactions.create(**kwargs),
                        operation_label="interactions.create",
                        status=status,
                    )
                    words = _extract_words_from_interaction(interaction)
                    if words:
                        logger.info("Extracted %d words from transcribe interaction", len(words))
                        return self._store_transcribed_words(words)
                    out_text = getattr(interaction, "output_text", "")
                    if out_text:
                        inline_words = _extract_words_from_text(out_text)
                        if inline_words:
                            logger.info("Extracted %d words with timestamps from interaction text", len(inline_words))
                            return self._store_transcribed_words(inline_words)
                        logger.warning("No word-level timestamps in interaction; attempting duration-based interpolation fallback")
                        token_words = [w.strip() for w in out_text.split() if w.strip()]
                        if token_words:
                            total_dur = duration_sec if (duration_sec and duration_sec > 0) else len(token_words) * 0.4
                            step = total_dur / len(token_words)
                            for i, w in enumerate(token_words):
                                words.append({
                                    "word": w,
                                    "start": round(i * step, 2),
                                    "end": round(min((i + 1) * step, total_dur), 2),
                                    })
                            return self._store_transcribed_words(words)
                    break
                except Exception as inter_exc:
                    err_s = str(inter_exc).lower()
                    if "unsupported model interaction" in err_s:
                        self._interactions_unsupported = True
                        break
                    if any(p in err_s for p in ("invalid", "not supported", "unknown field", "400")) and gen_cfg is not None:
                        logger.debug("interactions.create config rejected (%s); trying fallback config", inter_exc)
                        continue
                    logger.info("interactions.create failed (%s); using generate_content fallback", inter_exc)
                    break

        # 2. Second attempt: generate_content (native Vertex AI path & fallback)
        try:
            logger.info("Calling client.models.generate_content with model=%s", call_model)
            is_transcribe_mod = is_transcribe_model(call_model)

            if is_transcribe_mod:
                # Dedicated transcribe model on Vertex AI: pass audio Part directly per Google Cloud sample notebook
                if types is not None and hasattr(types, "Part") and hasattr(types.Part, "from_bytes"):
                    user_content = types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type=mime,
                    )
                else:
                    b64_data = base64.b64encode(audio_bytes).decode("ascii")
                    user_content = {"inline_data": {"data": b64_data, "mime_type": mime}}
            else:
                prompt_instruction = (
                    "Выканай паслоўную транскрыпцыю гэтага аўдыё выключна на беларускай мове (кірыліцай) з дакладнымі часамі пачатку і канца для кожнага слова.\n"
                    "Фармат на кожнае слова:\n"
                    "[MM:SS.ss - MM:SS.ss] слова\n"
                    "Напрыклад:\n"
                    "[00:00.10 - 00:00.45] Прывітанне\n"
                    "[00:00.45 - 00:00.80] свет\n"
                    "Выведзі кожнае слова з часовымі меткамі пачатку і канца. Транскрыпцыя выключна па-беларуску."
                )
                if self._prompt_text and self._prompt_text.strip():
                    prompt_instruction = f"{prompt_instruction}\n\nДадатковыя ўказанні: {self._prompt_text.strip()}"

                user_content = self._build_user_content(
                    audio_bytes=audio_bytes,
                    mime=mime,
                    extra_text=prompt_instruction,
                )

            gen_config = None
            if types is not None and hasattr(types, "GenerateContentConfig"):
                transcribe_mode = "VERBATIM"
                if hasattr(types, "AudioTranscriptionConfigMode") and hasattr(types.AudioTranscriptionConfigMode, "VERBATIM"):
                    transcribe_mode = types.AudioTranscriptionConfigMode.VERBATIM

                if language and language != "auto":
                    if language.lower() in ("be", "bel", "by"):
                        lang_codes = ["be-BY"]
                    elif language.lower() in ("ru", "rus"):
                        lang_codes = ["ru-RU"]
                    elif language.lower() in ("en", "eng"):
                        lang_codes = ["en-US"]
                    else:
                        lang_codes = [language]
                else:
                    lang_codes_env = os.getenv("TRANSCRIBE_LANGUAGE_CODES", os.getenv("LANGUAGE_CODES", "be-BY")).strip()
                    lang_codes = [c.strip() for c in lang_codes_env.split(",") if c.strip()] or ["be-BY"]

                audio_tx_kwargs: dict[str, Any] = {
                    "word_timestamp": True,
                    "language_codes": lang_codes,
                    "mode": transcribe_mode,
                }
                custom_vocab_raw = os.getenv("CUSTOM_VOCABULARY", "").strip()
                if custom_vocab_raw:
                    vocab_list = [v.strip() for v in custom_vocab_raw.split(",") if v.strip()]
                    if vocab_list:
                        audio_tx_kwargs["custom_vocabulary"] = vocab_list[:1000]

                audio_tx_cfg = None
                if hasattr(types, "AudioTranscriptionConfig"):
                    try:
                        audio_tx_cfg = types.AudioTranscriptionConfig(**audio_tx_kwargs)
                    except Exception:
                        try:
                            kw_no_mode = {k: v for k, v in audio_tx_kwargs.items() if k != "mode"}
                            audio_tx_cfg = types.AudioTranscriptionConfig(**kw_no_mode)
                        except Exception:
                            audio_tx_cfg = audio_tx_kwargs
                else:
                    audio_tx_cfg = audio_tx_kwargs

                try:
                    afc_cfg = (
                        types.AutomaticFunctionCallingConfig(disable=True)
                        if hasattr(types, "AutomaticFunctionCallingConfig")
                        else None
                    )
                    gen_config = types.GenerateContentConfig(
                        audio_transcription_config=audio_tx_cfg,
                        automatic_function_calling=afc_cfg,
                    )
                except Exception:
                    try:
                        gen_config = types.GenerateContentConfig(
                            audio_transcription_config=audio_tx_cfg,
                        )
                    except Exception:
                        try:
                            gen_config = types.GenerateContentConfig(
                                audio_timestamp=True,
                            )
                        except Exception:
                            gen_config = None

            response = self._call_with_retry(
                lambda: self._client.models.generate_content(
                    model=call_model,
                    contents=[user_content],
                    config=gen_config,
                ),
                operation_label=f"Vertex AI transcribe generate_content ({call_model})",
                status=status,
                max_retries=int(os.getenv("TRANSCRIBE_MAX_RETRIES", "2")),
            )

            words = _extract_words_from_interaction(response)
            if words:
                logger.info(
                    "Extracted %d words with timestamps from response object (mode=VERBATIM)",
                    len(words),
                )
                return self._store_transcribed_words(words)
            raw_text = self._extract_response_text(response, raise_on_empty=False)
            if raw_text:
                words = _extract_words_from_text(raw_text)
                if words:
                    logger.info("Extracted %d words with timestamps from text", len(words))
                    return self._store_transcribed_words(words)
                token_words = [w.strip() for w in raw_text.split() if w.strip()]
                if token_words:
                    logger.warning("No word-level timestamps in model response; falling back to duration-based interpolation.")
                    total_dur = duration_sec if (duration_sec and duration_sec > 0) else len(token_words) * 0.4
                    step = total_dur / len(token_words)
                    for i, w in enumerate(token_words):
                        words.append({
                            "word": w,
                            "start": round(i * step, 2),
                            "end": round(min((i + 1) * step, total_dur), 2),
                        })
                    return self._store_transcribed_words(words)
            raise GeminiTranscriptionError("Vertex AI returned empty response for transcribe model")
        except Exception as gen_exc:
            logger.exception("Vertex AI transcribe model failed: %s", gen_exc)
            raise GeminiTranscriptionError(
                f"Vertex AI transcription failed ({self._model}): {gen_exc}"
            ) from gen_exc

    _extract_words_from_interaction = staticmethod(_extract_words_from_interaction)
    _extract_words_from_text = staticmethod(_extract_words_from_text)
    _extract_words_from_steps = staticmethod(_extract_words_from_steps)

    def transcribe(
        self,
        path: str,
        status: Optional[Callable[[str], None]] = None,
        length_mode: str = "medium",
        duration_sec: float | None = None,
        time_offset: float = 0.0,
        language: Optional[str] = None,
    ) -> str:
        global _last_transcribed_words
        if self._is_transcribe:
            words = self.transcribe_words(path, status=status, duration_sec=duration_sec, language=language)
            self.last_words = words
            _last_transcribed_words = words
            from subtitle_generation import group_words_into_subtitles
            segments = group_words_into_subtitles(
                words=words,
                length_mode=length_mode,
                duration_sec=duration_sec,
                time_offset=time_offset,
            )
            return json.dumps(segments, ensure_ascii=False)

        _last_transcribed_words = None

        mime = _guess_audio_mime(path)

        if status is not None:
            status("Пачынаем транскрыпцыю …")

        logger.info(
            "Gemini transcription: model=%s length_mode=%s duration_sec=%s prompt starts with: %s ...",
            self._model,
            length_mode,
            duration_sec,
            self._prompt_text[:200],
        )

        try:
            with open(path, "rb") as f:
                audio_bytes = f.read()

            user_content = self._build_user_content(
                audio_bytes=audio_bytes,
                mime=mime,
            )

            system_instruction = _build_system_instruction(
                length_mode=length_mode,
                prompt_text=self._prompt_text,
                duration_sec=duration_sec,
            )

            text = self._generate_content_text(
                contents=[user_content],
                system_instruction=system_instruction,
                operation_label="transcription",
                status=status,
            )

            logger.info("Gemini raw response (%d chars):\n%s", len(text), text)

            return text

        except Exception as exc:  # pragma: no cover
            raise GeminiTranscriptionError(
                f"Gemini transcription failed: {exc}"
            ) from exc

    def refine_timestamps(
        self,
        path: str,
        draft_srt: str,
        duration_sec: float,
        status: Optional[Callable[[str], None]] = None,
    ) -> str:
        if self._is_transcribe:
            logger.info(
                "Skipping second-pass timestamp refinement because %s has exact word-level timings.",
                self._model,
            )
            return draft_srt

        mime = _guess_audio_mime(path)

        if status is not None:
            status("Другі праход: удакладняем часовыя меткі …")

        if not draft_srt.strip():
            raise GeminiTranscriptionError(
                "Draft SRT is empty; cannot refine timestamps."
            )

        if not duration_sec or duration_sec <= 0:
            raise GeminiTranscriptionError(
                "Audio duration is invalid; cannot refine timestamps."
            )

        user_prompt = f"""
Draft SRT to correct.

Important:
- Preserve all subtitle text exactly.
- Correct only timestamps.
- Audio duration is {duration_sec:.3f} seconds.

DRAFT SRT:
{draft_srt}
""".strip()

        logger.info(
            "Gemini timestamp refinement: model=%s duration_sec=%.3f draft_srt_chars=%s",
            self._model,
            duration_sec,
            len(draft_srt),
        )

        try:
            with open(path, "rb") as f:
                audio_bytes = f.read()

            user_content = self._build_user_content(
                audio_bytes=audio_bytes,
                mime=mime,
                extra_text=user_prompt,
            )

            system_instruction = _build_timestamp_refinement_instruction(
                duration_sec
            )

            text = self._generate_content_text(
                contents=[user_content],
                system_instruction=system_instruction,
                operation_label="timestamp_refinement",
                status=status,
            )

            logger.info("Gemini refined response (%d chars):\n%s", len(text), text)

            return text

        except Exception as exc:  # pragma: no cover
            raise GeminiTranscriptionError(
                f"Gemini timestamp refinement failed: {exc}"
            ) from exc


def _make_adapter(model: Optional[str] = None) -> GeminiTranscriptionAdapter:
    _load_local_env()

    api_key = (
        os.getenv("gemini")
        or os.getenv("gembeh")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )
    model = (model or os.getenv("mod", "")).strip() or "gemini-2.5-flash"
    prompt_text = os.getenv("p", "")

    return GeminiTranscriptionAdapter(
        api_key=api_key,
        model=model,
        prompt_text=prompt_text,
    )


def transcribe_with_gemini(
    path: str,
    status: Callable[[str], None],
    length_mode: str,
    duration_sec: float | None = None,
    model: Optional[str] = None,
    time_offset: float = 0.0,
) -> str:
    adapter = _make_adapter(model=model)

    return adapter.transcribe(
        path=path,
        status=status,
        length_mode=length_mode,
        duration_sec=duration_sec,
        time_offset=time_offset,
    )


def refine_timestamps_with_gemini(
    path: str,
    draft_srt: str,
    duration_sec: float,
    status: Callable[[str], None],
    model: Optional[str] = None,
) -> str:
    adapter = _make_adapter(model=model)

    return adapter.refine_timestamps(
        path=path,
        draft_srt=draft_srt,
        duration_sec=duration_sec,
        status=status,
    )


def transcribe_words_with_gemini(
    path: str,
    status: Optional[Callable[[str], None]] = None,
    duration_sec: Optional[float] = None,
    model: Optional[str] = None,
) -> list[dict]:
    adapter = _make_adapter(model=model)
    return adapter.transcribe_words(path, status=status, duration_sec=duration_sec)


def get_last_transcribed_words() -> list[dict] | None:
    return _last_transcribed_words
