"""Batch API Server - FastAPI application for asynchronous batch processing."""

import time
import uuid

from fastapi import FastAPI, HTTPException, status

from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel
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
        # Validate provider and model
        if request.provider == LLMProvider.OPENAI and request.model not in OpenAIModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider}'",
            )
        if request.provider == LLMProvider.GEMINI and request.model not in GeminiModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider}'",
            )

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Convert character requests to dicts for JSON serialization
        character_requests_dicts = [req.model_dump() for req in request.character_requests]

        # Create internal job data
        job_data = InternalJobData(
            job_id=job_id,
            provider=request.provider,
            model=request.model,
            character_requests=character_requests_dicts,
        )

        # Initialize job status in Redis
        status_data = {
            "job_id": job_id,
            "status": JobStatus.PENDING,
            "total_tasks": len(request.character_requests),
            "completed_tasks": 0,
            "failed_tasks": 0,
            "pending_tasks": len(request.character_requests),
            "submitted_at": time.time(),
            "provider": request.provider,
            "model": request.model,
        }
        await redis_client.set_job_status(job_id, status_data)

        # Enqueue job to Redis
        await redis_client.enqueue_job(QUEUE_NAME, job_data.model_dump())

        logger.info(
            f"Batch job {job_id} submitted with {len(request.character_requests)} tasks "
            f"using {request.provider}/{request.model}"
        )

        return BatchJobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            total_tasks=len(request.character_requests),
            submitted_at=status_data["submitted_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting batch job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting batch job: {str(e)}",
        )


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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        return BatchJobStatusResponse(**status_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving job status: {str(e)}",
        )


@app.get("/batch/{job_id}/result", response_model=BatchJobResultResponse, tags=["Batch"])
async def get_batch_job_result(job_id: str) -> BatchJobResultResponse:
    """
    Get the results of a completed batch job.

    Returns the generated characters for each task in the batch, along with
    any error information for failed tasks.
    """
    try:
        # Get job status
        status_data = await redis_client.get_job_status(job_id)
        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        # Get job results
        result_data = await redis_client.get_job_result(job_id)
        if not result_data:
            # Job exists but no results yet
            if status_data["status"] in [JobStatus.PENDING, JobStatus.PROCESSING]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Job {job_id} is still {status_data['status']}. Results not available yet.",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Results for job {job_id} not found",
                )

        return BatchJobResultResponse(**result_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving job results: {str(e)}",
        )


@app.get("/batch/queue/stats", tags=["Batch"])
async def get_queue_stats() -> dict:
    """Get statistics about the job queue."""
    try:
        queue_length = await redis_client.get_queue_length(QUEUE_NAME)
        return {
            "queue_name": QUEUE_NAME,
            "pending_jobs": queue_length,
        }
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting queue stats: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
