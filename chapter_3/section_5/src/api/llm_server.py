"""LLM API Server - FastAPI application that exposes LLM functionality."""

import time

from fastapi import FastAPI, HTTPException, status
from src.client.llm_client import AnthropicModel, LLMProvider, OpenAIModel
from src.logger import make_logger
from src.model.model import HealthResponse, LLMRequest, LLMResponse
from src.prompt.prompt import make_prompt
from src.service import request_anthropic, request_openai

logger = make_logger(__name__)

app = FastAPI(
    title="LLM API Server",
    description="API server for generating character descriptions using LLM",
    version="1.0.0",
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/generate", response_model=LLMResponse, tags=["LLM"])
async def generate_character(request: LLMRequest):
    """Generate a character using the specified LLM provider and model."""
    start_time = time.time()

    try:
        if request.provider == LLMProvider.OPENAI and request.model not in OpenAIModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
            )
        if request.provider == LLMProvider.ANTHROPIC and request.model not in AnthropicModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
            )

        prompt = make_prompt(character_request=request.character_request)

        if request.provider == LLMProvider.OPENAI:
            character = await request_openai(model=request.model, prompt=prompt)
        elif request.provider == LLMProvider.ANTHROPIC:
            character = await request_anthropic(model=request.model, prompt=prompt)
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
