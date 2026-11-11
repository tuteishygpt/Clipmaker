"""Service for handling Gemini Batch API operations."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from ..clients.genai import GenAIClient
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class BatchService:
    """Service to prepare, submit, and manage Gemini batch jobs."""
    
    def __init__(self) -> None:
        self.client = GenAIClient()
        self.batch_dir = settings.base_dir / "data" / "batch_jobs"
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        
        # Default models to test against if "all" is requested
        self.default_models = [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            # Add other models as they become available/relevant
        ]

    def create_jsonl_file(
        self,
        requests: list[dict[str, Any] | str],
        job_id: str,
        generation_config: dict[str, Any] | None = None
    ) -> Path:
        """
        Create a JSONL file formatted for Gemini Batch API.
        
        Args:
            requests: List of prompts (str) or formatted request objects (dict).
            job_id: Unique identifier for this job.
            generation_config: Optional config common for all requests (e.g. response_modalities).
            
        Returns:
            Path to the created file.
        """
        file_path = self.batch_dir / f"{job_id}.jsonl"
        
        with open(file_path, "w", encoding="utf-8") as f:
            for i, req in enumerate(requests):
                # Default structure
                custom_id = f"{job_id}-{i}"
                method = "generateContent"
                request_body = {}

                # Check if req provides specific batch fields
                is_batch_entry = isinstance(req, dict) and "request" in req
                
                if is_batch_entry:
                    if "custom_id" in req:
                        custom_id = req["custom_id"]
                    if "method" in req:
                        method = req["method"]
                    request_body = req["request"]
                elif isinstance(req, str):
                    # Simple text prompt
                    request_body = {
                        "contents": [
                            {"role": "user", "parts": [{"text": req}]}
                        ]
                    }
                else:
                    # Assumed to be a full request structure or parts list
                    if isinstance(req, list):
                         request_body = {
                            "contents": [{"role": "user", "parts": req}]
                         }
                    elif isinstance(req, dict) and "parts" in req:
                         request_body = {
                            "contents": [{"role": "user", "parts": [req]}]
                         }
                    else:
                        request_body = req
                
                entry = {
                    "custom_id": custom_id,
                    "method": method,
                    "request": request_body
                }
                
                # Apply generation config if provided and not present
                if generation_config:
                    if "generationConfig" not in entry["request"]:
                        entry["request"]["generationConfig"] = generation_config
                    else:
                        pass
                
                f.write(json.dumps(entry) + "\n")
        
        logger.info(f"Created batch file: {file_path}")
        return file_path

    def submit_batch_job(
        self,
        requests: list[dict[str, Any] | str],
        model_name: str,
        job_name: str | None = None,
        generation_config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Submits a batch job using the logic verified by the user (REST-based creation + File API).
        This integrates the 'GeminiBatchRunner' approach into our existing service structure.
        """
        job_base_id = f"batch-{uuid.uuid4().hex[:8]}"
        display_name = job_name or f"Job-{job_base_id}"
        
        # 1. Prepare JSONL using our existing method (it works fine for content)
        file_path = self.create_jsonl_file(requests, job_base_id, generation_config)
        
        if self.client.is_vertex:
            # Route exclusively via Vertex AI Batch API
            logger.info(f"Submitting batch job via Vertex AI for {display_name}...")
            job = self.client.create_batch_job(
                dataset_name=display_name,
                source=file_path,
                model_name=model_name,
            )
            job_name = getattr(job, "name", str(job))
            return {
                "job_id": job_name,
                "state": getattr(job, "state", "ACTIVE"),
                "model": model_name,
                "local_file": str(file_path),
                "dataset_name": display_name,
            }

        raise RuntimeError("Batch API is supported exclusively via Vertex AI.")

    async def wait_for_job_async(self, job_name: str, poll_interval: int = 10) -> str:
        """Wait for a Vertex AI batch job to complete (Async)."""
        logger.info(f"Waiting for Vertex AI batch job {job_name} (async)...")
        if not self.client.is_vertex:
            raise RuntimeError("Batch API is supported exclusively via Vertex AI.")
        import asyncio
        try:
            while True:
                job = self.client.get_batch_job(job_name)
                state = str(getattr(job, "state", "") or "").upper()
                logger.debug(f"Vertex AI job {job_name} state: {state}")
                if any(s in state for s in ["SUCCEEDED", "DONE"]):
                    return "SUCCEEDED"
                elif any(s in state for s in ["FAILED", "CANCELLED", "EXPIRED"]):
                    return "FAILED"
                await asyncio.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Error polling Vertex AI batch job: {e}")
            return "UNKNOWN"

    def wait_for_job(self, job_name: str, poll_interval: int = 10) -> str:
        """Wait for a Vertex AI batch job to complete (Sync/Blocking)."""
        logger.info(f"Waiting for Vertex AI batch job {job_name}...")
        if not self.client.is_vertex:
            raise RuntimeError("Batch API is supported exclusively via Vertex AI.")
        try:
            while True:
                job = self.client.get_batch_job(job_name)
                state = str(getattr(job, "state", "") or "").upper()
                logger.debug(f"Vertex AI job {job_name} state: {state}")
                if any(s in state for s in ["SUCCEEDED", "DONE"]):
                    return "SUCCEEDED"
                elif any(s in state for s in ["FAILED", "CANCELLED", "EXPIRED"]):
                    return "FAILED"
                time.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Error polling Vertex AI batch job: {e}")
            return "UNKNOWN"

    def get_job_results_url(self, job_name: str) -> str | None:
        """Get the output GCS URI for a Vertex AI batch job."""
        if not self.client.is_vertex:
            raise RuntimeError("Batch API is supported exclusively via Vertex AI.")
        job = self.client.get_batch_job(job_name)
        dest = getattr(job, "dest", None) if job else None
        return getattr(dest, "gcs_uri", None) if dest else None

    def download_results(self, job_name: str) -> list[Any]:
        """Download and parse JSONL results from a completed Vertex AI batch job."""
        if not self.client.is_vertex:
            raise RuntimeError("Batch API is supported exclusively via Vertex AI.")
        try:
            job = self.client.get_batch_job(job_name)
            state = str(getattr(job, "state", "") or "").upper()
            if not any(s in state for s in ["SUCCEEDED", "DONE"]):
                logger.warning(f"Job {job_name} state is {state}, cannot download results.")
                return []

            output_uri = self.get_job_results_url(job_name)
            if not output_uri or not str(output_uri).startswith("gs://"):
                logger.error(f"No GCS output URI found for Vertex AI job {job_name}: {output_uri}")
                return []

            from google.cloud import storage

            storage_client = storage.Client(
                project=self.client.project or None,
                credentials=self.client._credentials,
            )
            bucket_and_prefix = str(output_uri)[len("gs://"):]
            bucket_name, _, prefix = bucket_and_prefix.partition("/")
            bucket = storage_client.bucket(bucket_name)

            blobs = list(bucket.list_blobs(prefix=prefix))
            parsed_results: list[Any] = []
            for blob in blobs:
                if not blob.name.endswith(".jsonl"):
                    continue
                content_str = blob.download_as_text(encoding="utf-8", errors="replace")
                for line in content_str.splitlines():
                    if not line.strip():
                        continue
                    try:
                        parsed_results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return parsed_results
        except Exception as e:
            logger.error(f"Failed to download results for {job_name}: {e}")
            return []

    def broadcast_to_models(
        self,
        requests: list[dict[str, Any] | str],
        models: list[str] | None = None,
        job_prefix: str = "Broadcast"
    ) -> list[dict[str, Any]]:
        """Submit the same batch of requests to multiple models."""
        target_models = models or self.default_models
        results = []

        for model in target_models:
            logger.info(f"Submitting batch to model: {model}")
            result = self.submit_batch_job(
                requests=requests,
                model_name=model,
                job_name=f"{job_prefix} - {model}"
            )
            results.append(result)

        return results

    def check_job_status(self, job_name: str) -> dict[str, Any]:
        """Check status of a specific Vertex AI batch job."""
        if not self.client.is_vertex:
            raise RuntimeError("Batch API is supported exclusively via Vertex AI.")
        try:
            job = self.client.get_batch_job(job_name)
            if job is None:
                return {"job_id": job_name, "state": "UNKNOWN"}
            return {
                "job_id": getattr(job, "name", job_name),
                "state": str(getattr(job, "state", "") or "UNKNOWN"),
                "created_time": str(getattr(job, "create_time", "") or ""),
                "update_time": str(getattr(job, "update_time", "") or ""),
                "completed_count": 0,
                "failed_count": 0,
            }
        except Exception as e:
            logger.debug(f"Failed to check job status {job_name}: {e}")
            return {"error": str(e)}

    def list_active_jobs(self) -> list[dict[str, Any]]:
        """List recent Vertex AI batch jobs."""
        if not self.client.is_vertex:
            raise RuntimeError("Batch API is supported exclusively via Vertex AI.")
        try:
            jobs = self.client.list_batch_jobs(limit=50)
            return [
                {
                    "job_id": getattr(j, "name", None),
                    "state": str(getattr(j, "state", "") or "UNKNOWN"),
                    "model": str(getattr(j, "model", "unknown") or "unknown"),
                }
                for j in jobs
            ]
        except Exception as e:
            logger.error(f"Error listing batches: {e}")
            return []
