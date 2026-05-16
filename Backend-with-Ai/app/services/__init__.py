# ============================================================
# PhysioAI Pro V2 - Services Package
# ============================================================
# Business logic layer. Services are where the actual work
# happens — frame processing, AI analysis, posture scoring.
#
# INTEGRATION NOTE:
#   The ai_engine now runs real MediaPipe pose estimation
#   with per-client state management. The frame_router
#   coordinates lifecycle cleanup with the ai_engine.
# ============================================================

from app.services.frame_router import frame_router
from app.services.ai_engine import ai_engine

__all__ = ["frame_router", "ai_engine"]
