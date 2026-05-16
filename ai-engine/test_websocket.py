import asyncio
# pyrefly: ignore [missing-import]
import websockets
import json
import base64
# pyrefly: ignore [missing-import]
import cv2
import numpy as np

async def test_websocket():
    uri = "ws://127.0.0.1:8000/ws/stream"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to AI Engine!")
            
            # Create a dummy image to send
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(img, "Test Frame", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            _, buffer = cv2.imencode('.jpg', img)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
            payload = {
                "exercise": "chin_tuck",
                "image": f"data:image/jpeg;base64,{jpg_as_text}"
            }
            
            print("Sending frame...")
            await websocket.send(json.dumps(payload))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            print("\n--- Engine Response ---")
            print(json.dumps(data, indent=2))
            print("-----------------------")
            
    except ConnectionRefusedError:
        print(f"Failed to connect to {uri}. Ensure the server is running.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
