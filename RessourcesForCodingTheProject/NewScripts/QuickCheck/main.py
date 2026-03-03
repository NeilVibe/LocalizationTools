"""
QuickCheck — Entry Point

Multi-language LINE CHECK and TERM CHECK tool.
Inherits proven check logic from QuickSearch, adds multi-language batch mode.
"""
from __future__ import annotations

import logging
import os
import sys

# Ensure project root is on sys.path for direct imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _setup_logging() -> None:
    """Configure logging to both console and a rotating log file."""
    import logging.handlers
    from config import get_base_dir

    log_dir = os.path.join(get_base_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "quickcheck.log")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — DEBUG level, rotating
    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root_logger.addHandler(fh)

    # Console handler — INFO level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root_logger.addHandler(ch)


def main() -> None:
    _setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("QuickCheck starting...")

    try:
        from gui.app import QuickCheckApp
        app = QuickCheckApp()
        app.mainloop()
    except Exception:
        logger.exception("Fatal error during startup")
        raise


if __name__ == "__main__":
    main()
