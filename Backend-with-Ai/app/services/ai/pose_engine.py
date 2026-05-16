"""
============================================================
PhysioAI Pro V2 - MediaPipe Pose Engine
============================================================
PURPOSE:
    Wraps MediaPipe PoseLandmarker for real-time pose estimation.
    Uses the LIVE_STREAM running mode with async callback for
    non-blocking inference.

    Downloads the model file automatically on first use.

ORIGIN:
    Integrated from ai-engine/mediapipe_engine/pose.py
    Adapted to use backend logging and flexible asset paths.

THREADING NOTE:
    MediaPipe's LIVE_STREAM mode uses an internal thread for
    inference. The result_callback fires from that thread.
    We use a simple attribute assignment (thread-safe for
    Python's GIL) to pass results back.
============================================================
"""

import os
import urllib.request
from typing import Optional

import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================
# MODEL CONFIGURATION
# ============================================================
_ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets"
)
MODEL_PATH = os.path.join(_ASSETS_DIR, "pose_landmarker_full.task")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_full/float16/1/"
    "pose_landmarker_full.task"
)


def download_model_if_missing() -> None:
    """
    Download the MediaPipe PoseLandmarker model if not present.
    Creates the assets directory if needed.
    """
    os.makedirs(_ASSETS_DIR, exist_ok=True)

    if os.path.exists(MODEL_PATH):
        logger.info("mediapipe_model_found", path=MODEL_PATH)
        return

    logger.info("mediapipe_model_downloading", url=MODEL_URL)
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        file_size = os.path.getsize(MODEL_PATH)
        logger.info(
            "mediapipe_model_downloaded",
            path=MODEL_PATH,
            size_mb=round(file_size / (1024 * 1024), 1),
        )
    except Exception as e:
        logger.error("mediapipe_model_download_failed", error=str(e))
        raise


class PoseEngine:
    """
    MediaPipe PoseLandmarker wrapper for real-time pose estimation.

    Uses LIVE_STREAM running mode for non-blocking async inference.
    Results arrive via callback and are stored in `latest_result`.

    Usage:
        engine = PoseEngine()
        engine.process_frame(rgb_frame, timestamp_ms)
        # ... small delay for async processing ...
        result = engine.latest_result  # PoseLandmarkerResult or None
    """

    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        download_model_if_missing()

        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.LIVE_STREAM,
            result_callback=self._result_callback,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)
        self.latest_result = None

        # Store references for frame creation
        self._mp = mp

        logger.info("pose_engine_initialized")

    def _result_callback(self, result, output_image, timestamp_ms: int) -> None:
        """Callback fired by MediaPipe's internal thread when inference completes."""
        self.latest_result = result

    def process_frame(self, frame_rgb: np.ndarray, timestamp_ms: int):
        """
        Submit an RGB frame for async pose detection.

        Args:
            frame_rgb: numpy array of shape (H, W, 3) in RGB color order.
            timestamp_ms: Monotonically increasing timestamp in milliseconds.

        Returns:
            The latest available PoseLandmarkerResult (may be from a
            previous frame due to async processing).
        """
        mp_image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=frame_rgb,
        )
        self.landmarker.detect_async(mp_image, timestamp_ms)
        return self.latest_result

    def close(self) -> None:
        """Release MediaPipe resources."""
        if hasattr(self, "landmarker") and self.landmarker:
            try:
                self.landmarker.close()
            except Exception:
                pass
            logger.info("pose_engine_closed")
