"""LLM API Server - FastAPI application that exposes LLM functionality with priority queue support."""

import time

from fastapi import FastAPI, HTTPException, status

from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel
from src.logger import make_logger
from src.model.model import (
    HealthResponse,
    LLMRequest,
    LLMResponse,
    Priority,
    QueuedTask,
    QueueStatsResponse,
    TaskStatus,
    TaskStatusResponse,
    TaskSubmissionResponse,
    UserTier,
)
from src.prompt.prompt import make_prompt
from src.service import request_gemini, request_openai
from src.service.queue_manager import queue_manager

logger = make_logger(__name__)

app = FastAPI(
    title="LLM API Server with Priority Queuing",
    description="API server for generating character descriptions using LLM with request prioritization",
    version="2.0.0",
)


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    await queue_manager.connect()
    logger.info("API server started and connected to queue manager")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown."""
    await queue_manager.disconnect()
    logger.info("API server shutdown and disconnected from queue manager")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/generate/queue", response_model=TaskSubmissionResponse, tags=["LLM Queue"])
async def queue_generate_character(request: LLMRequest):
    """
    Queue a character generation request with priority based on user tier.

    This endpoint accepts requests and adds them to a priority queue for asynchronous processing.
    The priority is determined by the user's tier:
    - ENTERPRISE users: High priority (70% of processing capacity)
    - PREMIUM users: Medium priority (20% of processing capacity)
    - FREE users: Low priority (10% of processing capacity)

    Returns a task ID that can be used to check the status and retrieve results.
    """
    try:
        # Validate model for provider
        if request.provider == LLMProvider.OPENAI and request.model not in OpenAIModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
            )
        if request.provider == LLMProvider.GEMINI and request.model not in GeminiModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
            )

        # Map user tier to priority
        priority_map = {
            UserTier.ENTERPRISE: Priority.HIGH,
            UserTier.PREMIUM: Priority.MEDIUM,
            UserTier.FREE: Priority.LOW,
        }
        priority = priority_map.get(request.user_tier, Priority.LOW)

        # Create queued task
        task = QueuedTask(
            priority=priority,
            user_tier=request.user_tier,
            provider=request.provider.value,
            model=request.model,
            character_request=request.character_request,
        )

        # Enqueue the task
        task = await queue_manager.enqueue_task(task)

        # Get queue statistics for estimated wait time
        queue_position = await queue_manager.get_queue_position(task.task_id)
        queue_sizes = await queue_manager.get_all_queue_sizes()

        # Simple estimation: assume 5 seconds per task on average
        estimated_wait = None
        if queue_position is not None:
            estimated_wait = queue_position * 5.0

        logger.info(
            f"Queued task {task.task_id} for {request.user_tier.value} user "
            f"with {priority.value} priority (position: {queue_position}) out of {queue_sizes}"
        )

        return TaskSubmissionResponse(
            task_id=task.task_id,
            priority=priority,
            status=TaskStatus.PENDING,
            estimated_wait_time_seconds=estimated_wait,
            message=f"Task queued successfully with {priority.value} priority. Use /task/{{task_id}} to check status.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error queuing task: {str(e)}",
        )


@app.get("/task/{task_id}", response_model=TaskStatusResponse, tags=["LLM Queue"])
async def get_task_status(task_id: str):
    """
    Get the status of a queued task.

    Returns the current status, position in queue (if pending), or results (if completed).
    """
    try:
        task = await queue_manager.get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        # Get queue position if still pending
        queue_position = None
        if task.status == TaskStatus.PENDING:
            queue_position = await queue_manager.get_queue_position(task_id)

        # Convert result to LLMResponse if completed
        result = None
        if task.status == TaskStatus.COMPLETED and task.result:
            result = LLMResponse(
                character=task.result["character"],
                provider=task.result["provider"],
                model=task.result["model"],
                processing_time_ms=task.result["processing_time_ms"],
            )

        return TaskStatusResponse(
            task_id=task.task_id,
            priority=task.priority,
            status=task.status,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            result=result,
            error_message=task.error_message,
            queue_position=queue_position,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting task status: {str(e)}",
        )


@app.get("/queue/stats", response_model=QueueStatsResponse, tags=["LLM Queue"])
async def get_queue_stats():
    """
    Get statistics about all priority queues.

    Returns the number of pending tasks in each priority queue and currently processing tasks.
    """
    try:
        queue_sizes = await queue_manager.get_all_queue_sizes()
        processing_count = await queue_manager.get_processing_count()

        return QueueStatsResponse(
            high_priority_count=queue_sizes.get("high", 0),
            medium_priority_count=queue_sizes.get("medium", 0),
            low_priority_count=queue_sizes.get("low", 0),
            total_pending=sum(queue_sizes.values()),
            processing_count=processing_count,
        )

    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting queue stats: {str(e)}",
        )


@app.post("/generate", response_model=LLMResponse, tags=["LLM"])
async def generate_character(request: LLMRequest):
    """
    Generate a character using the specified LLM provider and model.

    This endpoint accepts requests to generate character descriptions using
    either OpenAI or Gemini models.
    """
    start_time = time.time()

    try:
        # Validate model for provider
        if request.provider == LLMProvider.OPENAI and request.model not in OpenAIModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
            )
        if request.provider == LLMProvider.GEMINI and request.model not in GeminiModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
            )

        prompt = make_prompt(character_request=request.character_request)

        # Generate character
        if request.provider == LLMProvider.OPENAI:
            character = await request_openai(model=request.model, prompt=prompt)
        elif request.provider == LLMProvider.GEMINI:
            character = await request_gemini(model=request.model, prompt=prompt)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported LLM provider: {request.provider.value}",
            )

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"Successfully generated character using {request.provider.value}/{request.model} "
            f"in {processing_time:.2f}ms"
        )

        return LLMResponse(
            character=character,
            provider=request.provider.value,
            model=request.model,
            processing_time_ms=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating character: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating character: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
