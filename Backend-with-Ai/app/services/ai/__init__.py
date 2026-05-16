# ============================================================
# PhysioAI Pro V2 - AI Processing Package
# ============================================================
# Integrated AI engine components from the AI team's MediaPipe
# pipeline, adapted to work within the backend's async
# architecture. All modules use the backend's logging and
# config systems for consistency.
# ============================================================

from app.services.ai.pose_engine import PoseEngine
from app.services.ai.landmark_filter import LandmarkFilter
from app.services.ai.posture_analyzer import IntegratedPostureAnalyzer as PostureAnalyzer
from app.services.ai.geometry import calculate_angle, calculate_angle_2d, get_vertical_angle
from app.services.ai.performance_monitor import PerformanceMonitor
from app.services.ai.exercise_fsm import BaseExerciseFSM, ExerciseState
from app.services.ai.exercise_chin_tuck import ChinTuckExercise
from app.services.ai.exercise_wall_angel import WallAngelExercise
from app.services.ai.exercise_thoracic_ext import ThoracicExtensionExercise

__all__ = [
    "PoseEngine",
    "LandmarkFilter",
    "PostureAnalyzer",
    "PerformanceMonitor",
    "calculate_angle",
    "calculate_angle_2d",
    "get_vertical_angle",
    "BaseExerciseFSM",
    "ExerciseState",
    "ChinTuckExercise",
    "WallAngelExercise",
    "ThoracicExtensionExercise",
]
