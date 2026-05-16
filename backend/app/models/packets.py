"""
============================================================
PhysioAI Pro V2 - WebSocket Packet Models
============================================================
PURPOSE:
    Define and validate all data structures flowing through
    the WebSocket connection. Pydantic models enforce schema
    at the boundary — if a packet doesn't match, it's rejected
    BEFORE any processing occurs.

WHY STRICT VALIDATION?
    - Prevents malformed data from reaching the AI engine
    - Catches bugs in the frontend early
    - Protects against injection or oversized payloads
    - Makes the API contract explicit and self-documenting

PACKET TYPES:
    CLIENT → SERVER:
        - "frame"       : Camera frame for pose analysis
        - "heartbeat"   : Keep-alive ping

    SERVER → CLIENT:
        - "pose_result" : AI analysis results
        - "error"       : Error notification
        - "heartbeat"   : Keep-alive pong

ARCHITECTURE DECISION:
    Using an enum for packet types prevents typos and makes
    it easy to add new types. Each type has its own Pydantic
    model with field-level validation.
============================================================
"""

import base64
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.config import settings


class PacketType(str, Enum):
    """
    All valid packet types in the WebSocket protocol.

    Using an Enum prevents typo-related bugs and gives us
    auto-complete support in IDEs.
    """
    FRAME = "frame"
    POSE_RESULT = "pose_result"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


# ============================================================
# CLIENT → SERVER PACKETS
# ============================================================


class FramePacket(BaseModel):
    """
    Camera frame sent from the client for pose analysis.

    The client captures a video frame, encodes it as base64 JPEG,
    and sends it through the WebSocket connection.

    Fields:
        type:      Must be "frame" — enforced by validator
        timestamp: Unix timestamp (seconds) of frame capture
        frame:     Base64-encoded JPEG image data

    Validation:
        - Type must be exactly "frame"
        - Timestamp must be a positive number
        - Frame data must be valid base64
        - Frame size must not exceed MAX_FRAME_SIZE_BYTES
    """
    type: str = Field(..., description="Packet type, must be 'frame'")
    timestamp: float = Field(..., description="Unix timestamp of frame capture (seconds)")
    frame: str = Field(..., description="Base64-encoded JPEG frame data")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Ensure packet type is exactly 'frame'."""
        if v != PacketType.FRAME.value:
            raise ValueError(f"Expected type 'frame', got '{v}'")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        """Ensure timestamp is a valid positive number."""
        if v <= 0:
            raise ValueError("Timestamp must be a positive number")
        return v

    @field_validator("frame")
    @classmethod
    def validate_frame(cls, v: str) -> str:
        """
        Validate the base64 frame data.

        Checks:
        1. String is not empty
        2. String is valid base64
        3. Decoded size doesn't exceed maximum allowed
        """
        if not v or len(v) == 0:
            raise ValueError("Frame data cannot be empty")

        # Attempt to decode base64 to verify validity
        try:
            decoded = base64.b64decode(v)
        except Exception:
            raise ValueError("Frame data is not valid base64")

        # Check decoded size against limit
        if len(decoded) > settings.max_frame_size_bytes:
            from app.utils.helpers import bytes_to_human
            max_size = bytes_to_human(settings.max_frame_size_bytes)
            actual_size = bytes_to_human(len(decoded))
            raise ValueError(
                f"Frame size {actual_size} exceeds maximum {max_size}"
            )

        return v


class HeartbeatPacket(BaseModel):
    """
    Keep-alive heartbeat packet.

    Sent by either side to keep the connection alive through
    NAT timeouts, load balancers, and proxy servers.

    Mobile networks are especially aggressive about closing
    idle connections, so heartbeats are essential for mobile/tablet.
    """
    type: str = Field(default=PacketType.HEARTBEAT.value, description="Must be 'heartbeat'")
    timestamp: Optional[float] = Field(default=None, description="Optional timestamp")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != PacketType.HEARTBEAT.value:
            raise ValueError(f"Expected type 'heartbeat', got '{v}'")
        return v


# ============================================================
# SERVER → CLIENT PACKETS
# ============================================================


class LandmarkPoint(BaseModel):
    """
    A single pose landmark point.

    MediaPipe returns 33 body landmarks, each with x/y/z
    coordinates and a visibility confidence score.

    Coordinates are normalized to [0, 1] relative to the image.
    """
    x: float = Field(..., description="X coordinate (0-1, normalized)")
    y: float = Field(..., description="Y coordinate (0-1, normalized)")
    z: float = Field(default=0.0, description="Z coordinate (depth, normalized)")
    visibility: float = Field(default=0.0, description="Visibility confidence (0-1)")


class PoseResultPacket(BaseModel):
    """
    Pose analysis result sent back to the client.

    Contains the AI engine's analysis of the camera frame,
    including detected landmarks, posture score, and feedback.

    Fields:
        type:          Always "pose_result"
        fps:           Current processing FPS
        landmarks:     List of detected body landmarks
        posture_score: Overall posture quality score (0-100)
        feedback:      Human-readable posture feedback text
        latency_ms:    Server processing latency in milliseconds
        exercise_data: Optional exercise-specific metrics (future)
    """
    type: str = Field(default=PacketType.POSE_RESULT.value, description="Packet type")
    fps: int = Field(default=20, description="Current processing FPS")
    landmarks: List[LandmarkPoint] = Field(default_factory=list, description="Detected pose landmarks")
    posture_score: int = Field(default=0, ge=0, le=100, description="Posture quality score (0-100)")
    feedback: str = Field(default="", description="Human-readable posture feedback")
    latency_ms: int = Field(default=0, ge=0, description="Processing latency in milliseconds")
    exercise_data: Optional[dict] = Field(default=None, description="Exercise-specific data (future)")


class ErrorPacket(BaseModel):
    """
    Error notification sent to the client.

    Used when the server encounters an error processing a frame
    or when the client sends invalid data.
    """
    type: str = Field(default=PacketType.ERROR.value, description="Packet type")
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[str] = Field(default=None, description="Additional error context")
