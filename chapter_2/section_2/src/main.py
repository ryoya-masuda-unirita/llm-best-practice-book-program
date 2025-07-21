import asyncio
import time
from functools import wraps
from uuid import uuid4

import click
from google.genai.types import GenerateContentConfig

from src.llms import google_genai_client, openai_client
from src.logger import make_logger, llm_logger
from src.model import CharacterResponse, LLMProvider
from src.prompt import make_prompt

logger = make_logger(__name__)


async def request_openai(user_id: str) -> tuple[CharacterResponse, str]:
    prompt = make_prompt()
    
    start_time = time.time()
    try:
        result = await openai_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=prompt,
            response_format=CharacterResponse,
            temperature=1.0,
        )
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        parsed_result = result.choices[0].message.parsed
        input_text = str(prompt)
        output_text = str(parsed_result.model_dump())
        
        prompt_id = await llm_logger.log_llm_request(
            model="gpt-4o-mini",
            user_id=user_id,
            provider=LLMProvider.OPENAI,
            input_text=input_text,
            output_text=output_text,
            temperature=1.0,
            latency_ms=latency_ms,
            status_code=200,
            metadata={"usage": result.usage.model_dump() if result.usage else None}
        )
        
        return parsed_result, prompt_id
        
    except Exception as e:
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        await llm_logger.log_llm_request(
            model="gpt-4o-mini",
            provider=LLMProvider.OPENAI,
            input_text=str(prompt),
            output_text=f"Error: {str(e)}",
            temperature=1.0,
            latency_ms=latency_ms,
            status_code=500,
            user_id=user_id,
            metadata={"error": str(e)}
        )
        raise


async def request_gemini(user_id: str) -> tuple[CharacterResponse, str]:
    prompt = make_prompt()
    
    start_time = time.time()
    try:
        result = await google_genai_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=CharacterResponse,
                temperature=2.0,
            ),
        )
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        input_text = str(prompt)
        output_text = str(result.parsed.model_dump())
        
        prompt_id = await llm_logger.log_llm_request(
            model="gemini-2.5-flash",
            provider=LLMProvider.GEMINI,
            user_id=user_id,
            input_text=input_text,
            output_text=output_text,
            temperature=2.0,
            latency_ms=latency_ms,
            status_code=200,
            metadata={"usage_metadata": result.usage_metadata.model_dump() if result.usage_metadata else None}
        )
        
        return result.parsed, prompt_id
        
    except Exception as e:
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        await llm_logger.log_llm_request(
            model="gemini-2.5-flash",
            provider=LLMProvider.GEMINI,
            input_text=str(prompt),
            output_text=f"Error: {str(e)}",
            temperature=2.0,
            latency_ms=latency_ms,
            status_code=500,
            user_id=user_id,
            metadata={"error": str(e)}
        )
        raise


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--llm-provider",
    "-lp",
    type=click.Choice(LLMProvider),
    default=LLMProvider.GEMINI,
    help="The LLM provider to use.",
)
@click.option(
    "--user-id",
    "-u",
    type=str,
    default=None,
    help="User ID for logging purposes.",
)
@async_cmd
async def main(
    llm_provider: LLMProvider = LLMProvider.GEMINI,
    user_id: str = None,
):
    logger.info(f"LLM provider: {llm_provider.value}")

    if llm_provider == LLMProvider.OPENAI:
        result, prompt_id = await request_openai(user_id=user_id)
    elif llm_provider == LLMProvider.GEMINI:
        result, prompt_id = await request_gemini(user_id=user_id)
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider.value}")

    output_filename = f"outputs/{llm_provider.value}_{uuid4().hex}.json"
    result.save_as_json(output_filename)
    
    logger.info(f"Result saved to: {output_filename}")
    logger.info(f"Structured log prompt_id: {prompt_id}")
    logger.info("Check ./logs/ and ./prompt_storage/ directories for structured logs")


if __name__ == "__main__":
    main()
