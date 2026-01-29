"""
DDS Handler Module

Handles loading and converting DDS (DirectDraw Surface) texture files
for display in Tkinter using Pillow + pillow-dds.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

# Import pillow-dds to register DDS format handler (Windows only)
# On non-Windows systems, DDS files are typically not available anyway
import sys as _sys
if _sys.platform == "win32":
    try:
        import pillow_dds  # noqa: F401 - imported for side effect (registers DDS handler)
    except ImportError:
        logging.warning("pillow-dds not installed. Run: pip install pillow-dds")

log = logging.getLogger(__name__)


# =============================================================================
# DDS HANDLER CLASS
# =============================================================================

class DDSHandler:
    """
    Handles DDS image loading and conversion.

    Uses Pillow with pillow-dds plugin for DDS format support.
    Implements LRU caching for performance.
    """

    def __init__(self, cache_size: int = 50):
        """
        Initialize DDS handler.

        Args:
            cache_size: Maximum number of images to cache
        """
        self._cache_size = cache_size
        self._thumbnail_cache: dict = {}
        self._full_cache: dict = {}

    def load_dds(self, path: Path) -> Optional[Image.Image]:
        """
        Load a DDS file and convert to PIL Image.

        Args:
            path: Path to DDS file

        Returns:
            PIL Image or None if loading fails
        """
        if not path.exists():
            log.warning("DDS file not found: %s", path)
            return None

        try:
            img = Image.open(path)
            # Convert to RGBA for consistent handling
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            return img
        except Exception as e:
            log.error("Failed to load DDS %s: %s", path, e)
            return None

    def get_thumbnail(
        self,
        path: Path,
        size: Tuple[int, int] = (128, 128)
    ) -> Optional[Image.Image]:
        """
        Get a thumbnail version of a DDS image.

        Uses caching for performance.

        Args:
            path: Path to DDS file
            size: Thumbnail size (width, height)

        Returns:
            PIL Image thumbnail or None
        """
        cache_key = (str(path), size)

        # Check cache
        if cache_key in self._thumbnail_cache:
            return self._thumbnail_cache[cache_key]

        # Load and resize
        img = self.load_dds(path)
        if img is None:
            return None

        # Create thumbnail (maintains aspect ratio)
        img.thumbnail(size, Image.Resampling.LANCZOS)

        # Cache result (with LRU-like behavior)
        if len(self._thumbnail_cache) >= self._cache_size:
            # Remove oldest entry
            oldest = next(iter(self._thumbnail_cache))
            del self._thumbnail_cache[oldest]

        self._thumbnail_cache[cache_key] = img
        return img

    def get_full_image(self, path: Path) -> Optional[Image.Image]:
        """
        Get full-size DDS image.

        Uses caching for performance.

        Args:
            path: Path to DDS file

        Returns:
            PIL Image or None
        """
        cache_key = str(path)

        # Check cache
        if cache_key in self._full_cache:
            return self._full_cache[cache_key]

        # Load full image
        img = self.load_dds(path)
        if img is None:
            return None

        # Cache result (with LRU-like behavior)
        if len(self._full_cache) >= self._cache_size:
            oldest = next(iter(self._full_cache))
            del self._full_cache[oldest]

        self._full_cache[cache_key] = img
        return img

    def clear_cache(self) -> None:
        """Clear all cached images."""
        self._thumbnail_cache.clear()
        self._full_cache.clear()
        log.info("Image cache cleared")

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            'thumbnail_count': len(self._thumbnail_cache),
            'full_count': len(self._full_cache),
            'max_size': self._cache_size,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global handler instance
_handler: Optional[DDSHandler] = None


def get_handler(cache_size: int = 50) -> DDSHandler:
    """
    Get or create the global DDS handler.

    Args:
        cache_size: Cache size for new handler

    Returns:
        DDSHandler instance
    """
    global _handler
    if _handler is None:
        _handler = DDSHandler(cache_size)
    return _handler


def load_dds_thumbnail(
    path: Path,
    size: Tuple[int, int] = (128, 128)
) -> Optional[Image.Image]:
    """
    Load a DDS thumbnail using the global handler.

    Args:
        path: Path to DDS file
        size: Thumbnail size

    Returns:
        PIL Image thumbnail or None
    """
    return get_handler().get_thumbnail(path, size)


def load_dds_full(path: Path) -> Optional[Image.Image]:
    """
    Load a full DDS image using the global handler.

    Args:
        path: Path to DDS file

    Returns:
        PIL Image or None
    """
    return get_handler().get_full_image(path)


# =============================================================================
# TKINTER HELPERS
# =============================================================================

def pil_to_tkinter(img: Image.Image):
    """
    Convert PIL Image to Tkinter-compatible PhotoImage.

    Note: Requires tkinter to be imported.

    Args:
        img: PIL Image

    Returns:
        ImageTk.PhotoImage
    """
    try:
        from PIL import ImageTk
        return ImageTk.PhotoImage(img)
    except ImportError:
        log.error("PIL.ImageTk not available")
        return None


def load_dds_for_tkinter(
    path: Path,
    size: Optional[Tuple[int, int]] = None
):
    """
    Load DDS file and convert to Tkinter PhotoImage.

    Args:
        path: Path to DDS file
        size: Optional size to resize to (thumbnail if specified)

    Returns:
        ImageTk.PhotoImage or None
    """
    if size:
        img = load_dds_thumbnail(path, size)
    else:
        img = load_dds_full(path)

    if img is None:
        return None

    return pil_to_tkinter(img)


# =============================================================================
# PLACEHOLDER IMAGE
# =============================================================================

def create_placeholder_image(
    size: Tuple[int, int] = (128, 128),
    text: str = "No Image"
) -> Image.Image:
    """
    Create a placeholder image when no texture is available.

    Args:
        size: Image size
        text: Text to display

    Returns:
        PIL Image
    """
    from PIL import ImageDraw, ImageFont

    # Create gray image
    img = Image.new('RGBA', size, (200, 200, 200, 255))
    draw = ImageDraw.Draw(img)

    # Draw border
    draw.rectangle(
        [0, 0, size[0] - 1, size[1] - 1],
        outline=(150, 150, 150, 255),
        width=2
    )

    # Draw text
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Get text size for centering
    if font:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width = len(text) * 6
        text_height = 10

    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2

    draw.text((x, y), text, fill=(100, 100, 100, 255), font=font)

    return img
