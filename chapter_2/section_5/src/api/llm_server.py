"""LLM API Server - FastAPI application that exposes LLM functionality."""

import time

from fastapi import FastAPI, HTTPException, status
from src.client.llm_client import AnthropicModel, LLMProvider, OpenAIModel  # , GeminiModel
from src.logger import make_logger
from src.model.model import HealthResponse, LLMRequest, LLMResponse
from src.prompt.prompt import make_anthropic_prompt, make_openai_prompt  # , make_gemini_prompt
from src.service import (
    get_anthropic_batch_results,
    get_anthropic_batch_status,
    # get_gemini_batch_results,
    # get_gemini_batch_status,
    get_openai_batch_results,
    get_openai_batch_status,
    submit_anthropic_batch,
    # submit_gemini_batch,
    submit_openai_batch,
)

logger = make_logger(__name__)

app = FastAPI(
    title="LLM API Server",
    description="API server for generating character descriptions using LLM",
    version="1.0.0",
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse()


@app.post("/generate", response_model=LLMResponse, tags=["LLM"])
async def generate_character(request: LLMRequest):
    """
    Generate a character using the specified LLM provider and model.

    This endpoint uses the batch API of each provider for processing.
    """
    start_time = time.time()

    try:
        # if request.provider == LLMProvider.GEMINI and request.model not in GeminiModel.list_str():
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail=f"Invalid model '{request.model}' for provider '{request.provider.value}'",
        #     )
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

        # if request.provider == LLMProvider.GEMINI:
        #     prompt = make_gemini_prompt(character_request=request.character_request)
        #     batch_id = submit_gemini_batch(model=request.model, prompts=[prompt])
        #
        #     while True:
        #         batch_status = get_gemini_batch_status(batch_id)
        #         if batch_status == "JOB_STATE_SUCCEEDED":
        #             break
        #         if batch_status in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"):
        #             raise HTTPException(
        #                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #                 detail=f"Gemini batch job failed with state: {batch_status}",
        #             )
        #         time.sleep(5)
        #
        #     results = get_gemini_batch_results(batch_id)

        if request.provider == LLMProvider.OPENAI:
            prompt = make_openai_prompt(character_request=request.character_request)
            batch_id = submit_openai_batch(model=request.model, prompts=[prompt])

            while True:
                batch_status = get_openai_batch_status(batch_id)
                if batch_status == "completed":
                    break
                if batch_status in ("failed", "expired", "cancelled"):
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"OpenAI batch job failed with status: {batch_status}",
                    )
                time.sleep(5)

            results = get_openai_batch_results(batch_id)

        elif request.provider == LLMProvider.ANTHROPIC:
            prompt = make_anthropic_prompt(character_request=request.character_request)
            batch_id = submit_anthropic_batch(model=request.model, prompts=[prompt])

            while True:
                batch_status = get_anthropic_batch_status(batch_id)
                if batch_status == "ended":
                    break
                time.sleep(5)

            results = get_anthropic_batch_results(batch_id)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported LLM provider: {request.provider.value}",
            )

        if not results or results[0] is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate character from batch API",
            )
        character = results[0]

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
