"""Логирование для J.A.R.V.I.S."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from rich.console import Console
from rich.logging import RichHandler

from jarvis.utils.paths import LOG_FILE, ensure_dirs

console = Console()


def setup_logger(name: str = "jarvis", level: int = logging.INFO) -> logging.Logger:
    """Настроить логгер с Rich-форматированием + ротирующий файл."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%H:%M:%S]"))
    logger.addHandler(handler)

    try:
        ensure_dirs()
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
        logger.addHandler(file_handler)
    except Exception:
        # Файловое логирование не критично
        pass

    return logger


log = setup_logger()
