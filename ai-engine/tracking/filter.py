import numpy as np
from typing import Dict

class EMAFilter:
    """Exponential Moving Average Filter for smoothing sequences of numbers."""
    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha
        self.state: Dict[int, float] = {}

    def filter(self, new_value: float, key: int = 0) -> float:
        if key not in self.state:
            self.state[key] = new_value
            return new_value
        
        self.state[key] = self.alpha * new_value + (1 - self.alpha) * self.state[key]
        return self.state[key]

class LandmarkFilter:
    """Filters 33 landmarks over time."""
    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha
        self.state = None

    def filter(self, landmarks: np.ndarray) -> np.ndarray:
        if self.state is None:
            self.state = landmarks
            return landmarks
        
        self.state = self.alpha * landmarks + (1 - self.alpha) * self.state
        return self.state
