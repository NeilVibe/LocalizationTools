"""
Map Canvas Module (SIMPLIFIED)

Shows nodes on a 2D scatter plot - no routes, just positions.
"""

import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

# Ensure parent directory is in sys.path for PyInstaller compatibility
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_ui_text
from core.linkage import LinkageResolver
from core.language import LanguageTable, get_translation


class MapCanvas(ttk.Frame):
    """Simple scatter plot map showing node positions."""

    def __init__(
        self,
        parent: tk.Widget,
        on_node_click: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)

        self._on_node_click = on_node_click
        self._resolver: Optional[LinkageResolver] = None
        self._lang_table: LanguageTable = {}

        # Node positions: strkey -> (x, z)
        self._node_positions: Dict[str, Tuple[float, float]] = {}
        self._selected_strkey: Optional[str] = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create matplotlib canvas."""
        # Create figure
        self._figure = Figure(figsize=(8, 6), dpi=100, facecolor='#2d2d2d')
        self._ax = self._figure.add_subplot(111)
        self._ax.set_facecolor('#1a1a1a')

        # Style
        self._ax.tick_params(colors='white')
        self._ax.xaxis.label.set_color('white')
        self._ax.yaxis.label.set_color('white')
        for spine in self._ax.spines.values():
            spine.set_color('gray')

        # Canvas
        self._canvas = FigureCanvasTkAgg(self._figure, self)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

        # Toolbar
        toolbar = NavigationToolbar2Tk(self._canvas, self)
        toolbar.update()

        # Scatter plot reference
        self._scatter = None
        self._selected_scatter = None
        self._strkeys: List[str] = []

        # Annotation for hover
        self._annot = self._ax.annotate(
            "", xy=(0, 0), xytext=(10, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="white", alpha=0.9),
            arrowprops=dict(arrowstyle="->"),
            fontsize=9,
            visible=False
        )

        # Connect events
        self._canvas.mpl_connect('motion_notify_event', self._on_hover)
        self._canvas.mpl_connect('button_press_event', self._on_click)

    def set_data(self, resolver: LinkageResolver, lang_table: LanguageTable) -> None:
        """Set data and redraw map."""
        self._resolver = resolver
        self._lang_table = lang_table
        self._node_positions.clear()

        # Collect node positions
        for strkey, entry in resolver.entries.items():
            if entry.position_2d:
                self._node_positions[strkey] = entry.position_2d

        self._draw_map()

    def _draw_map(self) -> None:
        """Draw nodes on the map."""
        self._ax.clear()
        self._ax.set_facecolor('#1a1a1a')

        # Recreate annotation after ax.clear() (clear removes all artists)
        self._annot = self._ax.annotate(
            "", xy=(0, 0), xytext=(10, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="white", alpha=0.9),
            arrowprops=dict(arrowstyle="->"),
            fontsize=9,
            visible=False
        )

        # Reset selection scatter reference (also removed by clear)
        self._selected_scatter = None

        if not self._node_positions:
            self._ax.text(0.5, 0.5, "No nodes with positions",
                         transform=self._ax.transAxes,
                         ha='center', va='center', color='gray')
            self._canvas.draw()
            return

        # Prepare data
        xs = []
        zs = []
        self._strkeys = []
        colors = []

        for strkey, (x, z) in self._node_positions.items():
            xs.append(x)
            zs.append(z)
            self._strkeys.append(strkey)

            # Color based on image availability
            entry = self._resolver.get_entry(strkey)
            if entry and entry.has_image:
                colors.append('#00ff00')  # Green = has image
            else:
                colors.append('#ff6666')  # Red = no image

        # Plot nodes
        self._scatter = self._ax.scatter(
            xs, zs,
            c=colors,
            s=30,
            alpha=0.8,
            edgecolors='white',
            linewidths=0.5,
            picker=True
        )

        # Axis labels
        self._ax.set_xlabel("X", color='white')
        self._ax.set_ylabel("Z", color='white')
        self._ax.tick_params(colors='white')

        # Title
        total = len(self._node_positions)
        with_image = sum(1 for sk in self._strkeys
                        if self._resolver.get_entry(sk) and self._resolver.get_entry(sk).has_image)
        self._ax.set_title(f"Map: {total} nodes ({with_image} with images)", color='white')

        self._figure.tight_layout()
        self._canvas.draw()

    def _on_hover(self, event) -> None:
        """Show tooltip on hover."""
        if event.inaxes != self._ax or self._scatter is None:
            self._annot.set_visible(False)
            self._canvas.draw_idle()
            return

        cont, ind = self._scatter.contains(event)
        if cont:
            idx = ind["ind"][0]
            strkey = self._strkeys[idx]
            entry = self._resolver.get_entry(strkey) if self._resolver else None

            if entry:
                name_tr, _ = get_translation(entry.name_kr, self._lang_table, entry.name_kr)
                pos = self._node_positions.get(strkey, (0, 0))

                text = f"{name_tr}\n({pos[0]:.0f}, {pos[1]:.0f})"
                if entry.has_image:
                    text += "\n✓ Has image"
                else:
                    text += "\n✗ No image"

                self._annot.xy = (pos[0], pos[1])
                self._annot.set_text(text)
                self._annot.set_visible(True)
        else:
            self._annot.set_visible(False)

        self._canvas.draw_idle()

    def _on_click(self, event) -> None:
        """Handle click on node."""
        if event.inaxes != self._ax or self._scatter is None:
            return

        cont, ind = self._scatter.contains(event)
        if cont:
            idx = ind["ind"][0]
            strkey = self._strkeys[idx]
            self.select_node(strkey)

            if self._on_node_click:
                self._on_node_click(strkey)

    def select_node(self, strkey: str) -> None:
        """Highlight a selected node."""
        if strkey not in self._node_positions:
            return

        self._selected_strkey = strkey
        pos = self._node_positions[strkey]

        # Remove old selection
        if self._selected_scatter:
            self._selected_scatter.remove()

        # Add selection highlight
        self._selected_scatter = self._ax.scatter(
            [pos[0]], [pos[1]],
            c='yellow',
            s=100,
            alpha=0.8,
            edgecolors='white',
            linewidths=2,
            zorder=10
        )

        self._canvas.draw_idle()

    def clear_selection(self) -> None:
        """Clear node selection."""
        self._selected_strkey = None
        if self._selected_scatter:
            self._selected_scatter.remove()
            self._selected_scatter = None
        self._canvas.draw_idle()
