"""
============================================================
PhysioAI Pro V2 - WebSocket Message Handler
============================================================
PURPOSE:
    Core message processing loop for WebSocket connections.
    This is where incoming messages are parsed, validated,
    routed, and responded to.

ARCHITECTURE DECISION:
    The handler is a pure async function, not a class. This is
    intentional — each WebSocket connection gets its own handler
    invocation, but they all share the same ConnectionManager
    and services via dependency injection.

MESSAGE FLOW:
    1. Receive raw text message from WebSocket
    2. Parse JSON
    3. Determine packet type
    4. Validate with appropriate Pydantic model
    5. Route to appropriate service
    6. Send response back to client

ERROR HANDLING STRATEGY:
    - Malformed JSON → send error, continue listening
    - Invalid packet → send error, continue listening
    - AI engine error → send error, continue listening
    - Connection closed → clean up, exit loop
    - Unexpected error → log, send error, continue listening

    The handler NEVER crashes. It always tries to recover and
    keep the connection alive. This is critical for realtime
    streaming where dropped connections = bad user experience.
============================================================
"""

import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect

from app.config import settings
from app.core.exceptions import (
    PhysioAIError,
    PacketParseError,
    FrameValidationError,
)
from app.models.packets import FramePacket, HeartbeatPacket, PacketType
from app.services.frame_router import frame_router
from app.utils.logger import get_logger
from app.utils.helpers import get_timestamp_ms
from app.websocket.manager import connection_manager

logger = get_logger(__name__)


async def websocket_handler(websocket: WebSocket) -> None:
    """
    Main WebSocket connection handler.

    This function manages the entire lifecycle of a single
    WebSocket connection:

    1. CONNECT:  Accept connection, assign client ID
    2. LISTEN:   Receive and process messages in a loop
    3. CLEANUP:  Handle disconnection and resource cleanup

    Args:
        websocket: The FastAPI WebSocket connection object.
    """
    client_id = None

    try:
        # ============================
        # PHASE 1: CONNECTION
        # ============================
        client_id = await connection_manager.connect(websocket)

        # Send welcome message with connection info
        await connection_manager.send_json(client_id, {
            "type": "connected",
            "client_id": client_id,
            "config": {
                "max_fps": settings.max_fps,
                "target_fps": settings.target_fps,
                "max_frame_size": settings.max_frame_size_bytes,
                "heartbeat_interval": settings.ws_heartbeat_interval,
            },
            "message": "Connected to PhysioAI Pro V2",
        })

        # ============================
        # PHASE 2: MESSAGE LOOP
        # ============================
        await _message_loop(websocket, client_id)

    except ConnectionError:
        # Connection limit reached — reject gracefully
        logger.warning("connection_rejected_limit", client_id=client_id)
        try:
            await websocket.close(code=1013, reason="Server is at capacity")
        except Exception:
            pass

    except WebSocketDisconnect as e:
        # Normal disconnection (client closed browser, etc.)
        logger.info(
            "client_disconnect_normal",
            client_id=client_id,
            code=e.code,
        )

    except Exception as e:
        # Unexpected error — log it but don't crash the server
        logger.error(
            "handler_unexpected_error",
            client_id=client_id,
            error=str(e),
            error_type=type(e).__name__,
        )

    finally:
        # ============================
        # PHASE 3: CLEANUP
        # ============================
        if client_id:
            await connection_manager.disconnect(client_id)


