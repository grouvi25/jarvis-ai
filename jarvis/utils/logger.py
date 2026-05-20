"""Логирование для J.A.R.V.I.S."""

import logging

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logger(name: str = "jarvis", level: int = logging.INFO) -> logging.Logger:
    """Настроить логгер с Rich-форматированием."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)

    handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    handler.setLevel(level)

    fmt = logging.Formatter("%(message)s", datefmt="[%H:%M:%S]")
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    file_handler = logging.FileHandler("jarvis.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger


log = setup_logger()
