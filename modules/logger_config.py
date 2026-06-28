import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> None:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path / "pipeline.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)

    root = logging.getLogger()
    # Avoid duplicate handlers if setup_logging called more than once
    if root.handlers:
        root.handlers.clear()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    # Suppress DEBUG-level logging from HTTP libraries to prevent
    # accidental API key leakage in request/response dumps.
    for noisy in ("requests", "urllib3", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))
