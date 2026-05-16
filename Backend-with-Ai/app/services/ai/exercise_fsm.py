"""
============================================================
PhysioAI Pro V2 - Exercise State Machine (FSM)
============================================================
PURPOSE:
    Base class for exercise tracking using a finite state machine.
    Each exercise transitions through: IDLE → MOVEMENT → HOLD → RELEASE → IDLE
    and counts reps with form quality tracking.

ORIGIN:
    Integrated from ai-engine/exercises/fsm.py
============================================================
"""

import time
from enum import Enum


class ExerciseState(Enum):
    IDLE = "idle"
    MOVEMENT = "movement"
    HOLD = "hold"
    RELEASE = "release"


class BaseExerciseFSM:
    """
    Base finite state machine for physiotherapy exercises.

    Subclasses implement process() to define exercise-specific
    landmark analysis and state transitions.
    """

    def __init__(self, hold_duration: float = 3.0):
        self.state = ExerciseState.IDLE
        self.rep_count = 0
        self.hold_start_time = 0.0
        self.hold_duration_target = hold_duration
        self.form_quality = 100
        self.mistakes = []
        self.name = "base"

    def reset(self) -> None:
        """Reset exercise state for a new session."""
        self.state = ExerciseState.IDLE
        self.rep_count = 0
        self.form_quality = 100
        self.mistakes = []

    def _transition(self, new_state: ExerciseState) -> None:
        """Transition to a new state, recording hold start time if entering HOLD."""
        if new_state == ExerciseState.HOLD and self.state != ExerciseState.HOLD:
            self.hold_start_time = time.time()
        self.state = new_state

    def process(self, landmarks: list) -> dict:
        """Process landmarks and update state. Must be implemented by subclasses."""
        raise NotImplementedError

    def get_feedback(self) -> dict:
        """Return current exercise state as a feedback dict."""
        return {
            "exercise": self.name,
            "rep_count": self.rep_count,
            "phase": self.state.value,
            "form_quality": self.form_quality,
            "mistakes": self.mistakes,
        }
