from __future__ import annotations

import json
import logging
import mimetypes
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Tuple

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

from gemini_integration import (
    GeminiTranscriptionError,
    get_last_transcribed_words,
    is_transcribe_model,
    refine_timestamps_with_gemini,
    transcribe_with_gemini,
)

logger = logging.getLogger(__name__)

MAX_MB = 600
ALLOWED_AUDIO_PREFIX = ("audio/",)
ALLOWED_VIDEO_PREFIX = ("video/",)
HISTORY = Path("transcripts")
HISTORY.mkdir(exist_ok=True)
TEXT_KEYS = ("text", "text_raw")

_RE_HMS_MS = re.compile(r"^(?:(\d{1,2}):)?(\d{1,2}):(\d{1,2})[.,](\d{1,3})$")
_RE_MS_COLON_MS = re.compile(r"^(\d{1,2}):(\d{1,2}):(\d{1,3})$")
_RE_SECONDS = re.compile(r"^\d+(?:[.,]\d+)?$")
_SRT_BLOCK_RE = re.compile(
    r"\s*(\d+)\s*?\n"
    r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*?\n"
    r"(.+?)(?=\n\s*\n|\Z)",
    re.DOTALL,
)


def _status_noop(_message: str) -> None:
    return None


def _validate(path: str, mime_prefixes: tuple[str, ...]) -> None:
    if not path or not os.path.isfile(path):
        raise ValueError("Файл не знойдзены.")

    if os.path.getsize(path) / 1_048_576 > MAX_MB:
        raise ValueError("Файл занадта вялікі.")

    mime, _ = mimetypes.guess_type(path)
    if not mime or not mime.startswith(mime_prefixes):
        raise ValueError(f"Непадтрыманы тып файла: {mime or 'невядомы'}.")


def _parse_raw_time(raw: float | int | str) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)

    s = str(raw).strip()
    if not s:
        return 0.0

    if s.lower().endswith("s"):
        s_no_s = s[:-1].strip()
        if _RE_SECONDS.match(s_no_s):
            return float(s_no_s.replace(",", "."))

    if match := _RE_HMS_MS.match(s):
        h, m, sec, ms = match.groups()
        ms = ms.ljust(3, "0")[:3]
        return int(h or 0) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000

    if match := _RE_MS_COLON_MS.match(s):
        m, sec, ms = match.groups()
        ms = ms.ljust(3, "0")[:3]
        return int(m) * 60 + int(sec) + int(ms) / 1000

    if _RE_SECONDS.match(s):
        return float(s.replace(",", "."))

    raise ValueError(f"Невядомы фармат часу: {raw!r}")


def _sec_to_ts(raw: float | int | str) -> str:
    sec = max(0.0, _parse_raw_time(raw))

    h, rem = divmod(sec, 3600)
    m, rem = divmod(rem, 60)
    s_int = int(rem)
    ms_int = int(round((rem - s_int) * 1000))

    if ms_int >= 1000:
        s_int += 1
        ms_int -= 1000

    if s_int >= 60:
        m += 1
        s_int -= 60

    if m >= 60:
        h += 1
        m -= 60

    return f"{int(h):02d}:{int(m):02d}:{s_int:02d},{ms_int:03d}"


def _sanitize_segments(raw_segments: list[dict], duration_sec: float | None = None) -> list[dict]:
    parsed: list[dict] = []

    for idx, seg in enumerate(raw_segments, 1):
        try:
            start = max(0.0, _parse_raw_time(seg["start"]))
            end = max(0.0, _parse_raw_time(seg["end"]))
            text = str(seg.get("text", "")).strip()
        except Exception as exc:
            logger.warning("Segment %s skipped: %s", idx, exc)
            continue

        if not text:
            continue

        if end < start:
            start, end = end, start

        parsed.append({"start": start, "end": end, "text": text})

    if not parsed:
        return []

    parsed.sort(key=lambda item: (item["start"], item["end"]))

    fixed: list[dict] = []
    prev_end = 0.0

    for seg in parsed:
        start = float(seg["start"])
        end = float(seg["end"])

        if duration_sec and duration_sec > 0:
            if start >= duration_sec:
                continue
            start = min(max(start, 0.0), duration_sec)
            end = min(max(end, 0.0), duration_sec)

        if start < prev_end:
            start = prev_end + 0.001

        if end <= start:
            end = start + 0.35

        if end - start < 0.08:
            end = start + 0.08

        if duration_sec and duration_sec > 0:
            end = min(end, duration_sec)

        if end <= start:
            continue

        fixed.append({"start": start, "end": end, "text": str(seg["text"]).strip()})
        prev_end = end

    return fixed
 
 
