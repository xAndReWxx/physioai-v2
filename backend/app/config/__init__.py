# ============================================================
# PhysioAI Pro V2 - Configuration Package
# ============================================================
# Centralized configuration management.
# All settings are loaded from environment variables via Pydantic.
# ============================================================

from app.config.settings import settings

__all__ = ["settings"]
