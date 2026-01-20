"""Gemini BATCH API helper."""
from __future__ import annotations
"""Helpers for running Gemini BATCH API jobs."""

from dataclasses import dataclass
import json
import mimetypes
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
import logging

try:  # pragma: no cover - optional dependency wiring
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - optional dependency wiring
    genai = None  # type: ignore
    types = None  # type: ignore

logger = logging.getLogger(__name__)

class AIModelError(Exception):
    pass

@dataclass
class BatchTask:
    """Represents a single audio file queued for BATCH processing."""

    key: str
    path: str
    mime_type: str
    file_uri: Optional[str] = None


class GeminiBatchRunner:
    """Create and poll Gemini BATCH jobs for multiple audio files."""

    def __init__(self, api_key: str, model: str) -> None:
        if genai is None:
            raise AIModelError("google-genai library is not available")
        self._api_key = api_key
        self._model = model
        self._client = genai.Client(api_key=api_key)

    def run_batch(
        self,
        tasks: Iterable[BatchTask],
        prompt_text: str,
        *,
        chunk_size: int = 20,
    ) -> Dict[str, Any]:
        """Run batch jobs and return mapping ``key -> text``."""

        pending = list(tasks)
        if not pending:
            return {}

        results: Dict[str, Any] = {}
        normalized_chunk_size = max(1, int(chunk_size))

        for chunk_idx in range(0, len(pending), normalized_chunk_size):
            chunk = pending[chunk_idx : chunk_idx + normalized_chunk_size]
            self._process_chunk(chunk, chunk_idx // normalized_chunk_size, prompt_text, results)

        return results

    def _process_chunk(
        self, chunk: List[BatchTask], chunk_index: int, prompt_text: str, results: Dict[str, Any]
    ) -> None:
        if not chunk:
            return

        uploaded_file_names: List[str] = []
        uploaded_jsonl_name: Optional[str] = None

        try:
            for task in chunk:
                logger.info(f"Uploading file for batch: {task.path}")
                uploaded = self._client.files.upload(file=task.path)
                task.file_uri = uploaded.uri
                task.mime_type = uploaded.mime_type or task.mime_type
                uploaded_file_names.append(uploaded.name)
                
                # Wait for file processing if needed (though audio/video usually needs it, images/text less so)
                # But typically for Batch API referenced files, we might not need to wait for ACTIVE state 
                # unless we are using them immediately?
                # However, the user provided code didn't have wait loop, but previous debug showed strict requirement.
                # Let's trust the provided code pattern but add a small safety wait if needed or observe behavior.
                # The provided code DOES NOT wait for file active state, it just proceeds. 
                # We will follow the provided code structure.

            with tempfile.TemporaryDirectory() as tmpdir:
                jsonl_path = os.path.join(tmpdir, f"batch_input_{chunk_index:03}.jsonl")
                self._prepare_chunk_jsonl(chunk, jsonl_path, prompt_text, chunk_index)
                
                logger.info(f"Uploading JSONL batch file: {jsonl_path}")
                uploaded_jsonl = self._upload_jsonl(jsonl_path, f"batch-input-{chunk_index:03}")
                uploaded_jsonl_name = uploaded_jsonl.name
                logger.info(f"JSONL uploaded: {uploaded_jsonl_name}")

            logger.info(f"Creating batch job via REST for chunk {chunk_index}")
            batch_name = self._create_batch_job_rest(
                model_id=self._model,
                input_file_name=uploaded_jsonl_name,
                display_name=f"audio-batch-{chunk_index:03}",
            )
            logger.info(f"Batch job queued: {batch_name}. Polling for completion...")
            dest_file_name = self._poll_batch_job(batch_name)
            logger.info(f"Batch job completed. Downloading results from: {dest_file_name}")
            
            file_content = self._client.files.download(file=dest_file_name)
            self._process_results_jsonl_bytes(file_content, results)
        except Exception as e:
            logger.error(f"Error processing batch chunk {chunk_index}: {e}")
            raise e
        finally:
            logger.info("Cleaning up batch files...")
            for name in uploaded_file_names:
                try:
                    self._client.files.delete(name=name)
                except Exception:  # pragma: no cover - cleanup best effort
                    pass
            if uploaded_jsonl_name:
                try:
                    self._client.files.delete(name=uploaded_jsonl_name)
                except Exception:  # pragma: no cover - cleanup best effort
                    pass

    # ------------------------- JSONL helpers -------------------------
    def _prepare_chunk_jsonl(
        self, tasks_chunk: List[BatchTask], jsonl_path: str, prompt_text: str, chunk_index: int
    ) -> None:
        os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for i, task in enumerate(tasks_chunk):
                unique_key = task.key or f"chunk{chunk_index:03}_batch_{i:03}"
                parts = self._build_parts_for_task(task, prompt_text)
                request_entry = {
                    "custom_id": unique_key, # Gemini Batch uses 'custom_id' typically, previously 'key'
                    "method": "POST",
                    "request": {
                         "model": f"models/{self._model}" if not self._model.startswith("models/") else self._model,
                         "url": f"/v1beta/models/{self._model}:generateContent",
                         "body": {
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": parts,
                                }
                            ],
                            "generationConfig": {
                                "responseMimeType": "application/json"
                            }
                        }
                    },
                }
                # The provided code uses a different structure ("key", "request": {"contents":...}).
                # The provided code seems to target a specific structure. 
                # Let's STICK TO THE USER PROVIDED STRUCTURE FIRST.
                # Reverting to user provided structure:
                request_entry_user = {
                    "key": unique_key,
                    "request": {
                        "contents": [
                            {
                                "role": "user",
                                "parts": parts,
                            }
                        ]
                    },
                }
                # Wait, the official docs say JSONL should look like:
                # {"custom_id": "...", "method": "POST", "request": ...}
                # BUT the user provided code might be using a newer sdk wrapper or specific API version that supports this simplified format?
                # Or maybe the user code IS the working implementation they want me to use.
                # However, looking at _build_parts_for_task, it's pretty standard.
                # Let's trust the User's code 100% and copy it exactly, only adapting imports/logger.
                
                f.write(json.dumps(request_entry_user, ensure_ascii=False) + "\n")

    @staticmethod
    def _build_parts_for_task(task: BatchTask, prompt_text: str) -> List[Dict[str, Any]]:
        clean_prompt = (prompt_text or "").strip()
        parts: List[Dict[str, Any]] = []
        if clean_prompt:
            parts.append({"text": clean_prompt})
        
        # Only add file_data if file_uri exists (audio/image/video)
        if task.file_uri:
            parts.append(
                {
                    "file_data": {
                        "mime_type": task.mime_type,
                        "file_uri": task.file_uri,
                    }
                }
            )
        return parts

    def _upload_jsonl(self, jsonl_path: str, display_name: str):
        try:
            return self._client.files.upload(
                file=jsonl_path,
                config=types.UploadFileConfig(display_name=display_name, mime_type="text/plain"), # Changed to text/plain based on recent learnings
            )
        except Exception:
            return self._client.files.upload(
                file=jsonl_path,
                config=types.UploadFileConfig(display_name=display_name),
            )

    # ------------------------- REST helpers --------------------------
    @staticmethod
    def _rest_model_name(model_id: str) -> str:
        return model_id.replace("models/", "")

    def _create_batch_job_rest(self, model_id: str, input_file_name: str, display_name: str) -> str:
        # NOTE: The URL uses v1beta.
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._rest_model_name(model_id)}:batchGenerateContent"
        )
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "batch": {
                "display_name": display_name,
                "input_config": {"file_name": input_file_name},
            }
        }

        # The user code uses requests.post. 
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if not resp.ok:
            # Add detailed error logging
            logger.error(f"REST create failed: {resp.status_code} {resp.text}")
            raise AIModelError(f"REST create failed: {resp.status_code} {resp.text}")

        data = resp.json()
        name = data.get("name")
        if not name and isinstance(data.get("batch"), dict):
            name = data["batch"].get("name")
        if not name:
            raise AIModelError(f"REST create succeeded but no batch name found. Response: {data}")

        return name

    def _get_batch_job_rest(self, name: str) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/{name}"
        headers = {"x-goog-api-key": self._api_key}
        resp = requests.get(url, headers=headers, timeout=60)
        if not resp.ok:
             # Add detailed error logging
            logger.error(f"REST get failed: {resp.status_code} {resp.text}")
            raise AIModelError(f"REST get failed: {resp.status_code} {resp.text}")
        return resp.json()

    @staticmethod
    def _extract_state(rest_obj: Dict[str, Any]) -> Optional[str]:
        # Handle various response shapes
        state = rest_obj.get("state")
        if not state:
             state = (rest_obj.get("metadata") or {}).get("state") 
        if not state:
            state = (rest_obj.get("batch") or {}).get("state")
        return state

    @staticmethod
    def _extract_result_file_name(rest_obj: Dict[str, Any]) -> Optional[str]:
        # Try finding at root level (batch object)
        if "output_file" in rest_obj:
            return rest_obj["output_file"]
            
        # Try 'response' -> 'dest'
        resp = rest_obj.get("response") or {}
        dest = resp.get("dest") or {}
        return (
            dest.get("file_name")
            or dest.get("fileName")
            or resp.get("file_name")
            or resp.get("fileName")
            or resp.get("responsesFile")
            or resp.get("responses_file")
        )

    def _poll_batch_job(self, batch_name: str) -> str:
        completed_states = {
            "BATCH_STATE_SUCCEEDED",
            "BATCH_STATE_FAILED",
            "BATCH_STATE_CANCELLED",
            "BATCH_STATE_EXPIRED",
            "BATCH_STATE_PAUSED",
            "SUCCEEDED", "FAILED", "CANCELLED" # Add short forms just in case
        }

        while True:
            rest_job = self._get_batch_job_rest(batch_name)
            state = self._extract_state(rest_job)
            logger.info(f"Batch job {batch_name} state: {state}")
            if state in completed_states:
                break
            time.sleep(10) # Reduced from 30s to 10s for faster feedback in UI

        if state not in ["BATCH_STATE_SUCCEEDED", "SUCCEEDED"]:
            err = rest_job.get("error") or (rest_job.get("response") or {}).get("error")
            raise AIModelError(f"Batch job failed with state {state}: {err}")

        result_file_name = self._extract_result_file_name(rest_job)
        if not result_file_name:
            # Fallback for debugging
            logger.error(f"Could not locate result file. Job dump: {json.dumps(rest_job, indent=2)}")
            # Sometimes it might be directly in 'outputFile' in the main resource
            result_file_name = rest_job.get("outputFile") or rest_job.get("output_file")
        
        if not result_file_name:    
            raise AIModelError("Could not locate result file name in REST response")
            
        return result_file_name

    # ------------------------- Results processing --------------------
    @staticmethod
    def _process_results_jsonl_bytes(content_bytes: bytes, results: Dict[str, Any]) -> None:
        content_str = content_bytes.decode("utf-8", errors="replace")

        for line in content_str.splitlines():
            if not line.strip():
                continue
            try:
                result = json.loads(line)
            except Exception:
                continue

            key = result.get("custom_id") or result.get("key") # Support both keys
            if not key:
                continue

            response_wrapper = result.get("response", {})
            if "error" in response_wrapper:
                logger.error(f"Error in batch result for {key}: {response_wrapper['error']}")
                continue

            candidates = response_wrapper.get("candidates", [])
            text: Optional[str] = None
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                for part in parts:
                    if isinstance(part, dict) and part.get("text"):
                        text = part["text"]
                        break
            
            # If we expect JSON in the text, we might want to return that
            # The callers of this runner will handle parsing the text string.
            if text is not None:
                results[key] = text


def guess_mime_type(path: str) -> str:
    mime_type, _ = mimetypes.guess_type(path)
    return mime_type or "application/octet-stream"
