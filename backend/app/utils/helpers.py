"""
============================================================
PhysioAI Pro V2 - Utility Helpers
============================================================
PURPOSE:
    Common utility functions used across the application.
    These are pure functions with no side effects — easy to
    test and reason about.

ARCHITECTURE DECISION:
    Keeping utilities in a dedicated module prevents code
    duplication and ensures consistency (e.g., all client IDs
    follow the same format).
============================================================
"""

import time
import uuid


def generate_client_id() -> str:
    """
    Generate a unique client identifier for WebSocket sessions.

    Uses UUID4 (random) with a short prefix for readability in logs.
    Example output: "client_a1b2c3d4"

    Returns:
        A unique string identifier for a WebSocket client.
    """
    short_id = uuid.uuid4().hex[:8]
    return f"client_{short_id}"


def get_timestamp_ms() -> int:
    """
    Get current timestamp in milliseconds.

    Used for measuring frame processing latency and
    synchronizing timestamps between client and server.

    Returns:
        Current Unix timestamp in milliseconds.
    """
    return int(time.time() * 1000)


def calculate_latency_ms(client_timestamp: int) -> int:
    """
    Calculate the latency between client frame capture and server processing.

    Args:
        client_timestamp: Unix timestamp (seconds) from the client frame packet.

    Returns:
        Latency in milliseconds. Returns 0 if client timestamp is invalid.
    """
    if client_timestamp <= 0:
        return 0
    # Client sends timestamp in seconds, convert to ms for comparison
    client_ms = int(client_timestamp * 1000)
    server_ms = get_timestamp_ms()
    latency = server_ms - client_ms
    # Clamp to 0 if clock drift causes negative values
    return max(0, latency)


def bytes_to_human(size_bytes: int) -> str:
    """
    Convert byte count to human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string (e.g., "512.0 KB").
    """
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
