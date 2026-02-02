"""
QuickTranslate GUI Module.

Tkinter-based GUI for QuickTranslate.
"""

try:
    from .app import QuickTranslateApp, run_app
    __all__ = ["QuickTranslateApp", "run_app"]
except ImportError:
    # tkinter not available (headless environment)
    QuickTranslateApp = None
    run_app = None
    __all__ = []
