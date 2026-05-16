from exercises.fsm import BaseExerciseFSM, ExerciseState
from posture.geometry import calculate_angle_2d
import time

class ThoracicExtensionExercise(BaseExerciseFSM):
    def __init__(self):
        super().__init__(hold_duration=3.0)
        self.name = "thoracic_extension"
        self.baseline_spine_angle = None

    def process(self, landmarks: list) -> dict:
        self.mistakes = []
        
        if not landmarks or len(landmarks) < 33:
            return self.get_feedback()

        l_shoulder = [landmarks[11].x, landmarks[11].y]
        l_hip = [landmarks[23].x, landmarks[23].y]
        l_knee = [landmarks[25].x, landmarks[25].y]
        
        spine_angle = calculate_angle_2d(l_shoulder, l_hip, l_knee)

        if self.baseline_spine_angle is None:
            self.baseline_spine_angle = spine_angle
            return self.get_feedback()

        # Extension means the angle increases (straightens out or bends backwards)
        angle_diff = spine_angle - self.baseline_spine_angle

        if self.state == ExerciseState.IDLE:
            if angle_diff > 10.0:
                self._transition(ExerciseState.MOVEMENT)
                
        elif self.state == ExerciseState.MOVEMENT:
            if angle_diff >= 20.0: # Target extension reached
                self._transition(ExerciseState.HOLD)
            elif angle_diff < 5.0:
                self._transition(ExerciseState.IDLE)
                
        elif self.state == ExerciseState.HOLD:
            if angle_diff < 15.0: # Dropped extension
                self.mistakes.append("Lost thoracic extension too soon")
                self.form_quality = max(0, self.form_quality - 15)
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
