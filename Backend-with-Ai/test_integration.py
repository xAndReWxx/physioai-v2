import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

"""
  6. Result packet schema
  7. Per-client cleanup
"""

import asyncio
import base64
import sys
import os

# Ensure the backend app is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def main():
    print("=" * 60)
    print("PhysioAI Pro V2 — Integration Smoke Test")
    print("=" * 60)

    # ---- 1. Import test ----
    print("\n[1/7] Testing imports...")
    try:
        from app.services.ai_engine import ai_engine, _AI_AVAILABLE
        from app.services.frame_router import frame_router
        from app.models.packets import FramePacket, PoseResultPacket
        print(f"  ✓ All imports successful")
        print(f"  ✓ MediaPipe available: {_AI_AVAILABLE}")
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return

    # ---- 2. AI engine init ----
    print("\n[2/7] Initializing AI engine...")
    try:
        await ai_engine.initialize()
        print(f"  ✓ AI engine initialized (mode: {'mediapipe' if ai_engine._ai_mode else 'placeholder'})")
    except Exception as e:
        print(f"  ✗ Init failed: {e}")
        return

    # ---- 3. Create a dummy frame (small red JPEG) ----
    print("\n[3/7] Creating test frame...")
    try:
        import numpy as np
        import cv2
        # Create a 320x240 solid-color test image
        test_img = np.zeros((240, 320, 3), dtype=np.uint8)
        test_img[:, :] = (0, 100, 200)  # BGR orange-ish
        _, jpeg_bytes = cv2.imencode(".jpg", test_img)
        frame_b64 = base64.b64encode(jpeg_bytes.tobytes()).decode("utf-8")
        print(f"  ✓ Test frame created ({len(frame_b64)} chars base64, {len(jpeg_bytes)} bytes JPEG)")
    except Exception as e:
        print(f"  ✗ Frame creation failed: {e}")
        return

    # ---- 4. Process frame through AI engine ----
    print("\n[4/7] Processing frame through AI engine...")
    client_id = "test_client_001"
    try:
        result = await ai_engine.process_frame(
            frame_data=frame_b64,
            client_id=client_id,
        )
        print(f"  ✓ Frame processed successfully")
        print(f"    type:          {result.get('type')}")
        print(f"    fps:           {result.get('fps')}")
        print(f"    landmarks:     {len(result.get('landmarks', []))} points")
        print(f"    posture_score: {result.get('posture_score')}")
        print(f"    feedback:      {result.get('feedback', '')[:60]}")
        print(f"    exercise_data: {result.get('exercise_data')}")
    except Exception as e:
        print(f"  ✗ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # ---- 5. Validate result schema ----
    print("\n[5/7] Validating result schema...")
    try:
        packet = PoseResultPacket(**result)
        print(f"  ✓ Result passes PoseResultPacket validation")
    except Exception as e:
        print(f"  ✗ Schema validation failed: {e}")

    # ---- 6. Process multiple frames (FPS test) ----
    print("\n[6/7] Processing 5 consecutive frames...")
    try:
        import time
        start = time.time()
        for i in range(5):
            r = await ai_engine.process_frame(frame_data=frame_b64, client_id=client_id)
        elapsed = time.time() - start
        avg_ms = (elapsed / 5) * 1000
        print(f"  ✓ 5 frames processed in {elapsed:.2f}s (avg {avg_ms:.1f}ms/frame)")
        print(f"    Last FPS: {r.get('fps')}")
    except Exception as e:
        print(f"  ✗ Multi-frame test failed: {e}")

    # ---- 7. Cleanup ----
    print("\n[7/7] Testing cleanup...")
    try:
        frame_router.cleanup_client(client_id)
        await ai_engine.cleanup()
        print(f"  ✓ Client and engine cleanup successful")
    except Exception as e:
        print(f"  ✗ Cleanup failed: {e}")

    print("\n" + "=" * 60)
    print("INTEGRATION SMOKE TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
