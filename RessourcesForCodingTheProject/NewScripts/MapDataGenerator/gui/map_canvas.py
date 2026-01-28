"""
Map Canvas Module

Matplotlib-based map visualization with:
- Scatter plot for nodes
- Line2D for routes
- Hover annotation with name/description
- Selected node highlighting
- Pan/zoom via NavigationToolbar
"""

import tkinter as tk
from tkinter import ttk
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

try:
    from config import get_ui_text
    from core.linkage import LinkageResolver, Route
    from core.language import LanguageTable, get_translation
except ImportError:
    from ..config import get_ui_text
    from ..core.linkage import LinkageResolver, Route
    from ..core.language import LanguageTable, get_translation


class MapCanvas(ttk.Frame):
    """Matplotlib-based map canvas for node visualization."""

    def __init__(
        self,
        parent: tk.Widget,
        on_node_click: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """
        Initialize map canvas.

        Args:
            parent: Parent widget
            on_node_click: Callback when a node is clicked (receives strkey)
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._on_node_click = on_node_click
        self._resolver: Optional[LinkageResolver] = None
        self._lang_table: LanguageTable = {}

        # Node data
        self._node_keys: List[str] = []
        self._node_positions: List[Tuple[float, float]] = []
        self._selected_node: Optional[str] = None

        # Route line objects
        self._route_lines: List[matplotlib.lines.Line2D] = []
        self._key_to_lines: Dict[str, List[int]] = defaultdict(list)

        # Colors
        self._default_color = "crimson"
        self._selected_color = "blue"
        self._highlight_color = "gold"
        self._route_color = "royalblue"

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create canvas widgets."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=5, pady=2)

        self._header_label = ttk.Label(
            header_frame,
            text=get_ui_text('map')
        )
        self._header_label.pack(side="left")

        # Create matplotlib figure
        self._fig = Figure(figsize=(8, 6), dpi=100)
        self._ax = self._fig.add_subplot(111)

        self._ax.set_title("World Map - Click to select node")
        self._ax.set_xlabel("X")
        self._ax.set_ylabel("Z")

        # Create Tkinter canvas
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Navigation toolbar
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(fill="x")
        self._toolbar = NavigationToolbar2Tk(self._canvas, toolbar_frame)
        self._toolbar.update()

        # Annotation for hover
        self._annot = self._ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="white", alpha=0.9),
            arrowprops=dict(arrowstyle="->"),
            fontsize=8
        )
        self._annot.set_visible(False)

        # Connect events
        self._canvas.mpl_connect("motion_notify_event", self._on_hover)
        self._canvas.mpl_connect("pick_event", self._on_pick)
        self._canvas.mpl_connect("figure_leave_event", self._on_leave)

        # Scatter plot placeholder
        self._scatter = None

    def set_data(
        self,
        resolver: LinkageResolver,
        lang_table: LanguageTable
    ) -> None:
        """
        Set data for visualization.

        Args:
            resolver: LinkageResolver with loaded data
            lang_table: Language table for translations
        """
        self._resolver = resolver
        self._lang_table = lang_table

        # Extract node positions
        self._node_keys = []
        self._node_positions = []

        for strkey, node in resolver.faction_nodes.items():
            self._node_keys.append(strkey)
            self._node_positions.append(node.position_2d)

        # Synthesize positions for route endpoints not in nodes
        for route in resolver.routes:
            if route.from_key and route.from_key not in resolver.faction_nodes:
                if route.points:
                    self._node_keys.append(route.from_key)
                    self._node_positions.append(route.points[0])

            if route.to_key and route.to_key not in resolver.faction_nodes:
                if route.points:
                    self._node_keys.append(route.to_key)
                    self._node_positions.append(route.points[-1])

        self._draw_map()

    def _draw_map(self) -> None:
        """Draw the map with nodes and routes."""
        self._ax.clear()

        if not self._node_positions:
            self._ax.set_title("No data loaded")
            self._canvas.draw()
            return

        # Get bounds
        xs = [p[0] for p in self._node_positions]
        zs = [p[1] for p in self._node_positions]

        dx = (max(xs) - min(xs)) * 0.05 or 1
        dz = (max(zs) - min(zs)) * 0.05 or 1

        self._ax.set_xlim(min(xs) - dx, max(xs) + dx)
        self._ax.set_ylim(min(zs) - dz, max(zs) + dz)
        self._ax.set_aspect("equal", adjustable="box")

        # Draw routes (initially invisible)
        self._route_lines = []
        self._key_to_lines = defaultdict(list)

        if self._resolver:
            for route in self._resolver.routes:
                x_pts = [p[0] for p in route.points]
                z_pts = [p[1] for p in route.points]

                line, = self._ax.plot(
                    x_pts, z_pts,
                    color=self._route_color,
                    linewidth=1.5,
                    alpha=0.0,
                    zorder=1
                )

                idx = len(self._route_lines)
                self._route_lines.append(line)

                if route.from_key:
                    self._key_to_lines[route.from_key].append(idx)
                if route.to_key:
                    self._key_to_lines[route.to_key].append(idx)

        # Draw nodes
        colors = [self._default_color] * len(self._node_positions)

        self._scatter = self._ax.scatter(
            xs, zs,
            s=30,
            c=colors,
            picker=True,
            pickradius=5,
            zorder=3,
            edgecolor="black",
            linewidths=0.5
        )

        self._ax.set_title(f"World Map ({len(self._node_keys)} nodes)")
        self._ax.set_xlabel("X")
        self._ax.set_ylabel("Z")

        # Re-create annotation
        self._annot = self._ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="white", alpha=0.9),
            arrowprops=dict(arrowstyle="->"),
            fontsize=8
        )
        self._annot.set_visible(False)

        self._fig.tight_layout()
        self._canvas.draw()

    def _hide_all_routes(self) -> None:
        """Hide all route lines."""
        for line in self._route_lines:
            line.set_alpha(0.0)

    def _on_hover(self, event) -> None:
        """Handle mouse hover."""
        if not event.inaxes or self._scatter is None:
            self._annot.set_visible(False)
            self._hide_all_routes()
            self._canvas.draw_idle()
            return

        cont, ind = self._scatter.contains(event)
        if cont:
            idx = ind["ind"][0]
            pos = self._node_positions[idx]
            strkey = self._node_keys[idx]

            # Get node info
            name_kr = strkey
            name_tr = strkey
            desc = ""

            if self._resolver:
                node = self._resolver.get_node(strkey)
                if node:
                    name_kr = node.name_kr or strkey
                    name_tr_val, _ = get_translation(node.name_kr, self._lang_table, node.name_kr)
                    name_tr = name_tr_val or name_kr

                    desc_tr, _ = get_translation(node.desc_kr, self._lang_table, "")
                    desc = desc_tr or node.desc_kr

            # Build annotation text
            if name_tr and name_tr != name_kr:
                label = f"{name_tr}\nKR: {name_kr}"
            else:
                label = name_kr

            if desc:
                desc_short = desc[:80] + "..." if len(desc) > 80 else desc
                label += f"\n\n{desc_short}"

            # Update annotation
            self._annot.xy = pos
            self._annot.set_text(label)
            self._annot.set_visible(True)

            # Show connected routes
            self._hide_all_routes()
            for line_idx in self._key_to_lines.get(strkey, []):
                self._route_lines[line_idx].set_alpha(1.0)

            self._canvas.draw_idle()
        else:
            self._annot.set_visible(False)
            self._hide_all_routes()
            self._canvas.draw_idle()

    def _on_pick(self, event) -> None:
        """Handle node pick (click)."""
        if event.mouseevent.button != 1:  # Left click only
            return

        idx = event.ind[0]
        strkey = self._node_keys[idx]

        self.select_node(strkey)

        if self._on_node_click:
            self._on_node_click(strkey)

    def _on_leave(self, event) -> None:
        """Handle mouse leave."""
        self._annot.set_visible(False)
        self._hide_all_routes()
        self._canvas.draw_idle()

    def select_node(self, strkey: Optional[str]) -> None:
        """
        Select a node by StrKey.

        Args:
            strkey: Node StrKey to select (None to deselect)
        """
        self._selected_node = strkey

        if self._scatter is None:
            return

        # Reset all colors
        colors = [self._default_color] * len(self._node_keys)

        # Highlight selected
        if strkey and strkey in self._node_keys:
            idx = self._node_keys.index(strkey)
            colors[idx] = self._selected_color

            # Center view on selected node
            pos = self._node_positions[idx]
            self._center_on(pos)

        self._scatter.set_color(colors)
        self._canvas.draw_idle()

    def _center_on(self, pos: Tuple[float, float], margin: float = 0.2) -> None:
        """Center the view on a position."""
        x, z = pos

        # Get current limits
        xlim = self._ax.get_xlim()
        ylim = self._ax.get_ylim()

        # Calculate current ranges
        x_range = xlim[1] - xlim[0]
        z_range = ylim[1] - ylim[0]

        # Set new limits centered on position
        self._ax.set_xlim(x - x_range / 2, x + x_range / 2)
        self._ax.set_ylim(z - z_range / 2, z + z_range / 2)

    def highlight_node(self, strkey: str) -> None:
        """
        Temporarily highlight a node.

        Args:
            strkey: Node StrKey to highlight
        """
        if self._scatter is None:
            return

        if strkey in self._node_keys:
            idx = self._node_keys.index(strkey)
            colors = list(self._scatter.get_facecolors())
            colors[idx] = matplotlib.colors.to_rgba(self._highlight_color)
            self._scatter.set_facecolors(colors)
            self._canvas.draw_idle()

    def clear(self) -> None:
        """Clear the map."""
        self._ax.clear()
        self._node_keys = []
        self._node_positions = []
        self._route_lines = []
        self._key_to_lines = defaultdict(list)
        self._scatter = None
        self._selected_node = None
        self._ax.set_title("No data loaded")
        self._canvas.draw()

    @property
    def selected_node(self) -> Optional[str]:
        """Get currently selected node StrKey."""
        return self._selected_node
