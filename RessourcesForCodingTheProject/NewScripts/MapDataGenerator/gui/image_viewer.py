"""
Image Viewer Module

Displays DDS texture images:
- Thumbnail preview in sidebar
- Click to open full-size modal
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional

from PIL import Image, ImageTk

try:
    from config import get_ui_text, THUMBNAIL_SIZE
    from core.dds_handler import (
        load_dds_thumbnail,
        load_dds_full,
        create_placeholder_image
    )
except ImportError:
    from ..config import get_ui_text, THUMBNAIL_SIZE
    from ..core.dds_handler import (
        load_dds_thumbnail,
        load_dds_full,
        create_placeholder_image
    )


class ImageViewer(ttk.Frame):
    """Image viewer panel for DDS texture display."""

    def __init__(
        self,
        parent: tk.Widget,
        thumbnail_size: tuple = THUMBNAIL_SIZE,
        **kwargs
    ):
        """
        Initialize image viewer.

        Args:
            parent: Parent widget
            thumbnail_size: Size for thumbnail display
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._thumbnail_size = thumbnail_size
        self._current_path: Optional[Path] = None
        self._current_image: Optional[ImageTk.PhotoImage] = None
        self._placeholder: Optional[ImageTk.PhotoImage] = None

        self._create_widgets()
        self._create_placeholder()

    def _create_widgets(self) -> None:
        """Create viewer widgets."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=5, pady=2)

        self._header_label = ttk.Label(
            header_frame,
            text=get_ui_text('image')
        )
        self._header_label.pack(side="left")

        # Image display canvas
        self._canvas = tk.Canvas(
            self,
            width=self._thumbnail_size[0],
            height=self._thumbnail_size[1],
            bg="white",
            highlightthickness=1,
            highlightbackground="gray"
        )
        self._canvas.pack(padx=5, pady=5)

        # Bind click to show full image
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Enter>", self._on_enter)
        self._canvas.bind("<Leave>", self._on_leave)

        # Texture name label
        self._texture_label = ttk.Label(
            self,
            text="",
            wraplength=self._thumbnail_size[0],
            font=('Arial', 8)
        )
        self._texture_label.pack(padx=5, pady=2)

        # Status
        self._status_label = ttk.Label(
            self,
            text="",
            font=('Arial', 8),
            foreground="gray"
        )
        self._status_label.pack(padx=5)

    def _create_placeholder(self) -> None:
        """Create placeholder image."""
        placeholder_pil = create_placeholder_image(
            size=self._thumbnail_size,
            text="No Image"
        )
        self._placeholder = ImageTk.PhotoImage(placeholder_pil)
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        """Display placeholder image."""
        self._canvas.delete("all")
        self._canvas.create_image(
            self._thumbnail_size[0] // 2,
            self._thumbnail_size[1] // 2,
            image=self._placeholder,
            anchor="center"
        )
        self._current_image = self._placeholder
        self._texture_label.config(text="")
        self._status_label.config(text="")

    def set_image(self, path: Optional[Path], texture_name: str = "") -> None:
        """
        Set the displayed image.

        Args:
            path: Path to DDS file or None for placeholder
            texture_name: Texture name to display
        """
        self._current_path = path

        if path is None or not path.exists():
            self._show_placeholder()
            if texture_name:
                self._texture_label.config(text=texture_name)
                self._status_label.config(text="(file not found)")
            return

        # Load thumbnail
        self._status_label.config(text="Loading...")
        self.update_idletasks()

        try:
            pil_image = load_dds_thumbnail(path, self._thumbnail_size)
            if pil_image:
                self._current_image = ImageTk.PhotoImage(pil_image)
                self._canvas.delete("all")
                self._canvas.create_image(
                    self._thumbnail_size[0] // 2,
                    self._thumbnail_size[1] // 2,
                    image=self._current_image,
                    anchor="center"
                )
                self._texture_label.config(text=texture_name or path.name)
                self._status_label.config(text="Click to enlarge")
            else:
                self._show_placeholder()
                self._texture_label.config(text=texture_name or path.name)
                self._status_label.config(text="(load failed)")
        except Exception as e:
            self._show_placeholder()
            self._status_label.config(text=f"Error: {str(e)[:20]}")

    def clear(self) -> None:
        """Clear the displayed image."""
        self._current_path = None
        self._show_placeholder()

    def _on_click(self, event) -> None:
        """Handle click - show full image."""
        if self._current_path and self._current_path.exists():
            self._show_full_image()

    def _on_enter(self, event) -> None:
        """Handle mouse enter."""
        if self._current_path and self._current_path.exists():
            self._canvas.config(cursor="hand2")

    def _on_leave(self, event) -> None:
        """Handle mouse leave."""
        self._canvas.config(cursor="")

    def _show_full_image(self) -> None:
        """Show full-size image in modal window."""
        if not self._current_path:
            return

        # Load full image
        pil_image = load_dds_full(self._current_path)
        if not pil_image:
            return

        # Create modal window
        modal = tk.Toplevel(self)
        modal.title(f"Image: {self._current_path.name}")
        modal.transient(self.winfo_toplevel())

        # Get image size
        img_width, img_height = pil_image.size

        # Limit window size
        max_width = 1200
        max_height = 800

        if img_width > max_width or img_height > max_height:
            # Need to scale down
            scale = min(max_width / img_width, max_height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            img_width, img_height = new_width, new_height

        # Create PhotoImage
        photo = ImageTk.PhotoImage(pil_image)

        # Canvas with scrollbars if needed
        frame = ttk.Frame(modal)
        frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(frame, width=img_width, height=img_height)
        canvas.create_image(0, 0, image=photo, anchor="nw")
        canvas.image = photo  # Keep reference

        canvas.pack(fill="both", expand=True)

        # Size info
        info_label = ttk.Label(
            modal,
            text=f"Size: {pil_image.size[0]} x {pil_image.size[1]} | File: {self._current_path.name}"
        )
        info_label.pack(pady=5)

        # Close button
        close_btn = ttk.Button(modal, text="Close", command=modal.destroy)
        close_btn.pack(pady=5)

        # Set window size
        modal.geometry(f"{img_width + 20}x{img_height + 80}")

        # Center on parent
        modal.update_idletasks()
        parent = self.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - modal.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - modal.winfo_height()) // 2
        modal.geometry(f"+{x}+{y}")

        # Focus
        modal.focus_set()
        modal.grab_set()

        # Bind escape to close
        modal.bind("<Escape>", lambda e: modal.destroy())
