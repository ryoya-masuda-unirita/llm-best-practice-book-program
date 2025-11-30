"""LLM API Server - FastAPI application that exposes LLM functionality."""

import time

from fastapi import FastAPI, HTTPException, status

from src.client.llm_client import GeminiModel, LLMProvider
from src.logger import make_logger
from src.model.model import HealthResponse, LLMRequest, LLMResponse
from src.prompt.prompt import make_prompt
from src.service import get_gemini_batch_results, get_gemini_batch_status, submit_gemini_batch

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
    """
    Generate a character using the specified LLM provider and model.

    This endpoint accepts requests to generate character descriptions using
    Gemini models.
    """
    start_time = time.time()

    try:
        # Validate model for provider
        if request.provider == LLMProvider.GEMINI and request.model not in GeminiModel.list_str():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
            )

        prompt = make_prompt(character_request=request.character_request)

        # Generate character using batch API
        if request.provider == LLMProvider.GEMINI:
            # Extract system and user prompts for batch API
            system_prompt = prompt[0]["content"]
            user_prompt = prompt[-1]["content"]

            # Submit batch job
            batch_job_name = submit_gemini_batch(model=request.model, prompts=[(system_prompt, user_prompt)])

            # Poll for completion
            while True:
                batch_status = get_gemini_batch_status(batch_job_name)
                if batch_status == "JOB_STATE_SUCCEEDED":
                    break
                if batch_status in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Batch job failed with state: {batch_status}",
                    )
                time.sleep(5)

            # Get results
            results = get_gemini_batch_results(batch_job_name)
            if not results or results[0] is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate character from batch API",
                )
            character = results[0]
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
