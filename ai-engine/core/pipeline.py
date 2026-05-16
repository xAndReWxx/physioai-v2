import base64
import json
import asyncio
import time
# pyrefly: ignore [missing-import]
import cv2
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
from fastapi import WebSocket, WebSocketDisconnect
# pyrefly: ignore [missing-import]
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from config.settings import settings
from utils.logging import logger
from utils.performance import monitor
from mediapipe_engine.pose import PoseEngine
from tracking.filter import LandmarkFilter
from posture.analyzer import PostureAnalyzer
from exercises.chin_tuck import ChinTuckExercise
from exercises.wall_angel import WallAngelExercise
from exercises.thoracic_ext import ThoracicExtensionExercise

async def process_stream(websocket: WebSocket):
    queue = asyncio.Queue(maxsize=settings.MAX_QUEUE_SIZE)
    
    # Initialize engines per connection
    pose_engine = PoseEngine()
    landmark_filter = LandmarkFilter(alpha=settings.EMA_ALPHA_LANDMARKS)
    posture_analyzer = PostureAnalyzer()
    
    exercises = {
        "chin_tuck": ChinTuckExercise(),
        "wall_angel": WallAngelExercise(),
        "thoracic_extension": ThoracicExtensionExercise()
    }
    
    current_exercise = "chin_tuck" # Default, could be set via first message
    
    async def receiver():
        try:
            while True:
                data = await websocket.receive_text()
                # If queue is full, remove oldest to prevent latency buildup
                if queue.full():
                    try:
                        queue.get_nowait()
                        logger.warning("Queue full, dropping stale frame")
                    except asyncio.QueueEmpty:
                        pass
                await queue.put(data)
        except (WebSocketDisconnect, ConnectionClosedOK, ConnectionClosedError):
            logger.info("Client disconnected from receiver")
        except Exception as e:
            logger.error(f"Receiver error: {e}")

    async def processor():
        nonlocal current_exercise
        try:
            while True:
                start_time = time.time()
                data = await queue.get()
                
                try:
                    payload = json.loads(data)
                    b64_img = payload.get("image")
                    
                    if payload.get("exercise"):
                        exercise_name = payload["exercise"]
                        if exercise_name in exercises and exercise_name != current_exercise:
                            current_exercise = exercise_name
                            exercises[current_exercise].reset()

                    if not b64_img:
                        queue.task_done()
                        continue

                    # Decode base64
                    img_bytes = base64.b64decode(b64_img.split(',')[1] if ',' in b64_img else b64_img)
                    np_arr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    
                    if frame is None:
                        logger.error("Failed to decode image frame")
                        queue.task_done()
                        continue

                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Pose inference
                    timestamp_ms = int(time.time() * 1000)
                    pose_result = pose_engine.process_frame(frame_rgb, timestamp_ms)

                    # By default wait a tiny bit to allow MediaPipe to finish async processing
                    await asyncio.sleep(0.005) 
                    
                    result = pose_engine.latest_result
                    
                    response_data = {
                        "type": "pose_result",
                        "fps": monitor.fps,
                        "landmarks": [],
                        "posture": None,
                        "exercise": None,
                        "latency_ms": monitor.avg_latency_ms
                    }

                    if result and result.pose_landmarks:
                        landmarks = result.pose_landmarks[0] # Single person
                        
                        # Convert to numpy array for filtering
                        lm_array = np.array([[lm.x, lm.y, lm.z, lm.visibility] for lm in landmarks])
                        filtered_lm = landmark_filter.filter(lm_array)
                        
                        # Format response
                        formatted_landmarks = [
                            {"x": float(l[0]), "y": float(l[1]), "z": float(l[2]), "visibility": float(l[3])}
                            for l in filtered_lm
                        ]
                        response_data["landmarks"] = formatted_landmarks
                        
                        # Posture Analysis
                        class TempLM:
                            pass
                        struct_lms = []
                        for l in filtered_lm:
                            t = TempLM()
                            t.x, t.y, t.z, t.visibility = l[0], l[1], l[2], l[3]
                            struct_lms.append(t)
                            
                        score, issues, feedback = posture_analyzer.analyze(struct_lms)
                        response_data["posture"] = {
                            "posture_score": score,
                            "issues": issues,
                            "feedback": feedback
                        }
                        
                        # Exercise Tracking
                        tracker = exercises[current_exercise]
                        exercise_feedback = tracker.process(struct_lms)
                        response_data["exercise"] = exercise_feedback
                        
                    # Calculate latency
                    latency = time.time() - start_time
                    monitor.update(latency)
                    response_data["fps"] = round(monitor.fps, 1)
                    response_data["latency_ms"] = round(monitor.avg_latency_ms, 1)

                    await websocket.send_json(response_data)
                    
                except Exception as e:
                    logger.error(f"Processing error: {e}")
                    await websocket.send_json({"error": str(e)})

                queue.task_done()
                
        except asyncio.CancelledError:
            pass
        except (WebSocketDisconnect, ConnectionClosedOK, ConnectionClosedError):
            logger.info("Client disconnected from processor")
        except Exception as e:
            logger.error(f"Processor fatal error: {e}")
            
    # Run both tasks concurrently
    receiver_task = asyncio.create_task(receiver())
    processor_task = asyncio.create_task(processor())
    
    done, pending = await asyncio.wait(
        [receiver_task, processor_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    
    for task in pending:
        task.cancel()
