import time
from collections import deque

class PerformanceMonitor:
    def __init__(self, max_history=30):
        self.frame_times = deque(maxlen=max_history)
        self.latency_times = deque(maxlen=max_history)
        self.last_time = time.time()

    def update(self, latency: float = 0.0):
        current_time = time.time()
        self.frame_times.append(current_time - self.last_time)
        self.last_time = current_time
        if latency > 0:
            self.latency_times.append(latency)

    @property
    def fps(self) -> float:
        if len(self.frame_times) < 2:
            return 0.0
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        if not self.latency_times:
            return 0.0
        return (sum(self.latency_times) / len(self.latency_times)) * 1000.0

monitor = PerformanceMonitor()
