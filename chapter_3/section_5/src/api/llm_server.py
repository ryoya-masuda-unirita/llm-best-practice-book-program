import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, status

from src.client.llm_client import LLMProvider, OpenAIModel
from src.logger import make_logger
from src.model.model import (
    HealthResponse,
    LLMRequest,
    LLMResponse,
    QueuedTask,
    QueueStatsResponse,
    TaskStatus,
    TaskStatusResponse,
    TaskSubmissionResponse,
)
from src.prompt.prompt import make_prompt
from src.service import request_openai
from src.service.queue_manager import queue_manager

logger = make_logger(__name__)

ESTIMATED_SECONDS_PER_TASK = 5.0


def validate_request(request: LLMRequest) -> None:
    if request.provider != LLMProvider.OPENAI:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider '{request.provider.value}'. Only 'openai' is supported.",
        )
    if request.model not in OpenAIModel.list_str():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
        )


def build_task_status_response(task: QueuedTask, queue_position: Optional[int]) -> TaskStatusResponse:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await queue_manager.connect()
    logger.info("API server started")
    yield
    await queue_manager.disconnect()
    logger.info("API server shutdown")


app = FastAPI(
    title="LLM API Server with Priority Queuing",
    description="API server for generating character descriptions using LLM with request prioritization",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse()


@app.post("/generate/queue", response_model=TaskSubmissionResponse, tags=["Queue"])
async def queue_generate_character(request: LLMRequest):
    validate_request(request)

    priority = queue_manager.get_priority_for_user_tier(request.user_tier)

    task = await queue_manager.enqueue_task(
        QueuedTask(
            priority=priority,
            user_tier=request.user_tier,
            provider=request.provider.value,
            model=request.model,
            character_request=request.character_request,
        )
    )

    queue_position = await queue_manager.get_queue_position(task.task_id)
    estimated_wait = queue_position * ESTIMATED_SECONDS_PER_TASK if queue_position is not None else None

    logger.info(f"Queued task {task.task_id} with {priority.value} priority (position: {queue_position})")

    return TaskSubmissionResponse(
        task_id=task.task_id,
        priority=priority,
        status=TaskStatus.PENDING,
        estimated_wait_time_seconds=estimated_wait,
        message=f"Task queued with {priority.value} priority. Use /task/{{task_id}} to check status.",
    )


@app.get("/task/{task_id}", response_model=TaskStatusResponse, tags=["Queue"])
async def get_task_status(task_id: str):
    task = await queue_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")

    queue_position = await queue_manager.get_queue_position(task_id) if task.status == TaskStatus.PENDING else None

    return build_task_status_response(task, queue_position)


@app.get("/queue/stats", response_model=QueueStatsResponse, tags=["Queue"])
async def get_queue_stats():
    queue_sizes = await queue_manager.get_all_queue_sizes()

    return QueueStatsResponse(
        high_priority_count=queue_sizes.get("high", 0),
        medium_priority_count=queue_sizes.get("medium", 0),
        low_priority_count=queue_sizes.get("low", 0),
        total_pending=sum(queue_sizes.values()),
        processing_count=await queue_manager.get_processing_count(),
    )


@app.post("/generate", response_model=LLMResponse, tags=["LLM"])
async def generate_character(request: LLMRequest):
    validate_request(request)

    start_time = time.time()
    prompt = make_prompt(character_request=request.character_request)
    character = await request_openai(model=request.model, prompt=prompt)
    processing_time_ms = (time.time() - start_time) * 1000

    logger.info(f"Generated character using {request.provider.value}/{request.model} in {processing_time_ms:.2f}ms")

    return LLMResponse(
        character=character,
        provider=request.provider.value,
        model=request.model,
        processing_time_ms=processing_time_ms,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
