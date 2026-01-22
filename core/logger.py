"""
Logging configuration and utilities.

This module provides centralized logging configuration using loguru.
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def get_logger(
    name: Optional[str] = None,
    verbose: bool = False,
    log_file: Optional[Path] = None,
    level: str = "INFO",
) -> "logger":
    """
    Get a configured logger instance.

    Args:
        name: Logger name (optional)
        verbose: Enable verbose logging
        log_file: Path to log file (optional)
        level: Logging level

    Returns:
        Configured logger instance
    """
    # Remove default handler
    logger.remove()

    # Set log level
    log_level = "DEBUG" if verbose else level

    # Console handler with colors
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        colorize=True,
    )

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="30 days",
            compression="zip",
        )

    # Set the name attribute for compatibility
    if name:
        logger.name = name

    return logger


def setup_logging(
    verbose: bool = False, log_file: Optional[Path] = None, level: str = "INFO"
) -> None:
    """
    Set up global logging configuration.

    Args:
        verbose: Enable verbose logging
        log_file: Path to log file (optional)
        level: Logging level
    """
    get_logger(verbose=verbose, log_file=log_file, level=level)
