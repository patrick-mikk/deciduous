"""Logging setup for the TUI prototype.

Configures a single rotating-file logger named "planner.tui" that the rest
of backend/tui/ imports and logs through, plus a `sys.excepthook` so
uncaught exceptions land in the log file instead of only flashing past on
stderr (important for a full-screen prompt_toolkit app, which owns the
terminal).
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

LOGGER_NAME = "planner.tui"

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_PATH = LOG_DIR / "tui.log"

_MAX_BYTES = 512 * 1024  # ~512KB per file
_BACKUP_COUNT = 2

_configured = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the "planner.tui" logger.

    Idempotent - safe to call repeatedly (app entry point, tests, etc.).
    The first call creates backend/tui/logs/ if needed and attaches a
    UTF-8 `RotatingFileHandler` pointed at `LOG_PATH` (~512KB x 2 backups),
    plus a `sys.excepthook` that logs uncaught exceptions (then chains to
    whatever hook was previously installed). Later calls only adjust the
    logger/handler level.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    global _configured
    if not _configured:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_PATH,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        handler.setLevel(level)
        logger.addHandler(handler)
        logger.propagate = False

        _install_excepthook(logger)
        _configured = True
    else:
        for handler in logger.handlers:
            handler.setLevel(level)

    return logger


def _install_excepthook(logger: logging.Logger) -> None:
    """Log uncaught exceptions to `logger`, then chain to the prior hook."""
    previous_hook = sys.excepthook

    def _log_uncaught_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            previous_hook(exc_type, exc_value, exc_tb)
            return
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
        previous_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _log_uncaught_exception
