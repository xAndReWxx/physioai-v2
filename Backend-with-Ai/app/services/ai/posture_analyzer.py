"""
============================================================
PhysioAI Pro V2 - Posture Analyzer (Integrated)
============================================================
PURPOSE:
    Analyzes MediaPipe landmarks to detect posture issues:
    - Forward head posture (ear-shoulder vertical angle)
    - Slouching / spine misalignment (shoulder-hip-vertical angle)

    Returns a score (0-100), list of issues, and feedback strings.

ORIGIN:
    Integrated from ai-engine/posture/analyzer.py
    Uses backend config for threshold values.
============================================================
"""

from typing import Any, List, Tuple

import numpy as np

from app.services.ai.geometry import get_vertical_angle, calculate_angle_2d
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================
# POSTURE THRESHOLDS (from AI engine config)
# ============================================================
POSTURE_FORWARD_HEAD_ANGLE = 20.0   # degrees — ear-shoulder deviation from vertical
POSTURE_SLOUCHING_ANGLE = 160.0     # degrees — spine angle below which = slouching


class IntegratedPostureAnalyzer:
    """
    Biomechanical posture analyzer operating on MediaPipe landmarks.

    Detects:
        - Forward head posture (ear vs shoulder alignment)
        - Slouching (shoulder-hip-vertical spine angle)

    Returns (score, issues_list, feedback_list).
    """

    def analyze(self, landmarks: List[Any]) -> Tuple[int, List[str], List[str]]:
        """
        Analyze pose landmarks and return posture assessment.

        Args:
            landmarks: List of landmark objects with .x, .y, .z attributes.
                       Must have at least 33 elements (MediaPipe body pose).

        Returns:
            Tuple of (score: int, issues: list[str], feedback: list[str]).
        """
        if not landmarks or len(landmarks) < 33:
            return 100, [], []

        issues = []
        feedback = []
        score = 100

        # Extract key landmark coordinates
        left_ear = [landmarks[7].x, landmarks[7].y, landmarks[7].z]
        left_shoulder = [landmarks[11].x, landmarks[11].y, landmarks[11].z]
        left_hip = [landmarks[23].x, landmarks[23].y, landmarks[23].z]

        right_ear = [landmarks[8].x, landmarks[8].y, landmarks[8].z]
        right_shoulder = [landmarks[12].x, landmarks[12].y, landmarks[12].z]
        right_hip = [landmarks[24].x, landmarks[24].y, landmarks[24].z]

        # ---- 1. Forward Head Posture ----
        left_fh_angle = get_vertical_angle(left_ear, left_shoulder)
        right_fh_angle = get_vertical_angle(right_ear, right_shoulder)
        avg_fh_angle = (left_fh_angle + right_fh_angle) / 2.0

        if avg_fh_angle > POSTURE_FORWARD_HEAD_ANGLE:
            issues.append("forward_head")
            feedback.append("Tuck your chin in to align ears with shoulders.")
            score -= 15

        # ---- 2. Slouching (Spine Alignment) ----
        left_spine_angle = calculate_angle_2d(
            left_shoulder, left_hip, [left_hip[0], left_hip[1] - 1.0]
        )
        right_spine_angle = calculate_angle_2d(
            right_shoulder, right_hip, [right_hip[0], right_hip[1] - 1.0]
        )
        avg_spine_angle = (left_spine_angle + right_spine_angle) / 2.0

        if abs(180.0 - avg_spine_angle) > (180.0 - POSTURE_SLOUCHING_ANGLE):
            issues.append("slouching")
            feedback.append("Straighten your back. Avoid rounding your lower spine.")
            score -= 20

        # Clamp score
        score = max(0, min(100, int(score)))

        return score, issues, feedback
