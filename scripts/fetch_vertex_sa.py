"""Fetch the Vertex AI service account JSON from GCP Secret Manager into tmpfs."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import tempfile
import urllib.request


METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)


def _fetch_metadata_token() -> str:
    req = urllib.request.Request(
        METADATA_TOKEN_URL,
        headers={"Metadata-Flavor": "Google"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = str(data.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("Empty access_token from GCE Metadata server")
    return token


def _fetch_secret_payload(project_id: str, secret_name: str, version: str, token: str) -> bytes:
    url = (
        f"https://secretmanager.googleapis.com/v1/projects/{project_id}"
        f"/secrets/{secret_name}/versions/{version}:access"
    )
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    b64_payload = data.get("payload", {}).get("data")
    if not b64_payload:
        raise RuntimeError(f"Secret '{secret_name}' returned empty payload")
    return base64.b64decode(b64_payload)


def _validate_sa_json(payload_bytes: bytes) -> None:
    parsed = json.loads(payload_bytes.decode("utf-8"))
    if not isinstance(parsed, dict) or parsed.get("type") != "service_account":
        raise RuntimeError("Secret payload is not a valid service_account JSON")
    for field in ("project_id", "client_email", "private_key"):
        if not str(parsed.get(field) or "").strip():
            raise RuntimeError(f"Service account JSON missing '{field}'")


def main() -> None:
    project_id = (
        os.getenv("GCP_PROJECT_ID")
        or os.getenv("VERTEX_SECRET_PROJECT")
        or "clipmaker-prod-2026"
    ).strip()
    secret_name = os.getenv("VERTEX_SECRET_NAME", "clipmaker-vertex-sa").strip()
    version = os.getenv("VERTEX_SECRET_VERSION", "latest").strip()
    target_path = Path(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_FILE", "/run/clipmaker/vertex-sa.json").strip()
    )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(target_path.parent, 0o700)

    token = _fetch_metadata_token()
    payload = _fetch_secret_payload(project_id, secret_name, version, token)
    _validate_sa_json(payload)

    fd, tmp_name = tempfile.mkstemp(prefix=".vertex-sa-", suffix=".json", dir=str(target_path.parent))
    tmp_path = Path(tmp_name)
    try:
        os.chmod(tmp_path, 0o400)
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
        os.chmod(tmp_path, 0o400)
        os.replace(tmp_path, target_path)
        os.chmod(target_path, 0o400)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
