import json
from datetime import datetime
from pathlib import Path
from typing import Any

from google import genai
from src.config import config


class ModelsWrapper:
    """Wrapper for genai models to add logging."""

    def __init__(self, models, log_dir: str = config.usage_log_directory):
        self._models = models
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    def generate_content(self, *args, **kwargs):
        start_time = datetime.now()
        response = self._models.generate_content(*args, **kwargs)
        self._log_usage(
            method="models.generate_content",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        model = args[0] if len(args) > 0 else kwargs.get("model")
        contents = args[1] if len(args) > 1 else kwargs.get("contents")

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": model,
                "contents": contents,
                "config": str(kwargs.get("config")) if kwargs.get("config") else None,
                "parameters": {k: v for k, v in kwargs.items() if k not in ["model", "contents", "config"]},
            },
            "response": {
                "text": getattr(response, "text", None),
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": part.text} for part in candidate.content.parts]
                            if hasattr(candidate, "content") and hasattr(candidate.content, "parts")
                            else None,
                            "role": candidate.content.role if hasattr(candidate, "content") else None,
                        },
                        "finish_reason": getattr(candidate, "finish_reason", None),
                        "safety_ratings": [
                            {
                                "category": rating.category,
                                "probability": rating.probability,
                            }
                            for rating in getattr(candidate, "safety_ratings", [])
                        ]
                        if hasattr(candidate, "safety_ratings") and getattr(candidate, "safety_ratings")
                        else None,
                    }
                    for candidate in getattr(response, "candidates", [])
                ],
                "usage_metadata": {
                    "prompt_token_count": response.usage_metadata.prompt_token_count
                    if hasattr(response, "usage_metadata")
                    else None,
                    "candidates_token_count": response.usage_metadata.candidates_token_count
                    if hasattr(response, "usage_metadata")
                    else None,
                    "total_token_count": response.usage_metadata.total_token_count
                    if hasattr(response, "usage_metadata")
                    else None,
                },
            },
        }

        log_filename = self._log_dir / f"genai_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        return getattr(self._models, name)


class AsyncModelsWrapper:
    """Wrapper for genai async models to add logging."""

    def __init__(self, models, log_dir: str = config.usage_log_directory):
        self._models = models
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    async def generate_content(self, *args, **kwargs):
        start_time = datetime.now()
        response = await self._models.generate_content(*args, **kwargs)
        self._log_usage(
            method="aio.models.generate_content",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        model = args[0] if len(args) > 0 else kwargs.get("model")
        contents = args[1] if len(args) > 1 else kwargs.get("contents")

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": model,
                "contents": contents,
                "config": str(kwargs.get("config")) if kwargs.get("config") else None,
                "parameters": {k: v for k, v in kwargs.items() if k not in ["model", "contents", "config"]},
            },
            "response": {
                "text": getattr(response, "text", None),
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": part.text} for part in candidate.content.parts]
                            if hasattr(candidate, "content") and hasattr(candidate.content, "parts")
                            else None,
                            "role": candidate.content.role if hasattr(candidate, "content") else None,
                        },
                        "finish_reason": getattr(candidate, "finish_reason", None),
                        "safety_ratings": [
                            {
                                "category": rating.category,
                                "probability": rating.probability,
                            }
                            for rating in getattr(candidate, "safety_ratings", [])
                        ]
                        if hasattr(candidate, "safety_ratings") and getattr(candidate, "safety_ratings")
                        else None,
                    }
                    for candidate in getattr(response, "candidates", [])
                ],
                "usage_metadata": {
                    "prompt_token_count": response.usage_metadata.prompt_token_count
                    if hasattr(response, "usage_metadata")
                    else None,
                    "candidates_token_count": response.usage_metadata.candidates_token_count
                    if hasattr(response, "usage_metadata")
                    else None,
                    "total_token_count": response.usage_metadata.total_token_count
                    if hasattr(response, "usage_metadata")
                    else None,
                },
            },
        }

        log_filename = self._log_dir / f"async_genai_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        return getattr(self._models, name)


class AioWrapper:
    """Wrapper for genai aio object to inject async models wrapper."""

    def __init__(self, aio, log_dir: str = config.usage_log_directory):
        self._aio = aio
        self._log_dir = log_dir
        self._models = None

    @property
    def models(self):
        if self._models is None:
            self._models = AsyncModelsWrapper(self._aio.models, self._log_dir)
        return self._models

    def __getattr__(self, name):
        return getattr(self._aio, name)


class GenAIWrapperClient(genai.Client):
    """Thin wrapper for genai.Client with usage logging."""

    def __init__(self, *args, log_dir: str = config.usage_log_directory, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_dir = log_dir
        self._models_wrapper = None
        self._aio_wrapper = None

    @property
    def models(self):
        if self._models_wrapper is None:
            self._models_wrapper = ModelsWrapper(super().models, self._log_dir)
        return self._models_wrapper

    @property
    def aio(self):
        if self._aio_wrapper is None:
            self._aio_wrapper = AioWrapper(super().aio, self._log_dir)
        return self._aio_wrapper

    def __getattr__(self, name):
        return super().__getattribute__(name)
