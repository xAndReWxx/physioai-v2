"""
============================================================
PhysioAI Pro V2 - Application Settings
============================================================
PURPOSE:
    Centralized configuration using Pydantic Settings.
    All values are loaded from environment variables (.env file)
    with sensible defaults for development.

WHY PYDANTIC SETTINGS?
    - Type-safe configuration (catches errors at startup, not runtime)
    - Automatic .env file loading
    - Validation on startup (fail fast if config is wrong)
    - Easy to override per-environment (dev/staging/prod)

ARCHITECTURE DECISION:
    We use a singleton pattern — one 'settings' instance imported
    everywhere. This prevents inconsistent config across modules.
============================================================
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """
    Application-wide configuration.

    Every setting here can be overridden via environment variables.
    The .env file is loaded automatically by Pydantic.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Application Identity ---
    app_name: str = Field(default="PhysioAI Pro V2", description="Application display name")
    app_version: str = Field(default="2.0.0", description="Current application version")
    app_env: str = Field(default="development", description="Environment: development/staging/production")
    debug: bool = Field(default=True, description="Enable debug mode (verbose logging, error details)")

    # --- Network Configuration ---
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8000, description="Server bind port")

    # --- WebSocket Configuration ---
    # These values control connection behavior and resource limits.
    # MAX_CONNECTIONS prevents server overload from too many simultaneous clients.
    # HEARTBEAT_INTERVAL keeps connections alive through NAT/proxy timeouts.
    # MAX_MESSAGE_SIZE prevents memory exhaustion from oversized frames.
    ws_max_connections: int = Field(default=50, description="Maximum simultaneous WebSocket connections")
    ws_heartbeat_interval: int = Field(default=30, description="Heartbeat ping interval in seconds")
    ws_max_message_size: int = Field(default=1_048_576, description="Max WebSocket message size in bytes (1MB)")

    # --- Frame Processing ---
    # These control the realtime video processing pipeline.
    # MAX_FPS caps the processing rate to prevent CPU overload.
    # TARGET_FPS is what we aim for in the response payload.
    # MAX_FRAME_SIZE prevents processing absurdly large images.
    max_fps: int = Field(default=25, description="Maximum frames per second to process")
    target_fps: int = Field(default=20, description="Target FPS reported to clients")
    max_frame_size_bytes: int = Field(default=524_288, description="Max frame size in bytes (512KB)")

    # --- CORS Configuration ---
    # Comma-separated list of allowed origins for cross-origin requests.
    # This is critical for mobile/tablet browser clients.
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:8080",
        description="Comma-separated list of allowed CORS origins"
    )

    # --- Logging ---
    log_level: str = Field(default="DEBUG", description="Logging level: DEBUG/INFO/WARNING/ERROR")
    log_format: str = Field(default="console", description="Log format: console/json")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"






# ============================================================
# SINGLETON INSTANCE
# ============================================================
# Import this everywhere: `from app.config import settings`
# This ensures all modules share the same configuration.
# ============================================================
settings = Settings()
