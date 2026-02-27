"""ExtractAnything v1.0 – unified extraction tool.

Entry point: logging setup, crash handling, GUI launch.
"""

import logging
import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Add this directory to sys.path so direct imports (import config,
# from core.xxx import ...) work regardless of what the folder is named.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def _setup_logging() -> None:
    """Configure root logger → file + console."""
    from config import SCRIPT_DIR

    log_file = SCRIPT_DIR / "extractanything.log"
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    _setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("ExtractAnything starting …")

    from config import init_settings
    init_settings()

    root = tk.Tk()

    # Global crash handler
    def _on_error(exc_type, exc_value, exc_tb):
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        try:
            messagebox.showerror(
                "ExtractAnything Error",
                f"{exc_type.__name__}: {exc_value}",
            )
        except Exception:
            pass

    sys.excepthook = _on_error

    from gui import ExtractAnythingApp
    ExtractAnythingApp(root)

    logger.info("GUI ready — entering mainloop")
    root.mainloop()


if __name__ == "__main__":
    main()
