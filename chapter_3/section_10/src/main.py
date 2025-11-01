import asyncio
import os
from functools import wraps
from uuid import uuid4

import click

from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel
from src.logger import make_logger
from src.service import request_gemini_outfit, request_openai_outfit

logger = make_logger(__name__)


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
    required=True,
    default=LLMProvider.GEMINI,
    help="The LLM provider to use.",
)
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str() + GeminiModel.list_str()),
    required=True,
    help="The model to use for the request.",
)
@click.option(
    "--latitude",
    "-lat",
    type=float,
    required=True,
    help="緯度 (例: 39.7456 for Kansas, USA)",
)
@click.option(
    "--longitude",
    "-lon",
    type=float,
    required=True,
    help="経度 (例: -97.0892 for Kansas, USA)",
)
@click.option(
    "--output-directory",
    "-od",
    type=click.Path(),
    required=False,
    default="outputs",
    help="The directory to save output files.",
)
@async_cmd
async def main(
    llm_provider: LLMProvider,
    model: str,
    latitude: float,
    longitude: float,
    output_directory: str = "outputs",
):
    """天気予報に基づいて服装を提案します

    Example:
        python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.7456 -lon -97.0892
    """
    logger.info(f"""LLM provider: {llm_provider.value}
Model: {model}
Latitude: {latitude}
Longitude: {longitude}
Output directory: {output_directory}""")

    if llm_provider == LLMProvider.OPENAI and model not in OpenAIModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")
    if llm_provider == LLMProvider.GEMINI and model not in GeminiModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")

    os.makedirs(output_directory, exist_ok=True)

    try:
        if llm_provider == LLMProvider.OPENAI:
            result = await request_openai_outfit(model=model, latitude=latitude, longitude=longitude)
        elif llm_provider == LLMProvider.GEMINI:
            result = await request_gemini_outfit(model=model, latitude=latitude, longitude=longitude)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider.value}")
    except ValueError as e:
        logger.error(f"\n❌ エラー: {e}")
        raise click.ClickException(str(e))

    file_name = f"outfit_{llm_provider.value}_{uuid4().hex}.json"
    file_path = os.path.join(output_directory, file_name)
    result.save_as_json(file_path)
    logger.info(f"""File saved to {file_path}""")

    # 結果を表示
    logger.info(f"""
=== 服装提案 ===
場所: {result.location}
天気概要: {result.weather_summary}

現在の天気:
  期間: {result.current_weather.period_name}
  気温: {result.current_weather.temperature}°{result.current_weather.temperature_unit}
  風: {result.current_weather.wind_speed} {result.current_weather.wind_direction}
  予報: {result.current_weather.forecast_summary}

推奨服装:
""")
    for i, rec in enumerate(result.outfit_recommendations, 1):
        logger.info(f"""  {i}. {rec.clothing_type}: {rec.item_suggestion}
     理由: {rec.reason}""")

    logger.info(f"""
追加アドバイス: {result.additional_advice}
""")


if __name__ == "__main__":
    main()
