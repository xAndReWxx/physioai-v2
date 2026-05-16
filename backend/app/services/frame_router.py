"""
============================================================
PhysioAI Pro V2 - Frame Router
============================================================
PURPOSE:
    Routes incoming camera frames to the appropriate AI
    processing pipeline. Acts as a mediator between the
    WebSocket handler and the AI engine.

WHY A SEPARATE ROUTER?
    - Decouples WebSocket handling from AI processing
    - Single point for adding pre/post-processing steps
    - Easy to add rate limiting, caching, or frame dropping
    - Future: route different exercise types to different engines
    - Future: add frame preprocessing (resize, crop, quality)

FRAME PROCESSING PIPELINE:
    1. Receive validated frame packet
    2. Apply rate limiting (prevent CPU overload)
    3. [Future] Preprocess frame (resize, normalize)
    4. Send to AI engine
    5. [Future] Post-process results (smoothing, filtering)
    6. Return results to handler

ARCHITECTURE DECISION:
    The router maintains per-client state for rate limiting.
    This prevents a single client from monopolizing the AI engine.
    asyncio.Semaphore limits concurrent AI processing calls.
============================================================
"""

import asyncio
import time
from typing import Dict

from app.config import settings
from app.core.exceptions import AIEngineError
from app.models.packets import FramePacket
from app.services.ai_engine import ai_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FrameRouter:
    """
    Routes camera frames to the AI processing pipeline.

    Features:
        - Per-client rate limiting (prevent FPS abuse)
        - Concurrent processing limiter (prevent CPU overload)
        - Frame dropping under load (preserve latency)
        - Extensible pipeline architecture
    """

    def __init__(self):
        # Per-client timestamp of last processed frame
        # Used for rate limiting (one frame per 1/MAX_FPS seconds)
        self._last_frame_time: Dict[str, float] = {}

        # Semaphore to limit concurrent AI processing
        # This prevents CPU overload when many clients send frames
        # simultaneously. Tune this based on your hardware.
        self._processing_semaphore = asyncio.Semaphore(10)

        # Frame drop counter for monitoring
        self._frames_dropped: Dict[str, int] = {}

    async def process_frame(self, frame_packet: FramePacket, client_id: str) -> Dict:
        """
        Process a camera frame through the AI pipeline.

        Steps:
        1. Check rate limit (drop if too fast)
        2. Acquire processing semaphore
        3. Route to AI engine
        4. Return results

        Args:
            frame_packet: Validated frame packet from client.
            client_id: Client that sent the frame.

        Returns:
            Dict with pose analysis results.

        Raises:
            AIEngineError: If the AI engine fails to process.
        """
        # ============================
        # STEP 1: Rate Limiting
        # ============================
        if not self._check_rate_limit(client_id):
            # Frame came too fast — drop it to maintain target FPS
            # This is NORMAL during high-FPS streaming
            self._frames_dropped[client_id] = (
                self._frames_dropped.get(client_id, 0) + 1
            )
            logger.debug(
                "frame_dropped_rate_limit",
                client_id=client_id,
                dropped_total=self._frames_dropped.get(client_id, 0),
            )
            # Return a lightweight "skipped" result instead of nothing
            return {
                "type": "pose_result",
                "fps": settings.target_fps,
                "landmarks": [],
                "posture_score": 0,
                "feedback": "",
                "latency_ms": 0,
                "skipped": True,
            }

        # ============================
        # STEP 2: Acquire Semaphore
        # ============================
        # This limits concurrent AI processing to prevent CPU overload.
        # If the semaphore is full, this will block until a slot opens.
        # The timeout prevents indefinite blocking.
        try:
            async with asyncio.timeout(2.0):
                async with self._processing_semaphore:
                    # ============================
                    # STEP 3: AI Processing
                    # ============================
                    return await self._route_to_engine(frame_packet, client_id)

        except asyncio.TimeoutError:
            logger.warning(
                "processing_timeout",
                client_id=client_id,
                reason="semaphore_full",
            )
            return {
                "type": "pose_result",
                "fps": settings.target_fps,
                "landmarks": [],
                "posture_score": 0,
                "feedback": "Server is processing. Please wait...",
                "latency_ms": 0,
                "skipped": True,
            }

    async def _route_to_engine(
        self, frame_packet: FramePacket, client_id: str
    ) -> Dict:
        """
        Route frame to the AI engine for processing.

        This is where the actual AI analysis happens.
        Separated from process_frame() for clarity and
        to make it easy to add pre/post-processing.

        Args:
            frame_packet: Validated frame packet.
            client_id: Client identifier.

        Returns:
            Dict with AI analysis results.
        """
        try:
            # ============================
            # FUTURE: PREPROCESSING
            # ============================
            # Before sending to AI engine, you might want to:
            # - Resize the frame (for consistent input size)
            # - Apply image normalization
            # - Crop to region of interest
            # - Cache previous frame for comparison

            # Send to AI engine
            result = await ai_engine.process_frame(
                frame_data=frame_packet.frame,
                client_id=client_id,
            )

            # ============================
            # FUTURE: POST-PROCESSING
            # ============================
            # After getting results, you might want to:
            # - Smooth landmarks across frames (reduce jitter)
            # - Apply temporal filtering to posture score
            # - Track exercise reps over time
            # - Generate Arabic voice coaching text

            return result

        except Exception as e:
            logger.error(
                "ai_engine_processing_error",
                client_id=client_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise AIEngineError(
                message=f"Failed to process frame: {str(e)}",
                original_error=e,
            )

    def _check_rate_limit(self, client_id: str) -> bool:
        """
        Check if enough time has passed since the last processed frame.

        Enforces the MAX_FPS setting to prevent CPU overload.
        Returns True if the frame should be processed, False if dropped.

        Args:
            client_id: Client to check rate limit for.

        Returns:
            True if frame should be processed, False if rate limited.
        """
        now = time.monotonic()
        min_interval = 1.0 / settings.max_fps  # e.g., 1/25 = 0.04s = 40ms

        last_time = self._last_frame_time.get(client_id, 0)

        if now - last_time < min_interval:
            return False  # Too soon, drop frame

        self._last_frame_time[client_id] = now
        return True

    def cleanup_client(self, client_id: str) -> None:
        """
        Clean up per-client state when a client disconnects.

        Prevents memory leaks from accumulating state for
        disconnected clients.

        Args:
            client_id: Client to clean up.
        """
        self._last_frame_time.pop(client_id, None)
        self._frames_dropped.pop(client_id, None)


# ============================================================
# SINGLETON INSTANCE
# ============================================================
frame_router = FrameRouter()
