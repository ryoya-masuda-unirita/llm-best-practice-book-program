import json
import logging
import os
from datetime import datetime

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.DEBUG)  # type: ignore
if isinstance(LOG_LEVEL, str):
    LOG_LEVEL = LOG_LEVEL.upper()


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread_id": record.thread,
            "process_id": record.process,
        }

        if hasattr(record, "stream_id"):
            log_entry["stream_id"] = record.stream_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id
        if hasattr(record, "llm_provider"):
            log_entry["llm_provider"] = record.llm_provider
        if hasattr(record, "request_duration"):
            log_entry["request_duration"] = record.request_duration
        if hasattr(record, "tokens_streamed"):
            log_entry["tokens_streamed"] = record.tokens_streamed
        if hasattr(record, "error_type"):
            log_entry["error_type"] = record.error_type

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def make_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(LOG_LEVEL)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)

    return logger


def log_stream_start(
    logger: logging.Logger, stream_id: str, user_id: str = None, session_id: str = None, llm_provider: str = None
):
    logger.info(
        "Stream started",
        extra={
            "stream_id": stream_id,
            "user_id": user_id,
            "session_id": session_id,
            "llm_provider": llm_provider,
            "event_type": "stream_start",
        },
    )


def log_token_received(logger: logging.Logger, stream_id: str, token: str, token_count: int):
    logger.debug(
        f"Token received: {token}",
        extra={"stream_id": stream_id, "token_count": token_count, "event_type": "token_received"},
    )


def log_stream_complete(logger: logging.Logger, stream_id: str, duration: float, total_tokens: int):
    logger.info(
        "Stream completed",
        extra={
            "stream_id": stream_id,
            "request_duration": duration,
            "tokens_streamed": total_tokens,
            "event_type": "stream_complete",
        },
    )


def log_stream_error(logger: logging.Logger, stream_id: str, error: Exception, error_type: str = None):
    logger.error(
        f"Stream error: {str(error)}",
        extra={"stream_id": stream_id, "error_type": error_type or type(error).__name__, "event_type": "stream_error"},
        exc_info=True,
    )