def group_words_into_subtitles(
    words: list[dict],
    length_mode: str = "medium",
    duration_sec: float | None = None,
    max_chars: int | None = None,
    time_offset: float = 0.0,
) -> list[dict]:
    """Group timestamped words into subtitle segments based on length_mode.
    
    Each word in `words` must be a dict with:
      - 'word' (or 'text'): str
      - 'start' (or 'start_time'): float | int | str
      - 'end' (or 'end_time'): float | int | str
    
    time_offset shifts all timestamps (negative = subtitles appear earlier).
    """
    if not words:
        return []

    normalized_mode = (length_mode or "medium").strip().lower()

    if normalized_mode == "short":
        target_words = 2
        mode_max_chars = max_chars or 24
        max_duration = 2.0
        max_pause = 0.35
    elif normalized_mode == "long":
        target_words = 12
        mode_max_chars = max_chars or 80
        max_duration = 7.0
        max_pause = 0.65
    else:  # medium
        target_words = 4
        mode_max_chars = max_chars or 42
        max_duration = 4.0
        max_pause = 0.45

    cleaned_words: list[dict] = []
    for w in words:
        raw_text = str(w.get("word") or w.get("text") or "").strip()
        if not raw_text:
            continue
        try:
            st = _parse_raw_time(w.get("start") if "start" in w else w.get("start_time", 0.0))
            et = _parse_raw_time(w.get("end") if "end" in w else w.get("end_time", st + 0.3))
        except (TypeError, ValueError):
            continue

        # Apply time offset
        st += time_offset
        et += time_offset

        if et < st:
            st, et = et, st
        if et == st:
            et = st + 0.25

        # Clamp to non-negative
        st = max(st, 0.0)
        et = max(et, 0.0)

        if duration_sec and duration_sec > 0:
            if st >= duration_sec:
                continue
            st = min(st, duration_sec)
            et = min(et, duration_sec)
            if et <= st:
                continue

        cleaned_words.append({"word": raw_text, "start": st, "end": et})

    if not cleaned_words:
        return []

    cleaned_words.sort(key=lambda x: (x["start"], x["end"]))

    segments: list[dict] = []
    current_chunk: list[dict] = []
    current_char_count = 0

    def _flush_chunk():
        nonlocal current_chunk, current_char_count
        if not current_chunk:
            return
        seg_start = _sec_to_ts(current_chunk[0]["start"])
        seg_end = _sec_to_ts(current_chunk[-1]["end"])
        seg_text = " ".join(item["word"] for item in current_chunk).strip()
        if seg_text:
            segments.append({"start": seg_start, "end": seg_end, "text": seg_text})
        current_chunk = []
        current_char_count = 0

    sentence_ends = (".", "!", "?", "…")

    for w in cleaned_words:
        if not current_chunk:
            current_chunk.append(w)
            current_char_count = len(w["word"])
            continue

        prev_w = current_chunk[-1]
        pause = w["start"] - prev_w["end"]
        chunk_duration = w["end"] - current_chunk[0]["start"]
        new_char_count = current_char_count + 1 + len(w["word"])

        should_break = False
        if pause >= max_pause:
            should_break = True
        elif len(current_chunk) >= target_words:
            should_break = True
        elif new_char_count > mode_max_chars:
            should_break = True
        elif chunk_duration > max_duration:
            should_break = True
        elif prev_w["word"].endswith(sentence_ends):
            if normalized_mode == "short" or len(current_chunk) >= 2:
                should_break = True

        if should_break:
            _flush_chunk()
            current_chunk.append(w)
            current_char_count = len(w["word"])
        else:
            current_chunk.append(w)
            current_char_count = new_char_count

    _flush_chunk()
    return segments


def _parse_srt(content: str) -> list[dict]:
    segments: list[dict] = []
    normalized = (content or "").replace("\r\n", "\n").replace("\r", "\n")

    for match in _SRT_BLOCK_RE.finditer(normalized.strip()):
        _idx, start, end, text = match.groups()
        text = text.strip()
        if text:
            segments.append({"start": start, "end": end, "text": text})

    return segments


def _segments_to_srt_text(segments: List[dict]) -> str:
    lines: list[str] = []

    for idx, seg in enumerate(segments, 1):
        lines.append(
            f"{idx}\n"
            f"{_sec_to_ts(seg['start'])} --> {_sec_to_ts(seg['end'])}\n"
            f"{seg['text']}\n"
        )

    return "\n".join(lines)


def _extract_text(seg: dict) -> str:
    for key in TEXT_KEYS + ("content", "segment_text", "utterance", "subtitle"):
        if seg.get(key):
            return str(seg[key]).strip()
    return ""


