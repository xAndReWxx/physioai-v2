"""
============================================================
PhysioAI Pro V2 - Chin Tuck Exercise Tracker
============================================================
PURPOSE:
    Tracks chin tuck exercise reps using ear-shoulder angle.
    Detects movement initiation, hold phase, and release.

ORIGIN:
    Integrated from ai-engine/exercises/chin_tuck.py
============================================================
"""

import time

from app.services.ai.exercise_fsm import BaseExerciseFSM, ExerciseState
from app.services.ai.geometry import get_vertical_angle

# Thresholds from AI engine config
CHIN_TUCK_TARGET_ANGLE_CHANGE = 15.0
HOLD_DURATION_SECONDS = 3.0


class ChinTuckExercise(BaseExerciseFSM):
    def __init__(self):
        super().__init__(hold_duration=HOLD_DURATION_SECONDS)
        self.baseline_angle = None
        self.name = "chin_tuck"

    def reset(self) -> None:
        super().reset()
        self.baseline_angle = None

    def process(self, landmarks: list) -> dict:
        self.mistakes = []

        if not landmarks or len(landmarks) < 33:
            return self.get_feedback()

        left_ear = [landmarks[7].x, landmarks[7].y, landmarks[7].z]
        left_shoulder = [landmarks[11].x, landmarks[11].y, landmarks[11].z]

        current_angle = get_vertical_angle(left_ear, left_shoulder)

        # Initialize baseline on first frame
        if self.baseline_angle is None:
            self.baseline_angle = current_angle
            return self.get_feedback()

        angle_diff = self.baseline_angle - current_angle

        if self.state == ExerciseState.IDLE:
            if angle_diff > 5.0:
                self._transition(ExerciseState.MOVEMENT)

        elif self.state == ExerciseState.MOVEMENT:
            if angle_diff >= CHIN_TUCK_TARGET_ANGLE_CHANGE:
                self._transition(ExerciseState.HOLD)
            elif angle_diff < 2.0:
                self._transition(ExerciseState.IDLE)

        elif self.state == ExerciseState.HOLD:
            if angle_diff < CHIN_TUCK_TARGET_ANGLE_CHANGE - 5.0:
                self.mistakes.append("Released too early")
                self.form_quality = max(0, self.form_quality - 10)
                self._transition(ExerciseState.RELEASE)
            else:
                elapsed = time.time() - self.hold_start_time
                if elapsed >= self.hold_duration_target:
                    self._transition(ExerciseState.RELEASE)

        elif self.state == ExerciseState.RELEASE:
            if angle_diff <= 5.0:
                self.rep_count += 1
                self._transition(ExerciseState.IDLE)

        return self.get_feedback()
