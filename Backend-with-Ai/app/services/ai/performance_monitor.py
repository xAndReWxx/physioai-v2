"""
============================================================
PhysioAI Pro V2 - Per-Client Performance Monitor
============================================================
PURPOSE:
    Tracks real-time FPS and latency metrics per client.
    Unlike the AI team's global singleton, this is instantiated
    per-client to support multi-client performance tracking.

ORIGIN:
    Adapted from ai-engine/utils/performance.py
============================================================
"""

import time
from collections import deque


class PerformanceMonitor:
    """
    Per-client performance tracker using a sliding window.

    Args:
        max_history: Number of recent frames to keep for averaging.
    """

    def __init__(self, max_history: int = 30):
        self.frame_times = deque(maxlen=max_history)
        self.latency_times = deque(maxlen=max_history)
        self.last_time = time.time()

    def update(self, latency: float = 0.0) -> None:
        """
        Record a new frame processing event.

        Args:
            latency: Processing time in seconds for this frame.
        """
        current_time = time.time()
        self.frame_times.append(current_time - self.last_time)
        self.last_time = current_time
        if latency > 0:
            self.latency_times.append(latency)

    @property
    def fps(self) -> float:
        """Current effective FPS based on recent frame intervals."""
        if len(self.frame_times) < 2:
            return 0.0
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Average processing latency in milliseconds."""
        if not self.latency_times:
            return 0.0
        return (sum(self.latency_times) / len(self.latency_times)) * 1000.0
