"""
QuickTranslate GUI Module.

Tkinter-based GUI for QuickTranslate.
"""

try:
    from .app import QuickTranslateApp
    __all__ = ["QuickTranslateApp"]
except ImportError:
    # tkinter not available (headless environment)
    QuickTranslateApp = None
    __all__ = []
