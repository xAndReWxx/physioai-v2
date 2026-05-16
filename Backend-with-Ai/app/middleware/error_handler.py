"""
============================================================
PhysioAI Pro V2 - Error Handling Middleware
============================================================
PURPOSE:
    Global error handling for the FastAPI application.
    Catches unhandled exceptions and converts them into
    structured JSON responses.

WHY GLOBAL ERROR HANDLERS?
    - Prevents raw stack traces from leaking to clients
    - Ensures consistent error response format
    - Centralizes error logging
    - In production: sanitizes error details
    - In development: includes full error context

ARCHITECTURE DECISION:
    We use FastAPI's exception_handler decorator pattern.
    This catches errors that escape route handlers and
    converts them into proper HTTP responses.

    Note: WebSocket errors are handled separately in the
    WebSocket handler — HTTP middleware doesn't apply to WS.
============================================================
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.exceptions import PhysioAIError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def setup_error_handlers(app: FastAPI) -> None:
    """
    Register global error handlers on the FastAPI application.

    This function is called once during app initialization.
    It registers handlers for:
    - PhysioAIError (application-specific errors)
    - StarletteHTTPException (HTTP errors like 404, 405)
    - Exception (catch-all for unexpected errors)

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(PhysioAIError)
    async def physioai_error_handler(
        request: Request, exc: PhysioAIError
    ) -> JSONResponse:
        """
        Handle application-specific errors.

        Returns a structured error response with the error code
        and message from the exception.
        """
        logger.error(
            "application_error",
            code=exc.code,
            message=exc.message,
            path=str(request.url),
        )

        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "code": exc.code,
                "message": exc.message,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """
        Handle standard HTTP exceptions (404, 405, etc.).

        Returns a consistent JSON format even for HTTP errors.
        """
        logger.warning(
            "http_error",
            status_code=exc.status_code,
            detail=exc.detail,
            path=str(request.url),
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all handler for unexpected exceptions.

        In development: includes error details for debugging.
        In production: returns a generic message (no info leak).
        """
        logger.error(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=str(request.url),
            exc_info=True,
        )

        # Only include error details in development mode
        if settings.is_development:
            message = f"Internal error: {str(exc)}"
        else:
            message = "An unexpected error occurred"

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": message,
            },
        )