def _candidate_list_from_json(obj) -> list[dict] | None:
    if isinstance(obj, list):
        return obj

    if isinstance(obj, dict):
        has_start = any(k in obj for k in ("start", "start_time", "from", "begin", "offset"))
        has_end = any(k in obj for k in ("end", "end_time", "to", "finish"))
        has_text = any(k in obj for k in TEXT_KEYS + ("content", "segment_text", "utterance", "subtitle"))

        if has_start and has_end and has_text:
            return [obj]

        for key in ("segments", "items", "result", "results", "data", "subtitles"):
            value = obj.get(key)
            if isinstance(value, list):
                return value

    return None


def _parse_gemini_json(json_obj) -> tuple[list[dict], list[str]]:
    segments: list[dict] = []
    texts_no_timing: list[str] = []

    if isinstance(json_obj, dict):
        for srt_key in ("srt", "subtitles", "srt_string"):
            srt_val = json_obj.get(srt_key)
            if isinstance(srt_val, str) and " --> " in srt_val:
                srt_segments = _parse_srt(srt_val)
                if srt_segments:
                    return srt_segments, texts_no_timing

        for txt_key in ("text", "transcript", "content", "full_text"):
            if isinstance(json_obj.get(txt_key), str):
                txt = json_obj[txt_key].strip()
                if txt:
                    texts_no_timing.append(txt)

    candidates = _candidate_list_from_json(json_obj)
    if not candidates:
        return segments, texts_no_timing

    for idx, seg in enumerate(candidates, 1):
        if not isinstance(seg, dict):
            logger.warning("Segment #%s is not dict; skipped", idx)
            continue

        text = _extract_text(seg)
        start = seg.get("start") or seg.get("start_time") or seg.get("from") or seg.get("begin") or seg.get("offset")
        end = seg.get("end") or seg.get("end_time") or seg.get("to") or seg.get("finish")

        if start is None and end is None and "time" in seg and "duration" in seg:
            try:
                start_sec = _parse_raw_time(seg["time"])
                start = start_sec
                end = start_sec + _parse_raw_time(seg["duration"])
            except Exception:
                logger.warning("Segment #%s has unparseable time/duration.", idx)

        if start is None or end is None or not text:
            continue

        segments.append({"start": start, "end": end, "text": text})
        texts_no_timing.append(text)

    return segments, texts_no_timing


def _iter_json_values_from_text(raw: str):
    decoder = json.JSONDecoder()
    idx = 0

    while idx < len(raw):
        starts = [pos for pos in (raw.find("[", idx), raw.find("{", idx)) if pos != -1]
        if not starts:
            break

        start = min(starts)
        try:
            obj, end = decoder.raw_decode(raw[start:])
        except json.JSONDecodeError:
            idx = start + 1
            continue

        yield obj
        idx = start + max(end, 1)


def _iter_json_objects_from_text(raw: str):
    decoder = json.JSONDecoder()
    idx = 0

    while idx < len(raw):
        start = raw.find("{", idx)
        if start < 0:
            break

        try:
            obj, end = decoder.raw_decode(raw[start:])
        except json.JSONDecodeError:
            idx = start + 1
            continue

        if isinstance(obj, dict):
            yield obj
        idx = start + max(end, 1)


def _looks_json_like(raw: str) -> bool:
    stripped = (raw or "").lstrip()
    return stripped.startswith("[") or stripped.startswith("{") or '"start"' in raw or '"end"' in raw or '"text"' in raw


def _parse_model_response_to_segments(raw: str) -> tuple[list[dict], list[str]]:
    collected_texts: list[str] = []

    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        obj = None

    if obj is not None:
        segments, texts = _parse_gemini_json(obj)
        if segments:
            return segments, texts
        collected_texts.extend(texts)

    for match in re.finditer(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE):
        try:
            obj = json.loads(match.group(1).strip())
        except Exception:
            continue

        segments, texts = _parse_gemini_json(obj)
        if segments:
            return segments, texts
        collected_texts.extend(texts)

    for obj in _iter_json_values_from_text(raw):
        segments, texts = _parse_gemini_json(obj)
        if segments:
            return segments, texts
        collected_texts.extend(texts)

    salvaged: list[dict] = []
    for obj in _iter_json_objects_from_text(raw):
        segments, texts = _parse_gemini_json(obj)
        salvaged.extend(segments)
        collected_texts.extend(texts)

    if salvaged:
        return salvaged, collected_texts

    if " --> " in raw:
        srt_segments = _parse_srt(raw)
        if srt_segments:
            return srt_segments, collected_texts

    return [], collected_texts


