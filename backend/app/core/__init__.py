# ============================================================
# PhysioAI Pro V2 - Core Package
# ============================================================
# Core application components: exceptions, events, constants.
# ============================================================

from app.core.exceptions import (
    PhysioAIError,
    FrameValidationError,
    ConnectionLimitError,
    AIEngineError,
    PacketParseError,
)

__all__ = [
    "PhysioAIError",
    "FrameValidationError",
    "ConnectionLimitError",
    "AIEngineError",
    "PacketParseError",
]
