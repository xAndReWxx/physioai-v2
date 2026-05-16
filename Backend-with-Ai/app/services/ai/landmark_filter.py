"""
============================================================
PhysioAI Pro V2 - Landmark EMA Filter
============================================================
PURPOSE:
    Exponential Moving Average filter for smoothing MediaPipe
    landmark data across frames. Reduces jitter in real-time
    pose tracking without introducing significant latency.

ORIGIN:
    Integrated from ai-engine/tracking/filter.py
============================================================
"""

import numpy as np


class LandmarkFilter:
    """
    Filters 33 MediaPipe landmarks over time using EMA.

    Args:
        alpha: Smoothing factor (0-1).
               Higher = more responsive (closer to raw data).
               Lower  = smoother (more lag).
    """

    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha
        self.state = None

    def filter(self, landmarks: np.ndarray) -> np.ndarray:
        """
        Apply EMA filter to a frame of landmarks.

        Args:
            landmarks: numpy array of shape (33, 4) — [x, y, z, visibility].

        Returns:
            Smoothed landmarks array with same shape.
        """
        if self.state is None:
            self.state = landmarks.copy()
            return landmarks

        self.state = self.alpha * landmarks + (1 - self.alpha) * self.state
        return self.state

    def reset(self) -> None:
        """Reset filter state (e.g., on exercise change)."""
        self.state = None
