from exercises.fsm import BaseExerciseFSM, ExerciseState
from posture.geometry import get_vertical_angle
from config.settings import settings
import time

class ChinTuckExercise(BaseExerciseFSM):
    def __init__(self):
        super().__init__(hold_duration=settings.HOLD_DURATION_SECONDS)
        self.baseline_angle = None
        self.name = "chin_tuck"

    def process(self, landmarks: list) -> dict:
        self.mistakes = []
        
        if not landmarks or len(landmarks) < 33:
            return self.get_feedback()

        # Chin tuck relies on ear (7, 8) and shoulder (11, 12) alignment.
        left_ear = [landmarks[7].x, landmarks[7].y, landmarks[7].z]
        left_shoulder = [landmarks[11].x, landmarks[11].y, landmarks[11].z]
        
        current_angle = get_vertical_angle(left_ear, left_shoulder)

        # Initialize baseline
        if self.baseline_angle is None:
            self.baseline_angle = current_angle
            return self.get_feedback()

        angle_diff = self.baseline_angle - current_angle

        if self.state == ExerciseState.IDLE:
            if angle_diff > 5.0:  # Movement started
                self._transition(ExerciseState.MOVEMENT)
                
        elif self.state == ExerciseState.MOVEMENT:
            if angle_diff >= settings.CHIN_TUCK_TARGET_ANGLE_CHANGE:
                self._transition(ExerciseState.HOLD)
            elif angle_diff < 2.0: # Returned to idle without reaching target
                self._transition(ExerciseState.IDLE)
                
        elif self.state == ExerciseState.HOLD:
            # Check if hold is maintained
            if angle_diff < settings.CHIN_TUCK_TARGET_ANGLE_CHANGE - 5.0:
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
