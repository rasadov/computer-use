import os
import sys

from loguru import logger

from backend.core.config import settings


def setup_logger(log_dir: str):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger.remove()

    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        level="DEBUG" if settings.DEBUG else "INFO",
        enqueue=True,
    )

    logger.add(
        os.path.join(log_dir, f"{settings.ENVIRONMENT}_debug_{{time}}.log"),
        rotation="500 MB",
        retention="10 days",
        level="DEBUG",
        compression="zip",
        enqueue=True,
        serialize=True,
    )

    logger.add(
        os.path.join(log_dir, f"{settings.ENVIRONMENT}_error_{{time}}.log"),
        rotation="100 MB",
        retention="1 month",
        level="ERROR",
        backtrace=True,
        diagnose=True,
        enqueue=True,
        serialize=True,
    )
