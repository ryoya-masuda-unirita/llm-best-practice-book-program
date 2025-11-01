import json
from datetime import datetime
from pathlib import Path
from typing import Any

from google import genai
from openai import AsyncOpenAI, OpenAI

from src.config import config


class ChatCompletionsWrapper:
    """Wrapper for OpenAI chat.completions to add logging."""

    def __init__(self, chat_completions, log_dir: str = config.usage_log_directory):
        self._chat_completions = chat_completions
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    def create(self, *args, **kwargs):
        """Wrap create method to log request and response."""
        start_time = datetime.now()

        # Call the original method
        response = self._chat_completions.create(*args, **kwargs)

        # Log the request and response
        self._log_usage(
            method="chat.completions.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )

        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        """Log usage information to JSON file."""
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "temperature": kwargs.get("temperature"),
                "max_tokens": kwargs.get("max_tokens"),
                "top_p": kwargs.get("top_p"),
                "stream": kwargs.get("stream"),
                "parameters": {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["model", "messages", "temperature", "max_tokens", "top_p", "stream"]
                },
            },
            "response": {
                "id": getattr(response, "id", None),
                "model": getattr(response, "model", None),
                "choices": [
                    {
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content,
                        },
                        "finish_reason": choice.finish_reason,
                        "index": choice.index,
                    }
                    for choice in getattr(response, "choices", [])
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens
                    if hasattr(response, "usage") and response.usage
                    else None,
                    "completion_tokens": response.usage.completion_tokens
                    if hasattr(response, "usage") and response.usage
                    else None,
                    "total_tokens": response.usage.total_tokens
                    if hasattr(response, "usage") and response.usage
                    else None,
                },
            },
        }

        # Write to log file
        log_filename = self._log_dir / f"openai_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        """Delegate other attributes to the original object."""
        return getattr(self._chat_completions, name)


class AsyncChatCompletionsWrapper:
    """Wrapper for AsyncOpenAI chat.completions to add logging."""

    def __init__(self, chat_completions, log_dir: str = config.usage_log_directory):
        self._chat_completions = chat_completions
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    async def create(self, *args, **kwargs):
        """Wrap create method to log request and response."""
        start_time = datetime.now()

        # Call the original method
        response = await self._chat_completions.create(*args, **kwargs)

        # Log the request and response
        self._log_usage(
            method="chat.completions.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )

        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        """Log usage information to JSON file."""
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "temperature": kwargs.get("temperature"),
                "max_tokens": kwargs.get("max_tokens"),
                "top_p": kwargs.get("top_p"),
                "stream": kwargs.get("stream"),
                "parameters": {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["model", "messages", "temperature", "max_tokens", "top_p", "stream"]
                },
            },
            "response": {
                "id": getattr(response, "id", None),
                "model": getattr(response, "model", None),
                "choices": [
                    {
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content,
                        },
                        "finish_reason": choice.finish_reason,
                        "index": choice.index,
                    }
                    for choice in getattr(response, "choices", [])
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens
                    if hasattr(response, "usage") and response.usage
                    else None,
                    "completion_tokens": response.usage.completion_tokens
                    if hasattr(response, "usage") and response.usage
                    else None,
                    "total_tokens": response.usage.total_tokens
                    if hasattr(response, "usage") and response.usage
                    else None,
                },
            },
        }

        # Write to log file
        log_filename = self._log_dir / f"async_openai_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        """Delegate other attributes to the original object."""
        return getattr(self._chat_completions, name)


class ResponsesWrapper:
    """Wrapper for OpenAI responses to add logging."""

    def __init__(self, responses, log_dir: str = config.usage_log_directory):
        self._responses = responses
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    def create(self, *args, **kwargs):
        """Wrap create method to log request and response."""
        start_time = datetime.now()

        # Call the original method
        response = self._responses.create(*args, **kwargs)

        # Log the request and response
        self._log_usage(
            method="responses.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )

        return response

    def parse(self, *args, **kwargs):
        """Wrap parse method to log request and response."""
        start_time = datetime.now()

        # Call the original method
        response = self._responses.parse(*args, **kwargs)

        # Log the request and response
        self._log_usage(
            method="responses.parse",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )

        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        """Log usage information to JSON file."""
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Extract usage information - handle both CompletionUsage and ResponseUsage
        usage_info = {}
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            # ResponseUsage uses input_tokens, output_tokens, total_tokens
            # CompletionUsage uses prompt_tokens, completion_tokens, total_tokens
            usage_info = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": kwargs.get("model"),
                "input": kwargs.get("input"),
                "tools": kwargs.get("tools"),
                "previous_response_id": kwargs.get("previous_response_id"),
                "stream": kwargs.get("stream"),
                "prompt": kwargs.get("prompt"),
                "text_format": str(kwargs.get("text_format")) if kwargs.get("text_format") else None,
                "parameters": {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["model", "input", "tools", "previous_response_id", "stream", "prompt", "text_format"]
                },
            },
            "response": {
                "id": getattr(response, "id", None),
                "model": getattr(response, "model", None),
                "output_text": getattr(response, "output_text", None),
                "output_parsed": str(getattr(response, "output_parsed", None)),
                "usage": usage_info,
            },
        }

        # Write to log file
        log_filename = self._log_dir / f"openai_responses_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        """Delegate other attributes to the original object."""
        return getattr(self._responses, name)


class AsyncResponsesWrapper:
    """Wrapper for AsyncOpenAI responses to add logging."""

    def __init__(self, responses, log_dir: str = config.usage_log_directory):
        self._responses = responses
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    async def create(self, *args, **kwargs):
        """Wrap create method to log request and response."""
        start_time = datetime.now()

        # Call the original method
        response = await self._responses.create(*args, **kwargs)

        # Log the request and response
        self._log_usage(
            method="responses.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )

        return response

    async def parse(self, *args, **kwargs):
        """Wrap parse method to log request and response."""
        start_time = datetime.now()

        # Call the original method
        response = await self._responses.parse(*args, **kwargs)

        # Log the request and response
        self._log_usage(
            method="responses.parse",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )

        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        """Log usage information to JSON file."""
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Extract usage information - handle both CompletionUsage and ResponseUsage
        usage_info = {}
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            # ResponseUsage uses input_tokens, output_tokens, total_tokens
            # CompletionUsage uses prompt_tokens, completion_tokens, total_tokens
            usage_info = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": kwargs.get("model"),
                "input": kwargs.get("input"),
                "tools": kwargs.get("tools"),
                "previous_response_id": kwargs.get("previous_response_id"),
                "stream": kwargs.get("stream"),
                "prompt": kwargs.get("prompt"),
                "text_format": str(kwargs.get("text_format")) if kwargs.get("text_format") else None,
                "parameters": {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["model", "input", "tools", "previous_response_id", "stream", "prompt", "text_format"]
                },
            },
            "response": {
                "id": getattr(response, "id", None),
                "model": getattr(response, "model", None),
                "output_text": getattr(response, "output_text", None),
                "output_parsed": str(getattr(response, "output_parsed", None)),
                "usage": usage_info,
            },
        }

        # Write to log file
        log_filename = self._log_dir / f"async_openai_responses_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        """Delegate other attributes to the original object."""
        return getattr(self._responses, name)


class ChatWrapper:
    """Wrapper for chat object to inject completions wrapper."""

    def __init__(self, chat, log_dir: str = config.usage_log_directory, is_async: bool = False):
        self._chat = chat
        self._log_dir = log_dir
        self._is_async = is_async
        self._completions = None

    @property
    def completions(self):
        """Wrap completions with logging."""
        if self._completions is None:
            if self._is_async:
                self._completions = AsyncChatCompletionsWrapper(self._chat.completions, self._log_dir)
            else:
                self._completions = ChatCompletionsWrapper(self._chat.completions, self._log_dir)
        return self._completions

    def __getattr__(self, name):
        """Delegate other attributes to the original object."""
        return getattr(self._chat, name)


class OpenAIWrapperClient(OpenAI):
    """Thin wrapper for OpenAI client with usage logging."""

    def __init__(self, *args, log_dir: str = config.usage_log_directory, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_dir = log_dir
        self._chat_wrapper = None
        self._responses_wrapper = None

    @property
    def chat(self):
        """Wrap chat object to add logging."""
        if self._chat_wrapper is None:
            self._chat_wrapper = ChatWrapper(super().chat, self._log_dir, is_async=False)
        return self._chat_wrapper

    @property
    def responses(self):
        """Wrap responses object to add logging."""
        if self._responses_wrapper is None:
            self._responses_wrapper = ResponsesWrapper(super().responses, self._log_dir)
        return self._responses_wrapper

    def __getattr__(self, name):
        """Delegate other attributes to the parent class."""
        return super().__getattribute__(name)


class AsyncOpenAIWrapperClient(AsyncOpenAI):
    """Thin wrapper for AsyncOpenAI client with usage logging."""

    def __init__(self, *args, log_dir: str = config.usage_log_directory, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_dir = log_dir
        self._chat_wrapper = None
        self._responses_wrapper = None

    @property
    def chat(self):
        """Wrap chat object to add logging."""
        if self._chat_wrapper is None:
            self._chat_wrapper = ChatWrapper(super().chat, self._log_dir, is_async=True)
        return self._chat_wrapper

    @property
    def responses(self):
        """Wrap responses object to add logging."""
        if self._responses_wrapper is None:
            self._responses_wrapper = AsyncResponsesWrapper(super().responses, self._log_dir)
        return self._responses_wrapper

    def __getattr__(self, name):
        """Delegate other attributes to the parent class."""
        return super().__getattribute__(name)


class ModelsWrapper:
    """Wrapper for genai models to add logging."""

    def __init__(self, models, log_dir: str = config.usage_log_directory):
        self._models = models
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    def generate_content(self, *args, **kwargs):
        """Wrap generate_content method to log request and response."""
        start_time = datetime.now()

        # Call the original method
        response = self._models.generate_content(*args, **kwargs)

        # Log the request and response
        self._log_usage(
            method="models.generate_content",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )

        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        """Log usage information to JSON file."""
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Extract model from args or kwargs
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

        # Write to log file
        log_filename = self._log_dir / f"genai_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        """Delegate other attributes to the original object."""
        return getattr(self._models, name)


class AsyncModelsWrapper:
    """Wrapper for genai async models to add logging."""

    def __init__(self, models, log_dir: str = config.usage_log_directory):
        self._models = models
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    async def generate_content(self, *args, **kwargs):
        """Wrap async generate_content method to log request and response."""
        start_time = datetime.now()

        # Call the original method
        response = await self._models.generate_content(*args, **kwargs)

        # Log the request and response
        self._log_usage(
            method="aio.models.generate_content",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )

        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        """Log usage information to JSON file."""
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Extract model from args or kwargs
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

        # Write to log file
        log_filename = self._log_dir / f"async_genai_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        """Delegate other attributes to the original object."""
        return getattr(self._models, name)


class AioWrapper:
    """Wrapper for genai aio object to inject async models wrapper."""

    def __init__(self, aio, log_dir: str = config.usage_log_directory):
        self._aio = aio
        self._log_dir = log_dir
        self._models = None

    @property
    def models(self):
        """Wrap models with logging."""
        if self._models is None:
            self._models = AsyncModelsWrapper(self._aio.models, self._log_dir)
        return self._models

    def __getattr__(self, name):
        """Delegate other attributes to the original object."""
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
        """Wrap models object to add logging."""
        if self._models_wrapper is None:
            self._models_wrapper = ModelsWrapper(super().models, self._log_dir)
        return self._models_wrapper

    @property
    def aio(self):
        """Wrap aio object to add logging for async methods."""
        if self._aio_wrapper is None:
            self._aio_wrapper = AioWrapper(super().aio, self._log_dir)
        return self._aio_wrapper

    def __getattr__(self, name):
        """Delegate other attributes to the parent class."""
        return super().__getattribute__(name)
