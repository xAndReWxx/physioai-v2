"""
============================================================
PhysioAI Pro V2 - Structured Logging System
============================================================
PURPOSE:
    Production-grade structured logging using structlog.
    All log entries include contextual metadata for debugging
    and monitoring realtime streaming sessions.

WHY STRUCTLOG?
    - Structured key-value logging (machine-parseable)
    - Context binding (attach client_id, session info to all logs)
    - Pretty console output in dev, JSON in production
    - Thread-safe and async-compatible
    - Zero-cost when log level is filtered out

USAGE:
    from app.utils import get_logger
    logger = get_logger(__name__)
    logger.info("frame_received", client_id="abc", size=1024)

ARCHITECTURE DECISION:
    We configure structlog once at import time. Every module
    gets its own logger via get_logger(__name__), which
    automatically includes the module name in log output.
============================================================
"""

import logging
import sys

import structlog
from app.config import settings


def _configure_structlog() -> None:
    """
    Configure structlog for the entire application.

    In development: colored, human-readable console output.
    In production:  JSON-formatted logs for log aggregation services.

    This function is called once at module import time.
    """

    # Shared processors that run on every log event
    shared_processors = [
        # Add log level as a string field
        structlog.stdlib.add_log_level,
        # Add logger name (module path)
        structlog.stdlib.add_logger_name,
        # Add timestamp in ISO format
        structlog.processors.TimeStamper(fmt="iso"),
        # Format stack traces for readability
        structlog.processors.StackInfoRenderer(),
        # Format exception info
        structlog.processors.format_exc_info,
        # Decode unicode properly
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.log_format == "json" or settings.is_production:
        # Production: JSON output for log aggregation (ELK, Datadog, etc.)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: Pretty colored console output
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            pad_event=35,
        )

    structlog.configure(
        processors=[
            # Filter by log level early (performance optimization)
            structlog.stdlib.filter_by_level,
            *shared_processors,
            # Wrap for stdlib compatibility
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure Python's built-in logging to use structlog formatting
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Set root logger level from config
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.DEBUG))

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("websockets").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger for the given module.

    Args:
        name: Module name, typically __name__

    Returns:
        A bound structlog logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("server_started", port=8000)
        logger.error("frame_invalid", reason="too large", size=2048000)
    """
    return structlog.get_logger(name)


# ============================================================
# INITIALIZE ON IMPORT
# ============================================================
# This runs once when the logging module is first imported.
# All subsequent imports reuse the configured structlog.
# ============================================================
_configure_structlog()
