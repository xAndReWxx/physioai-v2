"""
============================================================
PhysioAI Pro V2 - Test: Health Endpoints
============================================================
PURPOSE:
    Verify HTTP health check endpoints return correct data.
    These are the simplest tests and serve as a smoke test
    for the entire application setup.
============================================================
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint returns server info."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "PhysioAI Pro V2"
    assert data["status"] == "running"
    assert "version" in data
    assert data["websocket_endpoint"] == "/ws/pose"


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check returns detailed status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "connections" in data
    assert "config" in data
    assert data["connections"]["active"] >= 0


@pytest.mark.asyncio
async def test_readiness_endpoint():
    """Test readiness probe returns ready state."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


@pytest.mark.asyncio
async def test_404_returns_json():
    """Test that 404 errors return structured JSON, not HTML."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/nonexistent")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] is True
    assert "HTTP_404" in data["code"]
