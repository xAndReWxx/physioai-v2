"""
============================================================
PhysioAI Pro V2 - Test: Packet Validation
============================================================
PURPOSE:
    Verify Pydantic models correctly validate and reject
    WebSocket packet data. Tests both valid and invalid inputs.
============================================================
"""

import base64
import time

import pytest
from pydantic import ValidationError

from app.models.packets import (
    FramePacket,
    HeartbeatPacket,
    PoseResultPacket,
    ErrorPacket,
    LandmarkPoint,
)


class TestFramePacket:
    """Test FramePacket validation."""

    def test_valid_frame_packet(self):
        """Test that a valid frame packet is accepted."""
        frame_data = base64.b64encode(b"valid_test_jpeg_data").decode()

        packet = FramePacket(
            type="frame",
            timestamp=time.time(),
            frame=frame_data,
        )

        assert packet.type == "frame"
        assert packet.timestamp > 0
        assert packet.frame == frame_data

    def test_wrong_type_rejected(self):
        """Test that non-'frame' type is rejected."""
        frame_data = base64.b64encode(b"data").decode()

        with pytest.raises(ValidationError):
            FramePacket(
                type="not_frame",
                timestamp=time.time(),
                frame=frame_data,
            )

    def test_negative_timestamp_rejected(self):
        """Test that negative timestamps are rejected."""
        frame_data = base64.b64encode(b"data").decode()

        with pytest.raises(ValidationError):
            FramePacket(
                type="frame",
                timestamp=-1,
                frame=frame_data,
            )

    def test_empty_frame_rejected(self):
        """Test that empty frame data is rejected."""
        with pytest.raises(ValidationError):
            FramePacket(
                type="frame",
                timestamp=time.time(),
                frame="",
            )

    def test_invalid_base64_rejected(self):
        """Test that non-base64 frame data is rejected."""
        with pytest.raises(ValidationError):
            FramePacket(
                type="frame",
                timestamp=time.time(),
                frame="!!!not-valid-base64!!!",
            )


class TestPoseResultPacket:
    """Test PoseResultPacket creation."""

    def test_valid_result_packet(self):
        """Test creating a valid pose result."""
        result = PoseResultPacket(
            fps=20,
            landmarks=[
                LandmarkPoint(x=0.5, y=0.3, z=0.0, visibility=0.95),
            ],
            posture_score=85,
            feedback="Good posture",
        )

        assert result.type == "pose_result"
        assert result.fps == 20
        assert len(result.landmarks) == 1
        assert result.posture_score == 85

    def test_posture_score_bounds(self):
        """Test that posture score is bounded 0-100."""
        with pytest.raises(ValidationError):
            PoseResultPacket(posture_score=150)

        with pytest.raises(ValidationError):
            PoseResultPacket(posture_score=-10)

    def test_default_values(self):
        """Test that defaults are applied correctly."""
        result = PoseResultPacket()
        assert result.type == "pose_result"
        assert result.fps == 20
        assert result.landmarks == []
        assert result.posture_score == 0
        assert result.feedback == ""


class TestHeartbeatPacket:
    """Test HeartbeatPacket validation."""

    def test_valid_heartbeat(self):
        """Test valid heartbeat packet."""
        hb = HeartbeatPacket(type="heartbeat")
        assert hb.type == "heartbeat"

    def test_wrong_type_rejected(self):
        """Test that non-heartbeat type is rejected."""
        with pytest.raises(ValidationError):
            HeartbeatPacket(type="not_heartbeat")


class TestErrorPacket:
    """Test ErrorPacket creation."""

    def test_valid_error_packet(self):
        """Test creating a valid error packet."""
        err = ErrorPacket(
            code="TEST_ERROR",
            message="Something went wrong",
            details="Extra context",
        )
        assert err.type == "error"
        assert err.code == "TEST_ERROR"
        assert err.message == "Something went wrong"
        assert err.details == "Extra context"
