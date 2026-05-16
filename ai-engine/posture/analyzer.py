from typing import List, Dict, Any, Tuple
import numpy as np
from posture.geometry import get_vertical_angle, calculate_angle_2d
from config.settings import settings

class PostureAnalyzer:
    def __init__(self):
        pass

    def analyze(self, landmarks: List[Any]) -> Tuple[int, List[str], List[str]]:
        """
        landmarks is a list of normalized landmarks from MediaPipe (0-32).
        Returns (score, issues, feedback)
        """
        if not landmarks or len(landmarks) < 33:
            return 100, [], []

        issues = []
        feedback = []
        score = 100

        # Extract relevant landmarks
        # 0: nose, 7: left ear, 8: right ear, 11: left shoulder, 12: right shoulder
        # 23: left hip, 24: right hip
        
        left_ear = [landmarks[7].x, landmarks[7].y, landmarks[7].z]
        left_shoulder = [landmarks[11].x, landmarks[11].y, landmarks[11].z]
        left_hip = [landmarks[23].x, landmarks[23].y, landmarks[23].z]
        
        right_ear = [landmarks[8].x, landmarks[8].y, landmarks[8].z]
        right_shoulder = [landmarks[12].x, landmarks[12].y, landmarks[12].z]
        right_hip = [landmarks[24].x, landmarks[24].y, landmarks[24].z]

        # 1. Forward Head Posture
        # Measure angle between vertical and ear-shoulder line
        # Assuming profile view is mostly visible. Let's average left and right if both visible,
        # or just use 2D projection.
        left_fh_angle = get_vertical_angle(left_ear, left_shoulder)
        right_fh_angle = get_vertical_angle(right_ear, right_shoulder)
        
        avg_fh_angle = (left_fh_angle + right_fh_angle) / 2.0
        
        if avg_fh_angle > settings.POSTURE_FORWARD_HEAD_ANGLE:
            issues.append("forward_head")
            feedback.append("Tuck your chin in to align ears with shoulders.")
            score -= 15

        # 2. Slouching (Spine Alignment)
        # Angle between shoulder, hip, and vertical dropping from shoulder
        left_spine_angle = calculate_angle_2d(left_shoulder, left_hip, [left_hip[0], left_hip[1] - 1.0])
        right_spine_angle = calculate_angle_2d(right_shoulder, right_hip, [right_hip[0], right_hip[1] - 1.0])
        
        avg_spine_angle = (left_spine_angle + right_spine_angle) / 2.0
        # If the angle of shoulder-hip deviates significantly from vertical (180 deg)
        if abs(180.0 - avg_spine_angle) > (180.0 - settings.POSTURE_SLOUCHING_ANGLE):
            issues.append("slouching")
            feedback.append("Straighten your back. Avoid rounding your lower spine.")
            score -= 20

        # Ensure score is within 0-100
        score = max(0, min(100, int(score)))

        return score, issues, feedback
