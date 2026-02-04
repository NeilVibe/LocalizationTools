"""
QuickTranslate GUI Module.

Tkinter-based GUI for QuickTranslate.
"""

import importlib
import sys

# Check tkinter specifically FIRST, then import the rest
try:
    importlib.import_module("tkinter")
except ImportError:
    # tkinter genuinely not available (headless / missing python3-tk)
    QuickTranslateApp = None
    run_app = None
    __all__ = []
else:
    # tkinter is available - import app normally and let real errors propagate
    from .app import QuickTranslateApp, run_app
    __all__ = ["QuickTranslateApp", "run_app"]
