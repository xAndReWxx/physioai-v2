# pyrefly: ignore [missing-import]
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from websocket.manager import manager
from utils.logging import logger
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up AI Engine...")
    # Preload mediapipe model
    from mediapipe_engine.pose import download_model_if_missing
    download_model_if_missing()
    logger.info("AI Engine ready.")
    yield
    logger.info("Shutting down AI Engine...")

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": f"{settings.APP_NAME} is running"}

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect_and_serve(websocket)
