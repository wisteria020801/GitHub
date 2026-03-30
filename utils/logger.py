import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


_loggers = {}


def setup_logger(
    name: str = "github_radar",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if format_string is None:
        format_string = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"

    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _loggers[name] = logger
    return logger


def get_logger(name: str = "github_radar") -> logging.Logger:
    if name not in _loggers:
        return setup_logger(name)
    return _loggers[name]


logger = setup_logger()
