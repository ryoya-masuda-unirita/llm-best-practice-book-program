"""Batch API Server - FastAPI application for asynchronous batch processing."""

import time
import uuid

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from src.client.llm_client import GeminiModel, LLMProvider
from src.client.redis_client import redis_client
from src.logger import make_logger
from src.model.batch_model import (
    BatchJobRequest,
    BatchJobResponse,
    BatchJobResultResponse,
    BatchJobStatusResponse,
    InternalJobData,
    JobStatus,
)
from src.model.model import HealthResponse

logger = make_logger(__name__)

app = FastAPI(
    title="LLM Batch API Server",
    description="API server for asynchronous batch processing of LLM character generation",
    version="1.0.0",
)

QUEUE_NAME = "llm_batch_jobs"


class QueueStatsResponse(BaseModel):
    """Response model for queue statistics."""

    queue_name: str = Field(..., description="Name of the queue")
    pending_jobs: int = Field(..., description="Number of pending jobs in the queue")


class JobListResponse(BaseModel):
    """Response model for job ID listing."""

    job_ids: list[str] = Field(..., description="List of job IDs")
    count: int = Field(..., description="Total number of jobs")


def raise_not_found(job_id: str) -> None:
    """Raise HTTP 404 for job not found."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Job {job_id} not found",
    )


def raise_internal_error(message: str, error: Exception) -> None:
    """Raise HTTP 500 internal server error."""
    logger.error(f"{message}: {error}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"{message}: {str(error)}",
    )


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize Redis connection on startup."""
    await redis_client.connect()
    logger.info("Batch API Server started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Close Redis connection on shutdown."""
    await redis_client.disconnect()
    logger.info("Batch API Server shutdown")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse()


@app.post("/batch/submit", response_model=BatchJobResponse, tags=["Batch"])
async def submit_batch_job(request: BatchJobRequest) -> BatchJobResponse:
    """
    Submit a batch job for processing.

    This endpoint accepts a batch of character generation requests and queues them
    for asynchronous processing by background workers.
    """
    try:
        if request.provider == LLMProvider.GEMINI and request.model not in GeminiModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider}'",
            )

        job_id = str(uuid.uuid4())
        total_tasks = len(request.character_requests)
        submitted_at = time.time()

        job_data = InternalJobData(
            job_id=job_id,
            provider=request.provider,
            model=request.model,
            character_requests=[req.model_dump() for req in request.character_requests],
        )

        status_data = {
            "job_id": job_id,
            "status": JobStatus.PENDING,
            "total_tasks": total_tasks,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "pending_tasks": total_tasks,
            "submitted_at": submitted_at,
            "provider": request.provider,
            "model": request.model,
        }

        await redis_client.set_job_status(job_id, status_data)
        await redis_client.enqueue_job(QUEUE_NAME, job_data.model_dump())

        logger.info(f"Batch job {job_id} submitted with {total_tasks} tasks using {request.provider}/{request.model}")

        return BatchJobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            total_tasks=total_tasks,
            submitted_at=submitted_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise_internal_error("Error submitting batch job", e)


@app.get("/batch/{job_id}/status", response_model=BatchJobStatusResponse, tags=["Batch"])
async def get_batch_job_status(job_id: str) -> BatchJobStatusResponse:
    """
    Get the status of a batch job.

    Returns information about the job's progress including the number of
    completed, failed, and pending tasks.
    """
    try:
        status_data = await redis_client.get_job_status(job_id)
        if not status_data:
            raise_not_found(job_id)

        return BatchJobStatusResponse(**status_data)

    except HTTPException:
        raise
    except Exception as e:
        raise_internal_error("Error retrieving job status", e)


@app.get("/batch/{job_id}/result", response_model=BatchJobResultResponse, tags=["Batch"])
async def get_batch_job_result(job_id: str) -> BatchJobResultResponse:
    """
    Get the results of a completed batch job.

    Returns the generated characters for each task in the batch, along with
    any error information for failed tasks.
    """
    try:
        status_data = await redis_client.get_job_status(job_id)
        if not status_data:
            raise_not_found(job_id)

        result_data = await redis_client.get_job_result(job_id)
        if not result_data:
            if status_data["status"] in [JobStatus.PENDING, JobStatus.PROCESSING]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Job {job_id} is still {status_data['status']}. Results not available yet.",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Results for job {job_id} not found",
            )

        return BatchJobResultResponse(**result_data)

    except HTTPException:
        raise
    except Exception as e:
        raise_internal_error("Error retrieving job results", e)


@app.get("/batch/queue/stats", response_model=QueueStatsResponse, tags=["Batch"])
async def get_queue_stats() -> QueueStatsResponse:
    """Get statistics about the job queue."""
    try:
        queue_length = await redis_client.get_queue_length(QUEUE_NAME)
        return QueueStatsResponse(queue_name=QUEUE_NAME, pending_jobs=queue_length)
    except Exception as e:
        raise_internal_error("Error getting queue stats", e)


@app.get("/batch/jobs", response_model=JobListResponse, tags=["Batch"])
async def list_batch_job_ids() -> JobListResponse:
    """Get a list of all batch job IDs."""
    try:
        job_ids = await redis_client.list_job_ids()
        return JobListResponse(job_ids=job_ids, count=len(job_ids))
    except Exception as e:
        raise_internal_error("Error listing job IDs", e)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
