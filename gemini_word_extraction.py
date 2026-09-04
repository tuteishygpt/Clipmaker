from __future__ import annotations

import re
import json
import logging
from typing import Any
from gemini_auth import _clean_time

logger = logging.getLogger(__name__)

def _extract_words_from_text(text: str) -> list[dict]:
    """Extract word timestamps from text containing JSON or inline timestamps."""
    if not text or not text.strip():
        return []
    cleaned = text.strip()

    # 1. Strip markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        try:
            parsed = json.loads(fence_match.group(1).strip())
            words = _extract_words_from_interaction(parsed)
            if words:
                return words
        except Exception:
            pass

    # 2. Try raw JSON parse
    try:
        parsed = json.loads(cleaned)
        words = _extract_words_from_interaction(parsed)
        if words:
            return words
    except Exception:
        pass

    # 3. Try finding JSON array substring [...]
    arr_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", cleaned)
    if arr_match:
        try:
            parsed = json.loads(arr_match.group(0))
            words = _extract_words_from_interaction(parsed)
            if words:
                return words
        except Exception:
            pass

    # 4. Try parsing inline timestamp ranges: [00:01.20 - 00:01.80] слова
    range_pat = re.compile(
        r"\[?\s*(\d+[:\.]\d+(?:[:\.,]\d+)?)\s*(?:-|-->|,)\s*(\d+[:\.]\d+(?:[:\.,]\d+)?)\s*\]?\s*([^\n\[\]\<\>]+)",
        re.UNICODE,
    )
    range_matches = range_pat.findall(cleaned)
    if range_matches:
        inline_words: list[dict] = []
        for st_raw, et_raw, w_raw in range_matches:
            tokens = w_raw.strip().split()
            if not tokens:
                continue
            st = _clean_time(st_raw)
            et = _clean_time(et_raw)
            span = max(0.01, et - st)
            step = span / len(tokens)
            for i, t in enumerate(tokens):
                inline_words.append({
                    "word": t,
                    "start": round(st + i * step, 3),
                    "end": round(st + (i + 1) * step, 3),
                })
        if inline_words:
            return inline_words

    # 5. Try parsing point timestamps: [00:01.20] слова1 [00:01.80] слова2 [00:02.50]
    point_pat = re.compile(r"\[\s*(\d+[:\.]\d+(?:[:\.,]\d+)?)\s*\]\s*([^\n\[\]]*)", re.UNICODE)
    point_matches = point_pat.findall(cleaned)
    if point_matches:
        inline_words = []
        for i, (ts_raw, w_raw) in enumerate(point_matches):
            tokens = w_raw.strip().split()
            if not tokens:
                continue
            st = _clean_time(ts_raw)
            if i + 1 < len(point_matches):
                et = _clean_time(point_matches[i + 1][0])
            else:
                et = st + max(0.3, len(tokens) * 0.3)
            span = max(0.01, et - st)
            step = span / len(tokens)
            for j, t in enumerate(tokens):
                inline_words.append({
                    "word": t,
                    "start": round(st + j * step, 3),
                    "end": round(st + (j + 1) * step, 3),
                })
        if inline_words:
            return inline_words

    return []

def _extract_words_from_steps(interaction: Any) -> list[dict]:
    """Extract word annotations from interaction steps (modern google-genai schema)."""
    steps = None
    if hasattr(interaction, "steps"):
        steps = getattr(interaction, "steps")
    elif isinstance(interaction, dict) and "steps" in interaction:
        steps = interaction.get("steps")

    if not isinstance(steps, (list, tuple)) or len(steps) == 0:
        return []

    words: list[dict] = []
    for step in steps:
        contents = None
        if hasattr(step, "content"):
            contents = getattr(step, "content")
        elif hasattr(step, "contents"):
            contents = getattr(step, "contents")
        elif isinstance(step, dict):
            contents = step.get("content") or step.get("contents") or step.get("parts")

        if not contents:
            continue
        if not isinstance(contents, (list, tuple)):
            contents = [contents]

        for c in contents:
            annotations = None
            if hasattr(c, "annotations"):
                annotations = getattr(c, "annotations")
            elif isinstance(c, dict):
                annotations = c.get("annotations")

            if annotations:
                if not isinstance(annotations, (list, tuple)):
                    annotations = [annotations]
                for ann in annotations:
                    w_text = None
                    w_start = None
                    w_end = None
                    if isinstance(ann, dict):
                        w_text = ann.get("text") or ann.get("word") or ann.get("content")
                        w_start = (
                            ann.get("start_offset")
                            or ann.get("startOffset")
                            or ann.get("start_time")
                            or ann.get("startTime")
                            or ann.get("start")
                        )
                        w_end = (
                            ann.get("end_offset")
                            or ann.get("endOffset")
                            or ann.get("end_time")
                            or ann.get("endTime")
                            or ann.get("end")
                        )
                    else:
                        w_text = getattr(ann, "text", None) or getattr(ann, "word", None) or getattr(ann, "content", None)
                        w_start = (
                            getattr(ann, "start_offset", None)
                            or getattr(ann, "startOffset", None)
                            or getattr(ann, "start_time", None)
                            or getattr(ann, "startTime", None)
                            or getattr(ann, "start", None)
                        )
                        w_end = (
                            getattr(ann, "end_offset", None)
                            or getattr(ann, "endOffset", None)
                            or getattr(ann, "end_time", None)
                            or getattr(ann, "endTime", None)
                            or getattr(ann, "end", None)
                        )

                    if w_text is not None and w_start is not None and w_end is not None and str(w_text).strip():
                        try:
                            st = _clean_time(w_start)
                            et = _clean_time(w_end)
                            words.append({"word": str(w_text).strip(), "start": st, "end": et})
                        except Exception:
                            pass

    if words:
        words.sort(key=lambda x: (x["start"], x["end"]))
    return words

