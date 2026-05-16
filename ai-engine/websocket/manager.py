# pyrefly: ignore [missing-import]
from fastapi import WebSocket
from typing import Dict
from core.pipeline import process_stream
from utils.logging import logger

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, bool] = {}

    async def connect_and_serve(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = True
        logger.info("Client connected.")
        
        try:
            await process_stream(websocket)
        finally:
            self.disconnect(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
            logger.info("Client disconnected.")

manager = ConnectionManager()
