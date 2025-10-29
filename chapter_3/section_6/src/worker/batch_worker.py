"""Background worker for processing batch jobs from Redis queue."""

import asyncio
import signal
import sys
import time
from typing import Any

from src.client.llm_client import LLMProvider
from src.client.redis_client import redis_client
from src.logger import make_logger
from src.model.batch_model import InternalJobData, JobStatus, TaskStatus
from src.model.model import CharacterRequest, CharacterResponse
from src.prompt.prompt import make_prompt
from src.service import request_gemini, request_openai

logger = make_logger(__name__)

QUEUE_NAME = "llm_batch_jobs"
POLL_TIMEOUT = 5  # seconds


class BatchWorker:
    """Worker that processes batch jobs from Redis queue."""

    def __init__(self) -> None:
        """Initialize the batch worker."""
        self.running = False
        self.processed_jobs = 0

    async def start(self) -> None:
        """Start the worker and begin processing jobs."""
        self.running = True
        logger.info("Batch worker started, waiting for jobs...")

        # Connect to Redis
        await redis_client.connect()

        # Process jobs until stopped
        while self.running:
            try:
                # Try to dequeue a job (blocks for POLL_TIMEOUT seconds)
                job_data = await redis_client.dequeue_job(QUEUE_NAME, timeout=POLL_TIMEOUT)

                if job_data:
                    await self._process_job(job_data)
                    self.processed_jobs += 1
                else:
                    # No jobs available, continue waiting
                    logger.debug("No jobs in queue, waiting...")

            except Exception as e:
                logger.error(f"Error in worker main loop: {e}")
                # Continue processing even if one job fails
                await asyncio.sleep(1)

        # Cleanup
        await redis_client.disconnect()
        logger.info(f"Batch worker stopped. Processed {self.processed_jobs} jobs total.")

    async def _process_job(self, job_data: dict[str, Any]) -> None:
        """
        Process a single batch job.

        Args:
            job_data: Job data from the queue
        """
        try:
            # Parse job data
            job = InternalJobData(**job_data)
            job_id = job.job_id
            logger.info(f"Processing job {job_id} with {len(job.character_requests)} tasks")

            # Update job status to processing
            status_data = await redis_client.get_job_status(job_id)
            if not status_data:
                logger.error(f"Job status not found for {job_id}")
                return

            status_data["status"] = JobStatus.PROCESSING
            status_data["started_at"] = time.time()
            await redis_client.set_job_status(job_id, status_data)

            # Process each task in the batch
            task_results: list[TaskStatus] = []
            completed_count = 0
            failed_count = 0

            for idx, char_req_dict in enumerate(job.character_requests):
                task_result = await self._process_task(
                    job_id=job_id,
                    task_index=idx,
                    provider=job.provider,
                    model=job.model,
                    character_request_dict=char_req_dict,
                )
                task_results.append(task_result)

                if task_result.status == JobStatus.COMPLETED:
                    completed_count += 1
                elif task_result.status == JobStatus.FAILED:
                    failed_count += 1

                # Update progress in status
                status_data["completed_tasks"] = completed_count
                status_data["failed_tasks"] = failed_count
                status_data["pending_tasks"] = len(job.character_requests) - completed_count - failed_count
                await redis_client.set_job_status(job_id, status_data)

            # Determine final job status
            final_status = JobStatus.COMPLETED if failed_count == 0 else JobStatus.FAILED
            completion_time = time.time()

            # Update final job status
            status_data["status"] = final_status
            status_data["completed_at"] = completion_time
            await redis_client.set_job_status(job_id, status_data)

            # Store job results
            result_data = {
                "job_id": job_id,
                "status": final_status,
                "provider": job.provider,
                "model": job.model,
                "tasks": [task.model_dump() for task in task_results],
                "submitted_at": job.submitted_at,
                "completed_at": completion_time,
            }
            await redis_client.set_job_result(job_id, result_data)

            logger.info(
                f"Job {job_id} completed with status {final_status}. "
                f"Completed: {completed_count}, Failed: {failed_count}"
            )

        except Exception as e:
            logger.error(f"Error processing job: {e}")
            # Try to mark job as failed
            try:
                job_id = job_data.get("job_id", "unknown")
                status_data = await redis_client.get_job_status(job_id)
                if status_data:
                    status_data["status"] = JobStatus.FAILED
                    status_data["completed_at"] = time.time()
                    await redis_client.set_job_status(job_id, status_data)
            except Exception as inner_e:
                logger.error(f"Error updating failed job status: {inner_e}")

    async def _process_task(
        self,
        job_id: str,
        task_index: int,
        provider: str,
        model: str,
        character_request_dict: dict[str, Any],
    ) -> TaskStatus:
        """
        Process a single task within a batch job.

        Args:
            job_id: Job ID
            task_index: Index of the task
            provider: LLM provider
            model: Model name
            character_request_dict: Character request data

        Returns:
            TaskStatus with the result
        """
        start_time = time.time()

        try:
            # Parse character request
            character_request = CharacterRequest(**character_request_dict)

            # Generate prompt
            prompt = make_prompt(character_request=character_request)

            # Call LLM
            character: CharacterResponse
            if provider == LLMProvider.OPENAI:
                character = await request_openai(model=model, prompt=prompt)
            elif provider == LLMProvider.GEMINI:
                character = await request_gemini(model=model, prompt=prompt)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            processing_time = (time.time() - start_time) * 1000

            logger.info(f"Task {task_index} of job {job_id} completed successfully in {processing_time:.2f}ms")

            return TaskStatus(
                task_index=task_index,
                status=JobStatus.COMPLETED,
                character=character,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Task {task_index} of job {job_id} failed: {error_msg}")

            return TaskStatus(
                task_index=task_index,
                status=JobStatus.FAILED,
                error=error_msg,
                processing_time_ms=processing_time,
            )

    def stop(self) -> None:
        """Stop the worker gracefully."""
        logger.info("Stopping batch worker...")
        self.running = False


# Global worker instance
worker = BatchWorker()


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    worker.stop()


async def main() -> None:
    """Main entry point for the worker."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start worker
    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
