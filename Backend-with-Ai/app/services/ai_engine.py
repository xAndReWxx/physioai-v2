"""
============================================================
PhysioAI Pro V2 - AI Engine (Integrated MediaPipe)
============================================================
PURPOSE:
    Production AI processing engine that replaces the placeholder
    implementation with real MediaPipe pose estimation, posture
    analysis, and exercise tracking.

INTEGRATION ARCHITECTURE:
    - Per-client state: Each connected client gets its own
      PoseEngine, LandmarkFilter, PostureAnalyzer, and exercise
      trackers. This prevents cross-contamination between sessions
      and supports true multi-client concurrency.

    - Async processing: MediaPipe inference runs via asyncio's
      run_in_executor() to avoid blocking the event loop. The
      LIVE_STREAM mode's async callback handles the actual
      inference on a background thread.

    - Graceful degradation: If MediaPipe fails to load (e.g.,
      missing GPU driver, model download failure), the engine
      falls back to placeholder mode automatically.

FRAME PROCESSING PIPELINE:
    1. Decode base64 JPEG → raw bytes
    2. Convert to numpy array via OpenCV
    3. BGR → RGB color space conversion
    4. Submit to MediaPipe PoseLandmarker (async)
    5. Wait briefly for inference result
    6. Apply EMA landmark smoothing
    7. Run posture analysis on smoothed landmarks
    8. Run exercise tracking (if active)
    9. Package and return result

PERFORMANCE NOTES:
    - Frame decode + color conversion: ~1-3ms
    - MediaPipe inference: ~15-40ms (CPU), ~5-15ms (GPU)
    - Posture analysis: <1ms
    - Exercise tracking: <1ms
    - Total per-frame: ~20-45ms typical
============================================================
"""

import asyncio
import base64
import time
from typing import Dict, List, Optional

import cv2
import numpy as np

from app.config import settings
from app.models.packets import LandmarkPoint, PoseResultPacket
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================
# Lazy imports for AI components (avoid import-time failures
# if mediapipe isn't installed yet)
# ============================================================
_AI_AVAILABLE = False
try:
    from app.services.ai.pose_engine import PoseEngine, download_model_if_missing
    from app.services.ai.landmark_filter import LandmarkFilter
    from app.services.ai.posture_analyzer import IntegratedPostureAnalyzer
    from app.services.ai.performance_monitor import PerformanceMonitor
    from app.services.ai.exercise_chin_tuck import ChinTuckExercise
    from app.services.ai.exercise_wall_angel import WallAngelExercise
    from app.services.ai.exercise_thoracic_ext import ThoracicExtensionExercise
    _AI_AVAILABLE = True
    logger.info("ai_imports_successful", status="mediapipe_available")
except ImportError as e:
    logger.warning(
        "ai_imports_failed",
        error=str(e),
        fallback="placeholder_mode",
    )


class _ClientAIState:
    """
    Per-client AI processing state.

    Each connected client gets its own instance to ensure:
    - Independent landmark smoothing (EMA filter state)
    - Independent exercise tracking (rep counts, FSM state)
    - Independent performance metrics
    - No cross-client data leakage
    """

    def __init__(self):
        self.pose_engine: Optional[object] = None
        self.landmark_filter: Optional[object] = None
        self.posture_analyzer: Optional[object] = None
        self.performance_monitor: Optional[object] = None
        self.exercises: Dict[str, object] = {}
        self.current_exercise: str = "chin_tuck"
        self.timestamp_counter: int = 0  # Monotonic counter for MediaPipe
        self.initialized: bool = False


