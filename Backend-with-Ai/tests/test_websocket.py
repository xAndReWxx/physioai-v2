"""
============================================================
PhysioAI Pro V2 - Test: WebSocket Connection
============================================================
PURPOSE:
    Verify WebSocket connection lifecycle:
    - Connection acceptance
    - Welcome message
    - Frame processing
    - Heartbeat handling
    - Error handling for malformed packets
    - Clean disconnection
============================================================
"""

import base64
import json
import time

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from app.main import app


class TestWebSocketConnection:
    """Test WebSocket connection lifecycle."""

    def test_websocket_connect_and_welcome(self):
        """Test that WebSocket connection is accepted and welcome message is sent."""
        client = TestClient(app)

        with client.websocket_connect("/ws/pose") as ws:
            # Should receive welcome message
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert "client_id" in data
            assert "config" in data
            assert data["config"]["target_fps"] == 20
            assert "message" in data

    def test_websocket_heartbeat(self):
        """Test heartbeat request/response."""
        client = TestClient(app)

        with client.websocket_connect("/ws/pose") as ws:
            # Consume welcome message
            ws.receive_json()

            # Send heartbeat
            ws.send_json({
                "type": "heartbeat",
                "timestamp": time.time(),
            })

            # Should receive heartbeat response
            data = ws.receive_json()
            assert data["type"] == "heartbeat"
            assert "timestamp" in data

    def test_websocket_frame_processing(self):
        """Test that a valid frame packet returns pose results."""
        client = TestClient(app)

        with client.websocket_connect("/ws/pose") as ws:
            # Consume welcome message
            ws.receive_json()

            # Create a minimal valid base64 "frame"
            # This is just test data — not a real JPEG
            fake_frame = base64.b64encode(b"fake_jpeg_data_for_testing").decode()

            # Send frame packet
            ws.send_json({
                "type": "frame",
                "timestamp": time.time(),
                "frame": fake_frame,
            })

            # Should receive pose result
            data = ws.receive_json()
            assert data["type"] == "pose_result"
            assert "landmarks" in data
            assert "posture_score" in data
            assert "feedback" in data
            assert "fps" in data
            assert "latency_ms" in data

    def test_websocket_invalid_json(self):
        """Test that invalid JSON is handled gracefully."""
        client = TestClient(app)

        with client.websocket_connect("/ws/pose") as ws:
            # Consume welcome message
            ws.receive_json()

            # Send invalid JSON
            ws.send_text("this is not json{{{")

            # Should receive error, not crash
            data = ws.receive_json()
            assert data["type"] == "error"
            assert data["code"] == "INVALID_JSON"

    def test_websocket_unknown_packet_type(self):
        """Test that unknown packet types are rejected."""
        client = TestClient(app)

        with client.websocket_connect("/ws/pose") as ws:
            # Consume welcome message
            ws.receive_json()

            # Send unknown packet type
            ws.send_json({
                "type": "unknown_type",
                "data": "test",
            })

            # Should receive error
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "PACKET_PARSE_ERROR" in data["code"]

    def test_websocket_missing_type_field(self):
        """Test that packets without 'type' are rejected."""
        client = TestClient(app)

        with client.websocket_connect("/ws/pose") as ws:
            # Consume welcome message
            ws.receive_json()

            # Send packet without type
            ws.send_json({
                "data": "no type field here",
            })

            # Should receive error
            data = ws.receive_json()
            assert data["type"] == "error"

    def test_websocket_empty_frame(self):
        """Test that frames with empty data are rejected."""
        client = TestClient(app)

        with client.websocket_connect("/ws/pose") as ws:
            # Consume welcome message
            ws.receive_json()

            # Send frame with empty data
            ws.send_json({
                "type": "frame",
                "timestamp": time.time(),
                "frame": "",
            })

            # Should receive error about invalid frame
            data = ws.receive_json()
            assert data["type"] == "error"

    def test_websocket_invalid_timestamp(self):
        """Test that frames with invalid timestamps are rejected."""
        client = TestClient(app)

        with client.websocket_connect("/ws/pose") as ws:
            # Consume welcome message
            ws.receive_json()

            fake_frame = base64.b64encode(b"test_data").decode()

            # Send frame with negative timestamp
            ws.send_json({
                "type": "frame",
                "timestamp": -1,
                "frame": fake_frame,
            })

            # Should receive error
            data = ws.receive_json()
            assert data["type"] == "error"