def _get_duration_sec(path: str) -> float:
    if AudioSegment is not None:
        try:
            audio = AudioSegment.from_file(path)
            duration = float(audio.duration_seconds)
            if duration > 0:
                return duration
        except Exception:
            pass

    try:
        from app.core.audio_utils import get_audio_duration
        return get_audio_duration(Path(path))
    except Exception:
        pass

    import wave
    try:
        with wave.open(path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            if duration > 0:
                return duration
    except Exception:
        pass

    raise ValueError("Non-positive or unreadable audio duration.")


def model_response_to_srt(raw: str, duration_sec: float | None = None) -> Tuple[str, list[dict]]:
    segments, collected_texts = _parse_model_response_to_segments(raw)

    if segments:
        final_segments = _sanitize_segments(segments, duration_sec=duration_sec)
    else:
        if _looks_json_like(raw):
            raise ValueError("Gemini вярнуў JSON-падобны адказ без валідных subtitle segments.")

        full_text = "\n".join(t for t in collected_texts if t.strip()) or (raw or "").strip()
        if not full_text:
            raise ValueError("Gemini адказаў без тэксту субцітраў.")
        final_segments = [{"start": 0.0, "end": duration_sec or 60.0, "text": full_text}]

    if not final_segments:
        raise ValueError("Не ўдалося сфармаваць валідныя SRT-сегменты.")

    return _segments_to_srt_text(final_segments), final_segments


def _refine_segments_second_pass(
    path: str,
    first_pass_segments: list[dict],
    duration_sec: float,
    status: Callable[[str], None],
    model: Optional[str] = None,
) -> list[dict]:
    if not first_pass_segments:
        return first_pass_segments

    draft_srt = _segments_to_srt_text(first_pass_segments)

    try:
        refined_raw = refine_timestamps_with_gemini(
            path=path,
            draft_srt=draft_srt,
            duration_sec=duration_sec,
            status=status,
            model=model,
        )
    except Exception:
        logger.exception("Second Gemini timestamp refinement failed; using first pass.")
        return first_pass_segments

    refined_segments, _texts = _parse_model_response_to_segments(refined_raw)

    if len(refined_segments) == len(first_pass_segments):
        for original, refined in zip(first_pass_segments, refined_segments):
            refined["text"] = original["text"]
        return refined_segments

    return first_pass_segments


class SegmentList(list):
    def __init__(
        self,
        items=(),
        words: list[dict] | None = None,
        duration_sec: float | None = None,
    ):
        super().__init__(items)
        self.words = words
        self.duration_sec = duration_sec


class SubtitleProcessResult(tuple):
    def __new__(
        cls,
        content: str,
        path: str,
        words: list[dict] | None = None,
        duration_sec: float | None = None,
    ):
        return super().__new__(cls, (content, path))

    def __init__(
        self,
        content: str,
        path: str,
        words: list[dict] | None = None,
        duration_sec: float | None = None,
    ):
        self.content = content
        self.path = path
        self.words = words
        self.duration_sec = duration_sec


def transcribe_audio_to_segments(
    path: str,
    status: Callable[[str], None] | None = None,
    length_mode: str = "medium",
    model: Optional[str] = None,
    time_offset: float = 0.0,
) -> list[dict]:
    status = status or _status_noop
    _validate(path, ALLOWED_AUDIO_PREFIX)

    duration_sec = _get_duration_sec(path)
    try:
        raw = transcribe_with_gemini(
            path=path,
            status=status,
            length_mode=length_mode,
            duration_sec=duration_sec,
            model=model,
            time_offset=time_offset,
        )
    except GeminiTranscriptionError as exc:
        is_quota = any(q in str(exc).lower() for q in ("429", "resource_exhausted", "quota", "exhausted"))
        allow_fallback = os.getenv("GEMINI_FALLBACK_ON_QUOTA", "true").strip().lower() in ("1", "true", "yes")
        if is_transcribe_model(model) and is_quota and allow_fallback:
            fallback_model = os.getenv("mod_legacy", "gemini-2.5-flash")
            logger.warning(
                "Transcribe model %s exhausted quota: %s. Falling back to %s",
                model,
                exc,
                fallback_model,
            )
            status(
                f"Квота для {model or 'мадэлі'} вычарпана. "
                f"Пераключаемся на рэзервовую мадэль {fallback_model} …"
            )
            raw = transcribe_with_gemini(
                path=path,
                status=status,
                length_mode=length_mode,
                duration_sec=duration_sec,
                model=fallback_model,
            )
            first_pass_srt, first_pass_segments = model_response_to_srt(raw, duration_sec=duration_sec)
            refined_segments = _refine_segments_second_pass(
                path=path,
                first_pass_segments=first_pass_segments,
                duration_sec=duration_sec,
                status=status,
                model=fallback_model,
            )
            return SegmentList(
                _sanitize_segments(refined_segments, duration_sec=duration_sec),
                words=None,
                duration_sec=duration_sec,
            )
        raise

    extracted_words: list[dict] | None = get_last_transcribed_words()
    if extracted_words is None:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "words" in data and isinstance(data["words"], list):
                extracted_words = data["words"]
        except Exception:
            pass

    first_pass_srt, first_pass_segments = model_response_to_srt(raw, duration_sec=duration_sec)
    logger.info("Gemini first-pass SRT chars: %s", len(first_pass_srt))

    if is_transcribe_model(model):
        # Dedicated transcribe models (e.g. gemini-3.5-transcribe) already provide
        # exact word-level timings; no prompt-based second-pass refinement is needed.
        return SegmentList(
            _sanitize_segments(first_pass_segments, duration_sec=duration_sec),
            words=extracted_words,
            duration_sec=duration_sec,
        )

    refined_segments = _refine_segments_second_pass(
        path=path,
        first_pass_segments=first_pass_segments,
        duration_sec=duration_sec,
        status=status,
        model=model,
    )

    return SegmentList(
        _sanitize_segments(refined_segments, duration_sec=duration_sec),
        words=extracted_words,
        duration_sec=duration_sec,
    )


def transcripts_to_srt(segments: List[dict]) -> Tuple[str, str]:
    content = _segments_to_srt_text(segments)
    logger.info("Final generated SRT (%d segments):\n%s", len(segments), content)
    out_path = HISTORY / f"subtitles_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.srt"
    out_path.write_text(content, "utf-8")
    return content, str(out_path)


def extract_audio_from_video(video_path: str, status: Callable[[str], None] | None = None) -> str:
    status = status or _status_noop
    _validate(video_path, ALLOWED_VIDEO_PREFIX)
    status("Вылучаем аўдыё з відэа ...")

    import subprocess
    import shutil

    path = f"extracted_{uuid.uuid4().hex}.wav"

    # Try ffmpeg first for accurate PTS synchronization
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        try:
            cmd = [
                ffmpeg_bin, "-y",
                "-i", video_path,
                "-vn",                       # no video
                "-af", "aresample=async=1",   # sync audio PTS to video timeline
                "-ac", "1",                  # mono
                "-ar", "16000",              # 16kHz sample rate
                path,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120,
            )
            if result.returncode == 0 and os.path.isfile(path) and os.path.getsize(path) > 0:
                logger.info("Audio extracted with ffmpeg (aresample=async=1) for accurate sync")
                return path
            logger.warning("ffmpeg exited with code %d; falling back to pydub", result.returncode)
        except Exception as exc:
            logger.warning("ffmpeg extraction failed (%s); falling back to pydub", exc)

    # Fallback: pydub (may introduce PTS offset on some containers)
    audio = AudioSegment.from_file(video_path)
    audio.export(path, format="wav")
    logger.info("Audio extracted with pydub (fallback)")
    return path


def process_video_to_srt(
    video_path: str,
    status: Callable[[str], None] | None = None,
    length_mode: str = "medium",
    model: Optional[str] = None,
    time_offset: float = 0.0,
) -> SubtitleProcessResult:
    status = status or _status_noop
    audio_path = extract_audio_from_video(video_path, status=status)
    try:
        segments = transcribe_audio_to_segments(
            audio_path,
            status=status,
            length_mode=length_mode,
            model=model,
            time_offset=time_offset,
        )
        srt_result = transcripts_to_srt(segments)
        if isinstance(srt_result, tuple):
            content, out_path = srt_result[0], srt_result[1]
        else:
            content, out_path = str(srt_result), ""
        words = getattr(segments, "words", None)
        duration_sec = getattr(segments, "duration_sec", None)
        return SubtitleProcessResult(content, out_path, words=words, duration_sec=duration_sec)
    finally:
        # Clean up temporary extracted audio
        try:
            if audio_path and os.path.isfile(audio_path):
                os.remove(audio_path)
                logger.debug("Removed temp audio: %s", audio_path)
        except OSError:
            pass


def read_srt_file(path: str) -> str:
    if not path or not os.path.isfile(path):
        raise ValueError("SRT-файл не знойдзены.")

    if Path(path).suffix.lower() != ".srt":
        raise ValueError("Можна імпартаваць толькі .srt файл.")

    return Path(path).read_text(encoding="utf-8")
