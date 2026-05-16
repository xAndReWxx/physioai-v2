"""
============================================================
PhysioAI Pro V2 - WebSocket Routes
============================================================
PURPOSE:
    Define the WebSocket endpoint(s) for the application.
    Routes are separate from the handler logic — the route
    just delegates to the handler.

WHY SEPARATE FROM HANDLER?
    - Routes are FastAPI-specific (decorators, path definitions)
    - Handler is pure business logic (testable without FastAPI)
    - Easy to add new WebSocket endpoints later
    - Clean separation of concerns

ENDPOINT:
    WS /ws/pose → Main pose streaming endpoint
============================================================
"""

from fastapi import APIRouter, WebSocket

from app.websocket.handler import websocket_handler

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/pose")
async def pose_websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for realtime pose streaming.

    Protocol:
    1. Client connects to ws://host:port/ws/pose
    2. Server accepts and sends connection config
    3. Client sends frame packets (base64 JPEG)
    4. Server responds with pose analysis results
    5. Either side can close the connection

    This endpoint delegates all logic to the websocket_handler.
    """
    await websocket_handler(websocket)
