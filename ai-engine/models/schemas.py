from pydantic import BaseModel
from typing import List, Optional

class Landmark(BaseModel):
    x: float
    y: float
    z: float
    visibility: float

class PostureFeedback(BaseModel):
    posture_score: int
    issues: List[str]
    feedback: List[str]

class ExerciseFeedback(BaseModel):
    exercise: str
    rep_count: int
    phase: str
    form_quality: int
    mistakes: List[str]

class EngineResponse(BaseModel):
    type: str = "pose_result"
    fps: float
    latency_ms: float
    landmarks: List[Landmark]
    posture: Optional[PostureFeedback] = None
    exercise: Optional[ExerciseFeedback] = None
    error: Optional[str] = None
