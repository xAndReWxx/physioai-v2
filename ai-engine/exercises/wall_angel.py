from exercises.fsm import BaseExerciseFSM, ExerciseState
from posture.geometry import calculate_angle_2d
import time

class WallAngelExercise(BaseExerciseFSM):
    def __init__(self):
        super().__init__(hold_duration=2.0)
        self.name = "wall_angel"

    def process(self, landmarks: list) -> dict:
        self.mistakes = []
        
        if not landmarks or len(landmarks) < 33:
            return self.get_feedback()

        # Wall angel relies on shoulder (11, 12), elbow (13, 14), and wrist (15, 16) angles
        l_shoulder = [landmarks[11].x, landmarks[11].y]
        l_elbow = [landmarks[13].x, landmarks[13].y]
        l_wrist = [landmarks[15].x, landmarks[15].y]
        
        r_shoulder = [landmarks[12].x, landmarks[12].y]
        r_elbow = [landmarks[14].x, landmarks[14].y]
        r_wrist = [landmarks[16].x, landmarks[16].y]

        l_angle = calculate_angle_2d(l_shoulder, l_elbow, l_wrist)
        r_angle = calculate_angle_2d(r_shoulder, r_elbow, r_wrist)
        
        avg_angle = (l_angle + r_angle) / 2.0

        # State machine based on elbow angles (180 is straight up, ~90 is bottom)
        if self.state == ExerciseState.IDLE:
            if avg_angle < 150: # Moving down
                self._transition(ExerciseState.MOVEMENT)
                
        elif self.state == ExerciseState.MOVEMENT:
            if avg_angle <= 100: # Reached bottom
                self._transition(ExerciseState.HOLD)
            elif avg_angle > 160: # Returned to top
                self._transition(ExerciseState.IDLE)
                
        elif self.state == ExerciseState.HOLD:
            if avg_angle > 120: # Released early
                self.mistakes.append("Did not reach the bottom fully")
                self.form_quality = max(0, self.form_quality - 10)
                self._transition(ExerciseState.RELEASE)
            else:
                elapsed = time.time() - self.hold_start_time
                if elapsed >= self.hold_duration_target:
                    self._transition(ExerciseState.RELEASE)
                    
        elif self.state == ExerciseState.RELEASE:
            if avg_angle >= 160: # Back to top
                self.rep_count += 1
                self._transition(ExerciseState.IDLE)

        return self.get_feedback()
