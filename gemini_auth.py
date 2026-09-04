import atexit
import base64
import json
import logging
import os
import random
import time
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)
_SERVICE_ACCOUNT_CREDENTIALS_PATH: str | None = None

class GeminiTranscriptionError(RuntimeError):
    """Raised when Gemini transcription fails."""


def _is_retryable_error(exc: Exception | None) -> bool:
    """Return True if exception is transient and should be retried (e.g. 429 quota/rate limit or 5xx)."""
    if exc is None:
        return False

    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code is not None:
        try:
            code_int = int(code)
            if code_int in (429, 408, 500, 502, 503, 504):
                return True
            if 400 <= code_int < 500 and code_int != 429:
                return False
        except (ValueError, TypeError):
            pass

    status_str = str(getattr(exc, "status", "") or "").upper()
    if status_str in (
        "RESOURCE_EXHAUSTED",
        "UNAVAILABLE",
        "INTERNAL",
        "DEADLINE_EXCEEDED",
        "ABORTED",
    ):
        return True

    err_text = str(exc).lower()

    # Never retry explicitly unsupported model interactions or client invalid requests
    if "unsupported model interaction" in err_text or "invalid_request" in err_text:
        return False

    retryable_patterns = (
        "429",
        "resource_exhausted",
        "resource has been exhausted",
        "quota",
        "rate limit",
        "too many requests",
        "503",
        "unavailable",
        "service unavailable",
        "deadline exceeded",
        "504",
        "gateway timeout",
        "connection reset",
        "connection timed out",
        "read timed out",
        "timeout",
    )
    if any(pat in err_text for pat in retryable_patterns):
        return True

    if isinstance(
        exc,
        (TimeoutError, ConnectionResetError, ConnectionRefusedError, ConnectionAbortedError),
    ):
        return True

    return False


def _get_retry_after(exc: Exception) -> float | None:
    """Extract Retry-After header delay if available."""
    try:
        response = getattr(exc, "response", None)
        if response is not None:
            headers = getattr(response, "headers", None)
            if headers and hasattr(headers, "get"):
                val = headers.get("retry-after") or headers.get("Retry-After")
                if val is not None:
                    return float(val)
    except Exception:
        pass
    return None


def _call_with_retry(
    fn: Callable[[], Any],
    *,
    operation_label: str = "API request",
    status: Optional[Callable[[str], None]] = None,
    max_retries: Optional[int] = None,
    initial_delay: Optional[float] = None,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
) -> Any:
    """Execute callable with exponential backoff on retryable errors (429 / RESOURCE_EXHAUSTED)."""
    if max_retries is None:
        try:
            max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "5"))
        except ValueError:
            max_retries = 5

    if initial_delay is None:
        try:
            initial_delay = float(os.getenv("GEMINI_RETRY_INITIAL_DELAY", "2.0"))
        except ValueError:
            initial_delay = 2.0

    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable_error(exc) or attempt >= max_retries:
                logger.error(
                    "%s failed (attempt %d/%d, non-retryable or retries exhausted): %s",
                    operation_label,
                    attempt,
                    max_retries,
                    exc,
                )
                raise

            retry_after = _get_retry_after(exc)
            if retry_after is not None and retry_after > 0:
                delay = min(retry_after, max_delay)
            else:
                base = initial_delay * (backoff_factor ** (attempt - 1))
                jitter = random.uniform(0.2, 1.0)
                delay = min(base + jitter, max_delay)

            msg = (
                f"Перавышаны ліміт запытаў (429 / квота). "
                f"Чакаем {delay:.1f} сек. і паўтараем запыт ({attempt}/{max_retries}) …"
            )
            logger.warning(
                "%s encountered retryable error (attempt %d/%d): %s. Retrying in %.2fs...",
                operation_label,
                attempt,
                max_retries,
                exc,
                delay,
            )
            if status is not None:
                try:
                    status(msg)
                except Exception:
                    pass

            time.sleep(delay)

    if last_exc is not None:
        raise last_exc


def _validate_api_key_format(api_key: str) -> None:
    if not api_key.strip():
        raise GeminiTranscriptionError(
            "Gemini API key is empty. "
                "Set gemini, gembeh, GOOGLE_API_KEY, or GEMINI_API_KEY."
        )


