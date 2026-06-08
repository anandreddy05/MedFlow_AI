"""Structured JSON logging for the MedFlow AI backend."""

import asyncio
import json
import logging
import os
import time
import traceback
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable


def log_ctx(**kwargs: Any) -> dict:
    """Build the extra dict for structured context fields."""
    return {"extra_data": kwargs}


class JSONFormatter(logging.Formatter):
    """Format each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "logger": record.name,
        }

        if record.exc_info:
            log_obj["exception"] = "".join(
                traceback.format_exception(*record.exc_info)
            )

        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_obj.update(record.extra_data)

        return json.dumps(log_obj, default=str)


def get_logger(name: str = "medflow") -> logging.Logger:
    """
    Return a named JSON logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("Query received", extra=log_ctx(role="doctor"))
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, level, logging.INFO))
        logger.propagate = False
    return logger


def timed_log(logger: logging.Logger, operation: str):
    """Decorator that logs latency for sync or async callables."""

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    latency_ms = round((time.perf_counter() - start) * 1000, 2)
                    logger.info(
                        f"{operation} completed",
                        extra=log_ctx(
                            operation=operation,
                            latency_ms=latency_ms,
                            status="ok",
                        ),
                    )
                    return result
                except Exception as exc:
                    latency_ms = round((time.perf_counter() - start) * 1000, 2)
                    logger.exception(
                        f"{operation} failed",
                        extra=log_ctx(
                            operation=operation,
                            latency_ms=latency_ms,
                            status="error",
                            error=str(exc),
                        ),
                    )
                    raise

            return async_wrapper

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.info(
                    f"{operation} completed",
                    extra=log_ctx(
                        operation=operation,
                        latency_ms=latency_ms,
                        status="ok",
                    ),
                )
                return result
            except Exception as exc:
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.exception(
                    f"{operation} failed",
                    extra=log_ctx(
                        operation=operation,
                        latency_ms=latency_ms,
                        status="error",
                        error=str(exc),
                    ),
                )
                raise

        return wrapper

    return decorator