async def _message_loop(websocket: WebSocket, client_id: str) -> None:
    """
    Core message processing loop.

    Runs continuously until the client disconnects or an
    unrecoverable error occurs.

    Each iteration:
    1. Wait for a message (non-blocking via await)
    2. Parse and validate the message
    3. Route to appropriate handler
    4. Send response

    Args:
        websocket: Active WebSocket connection.
        client_id: Unique client identifier.
    """
    while True:
        try:
            # Wait for next message (this yields to the event loop)
            raw_message = await websocket.receive_text()

            # Update last activity timestamp
            connection_manager.update_metadata(
                client_id,
                last_activity=asyncio.get_event_loop().time(),
            )

            # Parse and route the message
            await _process_message(raw_message, client_id)

        except WebSocketDisconnect:
            # Re-raise to be handled by the outer handler
            raise

        except json.JSONDecodeError as e:
            # Client sent invalid JSON
            logger.warning(
                "invalid_json_received",
                client_id=client_id,
                error=str(e),
            )
            await connection_manager.send_error(
                client_id,
                code="INVALID_JSON",
                message="Message is not valid JSON",
                details=str(e),
            )

        except PacketParseError as e:
            # Client sent valid JSON but invalid packet structure
            logger.warning(
                "invalid_packet",
                client_id=client_id,
                error=e.message,
            )
            await connection_manager.send_error(
                client_id,
                code=e.code,
                message=e.message,
            )

        except FrameValidationError as e:
            # Frame data failed validation
            logger.warning(
                "frame_validation_failed",
                client_id=client_id,
                error=e.message,
            )
            await connection_manager.send_error(
                client_id,
                code=e.code,
                message=e.message,
            )

        except PhysioAIError as e:
            # Any other application-level error
            logger.error(
                "application_error",
                client_id=client_id,
                code=e.code,
                error=e.message,
            )
            await connection_manager.send_error(
                client_id,
                code=e.code,
                message=e.message,
            )

        except Exception as e:
            # Catch-all for unexpected errors
            # Log the full error but send a sanitized message to client
            logger.error(
                "unexpected_processing_error",
                client_id=client_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            await connection_manager.send_error(
                client_id,
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
            )


async def _process_message(raw_message: str, client_id: str) -> None:
    """
    Parse, validate, and route a single WebSocket message.

    This function is the packet-level dispatcher:
    1. Parse JSON
    2. Extract packet type
    3. Validate with appropriate model
    4. Route to handler

    Args:
        raw_message: Raw JSON string from WebSocket.
        client_id: Client that sent the message.

    Raises:
        PacketParseError: If the message cannot be parsed.
        FrameValidationError: If frame data is invalid.
    """
    # Parse JSON
    data = json.loads(raw_message)

    # Extract packet type
    packet_type = data.get("type")
    if not packet_type:
        raise PacketParseError("Missing 'type' field in packet")

    # Route based on packet type
    if packet_type == PacketType.FRAME.value:
        await _handle_frame(data, client_id)

    elif packet_type == PacketType.HEARTBEAT.value:
        await _handle_heartbeat(data, client_id)

    else:
        raise PacketParseError(f"Unknown packet type: '{packet_type}'")


async def _handle_frame(data: dict, client_id: str) -> None:
    """
    Handle an incoming camera frame.

    Steps:
    1. Validate frame packet with Pydantic
    2. Track frame count
    3. Route to AI engine via frame_router
    4. Send pose result back to client

    Args:
        data: Raw packet data dict.
        client_id: Client that sent the frame.
    """
    # Record processing start time for latency measurement
    start_time = get_timestamp_ms()

    # Validate frame packet using Pydantic model
    # This will raise ValidationError if the data is invalid
    try:
        frame_packet = FramePacket(**data)
    except Exception as e:
        raise FrameValidationError(f"Invalid frame packet: {e}")

    # Track frame count
    connection_manager.increment_counter(client_id, "frames_received")

    # Route frame to AI engine for processing
    # The frame_router handles the actual AI pipeline
    result = await frame_router.process_frame(frame_packet, client_id)

    # Calculate server-side processing latency
    processing_time = get_timestamp_ms() - start_time

    # Add latency to the result
    result["latency_ms"] = processing_time

    # Track processed frame count
    connection_manager.increment_counter(client_id, "frames_processed")

    # Send result back to client
    await connection_manager.send_json(client_id, result)

    # Log frame processing (debug level to avoid log spam)
    logger.debug(
        "frame_processed",
        client_id=client_id,
        latency_ms=processing_time,
        posture_score=result.get("posture_score", 0),
    )


async def _handle_heartbeat(data: dict, client_id: str) -> None:
    """
    Handle a heartbeat (keep-alive) message.

    Responds with a heartbeat pong to confirm the connection
    is still alive. This is important for mobile networks that
    aggressively close idle connections.

    Args:
        data: Raw heartbeat data.
        client_id: Client that sent the heartbeat.
    """
    # Validate heartbeat packet
    HeartbeatPacket(**data)

    # Respond with pong
    await connection_manager.send_json(client_id, {
        "type": "heartbeat",
        "timestamp": get_timestamp_ms() / 1000,
        "server_time": get_timestamp_ms(),
    })

    logger.debug("heartbeat_received", client_id=client_id)
