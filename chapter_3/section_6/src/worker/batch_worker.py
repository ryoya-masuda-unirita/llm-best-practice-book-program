"""Background worker for processing batch jobs from Redis queue."""

import asyncio
import signal
import sys
import time
from dataclasses import dataclass
from typing import Any

from src.client.llm_client import LLMProvider
from src.client.redis_client import redis_client
from src.logger import make_logger
from src.model.batch_model import (
    BatchJobResultResponse,
    BatchJobStatusResponse,
    InternalJobData,
    JobStatus,
    TaskStatus,
)
from src.model.model import CharacterRequest, CharacterResponse
from src.prompt.prompt import make_prompt
from src.service import get_gemini_batch_results, get_gemini_batch_status, submit_gemini_batch

logger = make_logger(__name__)

QUEUE_NAME = "llm_batch_jobs"
POLL_TIMEOUT = 1
BATCH_POLL_INTERVAL = 5

GEMINI_FAILED_STATES = ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED")


@dataclass
class ActiveJob:
    """Represents an active job being processed."""

    job_id: str
    gemini_batch_name: str
    job_data: InternalJobData
    status_data: BatchJobStatusResponse
    start_time: float
    num_tasks: int


def build_status_response(
    job_id: str,
    status: JobStatus,
    total_tasks: int,
    completed_tasks: int,
    failed_tasks: int,
    pending_tasks: int,
    submitted_at: float,
    started_at: float | None = None,
    completed_at: float | None = None,
) -> BatchJobStatusResponse:
    return BatchJobStatusResponse(
        job_id=job_id,
        status=status,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        pending_tasks=pending_tasks,
        submitted_at=submitted_at,
        started_at=started_at,
        completed_at=completed_at,
    )


def build_task_results(
    batch_results: list[CharacterResponse | None],
    processing_time_ms: float,
) -> tuple[list[TaskStatus], int, int]:
    task_results: list[TaskStatus] = []
    completed_count = 0
    failed_count = 0
    time_per_task = processing_time_ms / len(batch_results) if batch_results else 0

    for idx, result in enumerate(batch_results):
        if result is not None:
            task_results.append(
                TaskStatus(
                    task_index=idx,
                    status=JobStatus.COMPLETED,
                    character=result,
                    processing_time_ms=time_per_task,
                )
            )
            completed_count += 1
        else:
            task_results.append(
                TaskStatus(
                    task_index=idx,
                    status=JobStatus.FAILED,
                    error="No response from batch API",
                    processing_time_ms=time_per_task,
                )
            )
            failed_count += 1

    return task_results, completed_count, failed_count


def prepare_prompts(character_requests: list[dict[str, Any]]) -> list[tuple[str, str]]:
    prompts: list[tuple[str, str]] = []
    for char_req_dict in character_requests:
        character_request = CharacterRequest(**char_req_dict)
        prompt = make_prompt(character_request=character_request)
        system_prompt = prompt[0]["content"]
        user_prompt = prompt[-1]["content"]
        prompts.append((system_prompt, user_prompt))
    return prompts


