import sys
import platform

print("=== PhysioAI Environment Verification ===")

# Check Python version
py_version = sys.version_info
if py_version.major == 3 and py_version.minor >= 11:
    print(f"✅ Python {py_version.major}.{py_version.minor} detected.")
else:
    print(f"❌ Python 3.11+ required. Found: {sys.version}")

# Check MediaPipe
try:
    # pyrefly: ignore [missing-import]
    import mediapipe as mp
    print(f"✅ MediaPipe imported successfully (v{mp.__version__}).")
except ImportError as e:
    print(f"❌ MediaPipe import failed: {e}")

# Check OpenCV
try:
    # pyrefly: ignore [missing-import]
    import cv2
    print(f"✅ OpenCV imported successfully (v{cv2.__version__}).")
except ImportError as e:
    print(f"❌ OpenCV import failed: {e}")

# Check FastAPI
try:
    # pyrefly: ignore [missing-import]
    import fastapi
    print(f"✅ FastAPI imported successfully (v{fastapi.__version__}).")
except ImportError as e:
    print(f"❌ FastAPI import failed: {e}")

# Check WebSockets
try:
    # pyrefly: ignore [missing-import]
    import websockets
    print(f"✅ WebSockets imported successfully (v{websockets.__version__}).")
except ImportError as e:
    print(f"❌ WebSockets import failed: {e}")

print("=========================================")