def is_transcribe_model(model: str | None = None) -> bool:
    """Return True if model is a dedicated speech-to-text model (e.g. gemini-3.5-transcribe)."""
    if model is None:
        _load_local_env()
        model = os.getenv("mod", "")
    normalized = (model or "").strip().lower()
    return "transcribe" in normalized


def _clean_time(val: Any) -> float:
    """Normalize time offsets (e.g., '1.25s', '250ms', 1.25, {'seconds': 1, 'nanos': 250000000}, '00:01:23,456') to float seconds."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        sec = float(val.get("seconds", 0) or 0)
        nanos = float(val.get("nanos", 0) or 0)
        return sec + (nanos / 1e9)
    if hasattr(val, "seconds") or hasattr(val, "nanos"):
        sec = float(getattr(val, "seconds", 0) or 0)
        nanos = float(getattr(val, "nanos", 0) or 0)
        return sec + (nanos / 1e9)
    s = str(val).strip()
    if not s:
        return 0.0
    if s.lower().endswith("ms"):
        try:
            return float(s[:-2].strip()) / 1000.0
        except ValueError:
            pass
    if s.lower().endswith("s"):
        s = s[:-1].strip()
    s_clean = s.replace(",", ".")
    try:
        return float(s_clean)
    except ValueError:
        pass

    parts = s_clean.split(":")
    if len(parts) == 3:
        try:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except ValueError:
            pass
    elif len(parts) == 2:
        try:
            return float(parts[0]) * 60 + float(parts[1])
        except ValueError:
            pass

    try:
        from subtitle_generation import _parse_raw_time
        return _parse_raw_time(s)
    except Exception:
        return 0.0


def _load_local_env(env_path: str | Path = ".env") -> None:
    path = Path(env_path)

    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()

        if not key or key in os.environ:
            continue

        os.environ[key] = value.strip().strip('"').strip("'")


def _load_service_account_json_from_env() -> str:
    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_json:
        return raw_json

    raw_b64 = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_B64", "").strip()
    if raw_b64:
        try:
            return base64.b64decode(raw_b64, validate=True).decode("utf-8").strip()
        except Exception as exc:
            raise GeminiTranscriptionError(
                "GOOGLE_SERVICE_ACCOUNT_JSON_B64 must contain valid base64-encoded service account JSON."
            ) from exc

    for key in ("GOOGLE_SERVICE_ACCOUNT_JSON_FILE", "GOOGLE_APPLICATION_CREDENTIALS"):
        path_value = os.environ.get(key, "").strip()
        if not path_value:
            continue

        path = Path(path_value)
        if not path.is_file():
            raise GeminiTranscriptionError(f"{key} points to a missing file: {path}")

        return path.read_text(encoding="utf-8").strip()

    return ""


def _configure_adc_from_service_account_json(
    service_account_json: str,
    configured_project: str = "",
) -> str:
    global _SERVICE_ACCOUNT_CREDENTIALS_PATH

    raw_json = service_account_json.strip()
    if not raw_json:
        raise GeminiTranscriptionError("GOOGLE_SERVICE_ACCOUNT_JSON is empty.")

    try:
        service_account = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise GeminiTranscriptionError(
            "GOOGLE_SERVICE_ACCOUNT_JSON must contain valid service account JSON."
        ) from exc

    project_id = (configured_project or service_account.get("project_id") or "").strip()
    if not project_id:
        raise GeminiTranscriptionError(
            "Vertex AI project is not configured. Set GOOGLE_CLOUD_PROJECT "
            "or include project_id in GOOGLE_SERVICE_ACCOUNT_JSON."
        )

    if not _SERVICE_ACCOUNT_CREDENTIALS_PATH:
        credentials_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            prefix="google-service-account-",
            delete=False,
        )
        with credentials_file:
            credentials_file.write(raw_json)
        _SERVICE_ACCOUNT_CREDENTIALS_PATH = credentials_file.name

        def _cleanup_sa_file(path: str) -> None:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

        atexit.register(_cleanup_sa_file, _SERVICE_ACCOUNT_CREDENTIALS_PATH)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _SERVICE_ACCOUNT_CREDENTIALS_PATH
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
    return project_id