class BatchWorker:
    """Worker that processes batch jobs from Redis queue with concurrent polling."""

    def __init__(self) -> None:
        self.running = False
        self.processed_jobs = 0
        self.active_jobs: dict[str, ActiveJob] = {}

    async def start(self) -> None:
        self.running = True
        logger.info("Batch worker started, waiting for jobs...")

        await redis_client.connect()

        pickup_task = asyncio.create_task(self._job_pickup_loop())
        poll_task = asyncio.create_task(self._poll_active_jobs_loop())

        try:
            await asyncio.gather(pickup_task, poll_task)
        except asyncio.CancelledError:
            pass

        await redis_client.disconnect()
        logger.info(f"Batch worker stopped. Processed {self.processed_jobs} jobs total.")

    def stop(self) -> None:
        logger.info("Stopping batch worker...")
        self.running = False

    async def _job_pickup_loop(self) -> None:
        while self.running:
            try:
                job_data = await redis_client.dequeue_job(QUEUE_NAME, timeout=POLL_TIMEOUT)
                if job_data:
                    await self._submit_job_to_gemini(job_data)
                else:
                    logger.debug("No jobs in queue, waiting...")
            except Exception as e:
                logger.error(f"Error in job pickup loop: {e}")
                await asyncio.sleep(1)

    async def _poll_active_jobs_loop(self) -> None:
        while self.running:
            if not self.active_jobs:
                await asyncio.sleep(BATCH_POLL_INTERVAL)
                continue

            jobs_to_check = list(self.active_jobs.values())
            await asyncio.gather(*[self._check_job_status(job) for job in jobs_to_check])
            await asyncio.sleep(BATCH_POLL_INTERVAL)

    async def _submit_job_to_gemini(self, job_data: dict[str, Any]) -> None:
        try:
            job = InternalJobData(**job_data)
            job_id = job.job_id
            logger.info(f"Submitting job {job_id} with {len(job.character_requests)} tasks to Gemini")

            status_dict = await redis_client.get_job_status(job_id)
            if not status_dict:
                logger.error(f"Job status not found for {job_id}")
                return

            if job.provider != LLMProvider.GEMINI:
                raise ValueError(f"Unsupported provider: {job.provider}")

            status_data = build_status_response(
                job_id=status_dict["job_id"],
                status=JobStatus.PROCESSING,
                total_tasks=status_dict["total_tasks"],
                completed_tasks=status_dict.get("completed_tasks", 0),
                failed_tasks=status_dict.get("failed_tasks", 0),
                pending_tasks=status_dict.get("pending_tasks", status_dict["total_tasks"]),
                submitted_at=status_dict["submitted_at"],
                started_at=time.time(),
            )
            await redis_client.set_job_status(job_id, status_data.model_dump())

            prompts = prepare_prompts(job.character_requests)

            start_time = time.time()
            batch_job_name = submit_gemini_batch(model=job.model, prompts=prompts)
            logger.info(f"Job {job_id} submitted to Gemini as {batch_job_name}")

            self.active_jobs[job_id] = ActiveJob(
                job_id=job_id,
                gemini_batch_name=batch_job_name,
                job_data=job,
                status_data=status_data,
                start_time=start_time,
                num_tasks=len(prompts),
            )

        except Exception as e:
            logger.error(f"Error submitting job to Gemini: {e}")
            await self._mark_job_failed(job_data.get("job_id", "unknown"), str(e))

    async def _check_job_status(self, active_job: ActiveJob) -> None:
        try:
            batch_status = get_gemini_batch_status(active_job.gemini_batch_name)

            if batch_status == "JOB_STATE_SUCCEEDED":
                logger.info(f"Gemini batch job succeeded: {active_job.gemini_batch_name}")
                await self._process_completed_job(active_job)
                self._finalize_job(active_job.job_id)

            elif batch_status in GEMINI_FAILED_STATES:
                logger.error(f"Gemini batch job failed: {active_job.gemini_batch_name} with state {batch_status}")
                await self._mark_job_failed(active_job.job_id, f"Gemini batch job failed with state: {batch_status}")
                self._finalize_job(active_job.job_id)

            else:
                logger.debug(f"Job {active_job.job_id} status: {batch_status}")

        except Exception as e:
            logger.error(f"Error checking job {active_job.job_id}: {e}")

    def _finalize_job(self, job_id: str) -> None:
        del self.active_jobs[job_id]
        self.processed_jobs += 1

    async def _process_completed_job(self, active_job: ActiveJob) -> None:
        try:
            batch_results = get_gemini_batch_results(active_job.gemini_batch_name)
            processing_time_ms = (time.time() - active_job.start_time) * 1000

            logger.info(f"Batch API completed in {processing_time_ms:.2f}ms for {active_job.num_tasks} tasks")

            task_results, completed_count, failed_count = build_task_results(batch_results, processing_time_ms)

            final_status = JobStatus.COMPLETED if failed_count == 0 else JobStatus.FAILED
            completion_time = time.time()

            final_status_data = build_status_response(
                job_id=active_job.job_id,
                status=final_status,
                total_tasks=active_job.status_data.total_tasks,
                completed_tasks=completed_count,
                failed_tasks=failed_count,
                pending_tasks=0,
                submitted_at=active_job.status_data.submitted_at,
                started_at=active_job.status_data.started_at,
                completed_at=completion_time,
            )
            await redis_client.set_job_status(active_job.job_id, final_status_data.model_dump())

            result_data = BatchJobResultResponse(
                job_id=active_job.job_id,
                status=final_status,
                provider=active_job.job_data.provider,
                model=active_job.job_data.model,
                tasks=task_results,
                submitted_at=active_job.job_data.submitted_at,
                completed_at=completion_time,
            )
            await redis_client.set_job_result(active_job.job_id, result_data.model_dump())

            logger.info(f"Job {active_job.job_id} completed: {completed_count} succeeded, {failed_count} failed")

        except Exception as e:
            logger.error(f"Error processing completed job {active_job.job_id}: {e}")
            await self._mark_job_failed(active_job.job_id, str(e))

    async def _mark_job_failed(self, job_id: str, error_msg: str) -> None:
        try:
            status_dict = await redis_client.get_job_status(job_id)
            if not status_dict:
                logger.warning(f"Cannot mark job {job_id} as failed: status not found")
                return

            failed_status_data = build_status_response(
                job_id=status_dict["job_id"],
                status=JobStatus.FAILED,
                total_tasks=status_dict["total_tasks"],
                completed_tasks=status_dict.get("completed_tasks", 0),
                failed_tasks=status_dict.get("failed_tasks", 0),
                pending_tasks=status_dict.get("pending_tasks", 0),
                submitted_at=status_dict["submitted_at"],
                started_at=status_dict.get("started_at"),
                completed_at=time.time(),
            )
            await redis_client.set_job_status(job_id, failed_status_data.model_dump())
            logger.info(f"Job {job_id} marked as failed: {error_msg}")

        except Exception as e:
            logger.error(f"Error updating failed job status: {e}")


worker = BatchWorker()


def signal_handler(signum: int, frame: Any) -> None:
    logger.info(f"Received signal {signum}, shutting down...")
    worker.stop()


async def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
