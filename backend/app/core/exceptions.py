"""
============================================================
PhysioAI Pro V2 - Custom Exceptions
============================================================
PURPOSE:
    Define domain-specific exceptions for clear error handling.
    Each exception type maps to a specific failure mode in the
    realtime pipeline.

WHY CUSTOM EXCEPTIONS?
    - Generic exceptions (ValueError, RuntimeError) don't tell
      you WHAT went wrong in the pipeline
    - Custom exceptions enable specific error handling at each layer
    - The middleware can map exceptions to appropriate error responses
    - Makes debugging faster: "ConnectionLimitError" is instantly
      clear vs "RuntimeError: too many connections"

ARCHITECTURE DECISION:
    All exceptions inherit from PhysioAIError, so you can catch
    all application errors with a single except clause when needed,
    but still handle specific errors individually.
============================================================
"""


class PhysioAIError(Exception):
    """
    Base exception for all PhysioAI application errors.

    All custom exceptions inherit from this class.
    Catch this to handle any application-level error.
    """

    def __init__(self, message: str, code: str = "PHYSIOAI_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class FrameValidationError(PhysioAIError):
    """
    Raised when a received frame fails validation.

    Causes:
        - Invalid base64 encoding
        - Frame too large
        - Corrupt JPEG data
        - Missing required fields
    """

    def __init__(self, message: str):
        super().__init__(message=message, code="FRAME_VALIDATION_ERROR")


class ConnectionLimitError(PhysioAIError):
    """
    Raised when maximum connection limit is reached.

    The server caps simultaneous connections to prevent
    resource exhaustion. This is configurable via WS_MAX_CONNECTIONS.
    """

    def __init__(self, max_connections: int):
        super().__init__(
            message=f"Connection limit reached ({max_connections} max)",
            code="CONNECTION_LIMIT_ERROR",
        )
        self.max_connections = max_connections


class AIEngineError(PhysioAIError):
    """
    Raised when the AI engine fails to process a frame.

    This wraps errors from MediaPipe, OpenCV, or any
    future AI processing pipeline. The original error
    is preserved for debugging.
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message=message, code="AI_ENGINE_ERROR")
        self.original_error = original_error


class PacketParseError(PhysioAIError):
    """
    Raised when a WebSocket message cannot be parsed.

    Causes:
        - Invalid JSON
        - Missing 'type' field
        - Unknown packet type
    """

    def __init__(self, message: str):
        super().__init__(message=message, code="PACKET_PARSE_ERROR")