def _extract_words_from_interaction(interaction: Any) -> list[dict]:
    """Extract a normalized list of {'word': str, 'start': float, 'end': float} from Interaction or GenerateContentResponse."""
    if interaction is None:
        return []

    # 1. First priority: modern google-genai Interactions API steps -> annotations
    steps_words = _extract_words_from_steps(interaction)
    if steps_words:
        return steps_words

    # 2. Check direct output_words attribute / dict key
    out_words = getattr(interaction, "output_words", None)
    if not isinstance(out_words, (list, tuple)) and isinstance(interaction, dict):
        out_words = interaction.get("output_words")
    if isinstance(out_words, (list, tuple)) and len(out_words) > 0:
        direct_words = []
        for ow in out_words:
            w_text = ow.get("text") or ow.get("word") if isinstance(ow, dict) else getattr(ow, "text", None) or getattr(ow, "word", None)
            w_start = ow.get("start_offset") or ow.get("start") if isinstance(ow, dict) else getattr(ow, "start_offset", None) or getattr(ow, "start", None)
            w_end = ow.get("end_offset") or ow.get("end") if isinstance(ow, dict) else getattr(ow, "end_offset", None) or getattr(ow, "end", None)
            if w_text and w_start is not None and w_end is not None:
                try:
                    direct_words.append({"word": str(w_text).strip(), "start": _clean_time(w_start), "end": _clean_time(w_end)})
                except Exception:
                    pass
        if direct_words:
            direct_words.sort(key=lambda x: (x["start"], x["end"]))
            return direct_words

    # 3. Search candidates.content.parts for audio_transcription
    words: list[dict] = []
    visited: set[int] = set()
    visited_objs: list[Any] = []

    def _get_field(obj: Any, keys: list[str]) -> Any:
        if isinstance(obj, dict):
            for k in keys:
                if k in obj and obj[k] is not None:
                    return obj[k]
        else:
            for k in keys:
                if hasattr(obj, k):
                    try:
                        val = getattr(obj, k)
                        if val is not None:
                            return val
                    except Exception:
                        pass
        return None

    def _search(obj: Any):
        nonlocal words
        if obj is None:
            return

        # Skip mock/test objects to prevent infinite recursion
        obj_type = type(obj)
        obj_module = getattr(obj_type, "__module__", "") or ""
        if "mock" in obj_module or "unittest.mock" in obj_module:
            return

        obj_id = id(obj)
        if obj_id in visited:
            return
        visited.add(obj_id)
        visited_objs.append(obj)

        w_text = _get_field(obj, ["word", "text", "content", "token"])
        w_start = _get_field(obj, ["start_offset", "startOffset", "start_time", "startTime", "start", "offset"])
        w_end = _get_field(obj, ["end_offset", "endOffset", "end_time", "endTime", "end"])

        if (
            w_text is not None
            and w_start is not None
            and w_end is not None
            and isinstance(w_text, str)
            and w_text.strip()
        ):
            try:
                st = _clean_time(w_start)
                et = _clean_time(w_end)
                tokens = w_text.strip().split()
                if len(tokens) <= 1:
                    words.append({"word": w_text.strip(), "start": st, "end": et})
                    return
                else:
                    span = max(0.01, et - st)
                    step = span / len(tokens)
                    for i, t in enumerate(tokens):
                        words.append({
                            "word": t,
                            "start": round(st + i * step, 3),
                            "end": round(st + (i + 1) * step, 3),
                        })
                    return
            except Exception:
                pass

        # Inspect specific known attributes on objects or dicts
        for attr in (
            "words",
            "word_timestamps",
            "word_level_timestamps",
            "timestamped_words",
            "tokens",
            "audio_transcription",
            "transcription",
            "segments",
            "parts",
            "annotations",
        ):
            if hasattr(obj, attr):
                try:
                    child = getattr(obj, attr)
                    # Only recurse into real list/tuple/dict children, not mock objects
                    if child is not None and child is not obj and isinstance(child, (list, tuple, dict)):
                        _search(child)
                except Exception:
                    pass

        if isinstance(obj, dict):
            for key in (
                "words",
                "word_timestamps",
                "word_level_timestamps",
                "timestamped_words",
                "tokens",
                "audio_transcription",
                "transcription",
                "segments",
                "parts",
                "annotations",
            ):
                if key in obj and obj[key] is not None:
                    _search(obj[key])

            for v in obj.values():
                _search(v)
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                _search(item)
        elif hasattr(obj, "model_dump"):
            try:
                _search(obj.model_dump())
            except Exception:
                pass
        elif hasattr(obj, "__dict__"):
            for v in obj.__dict__.values():
                _search(v)

    parts_to_inspect = []
    parts_val = getattr(interaction, "parts", None)
    if isinstance(parts_val, (list, tuple)) and parts_val:
        parts_to_inspect.extend(parts_val)

    candidates_val = getattr(interaction, "candidates", None)
    if not candidates_val and isinstance(interaction, dict):
        candidates_val = interaction.get("candidates")
    if isinstance(candidates_val, (list, tuple)):
        for cand in candidates_val:
            content = getattr(cand, "content", None) if not isinstance(cand, dict) else cand.get("content")
            if content:
                cand_parts = getattr(content, "parts", None) if not isinstance(content, dict) else content.get("parts")
                if isinstance(cand_parts, (list, tuple)):
                    for p in cand_parts:
                        if p not in parts_to_inspect:
                            parts_to_inspect.append(p)

    if parts_to_inspect:
        for part in parts_to_inspect:
            at = (
                getattr(part, "audio_transcription", None)
                or getattr(part, "transcription", None)
                or getattr(part, "audioTranscription", None)
            )
            if at is None and hasattr(part, "model_extra") and part.model_extra:
                at = (
                    part.model_extra.get("audio_transcription")
                    or part.model_extra.get("audioTranscription")
                    or part.model_extra.get("transcription")
                )
            if at is None and hasattr(part, "model_dump"):
                try:
                    dump = part.model_dump()
                    at = (
                        dump.get("audio_transcription")
                        or dump.get("audioTranscription")
                        or dump.get("transcription")
                    )
                except Exception:
                    pass
            if at is None and isinstance(part, dict):
                at = (
                    part.get("audio_transcription")
                    or part.get("audioTranscription")
                    or part.get("transcription")
                )

            if at is not None:
                # Direct check for words list on audio_transcription per Google Cloud gemini_3_5_transcribe sample
                at_words = None
                for attr in ("words", "word_timestamps", "wordTimestamps", "tokens", "segments"):
                    if isinstance(at, dict) and attr in at and at[attr]:
                        at_words = at[attr]
                        break
                    elif hasattr(at, attr):
                        val = getattr(at, attr)
                        if val:
                            at_words = val
                            break

                if isinstance(at_words, (list, tuple)) and at_words:
                    direct_at_words = []
                    for w in at_words:
                        w_text = (
                            w.get("word") or w.get("text") or w.get("content") or w.get("token")
                            if isinstance(w, dict)
                            else (
                                getattr(w, "word", None)
                                or getattr(w, "text", None)
                                or getattr(w, "content", None)
                                or getattr(w, "token", None)
                            )
                        )
                        w_start = (
                            w.get("start_offset")
                            or w.get("startOffset")
                            or w.get("start_time")
                            or w.get("startTime")
                            or w.get("start")
                            or w.get("offset")
                            if isinstance(w, dict)
                            else (
                                getattr(w, "start_offset", None)
                                or getattr(w, "startOffset", None)
                                or getattr(w, "start_time", None)
                                or getattr(w, "startTime", None)
                                or getattr(w, "start", None)
                                or getattr(w, "offset", None)
                            )
                        )
                        w_end = (
                            w.get("end_offset")
                            or w.get("endOffset")
                            or w.get("end_time")
                            or w.get("endTime")
                            or w.get("end")
                            if isinstance(w, dict)
                            else (
                                getattr(w, "end_offset", None)
                                or getattr(w, "endOffset", None)
                                or getattr(w, "end_time", None)
                                or getattr(w, "endTime", None)
                                or getattr(w, "end", None)
                            )
                        )
                        if w_text and w_start is not None and w_end is not None:
                            try:
                                direct_at_words.append({
                                    "word": str(w_text).strip(),
                                    "start": _clean_time(w_start),
                                    "end": _clean_time(w_end),
                                })
                            except Exception:
                                pass
                    if direct_at_words:
                        direct_at_words.sort(key=lambda x: (x["start"], x["end"]))
                        return direct_at_words

                _search(at)
                if words:
                    return words

            text = getattr(part, "text", None)
            if text and isinstance(text, str):
                extracted = _extract_words_from_text(text)
                if extracted:
                    return extracted

    # General recursive search
    data = None
    if hasattr(interaction, "model_dump"):
        try:
            data = interaction.model_dump()
        except Exception:
            data = None
    elif hasattr(interaction, "to_dict"):
        try:
            data = interaction.to_dict()
        except Exception:
            data = None
    elif isinstance(interaction, (dict, list)):
        data = interaction

    if data:
        _search(data)
        if words:
            return words

    # Fallback output_text check
    output_text = getattr(interaction, "output_text", "")
    if not output_text and isinstance(interaction, dict):
        output_text = interaction.get("output_text", "")
    if output_text and isinstance(output_text, str) and output_text.strip():
        extracted = _extract_words_from_text(output_text)
        if extracted:
            return extracted

    return words

