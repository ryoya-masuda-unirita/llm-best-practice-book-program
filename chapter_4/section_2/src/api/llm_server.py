import time

from fastapi import FastAPI, HTTPException, status
from src.logger import make_logger
from src.model.model import (
    HealthResponse,
    LLMRequest,
    LLMResponse,
    TextClassificationRequest,
    TextClassificationResponse,
)
from src.service.container import service_container

logger = make_logger(__name__)

app = FastAPI(
    title="LLM API Server",
    description="API server for LLM operations with segregated service interfaces",
    version="2.0.0",
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/generate", response_model=LLMResponse, tags=["Text Generation"])
async def generate_character(request: LLMRequest):
    """
    Generate a character using Anthropic Claude.

    Model availability depends on user plan:
    - Free plan: claude-sonnet-4-6
    - Standard plan: All models (claude-sonnet-4-6, claude-haiku-4-5)
    """
    start_time = time.time()

    try:
        service = service_container.get_text_generation_service()

        character = await service.generate_character(
            gender=request.character_request.gender,
            age=request.character_request.age,
            additional_instructions=request.character_request.additional_instructions,
            model=request.model,
            user_plan=request.user_plan,
        )

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"Successfully generated character using {request.model} "
            f"for {request.user_plan.value} plan in {processing_time:.2f}ms"
        )

        return LLMResponse(
            character=character,
            model=request.model,
            processing_time_ms=processing_time,
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating character: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating character: {str(e)}",
        )


@app.post("/classify", response_model=TextClassificationResponse, tags=["Text Classification"])
async def classify_text(request: TextClassificationRequest):
    """
    Classify text into one of the provided categories using Anthropic Claude.

    Model availability depends on user plan:
    - Free plan: claude-sonnet-4-6
    - Standard plan: All models (claude-sonnet-4-6, claude-haiku-4-5)
    """
    start_time = time.time()

    try:
        service = service_container.get_text_classification_service()

        classification_result = await service.classify(
            text=request.text,
            categories=request.categories,
            model=request.model,
            user_plan=request.user_plan,
        )

        processing_time = (time.time() - start_time) * 1000

        logger.info(
            f"Successfully classified text using {request.model} "
            f"for {request.user_plan.value} plan in {processing_time:.2f}ms. "
            f"Result: {classification_result.category}"
        )

        return TextClassificationResponse(
            category=classification_result.category,
            model=request.model,
            processing_time_ms=processing_time,
            classification_result=classification_result,
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error classifying text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error classifying text: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
