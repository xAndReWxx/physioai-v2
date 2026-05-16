"""
============================================================
PhysioAI Pro V2 - Geometry Utilities
============================================================
PURPOSE:
    Mathematical functions for computing angles between body
    landmarks. Used by PostureAnalyzer and exercise trackers
    to determine joint angles and posture deviations.

ORIGIN:
    Integrated from ai-engine/posture/geometry.py
============================================================
"""

import numpy as np


def calculate_angle(a, b, c) -> float:
    """
    Calculate the angle at vertex b formed by points a-b-c.

    Args:
        a: First point (array-like, at least 2-3 elements).
        b: Vertex point (array-like).
        c: Third point (array-like).

    Returns:
        Angle in degrees (0-180).
    """
    a = np.array(a, dtype=np.float64)
    b = np.array(b, dtype=np.float64)
    c = np.array(c, dtype=np.float64)

    ba = a - b
    bc = c - b

    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))

    return float(np.degrees(angle))


def calculate_angle_2d(a, b, c) -> float:
    """Calculate 2D angle (XY plane only) at vertex b."""
    return calculate_angle(a[:2], b[:2], c[:2])


def get_vertical_angle(a, b) -> float:
    """
    Calculate angle of the line a→b relative to the vertical Y-axis.

    Useful for measuring forward head posture (ear relative to
    shoulder vertically).

    Args:
        a: Upper point (e.g., ear).
        b: Lower point (e.g., shoulder).

    Returns:
        Angle in degrees from vertical.
    """
    a = np.array(a[:2], dtype=np.float64)
    b = np.array(b[:2], dtype=np.float64)

    # Vertical reference line dropping down from b
    vertical_pt = np.array([b[0], b[1] + 1.0])

    return calculate_angle_2d(a, b, vertical_pt)
