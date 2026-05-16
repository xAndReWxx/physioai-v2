"""
============================================================
PhysioAI Pro V2 - Application Events (Lifecycle Hooks)
============================================================
PURPOSE:
    Define startup and shutdown event handlers for the FastAPI
    application. These run once when the server starts/stops.

WHY LIFECYCLE EVENTS?
    - Initialize resources that are expensive to create per-request
      (e.g., AI engine, connection pool)
    - Ensure clean shutdown (close connections, flush logs)
    - Log server state for debugging deployment issues

ARCHITECTURE DECISION:
    Using FastAPI's lifespan context manager (modern approach)
    instead of deprecated @app.on_event decorators.
============================================================
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Everything before 'yield' runs at STARTUP.
    Everything after 'yield' runs at SHUTDOWN.
    """
    # ============================
    # STARTUP
    # ============================
    logger.info(
        "server_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
    )
    logger.info(
        "websocket_config",
        max_connections=settings.ws_max_connections,
        heartbeat_interval=settings.ws_heartbeat_interval,
        max_message_size=settings.ws_max_message_size,
    )
    logger.info(
        "frame_processing_config",
        max_fps=settings.max_fps,
        target_fps=settings.target_fps,
        max_frame_size=settings.max_frame_size_bytes,
    )
    logger.info(
        "cors_config",
        allowed_origins=settings.cors_origins_list,
    )

    logger.info("server_ready", status="accepting connections")

    # Hand control to the application
    yield

    # ============================
    # SHUTDOWN
    # ============================
    logger.info("server_shutting_down", status="graceful shutdown initiated")

    # Import here to avoid circular imports
    from app.websocket.manager import connection_manager
    await connection_manager.disconnect_all()

    logger.info("server_stopped", status="all connections closed, goodbye")
