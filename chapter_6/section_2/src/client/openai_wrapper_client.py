import json
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI, OpenAI
from src.config import config


class ChatCompletionsWrapper:
    """Wrapper for OpenAI chat.completions to add logging."""

    def __init__(self, chat_completions, log_dir: str = config.usage_log_directory):
        self._chat_completions = chat_completions
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    def create(self, *args, **kwargs):
        start_time = datetime.now()
        response = self._chat_completions.create(*args, **kwargs)
        self._log_usage(
            method="chat.completions.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
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

        log_filename = self._log_dir / f"openai_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        return getattr(self._chat_completions, name)


class AsyncChatCompletionsWrapper:
    """Wrapper for AsyncOpenAI chat.completions to add logging."""

    def __init__(self, chat_completions, log_dir: str = config.usage_log_directory):
        self._chat_completions = chat_completions
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    async def create(self, *args, **kwargs):
        start_time = datetime.now()
        response = await self._chat_completions.create(*args, **kwargs)
        self._log_usage(
            method="chat.completions.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
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

        log_filename = self._log_dir / f"async_openai_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        return getattr(self._chat_completions, name)


class ResponsesWrapper:
    """Wrapper for OpenAI responses to add logging."""

    def __init__(self, responses, log_dir: str = config.usage_log_directory):
        self._responses = responses
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    def create(self, *args, **kwargs):
        start_time = datetime.now()
        response = self._responses.create(*args, **kwargs)
        self._log_usage(
            method="responses.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def parse(self, *args, **kwargs):
        start_time = datetime.now()
        response = self._responses.parse(*args, **kwargs)
        self._log_usage(
            method="responses.parse",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        usage_info = {}
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
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

        log_filename = self._log_dir / f"openai_responses_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        return getattr(self._responses, name)


class AsyncResponsesWrapper:
    """Wrapper for AsyncOpenAI responses to add logging."""

    def __init__(self, responses, log_dir: str = config.usage_log_directory):
        self._responses = responses
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    async def create(self, *args, **kwargs):
        start_time = datetime.now()
        response = await self._responses.create(*args, **kwargs)
        self._log_usage(
            method="responses.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    async def parse(self, *args, **kwargs):
        start_time = datetime.now()
        response = await self._responses.parse(*args, **kwargs)
        self._log_usage(
            method="responses.parse",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        usage_info = {}
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
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

        log_filename = self._log_dir / f"async_openai_responses_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
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
        if self._completions is None:
            if self._is_async:
                self._completions = AsyncChatCompletionsWrapper(self._chat.completions, self._log_dir)
            else:
                self._completions = ChatCompletionsWrapper(self._chat.completions, self._log_dir)
        return self._completions

    def __getattr__(self, name):
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
        if self._chat_wrapper is None:
            self._chat_wrapper = ChatWrapper(super().chat, self._log_dir, is_async=False)
        return self._chat_wrapper

    @property
    def responses(self):
        if self._responses_wrapper is None:
            self._responses_wrapper = ResponsesWrapper(super().responses, self._log_dir)
        return self._responses_wrapper

    def __getattr__(self, name):
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
        if self._chat_wrapper is None:
            self._chat_wrapper = ChatWrapper(super().chat, self._log_dir, is_async=True)
        return self._chat_wrapper

    @property
    def responses(self):
        if self._responses_wrapper is None:
            self._responses_wrapper = AsyncResponsesWrapper(super().responses, self._log_dir)
        return self._responses_wrapper

    def __getattr__(self, name):
        return super().__getattribute__(name)
