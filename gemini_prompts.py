from __future__ import annotations

import mimetypes
from pathlib import Path
from gemini_auth import GeminiTranscriptionError

def _seconds_to_srt_timestamp(seconds: float) -> str:
    seconds = max(0.0, float(seconds))

    h, rem = divmod(seconds, 3600)
    m, rem = divmod(rem, 60)
    s = int(rem)
    ms = int(round((rem - s) * 1000))

    if ms >= 1000:
        s += 1
        ms -= 1000

    if s >= 60:
        m += 1
        s -= 60

    if m >= 60:
        h += 1
        m -= 60

    return f"{int(h):02d}:{int(m):02d}:{s:02d},{ms:03d}"

def _build_duration_instruction(duration_sec: float | None) -> str:
    if not duration_sec or duration_sec <= 0:
        return ""

    duration_ts = _seconds_to_srt_timestamp(duration_sec)

    return f"""
Audio duration constraint:
- The exact audio duration is {duration_sec:.3f} seconds.
- The exact audio duration in SRT format is {duration_ts}.
- No subtitle "start" or "end" value may be greater than {duration_ts}.
- The final subtitle "end" must be less than or equal to {duration_ts}.
- Do not force the final subtitle to end at {duration_ts}; silence after the last spoken phrase should remain silence.
- Do not invent speech after the end of the audio.
- Do not force subtitles to fill the whole audio duration.
- If speech ends before the audio ends, the last subtitle must end when speech ends, not at {duration_ts}.
- Preserve natural silence gaps when present.
""".strip()

def _get_format_instruction(length_mode: str) -> str:
    normalized = (length_mode or "medium").strip().lower()

    if normalized == "short":
        segmentation = """
Field rules:
- Each "text" value MUST contain exactly ONE Belarusian word.
- If a sentence is long, split it into many consecutive one-word subtitle segments with accurate timings.
- Avoid meaningless isolated particles when possible, unless they are clearly spoken and meaningful.
""".strip()
        timing = """
Timing rules:
- Use the real speech timing from the audio.
- "start" must match when the corresponding word begins.
- "end" must match when the corresponding word ends.
""".strip()
    elif normalized == "long":
        segmentation = """
Field rules:
- Each "text" value MUST represent a complete Belarusian sentence or a clear clause with natural punctuation.
- Do NOT artificially split sentences into 1-3 word fragments.
- Keep subtitles readable: avoid very long text that stays on screen for too short a time.
""".strip()
        timing = """
Timing rules:
- Use the real speech timing from the audio.
- "start" must match the beginning of the spoken sentence or clause.
- "end" must match the end of the spoken sentence or clause.
""".strip()
    else:
        segmentation = """
Field rules:
- Each "text" value MUST be a short Belarusian phrase.
- Each subtitle should typically contain 2-3 words.
- Never put more than 4 words in a single "text" value.
- If a sentence is long, split it into multiple short consecutive subtitle segments with accurate timings.
- Avoid extremely short fragments of one word unless it is a meaningful separate unit.
""".strip()
        timing = """
Timing rules:
- Use the real speech timing from the audio.
- "start" must match the beginning of the spoken phrase.
- "end" must match the end of the spoken phrase.
""".strip()

    return f"""
You are a transcription, translation, forced-alignment, and subtitle generation model specialized in Belarusian language.

Your task:
- Listen carefully to the input audio.
- Produce subtitles in Belarusian language ONLY.
- The subtitle text MUST be in Belarusian Cyrillic, for example: "прыклад тэксту".
- Do NOT use Latin transliteration.
- If the spoken language is not Belarusian, translate it into natural Belarusian in the subtitles.

{timing}
- Do NOT distribute timestamps evenly across the whole audio unless the speech itself is evenly paced.
- Preserve natural pauses and silence gaps when they are present.
- Segments must be strictly ordered and must not overlap.
- Do not create timestamps beyond the actual audio duration.
- Do not force subtitles to fill the whole audio duration.

Output format:
- Return ONLY valid JSON.
- Do NOT return markdown.
- Do NOT wrap the response in ```json or ``` blocks.
- The JSON must be a single array of objects like this:
[
  {{
"start": "00:00:00,000",
"end": "00:00:01,500",
"text": "Кароткі радок"
  }}
]
- "start" and "end" MUST be strings in SRT time format: "HH:MM:SS,mmm".

{segmentation}

Global constraints:
- Do NOT include any other top-level keys besides the JSON array.
- Do NOT add comments, explanations, summaries, or additional text.
- Return raw JSON only.
""".strip()

def _build_system_instruction(
    length_mode: str,
    prompt_text: str = "",
    duration_sec: float | None = None,
) -> str:
    parts: list[str] = []

    if prompt_text and prompt_text.strip():
        parts.append(prompt_text.strip())

    duration_instruction = _build_duration_instruction(duration_sec)

    if duration_instruction:
        parts.append(duration_instruction)

    parts.append(_get_format_instruction(length_mode).strip())

    return "\n\n".join(parts).strip()

def _build_timestamp_refinement_instruction(duration_sec: float) -> str:
    duration_ts = _seconds_to_srt_timestamp(duration_sec)

    return f"""
You are a precise subtitle timestamp correction model.

Your task:
- Listen to the audio carefully.
- You will receive a draft SRT transcript.
- Correct ONLY the subtitle timestamps.
- Preserve the subtitle text exactly as provided.
- Do NOT translate.
- Do NOT rewrite.
- Do NOT change spelling.
- Do NOT add new subtitles.
- Remove a subtitle only if its text is not actually present in the audio or is completely impossible to place.
- Keep the same subtitle order.
- Keep the same number of segments whenever possible, but do not keep hallucinated tail text.

Audio duration:
- Exact duration: {duration_sec:.3f} seconds.
- Exact duration in SRT format: {duration_ts}.
- No "start" or "end" may be greater than {duration_ts}.
- The final subtitle "end" must be less than or equal to {duration_ts}.
- Do not force the final subtitle to end at {duration_ts}; silence after the last spoken phrase should remain silence.

Timing rules:
- "start" must match when the corresponding phrase begins in the audio.
- "end" must match when the corresponding phrase ends in the audio.
- Segments must be strictly ordered.
- Segments must not overlap.
- Preserve silence gaps where they exist.
- Do not distribute timestamps evenly unless the speech is actually evenly paced.
- If a draft timestamp is beyond the audio duration, repair it by listening to the audio, not by inventing speech.
- If the draft contains extra text after the real audio has ended, remove those impossible tail segments.
- Do not stretch earlier subtitle text across later silence just to reach the end of the audio.

Output format:
- Return ONLY valid JSON.
- Do NOT return markdown.
- Do NOT wrap the response in ```json or ``` blocks.
- Return a single JSON array.
- Each item must have exactly these fields:
  - "start": SRT timestamp string, format "HH:MM:SS,mmm"
  - "end": SRT timestamp string, format "HH:MM:SS,mmm"
  - "text": the exact same subtitle text from the draft SRT

Critical constraint:
- The text values must be copied from the draft SRT exactly.
- The only intended changes are start and end timestamps.
""".strip()

def _guess_audio_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)

    if mime:
        return mime

    ext = Path(path).suffix.lower()
    fallback = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/m4a",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".aac": "audio/x-aac",
        ".mp4": "audio/mp4",
        ".pcm": "audio/pcm",
        ".mpga": "audio/mpga",
    }

    if ext in fallback:
        return fallback[ext]

    raise GeminiTranscriptionError(
        f"Could not determine MIME type for audio file: {path}"
    )

