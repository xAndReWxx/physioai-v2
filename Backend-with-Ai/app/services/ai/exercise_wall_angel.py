"""
============================================================
PhysioAI Pro V2 - Wall Angel Exercise Tracker
============================================================
PURPOSE:
    Tracks wall angel exercise reps using shoulder-elbow-wrist angles.
    Monitors the sliding motion from arms-up to arms-down position.

ORIGIN:
    Integrated from ai-engine/exercises/wall_angel.py
============================================================
"""

import time

from app.services.ai.exercise_fsm import BaseExerciseFSM, ExerciseState
from app.services.ai.geometry import calculate_angle_2d


class WallAngelExercise(BaseExerciseFSM):
    def __init__(self):
        super().__init__(hold_duration=2.0)
        self.name = "wall_angel"

    def process(self, landmarks: list) -> dict:
        self.mistakes = []

        if not landmarks or len(landmarks) < 33:
            return self.get_feedback()

        l_shoulder = [landmarks[11].x, landmarks[11].y]
        l_elbow = [landmarks[13].x, landmarks[13].y]
        l_wrist = [landmarks[15].x, landmarks[15].y]

        r_shoulder = [landmarks[12].x, landmarks[12].y]
        r_elbow = [landmarks[14].x, landmarks[14].y]
        r_wrist = [landmarks[16].x, landmarks[16].y]

        l_angle = calculate_angle_2d(l_shoulder, l_elbow, l_wrist)
        r_angle = calculate_angle_2d(r_shoulder, r_elbow, r_wrist)
        avg_angle = (l_angle + r_angle) / 2.0

        if self.state == ExerciseState.IDLE:
            if avg_angle < 150:
                self._transition(ExerciseState.MOVEMENT)

        elif self.state == ExerciseState.MOVEMENT:
            if avg_angle <= 100:
                self._transition(ExerciseState.HOLD)
            elif avg_angle > 160:
                self._transition(ExerciseState.IDLE)

        elif self.state == ExerciseState.HOLD:
            if avg_angle > 120:
                self.mistakes.append("Did not reach the bottom fully")
                self.form_quality = max(0, self.form_quality - 10)
                self._transition(ExerciseState.RELEASE)
            else:
                elapsed = time.time() - self.hold_start_time
                if elapsed >= self.hold_duration_target:
                    self._transition(ExerciseState.RELEASE)

        elif self.state == ExerciseState.RELEASE:
            if avg_angle >= 160:
                self.rep_count += 1
                self._transition(ExerciseState.IDLE)

        return self.get_feedback()
