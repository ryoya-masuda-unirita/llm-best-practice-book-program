import json
from datetime import datetime
from pathlib import Path
from typing import Any

from anthropic import Anthropic, AsyncAnthropic

from src.config import config


class MessagesWrapper:
    """Wrapper for Anthropic messages to add logging."""

    def __init__(self, messages, log_dir: str = config.usage_log_directory):
        self._messages = messages
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    def create(self, *args, **kwargs):
        start_time = datetime.now()
        response = self._messages.create(*args, **kwargs)
        self._log_usage(
            method="messages.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def count_tokens(self, *args, **kwargs):
        start_time = datetime.now()
        response = self._messages.count_tokens(*args, **kwargs)
        self._log_token_count(
            method="messages.count_tokens",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        content_data = []
        for block in getattr(response, "content", []):
            block_data = {"type": getattr(block, "type", None)}
            if hasattr(block, "text"):
                block_data["text"] = block.text
            if hasattr(block, "name"):
                block_data["name"] = block.name
            if hasattr(block, "input"):
                block_data["input"] = block.input
            if hasattr(block, "id"):
                block_data["id"] = block.id
            content_data.append(block_data)

        usage_info = {}
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            usage_info = {
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
            }

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "system": kwargs.get("system"),
                "max_tokens": kwargs.get("max_tokens"),
                "temperature": kwargs.get("temperature"),
                "top_p": kwargs.get("top_p"),
                "top_k": kwargs.get("top_k"),
                "stop_sequences": kwargs.get("stop_sequences"),
                "stream": kwargs.get("stream"),
                "tools": kwargs.get("tools"),
                "tool_choice": kwargs.get("tool_choice"),
                "parameters": {
                    k: v
                    for k, v in kwargs.items()
                    if k
                    not in [
                        "model",
                        "messages",
                        "system",
                        "max_tokens",
                        "temperature",
                        "top_p",
                        "top_k",
                        "stop_sequences",
                        "stream",
                        "tools",
                        "tool_choice",
                    ]
                },
            },
            "response": {
                "id": getattr(response, "id", None),
                "type": getattr(response, "type", None),
                "role": getattr(response, "role", None),
                "model": getattr(response, "model", None),
                "content": content_data,
                "stop_reason": getattr(response, "stop_reason", None),
                "stop_sequence": getattr(response, "stop_sequence", None),
                "usage": usage_info,
            },
        }

        log_filename = self._log_dir / f"anthropic_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def _log_token_count(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "system": kwargs.get("system"),
                "tools": kwargs.get("tools"),
            },
            "response": {
                "input_tokens": getattr(response, "input_tokens", None),
            },
        }

        log_filename = self._log_dir / f"anthropic_count_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        return getattr(self._messages, name)


