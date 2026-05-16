"""
============================================================
PhysioAI Pro V2 - Main Application Entry Point
============================================================
PURPOSE:
    Create and configure the FastAPI application instance.
    This is where everything comes together:
    - CORS middleware
    - Error handlers
    - Route registration
    - Lifespan events

WHY THIS STRUCTURE?
    The 'create_app()' factory pattern allows:
    - Clean testing (create fresh app per test)
    - Configuration injection
    - Multiple app instances if needed
    - Clear initialization order

STARTUP FLOW:
    1. Create FastAPI instance with lifespan
    2. Add CORS middleware (required for browser clients)
    3. Register error handlers
    4. Include route modules
    5. Server starts via uvicorn

RUNNING:
    Development:  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    Production:   uvicorn app.main:app --workers 1 --host 0.0.0.0 --port 8000

NOTE ON WORKERS:
    WebSocket applications should typically run with a SINGLE worker
    because WebSocket connections are stateful and pinned to the
    process that accepted them. Multiple workers would split
    connections across processes, making the ConnectionManager
    inconsistent. For scaling, use horizontal scaling (multiple
    server instances) with a message broker like Redis.
============================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.events import lifespan
from app.middleware import setup_error_handlers
from app.routers import health_router, ws_router


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI app.

    Returns:
        Fully configured FastAPI application instance.
    """

    # ============================
    # CREATE APP
    # ============================
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Realtime AI-powered physiotherapy posture tracking system. "
            "Accepts camera frames via WebSocket and returns pose analysis "
            "results with posture scoring and coaching feedback."
        ),
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ============================
    # CORS MIDDLEWARE
    # ============================
    # CORS is required for browser-based clients (React, Vue, etc.)
    # and for mobile WebView clients.
    #
    # In development: allow all configured origins
    # In production: restrict to specific domains
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============================
    # ERROR HANDLERS
    # ============================
    setup_error_handlers(application)

    # ============================
    # REGISTER ROUTERS
    # ============================
    # Health check endpoints (HTTP)
    application.include_router(health_router)

    # WebSocket endpoints
    application.include_router(ws_router)

    return application


# ============================================================
# APPLICATION INSTANCE
# ============================================================
# This is what uvicorn imports: `uvicorn app.main:app`
# ============================================================
app = create_app()
