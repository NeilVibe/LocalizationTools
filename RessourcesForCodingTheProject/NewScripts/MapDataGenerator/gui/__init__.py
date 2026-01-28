"""
MapDataGenerator GUI Module

Contains:
- app: Main application window
- search_panel: Search interface
- result_panel: Search results display
- image_viewer: DDS image display
- map_canvas: Matplotlib map visualization
"""

try:
    from .app import MapDataGeneratorApp
    __all__ = ['MapDataGeneratorApp']
except ImportError:
    # tkinter not available (e.g., headless Linux)
    __all__ = []
