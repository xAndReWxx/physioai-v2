from enum import Enum
import time

class ExerciseState(Enum):
    IDLE = "idle"
    MOVEMENT = "movement"
    HOLD = "hold"
    RELEASE = "release"

class BaseExerciseFSM:
    def __init__(self, hold_duration: float = 3.0):
        self.state = ExerciseState.IDLE
        self.rep_count = 0
        self.hold_start_time = 0.0
        self.hold_duration_target = hold_duration
        self.form_quality = 100
        self.mistakes = []
        self.name = "base"

    def reset(self):
        self.state = ExerciseState.IDLE
        self.rep_count = 0
        self.form_quality = 100
        self.mistakes = []
        
    def _transition(self, new_state: ExerciseState):
        if new_state == ExerciseState.HOLD and self.state != ExerciseState.HOLD:
            self.hold_start_time = time.time()
        self.state = new_state

    def process(self, landmarks: list) -> dict:
        """Process landmarks and update state. Must be implemented by subclasses."""
        raise NotImplementedError

    def get_feedback(self) -> dict:
        return {
            "exercise": self.name,
            "rep_count": self.rep_count,
            "phase": self.state.value,
            "form_quality": self.form_quality,
            "mistakes": self.mistakes
        }
