"""
============================================================
PhysioAI Pro V2 - Health Check Router
============================================================
PURPOSE:
    HTTP health check endpoints for monitoring and load balancing.
    These are standard REST endpoints (not WebSocket).

WHY HEALTH CHECKS?
    - Load balancers need to know if the server is healthy
    - Monitoring systems poll these endpoints
    - Kubernetes/Docker health probes
    - Quick status check during development

ENDPOINTS:
    GET /               → Welcome message
    GET /health         → Detailed health status
    GET /health/ready   → Simple readiness check
============================================================
"""

from fastapi import APIRouter

from app.config import settings
from app.websocket.manager import connection_manager

router = APIRouter(tags=["Health"])


@router.get(
    "/",
    summary="Welcome",
    description="Root endpoint with server info.",
)
async def root():
    """
    Root endpoint — returns server identity and version.

    Use this to verify the server is running and accessible.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.app_env,
        "websocket_endpoint": "/ws/pose",
    }


@router.get(
    "/health",
    summary="Health Check",
    description="Detailed server health status.",
)
async def health_check():
    """
    Detailed health check with connection statistics.

    Returns server status, active connections, and configuration.
    Used by monitoring dashboards and alerting systems.
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.app_env,
        "connections": {
            "active": connection_manager.active_count,
            "max": settings.ws_max_connections,
        },
        "config": {
            "target_fps": settings.target_fps,
            "max_fps": settings.max_fps,
            "max_frame_size_bytes": settings.max_frame_size_bytes,
        },
    }


@router.get(
    "/health/ready",
    summary="Readiness Probe",
    description="Simple readiness check for load balancers.",
)
async def readiness_check():
    """
    Simple readiness probe.

    Returns 200 if the server is ready to accept connections.
    Used by Kubernetes readiness probes and load balancers.
    """
    return {"ready": True}
