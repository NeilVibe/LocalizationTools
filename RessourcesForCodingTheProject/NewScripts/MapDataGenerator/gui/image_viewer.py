"""
Image Viewer Module (REDESIGNED)

Large image display with dynamic sizing:
- Default 512×512 display
- Expands to fill available space
- Click to open full-size modal
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageTk

try:
    from config import get_ui_text, THUMBNAIL_SIZE, MAX_INLINE_IMAGE_SIZE
except ImportError:
    from ..config import get_ui_text, THUMBNAIL_SIZE, MAX_INLINE_IMAGE_SIZE

try:
    from core.dds_handler import (
        load_dds_thumbnail,
        load_dds_full,
        create_placeholder_image
    )
except ImportError:
    from ..core.dds_handler import (
        load_dds_thumbnail,
        load_dds_full,
        create_placeholder_image
    )


class ImageViewer(ttk.Frame):
    """
    Large image viewer panel for DDS texture display.

    Features:
    - Dynamic sizing (fills available space)
    - Default 512×512 display
    - Click to enlarge in modal
    - Shows texture name and file info
    """

    def __init__(
        self,
        parent: tk.Widget,
        min_size: Tuple[int, int] = (256, 256),
        preferred_size: Tuple[int, int] = THUMBNAIL_SIZE,
        **kwargs
    ):
        """
        Initialize image viewer.

        Args:
            parent: Parent widget
            min_size: Minimum display size
            preferred_size: Preferred display size (default 512×512)
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._min_size = min_size
        self._preferred_size = preferred_size
        self._current_size = preferred_size
        self._current_path: Optional[Path] = None
        self._current_image: Optional[ImageTk.PhotoImage] = None
        self._placeholder: Optional[ImageTk.PhotoImage] = None
        self._pil_image: Optional[Image.Image] = None

        self._create_widgets()
        self._create_placeholder()

        # Bind resize events
        self.bind("<Configure>", self._on_resize)

    def _create_widgets(self) -> None:
        """Create viewer widgets."""
        # Main container with proper expansion
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Image row expands

        # Header
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)

        self._header_label = ttk.Label(
            header_frame,
            text=get_ui_text('image'),
            font=('TkDefaultFont', 10, 'bold')
        )
        self._header_label.pack(side="left")

        # Image container frame
        self._image_frame = ttk.Frame(self, relief="sunken", borderwidth=1)
        self._image_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self._image_frame.columnconfigure(0, weight=1)
        self._image_frame.rowconfigure(0, weight=1)

        # Image display canvas (large!)
        self._canvas = tk.Canvas(
            self._image_frame,
            width=self._preferred_size[0],
            height=self._preferred_size[1],
            bg="#2d2d2d",  # Dark background for better image contrast
            highlightthickness=0
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")

        # Bind click to show full image
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Enter>", self._on_enter)
        self._canvas.bind("<Leave>", self._on_leave)

        # Info panel below image
        info_frame = ttk.Frame(self)
        info_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=2)

        # Texture name label
        self._texture_label = ttk.Label(
            info_frame,
            text="",
            wraplength=self._preferred_size[0],
            font=('TkDefaultFont', 9)
        )
        self._texture_label.pack(anchor="w")

        # Size and status
        status_frame = ttk.Frame(info_frame)
        status_frame.pack(anchor="w", fill="x")

        self._size_label = ttk.Label(
            status_frame,
            text="",
            font=('TkDefaultFont', 8),
            foreground="gray"
        )
        self._size_label.pack(side="left")

        self._status_label = ttk.Label(
            status_frame,
            text="",
            font=('TkDefaultFont', 8),
            foreground="gray"
        )
        self._status_label.pack(side="right")

    def _create_placeholder(self) -> None:
        """Create placeholder image."""
        placeholder_pil = create_placeholder_image(
            size=self._preferred_size,
            text="No Image Selected"
        )
        self._placeholder = ImageTk.PhotoImage(placeholder_pil)
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        """Display placeholder image."""
        self._canvas.delete("all")

        # Center the placeholder
        canvas_width = self._canvas.winfo_width() or self._preferred_size[0]
        canvas_height = self._canvas.winfo_height() or self._preferred_size[1]

        self._canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self._placeholder,
            anchor="center"
        )
        self._current_image = self._placeholder
        self._pil_image = None
        self._texture_label.config(text="")
        self._size_label.config(text="")
        self._status_label.config(text="")

    def _on_resize(self, event) -> None:
        """Handle resize event - redraw current image."""
        if self._current_path and self._pil_image:
            self._display_image(self._pil_image)
        elif self._current_image == self._placeholder:
            self._show_placeholder()

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

        # Show loading state
        self._status_label.config(text="Loading...")
        self.update_idletasks()

        try:
            # Get canvas size for loading appropriate resolution
            canvas_width = self._canvas.winfo_width() or self._preferred_size[0]
            canvas_height = self._canvas.winfo_height() or self._preferred_size[1]
            display_size = (canvas_width, canvas_height)

            # Load image at display size
            pil_image = load_dds_thumbnail(path, display_size)

            if pil_image:
                self._pil_image = pil_image
                self._display_image(pil_image)
                self._texture_label.config(text=texture_name or path.name)
                self._size_label.config(text=f"Size: {pil_image.size[0]}×{pil_image.size[1]}")
                self._status_label.config(text="Click to enlarge")
            else:
                self._show_placeholder()
                self._texture_label.config(text=texture_name or path.name)
                self._status_label.config(text="(load failed)")

        except Exception as e:
            self._show_placeholder()
            self._texture_label.config(text=texture_name or (path.name if path else ""))
            self._status_label.config(text=f"Error: {str(e)[:30]}")

    def _display_image(self, pil_image: Image.Image) -> None:
        """Display PIL image on canvas, centered and scaled to fit."""
        self._canvas.delete("all")

        canvas_width = self._canvas.winfo_width() or self._preferred_size[0]
        canvas_height = self._canvas.winfo_height() or self._preferred_size[1]

        img_width, img_height = pil_image.size

        # Scale to fit canvas while maintaining aspect ratio
        scale = min(canvas_width / img_width, canvas_height / img_height)

        if scale < 1:
            # Need to scale down
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            display_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            # Image fits, show at original size (or scale up slightly)
            if scale > 1 and img_width < canvas_width // 2 and img_height < canvas_height // 2:
                # Small image - scale up to fill more space (max 2x)
                scale = min(2.0, scale)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                display_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                display_image = pil_image

        # Convert to PhotoImage
        self._current_image = ImageTk.PhotoImage(display_image)

        # Center on canvas
        self._canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self._current_image,
            anchor="center"
        )

    def clear(self) -> None:
        """Clear the displayed image."""
        self._current_path = None
        self._pil_image = None
        self._show_placeholder()

    def set_display_size(self, width: int, height: int) -> None:
        """
        Set the preferred display size.

        Args:
            width: New width
            height: New height
        """
        self._preferred_size = (width, height)
        self._canvas.config(width=width, height=height)

        # Recreate placeholder at new size
        self._create_placeholder()

        # Redraw current image if any
        if self._pil_image:
            self._display_image(self._pil_image)

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
        original_size = (img_width, img_height)

        # Limit window size
        max_width = MAX_INLINE_IMAGE_SIZE[0]
        max_height = MAX_INLINE_IMAGE_SIZE[1]

        if img_width > max_width or img_height > max_height:
            # Need to scale down
            scale = min(max_width / img_width, max_height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            img_width, img_height = new_width, new_height

        # Create PhotoImage
        photo = ImageTk.PhotoImage(pil_image)

        # Canvas
        frame = ttk.Frame(modal)
        frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            frame,
            width=img_width,
            height=img_height,
            bg="#1a1a1a",
            highlightthickness=0
        )
        canvas.create_image(0, 0, image=photo, anchor="nw")
        canvas.image = photo  # Keep reference
        canvas.pack(fill="both", expand=True, padx=5, pady=5)

        # Info bar
        info_frame = ttk.Frame(modal)
        info_frame.pack(fill="x", padx=5, pady=2)

        info_label = ttk.Label(
            info_frame,
            text=f"Original: {original_size[0]}×{original_size[1]} | "
                 f"Display: {img_width}×{img_height} | "
                 f"File: {self._current_path.name}"
        )
        info_label.pack(side="left")

        # Close button
        close_btn = ttk.Button(info_frame, text="Close (Esc)", command=modal.destroy)
        close_btn.pack(side="right", padx=5)

        # Set window size
        window_width = img_width + 20
        window_height = img_height + 60
        modal.geometry(f"{window_width}x{window_height}")

        # Center on parent
        modal.update_idletasks()
        parent = self.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - modal.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - modal.winfo_height()) // 2
        modal.geometry(f"+{max(0, x)}+{max(0, y)}")

        # Focus and key bindings
        modal.focus_set()
        modal.grab_set()
        modal.bind("<Escape>", lambda e: modal.destroy())
        modal.bind("<Return>", lambda e: modal.destroy())
        modal.bind("<space>", lambda e: modal.destroy())
