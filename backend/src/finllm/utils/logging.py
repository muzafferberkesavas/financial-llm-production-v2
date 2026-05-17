from __future__ import annotations

import sys

from loguru import logger

from finllm.config.settings import settings

logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <cyan>{name}</cyan> - {message}",
)

__all__ = ["logger"]
