"""
Centralized logging configuration using loguru.
Provides setup_logger() and get_logger() for consistent logging across modules.
"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger

# Global flag to avoid duplicate setup
_logger_initialized = False

def setup_logger(
    log_file: Optional[str] = None,
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "7 days",
    json_format: bool = False
    ):
    global _logger_initialized
    if _logger_initialized:
        logger.debug("Logger already configured, skipping reconfiguration.")
        return logger

    # Remove default handler
    logger.remove()

    # Console handler with colored output (unless JSON)
    if not json_format:
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            level=level,
            colorize=True
        )
    else:
        # JSON format for console (machine-readable)
        logger.add(
            sys.stderr,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
            level=level,
            serialize=True
        )

    # File handler if log_file provided
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_path),
            rotation=rotation,
            retention=retention,
            level="DEBUG",  # Always log DEBUG to file for forensic analysis
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            encoding="utf-8",
            enqueue=True,  # Thread-safe asynchronous logging
            backtrace=True,
            diagnose=True
        )
        logger.info(f"Logging to file: {log_path}")

    _logger_initialized = True
    logger.debug("Logger configuration completed.")
    return logger

def get_logger(name: str = None):
    """
    Get a logger instance. If name is provided, it will be bound to the logger.

    Args:
        name: Optional name to bind (e.g., module name).

    Returns:
        A logger instance (bound if name provided).
    """
    if name:
        return logger.bind(name=name)
    return logger