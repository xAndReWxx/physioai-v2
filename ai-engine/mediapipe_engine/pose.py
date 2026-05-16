import os
# pyrefly: ignore [missing-import]
import urllib.request
# pyrefly: ignore [missing-import]
import mediapipe as mp
# pyrefly: ignore [missing-import]
from mediapipe.tasks import python
# pyrefly: ignore [missing-import]
from mediapipe.tasks.python import vision   
# pyrefly: ignore [missing-import]
from config.settings import settings
from utils.logging import logger
# pyrefly: ignore [missing-import]
import numpy as np

def download_model_if_missing():
    if not os.path.exists(settings.MODEL_PATH):
        logger.info(f"Downloading MediaPipe model from {settings.MODEL_URL}...")
        try:
            urllib.request.urlretrieve(settings.MODEL_URL, settings.MODEL_PATH)
            logger.info("Download complete.")
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            raise

class PoseEngine:
    def __init__(self):
        download_model_if_missing()
        
        base_options = python.BaseOptions(model_asset_path=settings.MODEL_PATH)
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

    def _result_callback(self, result: vision.PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        self.latest_result = result

    def process_frame(self, frame_rgb: np.ndarray, timestamp_ms: int):
        """Processes RGB frame. Expected shape is (H, W, 3)."""
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        self.landmarker.detect_async(mp_image, timestamp_ms)
        
        # We return the latest result which might be from a slightly older frame
        # depending on processing speed, but async API avoids blocking.
        return self.latest_result
