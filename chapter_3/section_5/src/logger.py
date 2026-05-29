import logging
import os

_LOG_LEVEL_ENV = os.getenv("LOG_LEVEL", "DEBUG")
LOG_LEVEL: int | str = _LOG_LEVEL_ENV.upper() if isinstance(_LOG_LEVEL_ENV, str) else _LOG_LEVEL_ENV

_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] [%(funcName)s] %(message)s"


def make_logger(name: str) -> logging.Logger:
    """Create a configured logger with standard formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    handler = logging.StreamHandler()
    handler.setLevel(LOG_LEVEL)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)

    return logger
