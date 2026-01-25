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
        
        # We need to reuse the connection logic from GenAIClient but use the robust Runner logic
        # Since we just added 'app/services/gemini_batch_runner.py', let's use it.
        from app.services.gemini_batch_runner import GeminiBatchRunner, BatchTask
        
        runner = GeminiBatchRunner(
            api_key=self.client.api_key,
            model=model_name
        )
        
        # 1. Adapt requests to what Runner logic expects (or mimic it here)
        # Runner logic expects "tasks" (BatchTask) and "prompt_text".
        # But our requests are pre-formed prompts or complex objects.
        
        # To strictly use the USER's code, we should call runner.run_batch().
        # BUT runner.run_batch() waits for completion. We might want async submission?
        # The user's code is blocking: "run_batch ... returns results". 
        # For now, let's keep it blocking as requested implicitly by "use this code".
        # This means submit_batch_job will now WAIT until completion. 
        # This changes the behavior of our service (it was asynchronous-ish/manual polling before).
        # However, the user demand "make it work" with this code implies replacing the broken async flow.
        
        # Wait - Pipeline expects 'submit' then 'wait'. 
        # If I make 'submit' block, then 'wait' step becomes redundant but safe.
        # Let's try to preserve non-blocking if possible, but the User code IS blocking.
        # "GeminiBatchRunner... run_batch".
        
        # Let's extract the "submission" part from their Runner code or re-implement it here 
        # to just submit and return the job name.
        
        # Re-implementing the "REST CREATE" logic from User's code here to fix our broken submit.
        
        import requests as http_requests
        
        # 1. Prepare JSONL using our existing method (it works fine for content)
        # Re-use create_jsonl_file but ensure we match the User's finding on uploading
        file_path = self.create_jsonl_file(requests, job_base_id, generation_config)
        
        # 2. Upload file using GenAI SDK (User code: uploads with mime_type="text/plain" or guessed)
        # User code: _client.files.upload(file=path, config={"mime_type": "text/plain"})
        # Let's do that.
        
        logger.info(f"Uploading batch file: {file_path}")
        file_ref = self.client._client.files.upload(
            file=str(file_path),
            config={"mime_type": "text/plain"} # User's code suggests this might be safer/better
        )
        
        # 3. Wait for file to be active? User code DOES NOT wait in the loop, but debug showed we might need to.
        # However, User code logic:
        # uploaded = client.files.upload(...)
        # ... prepare jsonl ...
        # uploaded_jsonl = client.files.upload(jsonl_path, ...)    <-- THIS IS THE BATCH FILE
        # batch_name = create_batch_job_rest(...)
        
        # The key difference: User code uploads THE JSONL via `files.upload` too!
        # And creates batch job via REST.
        
        # In my previous attempts, I was doing `client.batches.create(src=local_file)`.
        # The correct way (User's way) is:
        # 1. Upload JSONL to File API -> get URI/Name
        # 2. Call batches.create (REST or SDK) referencing that File Name.
        
        # Let's do exactly that.
        
        logger.info(f"Uploaded batch file {file_ref.name}. Creating job via REST...")
        
        # 4. Create Job via REST (User's "Magic" Fix)
        # Using the helper from User's code to get the correct URL format
        
        # Extract clean model name
        clean_model = model_name.replace("models/", "")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:batchGenerateContent"
        headers = {
            "x-goog-api-key": self.client.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "batch": {
                "display_name": display_name,
                "input_config": {"file_name": file_ref.name}, # Reference the uploaded file!
            }
        }
        
        resp = http_requests.post(url, headers=headers, json=payload, timeout=60)
        
        if not resp.ok:
            logger.error(f"REST batch create failed: {resp.status_code} {resp.text}")
            raise RuntimeError(f"Failed to create batch job: {resp.text}")
            
        data = resp.json()
        
        # Extract job name
        created_name = data.get("name")
        if not created_name and "batch" in data:
            created_name = data["batch"].get("name")
            
        if not created_name:
             raise RuntimeError(f"Created batch job but got no name. Response: {data}")
             
        logger.info(f"Batch job submitted successfully via REST: {created_name}")
        
        # Return dict compatible with our pipeline
        return {
            "job_id": created_name,
            "state": "ACTIVE", # Assume active if created
            "model": model_name,
            "local_file": str(file_path),
            "dataset_name": display_name
        }

    async def wait_for_job_async(self, job_name: str, poll_interval: int = 10) -> str:
        """
        Wait for a batch job to complete (Async).
        """
        logger.info(f"Waiting for batch job {job_name} (async)...")
        from app.services.gemini_batch_runner import GeminiBatchRunner
        import asyncio
        
        runner = GeminiBatchRunner(api_key=self.client.api_key, model="gemini-1.5-flash")
        
        try:
            while True:
                # We need to run the REST call in a thread because it's synchronous requests
                loop = asyncio.get_running_loop()
                rest_job = await loop.run_in_executor(None, runner._get_batch_job_rest, job_name)
                
                state = runner._extract_state(rest_job)
                logger.debug(f"Job {job_name} state: {state}")
                
                if state in ["BATCH_STATE_SUCCEEDED", "SUCCEEDED"]:
                    return "SUCCEEDED"
                elif state in ["BATCH_STATE_FAILED", "FAILED", "BATCH_STATE_CANCELLED", "CANCELLED", "BATCH_STATE_EXPIRED"]:
                    return "FAILED"
                
                await asyncio.sleep(poll_interval)
                
        except Exception as e:
            logger.error(f"Error polling batch job: {e}")
            return "UNKNOWN"

    def wait_for_job(self, job_name: str, poll_interval: int = 10) -> str:
        """
        Wait for a batch job to complete (Sync/Blocking).
        """
        logger.info(f"Waiting for batch job {job_name}...")
        from app.services.gemini_batch_runner import GeminiBatchRunner
        
        runner = GeminiBatchRunner(api_key=self.client.api_key, model="gemini-1.5-flash")
        
        try:
            while True:
                rest_job = runner._get_batch_job_rest(job_name)
                state = runner._extract_state(rest_job)
                
                logger.debug(f"Job {job_name} state: {state}")
                
                if state in ["BATCH_STATE_SUCCEEDED", "SUCCEEDED"]:
                    return "SUCCEEDED"
                elif state in ["BATCH_STATE_FAILED", "FAILED", "BATCH_STATE_CANCELLED", "CANCELLED", "BATCH_STATE_EXPIRED"]:
                    return "FAILED"
                
                time.sleep(poll_interval)
                
        except Exception as e:
            logger.error(f"Error polling batch job: {e}")
            return "UNKNOWN"

    def get_job_results_url(self, job_name: str) -> str | None:
        """Get the resource name for the job output file."""
        from app.services.gemini_batch_runner import GeminiBatchRunner
        runner = GeminiBatchRunner(api_key=self.client.api_key, model="gemini-1.5-flash")
        try:
            rest_job = runner._get_batch_job_rest(job_name)
            return runner._extract_result_file_name(rest_job)
        except Exception:
            return None

    def download_results(self, job_name: str) -> list[Any]:
        """
        Download and parse results from a completed batch job via REST.
        """
        from app.services.gemini_batch_runner import GeminiBatchRunner
        runner = GeminiBatchRunner(api_key=self.client.api_key, model="gemini-1.5-flash")
        
        try:
            # 1. Get the result file name (URI)
            rest_job = runner._get_batch_job_rest(job_name)
            state = runner._extract_state(rest_job)
            
            if state not in ["BATCH_STATE_SUCCEEDED", "SUCCEEDED"]:
                logger.warning(f"Job {job_name} state is {state}, cannot download results.")
                return []
                
            output_file_name = runner._extract_result_file_name(rest_job)
            if not output_file_name:
                logger.error(f"No output file found for job {job_name}")
                return []
                
            logger.info(f"Downloading results from {output_file_name}...")
            
            # 2. Download the content using SDK or REST
            # The SDK's client.files.download(file=...) works if we pass the right name
            # Runner uses: self._client.files.download(file=dest_file_name)
            
            # 2. Download the content using SDK or REST
            content_bytes = self.client._client.files.download(file=output_file_name)
            
            # 3. Parse results directly from JSONL
            content_str = content_bytes.decode("utf-8", errors="replace")
            parsed_results = []
            
            for line in content_str.splitlines():
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    parsed_results.append(item)
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
        """
        Submit the same batch of requests to multiple models (default: all configured).
        
        Args:
            requests: The requests to send.
            models: List of model names. If None, uses self.default_models.
            job_prefix: Prefix for the job names.
            
        Returns:
            List of job submission results.
        """
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
        """Check status of a specific batch job via REST."""
        from app.services.gemini_batch_runner import GeminiBatchRunner
        runner = GeminiBatchRunner(api_key=self.client.api_key, model="gemini-1.5-flash")
        
        try:
            rest_job = runner._get_batch_job_rest(job_name)
            state = runner._extract_state(rest_job)
            
            return {
                "job_id": job_name,
                "state": state,
                "created_time": rest_job.get("createTime", ""),
                "update_time": rest_job.get("updateTime", ""),
                "completed_count": 0, # Not constantly available in basic REST view
                "failed_count": 0
            }
        except Exception as e:
            # Only log debug to avoid spam if job is just missing temporarily
            logger.debug(f"Failed to check job status {job_name}: {e}")
            return {"error": str(e)}

    def list_active_jobs(self) -> list[dict[str, Any]]:
        """List all recent batch jobs via REST."""
        import requests
        api_key = self.client.api_key
        # Attempt to list batches using the standard endpoint pattern
        url = f"https://generativelanguage.googleapis.com/v1beta/batches?key={api_key}&pageSize=50"
        
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Failed to list batches: {resp.status_code}")
                return []
                
            data = resp.json()
            jobs = data.get("batches", [])
            return [
                {
                    "job_id": j.get("name"),
                    "state": j.get("state"),
                    "model": "unknown" 
                }
                for j in jobs
            ]
        except Exception as e:
            logger.error(f"Error listing batches: {e}")
            return []
