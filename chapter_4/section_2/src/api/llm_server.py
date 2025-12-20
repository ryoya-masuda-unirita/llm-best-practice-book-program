"""LLM API Server - FastAPI application that exposes LLM functionality."""

import time

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from src.client.llm_client import GeminiModel
from src.logger import make_logger
from src.model.knowledge import KnowledgeRegisterCommand
from src.model.model import HealthResponse, LLMRequest, LLMResponse
from src.prompt.prompt import make_prompt
from src.service import request_gemini
from src.service.knowledge_command import register_knowledge_async

logger = make_logger(__name__)

app = FastAPI(
    title="LLM API Server",
    description="API server for generating character descriptions using Gemini LLM",
    version="1.0.0",
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/generate", response_model=LLMResponse, tags=["LLM"])
async def generate_character(request: LLMRequest, background_tasks: BackgroundTasks, store_knowledge: bool = True):
    """Generate a character using Gemini LLM."""
    start_time = time.time()

    try:
        if request.model not in GeminiModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}'. Valid models: {GeminiModel.list_str()}",
            )

        prompt = make_prompt(character_request=request.character_request)
        character = await request_gemini(model=request.model, prompt=prompt)

        processing_time = (time.time() - start_time) * 1000

        logger.info(f"Successfully generated character using gemini/{request.model} in {processing_time:.2f}ms")

        if store_knowledge:
            knowledge_command = KnowledgeRegisterCommand(
                character_request=request.character_request,
                character_response=character,
                model=request.model,
                prompt=prompt,
                processing_time_ms=processing_time,
            )

            background_tasks.add_task(register_knowledge_async, knowledge_command)
            logger.info("Queued knowledge registration for background processing")

        return LLMResponse(
            character=character,
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
