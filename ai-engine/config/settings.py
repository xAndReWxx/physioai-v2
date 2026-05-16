import os
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "PhysioAI Pro V2 Engine"
    DEBUG: bool = False

    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR: str = os.path.join(BASE_DIR, "assets")
    MODEL_PATH: str = os.path.join(ASSETS_DIR, "pose_landmarker_full.task")
    MODEL_URL: str = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"

    # Performance
    TARGET_FPS: int = 30
    MAX_QUEUE_SIZE: int = 2 # Drop older frames if queue is full
    
    # EMA Smoothing
    EMA_ALPHA_LANDMARKS: float = 0.5  # Higher = more responsive, lower = smoother
    EMA_ALPHA_ANGLES: float = 0.3

    # Posture Thresholds
    POSTURE_FORWARD_HEAD_ANGLE: float = 20.0
    POSTURE_ROUNDED_SHOULDERS_ANGLE: float = 15.0
    POSTURE_SLOUCHING_ANGLE: float = 160.0 # spine angle < 160 is slouching

    # Exercise Thresholds
    CHIN_TUCK_TARGET_ANGLE_CHANGE: float = 15.0
    HOLD_DURATION_SECONDS: float = 3.0

    class Config:
        env_file = ".env"

settings = Settings()

# Ensure assets dir exists
os.makedirs(settings.ASSETS_DIR, exist_ok=True)