class AsyncMessagesWrapper:
    """Wrapper for Anthropic async messages to add logging."""

    def __init__(self, messages, log_dir: str = config.usage_log_directory):
        self._messages = messages
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    async def create(self, *args, **kwargs):
        start_time = datetime.now()
        response = await self._messages.create(*args, **kwargs)
        self._log_usage(
            method="messages.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    async def count_tokens(self, *args, **kwargs):
        start_time = datetime.now()
        response = await self._messages.count_tokens(*args, **kwargs)
        self._log_token_count(
            method="messages.count_tokens",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        content_data = []
        for block in getattr(response, "content", []):
            block_data = {"type": getattr(block, "type", None)}
            if hasattr(block, "text"):
                block_data["text"] = block.text
            if hasattr(block, "name"):
                block_data["name"] = block.name
            if hasattr(block, "input"):
                block_data["input"] = block.input
            if hasattr(block, "id"):
                block_data["id"] = block.id
            content_data.append(block_data)

        usage_info = {}
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            usage_info = {
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
            }

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "system": kwargs.get("system"),
                "max_tokens": kwargs.get("max_tokens"),
                "temperature": kwargs.get("temperature"),
                "top_p": kwargs.get("top_p"),
                "top_k": kwargs.get("top_k"),
                "stop_sequences": kwargs.get("stop_sequences"),
                "stream": kwargs.get("stream"),
                "tools": kwargs.get("tools"),
                "tool_choice": kwargs.get("tool_choice"),
                "parameters": {
                    k: v
                    for k, v in kwargs.items()
                    if k
                    not in [
                        "model",
                        "messages",
                        "system",
                        "max_tokens",
                        "temperature",
                        "top_p",
                        "top_k",
                        "stop_sequences",
                        "stream",
                        "tools",
                        "tool_choice",
                    ]
                },
            },
            "response": {
                "id": getattr(response, "id", None),
                "type": getattr(response, "type", None),
                "role": getattr(response, "role", None),
                "model": getattr(response, "model", None),
                "content": content_data,
                "stop_reason": getattr(response, "stop_reason", None),
                "stop_sequence": getattr(response, "stop_sequence", None),
                "usage": usage_info,
            },
        }

        log_filename = self._log_dir / f"async_anthropic_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def _log_token_count(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "system": kwargs.get("system"),
                "tools": kwargs.get("tools"),
            },
            "response": {
                "input_tokens": getattr(response, "input_tokens", None),
            },
        }

        log_filename = self._log_dir / f"async_anthropic_count_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        return getattr(self._messages, name)


class BetaMessagesWrapper:
    """Wrapper for Anthropic beta.messages to add logging."""

    def __init__(self, messages, log_dir: str = config.usage_log_directory):
        self._messages = messages
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    def parse(self, *args, **kwargs):
        start_time = datetime.now()
        response = self._messages.parse(*args, **kwargs)
        self._log_usage(
            method="beta.messages.parse",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def create(self, *args, **kwargs):
        start_time = datetime.now()
        response = self._messages.create(*args, **kwargs)
        self._log_usage(
            method="beta.messages.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        content_data = []
        for block in getattr(response, "content", []):
            block_data = {"type": getattr(block, "type", None)}
            if hasattr(block, "text"):
                block_data["text"] = block.text
            if hasattr(block, "name"):
                block_data["name"] = block.name
            if hasattr(block, "input"):
                block_data["input"] = block.input
            if hasattr(block, "id"):
                block_data["id"] = block.id
            content_data.append(block_data)

        usage_info = {}
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            usage_info = {
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
            }

        parsed_output = None
        if hasattr(response, "parsed_output") and response.parsed_output:
            try:
                parsed_output = str(response.parsed_output)
            except Exception:
                parsed_output = "<serialization failed>"

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "system": kwargs.get("system"),
                "max_tokens": kwargs.get("max_tokens"),
                "temperature": kwargs.get("temperature"),
                "betas": kwargs.get("betas"),
                "output_format": str(kwargs.get("output_format")) if kwargs.get("output_format") else None,
                "parameters": {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["model", "messages", "system", "max_tokens", "temperature", "betas", "output_format"]
                },
            },
            "response": {
                "id": getattr(response, "id", None),
                "type": getattr(response, "type", None),
                "role": getattr(response, "role", None),
                "model": getattr(response, "model", None),
                "content": content_data,
                "parsed_output": parsed_output,
                "stop_reason": getattr(response, "stop_reason", None),
                "usage": usage_info,
            },
        }

        log_filename = self._log_dir / f"anthropic_beta_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        return getattr(self._messages, name)


