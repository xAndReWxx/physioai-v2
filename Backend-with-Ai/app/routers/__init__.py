# ============================================================
# PhysioAI Pro V2 - Routers Package
# ============================================================

from app.routers.health import router as health_router
from app.routers.websocket_routes import router as ws_router

__all__ = ["health_router", "ws_router"]
