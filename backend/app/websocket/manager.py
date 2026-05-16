"""
============================================================
PhysioAI Pro V2 - WebSocket Connection Manager
============================================================
PURPOSE:
    Manage all active WebSocket connections. This is the central
    hub for tracking, messaging, and cleaning up client sessions.

WHY A CONNECTION MANAGER?
    In a realtime streaming system, you need to:
    1. Track who is connected (for resource management)
    2. Enforce connection limits (prevent overload)
    3. Send messages safely (handle disconnects gracefully)
    4. Clean up on disconnect (prevent memory leaks)
    5. Support broadcast (future: admin notifications)

ARCHITECTURE DECISION:
    The manager is a singleton — one instance shared across the
    entire application. This prevents duplicate tracking and
    ensures consistent state.

    We use asyncio.Lock for thread-safe operations on the
    connections dict. This prevents race conditions when
    multiple clients connect/disconnect simultaneously.

CONCURRENCY SAFETY:
    All mutations to self._connections are protected by
    self._lock (asyncio.Lock). This is critical because:
    - Multiple WebSocket handlers run concurrently
    - A client could disconnect while another connects
    - Without locking, we'd get dict mutation during iteration
============================================================
"""

import asyncio
from typing import Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.config import settings
from app.core.exceptions import ConnectionLimitError
from app.utils.logger import get_logger
from app.utils.helpers import generate_client_id

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages all active WebSocket connections.

    Responsibilities:
        - Track active connections with unique client IDs
        - Enforce maximum connection limits
        - Provide safe message sending (handles disconnects)
        - Clean up resources on disconnect
        - Support graceful shutdown (disconnect all)
    """

    def __init__(self):
        # Dict mapping client_id -> WebSocket connection
        # Using a dict (not a list) for O(1) lookup/removal
        self._connections: Dict[str, WebSocket] = {}

        # Async lock for thread-safe mutations
        self._lock = asyncio.Lock()

        # Track connection metadata for monitoring
        self._metadata: Dict[str, dict] = {}

    @property
    def active_count(self) -> int:
        """Number of currently active connections."""
        return len(self._connections)

    @property
    def client_ids(self) -> list:
        """List of all connected client IDs."""
        return list(self._connections.keys())

    async def connect(self, websocket: WebSocket) -> str:
        """
        Accept a new WebSocket connection.

        Steps:
        1. Check if connection limit is reached
        2. Accept the WebSocket handshake
        3. Generate a unique client ID
        4. Store the connection
        5. Log the event

        Args:
            websocket: The incoming WebSocket connection.

        Returns:
            The unique client_id assigned to this connection.

        Raises:
            ConnectionLimitError: If max connections reached.
        """
        async with self._lock:
            # Check connection limit BEFORE accepting
            if self.active_count >= settings.ws_max_connections:
                logger.warning(
                    "connection_rejected",
                    reason="limit_reached",
                    active=self.active_count,
                    max=settings.ws_max_connections,
                )
                raise ConnectionLimitError(settings.ws_max_connections)

            # Accept the WebSocket handshake
            await websocket.accept()

            # Generate unique client ID
            client_id = generate_client_id()

            # Store connection and metadata
            self._connections[client_id] = websocket
            self._metadata[client_id] = {
                "connected_at": asyncio.get_event_loop().time(),
                "frames_received": 0,
                "frames_processed": 0,
                "last_activity": asyncio.get_event_loop().time(),
            }

            logger.info(
                "client_connected",
                client_id=client_id,
                active_connections=self.active_count,
            )

            return client_id

    async def disconnect(self, client_id: str) -> None:
        """
        Remove a client connection and clean up resources.

        This method is safe to call even if the client is
        already disconnected (idempotent).

        Args:
            client_id: The unique client identifier.
        """
        async with self._lock:
            websocket = self._connections.pop(client_id, None)
            metadata = self._metadata.pop(client_id, {})

            if websocket:
                # Try to close gracefully, but don't crash if already closed
                try:
                    await websocket.close()
                except Exception:
                    pass  # Connection may already be closed

                logger.info(
                    "client_disconnected",
                    client_id=client_id,
                    active_connections=self.active_count,
                    frames_received=metadata.get("frames_received", 0),
                    frames_processed=metadata.get("frames_processed", 0),
                )

    async def disconnect_all(self) -> None:
        """
        Disconnect all active clients.

        Used during graceful server shutdown to ensure all
        connections are properly closed.
        """
        # Copy keys to avoid dict mutation during iteration
        client_ids = list(self._connections.keys())

        logger.info("disconnecting_all_clients", count=len(client_ids))

        for client_id in client_ids:
            await self.disconnect(client_id)

        logger.info("all_clients_disconnected")

    async def send_json(self, client_id: str, data: dict) -> bool:
        """
        Send a JSON message to a specific client.

        Returns True if the message was sent successfully,
        False if the client is disconnected or the send failed.

        This method NEVER raises an exception — it's designed
        to be safe for use in async loops where you don't want
        a single failed send to crash the entire pipeline.

        Args:
            client_id: Target client identifier.
            data: Dictionary to send as JSON.

        Returns:
            True if sent successfully, False otherwise.
        """
        websocket = self._connections.get(client_id)

        if not websocket:
            logger.debug("send_failed", client_id=client_id, reason="not_connected")
            return False

        try:
            await websocket.send_json(data)
            return True
        except WebSocketDisconnect:
            logger.info("send_failed_disconnect", client_id=client_id)
            await self.disconnect(client_id)
            return False
        except Exception as e:
            logger.error(
                "send_failed_error",
                client_id=client_id,
                error=str(e),
            )
            await self.disconnect(client_id)
            return False

    async def send_error(
        self, client_id: str, code: str, message: str, details: str = None
    ) -> bool:
        """
        Send an error packet to a specific client.

        Convenience method that constructs an error packet
        and sends it via send_json.

        Args:
            client_id: Target client identifier.
            code: Machine-readable error code.
            message: Human-readable error description.
            details: Optional additional context.

        Returns:
            True if sent successfully, False otherwise.
        """
        error_data = {
            "type": "error",
            "code": code,
            "message": message,
        }
        if details:
            error_data["details"] = details

        return await self.send_json(client_id, error_data)

    async def broadcast(self, data: dict, exclude: Optional[str] = None) -> int:
        """
        Send a message to all connected clients.

        Useful for future features like system announcements
        or server-wide notifications.

        Args:
            data: Dictionary to send as JSON.
            exclude: Optional client_id to exclude from broadcast.

        Returns:
            Number of clients that received the message.
        """
        sent_count = 0
        for client_id in list(self._connections.keys()):
            if client_id != exclude:
                if await self.send_json(client_id, data):
                    sent_count += 1
        return sent_count

    def update_metadata(self, client_id: str, **kwargs) -> None:
        """
        Update tracking metadata for a client.

        Args:
            client_id: The client to update.
            **kwargs: Key-value pairs to update in metadata.
        """
        if client_id in self._metadata:
            self._metadata[client_id].update(kwargs)

    def get_metadata(self, client_id: str) -> dict:
        """Get metadata for a specific client."""
        return self._metadata.get(client_id, {})

    def increment_counter(self, client_id: str, counter: str) -> None:
        """Increment a counter in client metadata."""
        if client_id in self._metadata:
            self._metadata[client_id][counter] = (
                self._metadata[client_id].get(counter, 0) + 1
            )


# ============================================================
# SINGLETON INSTANCE
# ============================================================
# Import this everywhere: `from app.websocket import connection_manager`
# ============================================================
connection_manager = ConnectionManager()