class AIEngine:
    """
    AI processing engine for pose estimation and posture analysis.

    Manages per-client AI state and routes frames through the
    MediaPipe → PostureAnalysis → ExerciseTracking pipeline.

    Falls back to placeholder mode if MediaPipe is unavailable.
    """

    def __init__(self):
        self._initialized = False
        self._ai_mode = False  # True = real MediaPipe, False = placeholder

        # Per-client AI state
        self._client_states: Dict[str, _ClientAIState] = {}

        # Placeholder feedback messages (used when AI is unavailable)
        self._feedback_messages = [
            "Keep your back straight",
            "Shoulders are aligned well",
            "Slight forward head posture detected",
            "Good posture! Maintain this position",
            "Try to relax your shoulders",
            "Core engagement looks good",
            "Adjust your hip alignment slightly",
            "Excellent standing posture",
            "Watch your neck alignment",
            "Great improvement from last frame",
        ]

    async def initialize(self) -> None:
        """
        Initialize the AI engine.

        Attempts to download the MediaPipe model and verify
        that all AI components are available. Falls back to
        placeholder mode on failure.
        """
        logger.info("ai_engine_initializing")

        if _AI_AVAILABLE:
            try:
                # Download model synchronously at startup (one-time cost)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, download_model_if_missing)

                self._ai_mode = True
                logger.info("ai_engine_ready", mode="mediapipe_live")
            except Exception as e:
                logger.error(
                    "ai_engine_init_failed",
                    error=str(e),
                    fallback="placeholder_mode",
                )
                self._ai_mode = False
        else:
            self._ai_mode = False
            logger.info("ai_engine_ready", mode="placeholder")

        self._initialized = True

    def _get_client_state(self, client_id: str) -> _ClientAIState:
        """
        Get or create per-client AI state.

        Lazily initializes AI components on first frame from a client.
        This spreads the initialization cost and avoids creating
        resources for clients that never send frames.
        """
        if client_id not in self._client_states:
            state = _ClientAIState()

            if self._ai_mode:
                try:
                    state.pose_engine = PoseEngine()
                    state.landmark_filter = LandmarkFilter(alpha=0.5)
                    state.posture_analyzer = IntegratedPostureAnalyzer()
                    state.performance_monitor = PerformanceMonitor()
                    state.exercises = {
                        "chin_tuck": ChinTuckExercise(),
                        "wall_angel": WallAngelExercise(),
                        "thoracic_extension": ThoracicExtensionExercise(),
                    }
                    state.initialized = True
                    logger.info(
                        "client_ai_state_created",
                        client_id=client_id,
                        mode="mediapipe",
                    )
                except Exception as e:
                    logger.error(
                        "client_ai_state_failed",
                        client_id=client_id,
                        error=str(e),
                    )
                    state.initialized = False
            else:
                state.initialized = False

            self._client_states[client_id] = state

        return self._client_states[client_id]

    async def process_frame(
        self,
        frame_data: str,
        client_id: str,
    ) -> Dict:
        """
        Process a single camera frame and return pose analysis results.

        Routes to real MediaPipe processing or placeholder based on
        engine mode. All processing is offloaded from the event loop
        via run_in_executor to prevent blocking.

        Args:
            frame_data: Base64-encoded JPEG frame from client.
            client_id: Client ID for per-client state tracking.

        Returns:
            Dict matching PoseResultPacket schema.
        """
        if not self._initialized:
            await self.initialize()

        client_state = self._get_client_state(client_id)

        if self._ai_mode and client_state.initialized:
            return await self._process_frame_mediapipe(frame_data, client_id, client_state)
        else:
            return await self._process_frame_placeholder(frame_data, client_id)

    async def _process_frame_mediapipe(
        self,
        frame_data: str,
        client_id: str,
        state: _ClientAIState,
    ) -> Dict:
        """
        Real MediaPipe processing pipeline.

        Runs the CPU-bound work (decode, inference, analysis) in a
        thread pool executor to avoid blocking the async event loop.
        """
        start_time = time.time()
        loop = asyncio.get_event_loop()

        try:
            # ============================
            # STEP 1: Decode base64 → OpenCV image (CPU-bound)
            # ============================
            frame = await loop.run_in_executor(
                None, self._decode_frame, frame_data
            )

            if frame is None:
                logger.warning("frame_decode_failed", client_id=client_id)
                return self._empty_result("Failed to decode frame")

            # ============================
            # STEP 2: BGR → RGB conversion
            # ============================
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # ============================
            # STEP 3: MediaPipe pose inference (CPU-bound)
            # ============================
            state.timestamp_counter += 1
            timestamp_ms = int(time.time() * 1000)

            await loop.run_in_executor(
                None,
                state.pose_engine.process_frame,
                frame_rgb,
                timestamp_ms,
            )

            # Brief yield to allow MediaPipe's async callback to fire
            await asyncio.sleep(0.005)

            result = state.pose_engine.latest_result

            # ============================
            # STEP 4: Process landmarks if detected
            # ============================
            landmarks_list = []
            posture_score = 100
            posture_feedback = []
            posture_issues = []
            exercise_data = None

            if result and result.pose_landmarks:
                raw_landmarks = result.pose_landmarks[0]  # Single person

                # Convert to numpy array for filtering
                lm_array = np.array(
                    [[lm.x, lm.y, lm.z, lm.visibility] for lm in raw_landmarks],
                    dtype=np.float64,
                )

                # Apply EMA smoothing
                filtered_lm = state.landmark_filter.filter(lm_array)

                # Build LandmarkPoint list for response
                landmarks_list = [
                    LandmarkPoint(
                        x=round(float(lm[0]), 4),
                        y=round(float(lm[1]), 4),
                        z=round(float(lm[2]), 4),
                        visibility=round(float(lm[3]), 4),
                    )
                    for lm in filtered_lm
                ]

                # ============================
                # STEP 5: Posture Analysis
                # ============================
                # Create lightweight landmark structs for the analyzer
                class _LM:
                    __slots__ = ("x", "y", "z", "visibility")

                struct_landmarks = []
                for lm in filtered_lm:
                    obj = _LM()
                    obj.x, obj.y, obj.z, obj.visibility = (
                        float(lm[0]),
                        float(lm[1]),
                        float(lm[2]),
                        float(lm[3]),
                    )
                    struct_landmarks.append(obj)

                posture_score, posture_issues, posture_feedback = (
                    state.posture_analyzer.analyze(struct_landmarks)
                )

                # ============================
                # STEP 6: Exercise Tracking
                # ============================
                if state.current_exercise in state.exercises:
                    tracker = state.exercises[state.current_exercise]
                    exercise_data = tracker.process(struct_landmarks)

            # ============================
            # STEP 7: Performance metrics
            # ============================
            latency = time.time() - start_time
            state.performance_monitor.update(latency)

            # Build feedback string
            feedback_str = "; ".join(posture_feedback) if posture_feedback else "Good posture!"

            # Build result packet
            result_packet = PoseResultPacket(
                type="pose_result",
                fps=round(state.performance_monitor.fps),
                landmarks=landmarks_list,
                posture_score=posture_score,
                feedback=feedback_str,
                exercise_data=exercise_data,
            )

            logger.debug(
                "mediapipe_frame_processed",
                client_id=client_id,
                landmarks_count=len(landmarks_list),
                posture_score=posture_score,
                fps=round(state.performance_monitor.fps, 1),
                latency_ms=round(latency * 1000, 1),
            )

            return result_packet.model_dump()

        except Exception as e:
            logger.error(
                "mediapipe_processing_error",
                client_id=client_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return self._empty_result(f"AI processing error: {type(e).__name__}")

    async def _process_frame_placeholder(
        self,
        frame_data: str,
        client_id: str,
    ) -> Dict:
        """
        Placeholder processing when MediaPipe is unavailable.

        Returns realistic-looking mock data so the frontend can
        be developed independently of the AI pipeline.
        """
        import random

        await asyncio.sleep(0.02)  # Simulate 20ms processing

        # Generate placeholder landmarks (33 body points)
        base_landmarks = [
            (0.50, 0.15), (0.49, 0.13), (0.48, 0.12), (0.47, 0.13),
            (0.51, 0.13), (0.52, 0.12), (0.53, 0.13), (0.46, 0.15),
            (0.54, 0.15), (0.49, 0.18), (0.51, 0.18), (0.40, 0.25),
            (0.60, 0.25), (0.35, 0.40), (0.65, 0.40), (0.32, 0.52),
            (0.68, 0.52), (0.31, 0.54), (0.69, 0.54), (0.30, 0.53),
            (0.70, 0.53), (0.32, 0.52), (0.68, 0.52), (0.43, 0.55),
            (0.57, 0.55), (0.42, 0.72), (0.58, 0.72), (0.41, 0.90),
            (0.59, 0.90), (0.40, 0.92), (0.60, 0.92), (0.42, 0.94),
            (0.58, 0.94),
        ]

        landmarks = [
            LandmarkPoint(
                x=round(x + random.uniform(-0.01, 0.01), 4),
                y=round(y + random.uniform(-0.01, 0.01), 4),
                z=round(random.uniform(-0.1, 0.1), 4),
                visibility=round(random.uniform(0.85, 1.0), 4),
            )
            for x, y in base_landmarks
        ]

        posture_score = max(0, min(100, int(random.gauss(82, 8))))
        feedback = random.choice(self._feedback_messages)

        result = PoseResultPacket(
            type="pose_result",
            fps=settings.target_fps,
            landmarks=landmarks,
            posture_score=posture_score,
            feedback=feedback,
            exercise_data=None,
        )

        return result.model_dump()

    @staticmethod
    def _decode_frame(frame_data: str) -> Optional[np.ndarray]:
        """
        Decode a base64-encoded JPEG frame to an OpenCV image.

        Handles both raw base64 and data-URI formatted strings
        (e.g., "data:image/jpeg;base64,/9j/4AAQ...").

        Args:
            frame_data: Base64 string (with or without data URI prefix).

        Returns:
            OpenCV BGR image as numpy array, or None on failure.
        """
        try:
            # Strip data URI prefix if present
            if "," in frame_data:
                frame_data = frame_data.split(",", 1)[1]

            img_bytes = base64.b64decode(frame_data)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame
        except Exception:
            return None

    @staticmethod
    def _empty_result(feedback: str = "") -> Dict:
        """Return an empty pose result for error/fallback cases."""
        return PoseResultPacket(
            type="pose_result",
            fps=0,
            landmarks=[],
            posture_score=0,
            feedback=feedback,
            exercise_data=None,
        ).model_dump()

    def set_exercise(self, client_id: str, exercise_name: str) -> bool:
        """
        Change the active exercise for a client.

        Args:
            client_id: Target client.
            exercise_name: Exercise to activate (chin_tuck, wall_angel, thoracic_extension).

        Returns:
            True if exercise was changed successfully.
        """
        state = self._client_states.get(client_id)
        if not state or not state.initialized:
            return False

        if exercise_name in state.exercises and exercise_name != state.current_exercise:
            state.current_exercise = exercise_name
            state.exercises[exercise_name].reset()
            logger.info(
                "exercise_changed",
                client_id=client_id,
                exercise=exercise_name,
            )
            return True
        return False

    def cleanup_client(self, client_id: str) -> None:
        """
        Clean up per-client AI resources on disconnect.

        Releases the MediaPipe PoseEngine for this client to
        free memory and GPU resources.
        """
        state = self._client_states.pop(client_id, None)
        if state and state.pose_engine:
            try:
                state.pose_engine.close()
            except Exception:
                pass
            logger.info("client_ai_state_cleaned", client_id=client_id)

    async def cleanup(self) -> None:
        """
        Clean up ALL AI engine resources (server shutdown).
        """
        logger.info("ai_engine_cleanup", clients=len(self._client_states))
        client_ids = list(self._client_states.keys())
        for client_id in client_ids:
            self.cleanup_client(client_id)
        self._initialized = False
        logger.info("ai_engine_cleanup_complete")


# ============================================================
# SINGLETON INSTANCE
# ============================================================
ai_engine = AIEngine()