class AsyncBetaMessagesWrapper:
    """Wrapper for Anthropic async beta.messages to add logging."""

    def __init__(self, messages, log_dir: str = config.usage_log_directory):
        self._messages = messages
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

    async def parse(self, *args, **kwargs):
        start_time = datetime.now()
        response = await self._messages.parse(*args, **kwargs)
        self._log_usage(
            method="beta.messages.parse",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    async def create(self, *args, **kwargs):
        start_time = datetime.now()
        response = await self._messages.create(*args, **kwargs)
        self._log_usage(
            method="beta.messages.create",
            args=args,
            kwargs=kwargs,
            response=response,
            start_time=start_time,
        )
        return response

    def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        content_data = []
        for block in getattr(response, "content", []):
            block_data = {"type": getattr(block, "type", None)}
            if hasattr(block, "text"):
                block_data["text"] = block.text
            if hasattr(block, "name"):
                block_data["name"] = block.name
            if hasattr(block, "input"):
                block_data["input"] = block.input
            if hasattr(block, "id"):
                block_data["id"] = block.id
            content_data.append(block_data)

        usage_info = {}
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            usage_info = {
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
            }

        parsed_output = None
        if hasattr(response, "parsed_output") and response.parsed_output:
            try:
                parsed_output = str(response.parsed_output)
            except Exception:
                parsed_output = "<serialization failed>"

        log_data = {
            "timestamp": start_time.isoformat(),
            "method": method,
            "duration_ms": duration_ms,
            "request": {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "system": kwargs.get("system"),
                "max_tokens": kwargs.get("max_tokens"),
                "temperature": kwargs.get("temperature"),
                "betas": kwargs.get("betas"),
                "output_format": str(kwargs.get("output_format")) if kwargs.get("output_format") else None,
                "parameters": {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["model", "messages", "system", "max_tokens", "temperature", "betas", "output_format"]
                },
            },
            "response": {
                "id": getattr(response, "id", None),
                "type": getattr(response, "type", None),
                "role": getattr(response, "role", None),
                "model": getattr(response, "model", None),
                "content": content_data,
                "parsed_output": parsed_output,
                "stop_reason": getattr(response, "stop_reason", None),
                "usage": usage_info,
            },
        }

        log_filename = self._log_dir / f"async_anthropic_beta_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(log_filename, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    def __getattr__(self, name):
        return getattr(self._messages, name)


class BetaWrapper:
    """Wrapper for Anthropic beta object to inject messages wrapper."""

    def __init__(self, beta, log_dir: str = config.usage_log_directory, is_async: bool = False):
        self._beta = beta
        self._log_dir = log_dir
        self._is_async = is_async
        self._messages = None

    @property
    def messages(self):
        if self._messages is None:
            if self._is_async:
                self._messages = AsyncBetaMessagesWrapper(self._beta.messages, self._log_dir)
            else:
                self._messages = BetaMessagesWrapper(self._beta.messages, self._log_dir)
        return self._messages

    def __getattr__(self, name):
        return getattr(self._beta, name)


class AnthropicWrapperClient(Anthropic):
    """Thin wrapper for Anthropic client with usage logging."""

    def __init__(self, *args, log_dir: str = config.usage_log_directory, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_dir = log_dir
        self._messages_wrapper = None
        self._beta_wrapper = None

    @property
    def messages(self):
        if self._messages_wrapper is None:
            self._messages_wrapper = MessagesWrapper(super().messages, self._log_dir)
        return self._messages_wrapper

    @property
    def beta(self):
        if self._beta_wrapper is None:
            self._beta_wrapper = BetaWrapper(super().beta, self._log_dir, is_async=False)
        return self._beta_wrapper

    def __getattr__(self, name):
        return super().__getattribute__(name)


class AsyncAnthropicWrapperClient(AsyncAnthropic):
    """Thin wrapper for AsyncAnthropic client with usage logging."""

    def __init__(self, *args, log_dir: str = config.usage_log_directory, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_dir = log_dir
        self._messages_wrapper = None
        self._beta_wrapper = None

    @property
    def messages(self):
        if self._messages_wrapper is None:
            self._messages_wrapper = AsyncMessagesWrapper(super().messages, self._log_dir)
        return self._messages_wrapper

    @property
    def beta(self):
        if self._beta_wrapper is None:
            self._beta_wrapper = BetaWrapper(super().beta, self._log_dir, is_async=True)
        return self._beta_wrapper

    def __getattr__(self, name):
        return super().__getattribute__(name)
