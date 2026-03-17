#!/usr/bin/env python3
"""Generate program icons for all NewScripts apps using pycairo + Pillow."""

import cairo
import math
import io
from PIL import Image
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SIZE = 512
FONT_PATH = "/mnt/c/Windows/Fonts/segoeuib.ttf"
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (128, 128), (256, 256)]


def create_surface():
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
    ctx = cairo.Context(surface)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    return surface, ctx


def draw_gradient_circle(ctx, r, g1_start, g1_end, g2_start, g2_end, g3_start, g3_end):
    """Draw a radial gradient circle filling the canvas."""
    cx, cy = SIZE / 2, SIZE / 2
    radius = SIZE / 2 - 8  # small padding

    # Radial gradient from center outward
    pat = cairo.RadialGradient(cx - radius * 0.3, cy - radius * 0.3, radius * 0.1,
                                cx, cy, radius)
    pat.add_color_stop_rgba(0, g1_start, g2_start, g3_start, 1.0)
    pat.add_color_stop_rgba(1, g1_end, g2_end, g3_end, 1.0)

    ctx.arc(cx, cy, radius, 0, 2 * math.pi)
    ctx.set_source(pat)
    ctx.fill()

    # Subtle inner highlight
    highlight = cairo.RadialGradient(cx - radius * 0.25, cy - radius * 0.3, 0,
                                      cx - radius * 0.25, cy - radius * 0.3, radius * 0.6)
    highlight.add_color_stop_rgba(0, 1, 1, 1, 0.25)
    highlight.add_color_stop_rgba(1, 1, 1, 1, 0.0)
    ctx.arc(cx, cy, radius, 0, 2 * math.pi)
    ctx.set_source(highlight)
    ctx.fill()


def draw_shadow(ctx):
    """Draw subtle drop shadow under the circle."""
    cx, cy = SIZE / 2, SIZE / 2 + 6
    radius = SIZE / 2 - 8
    shadow = cairo.RadialGradient(cx, cy, radius * 0.85, cx, cy, radius * 1.05)
    shadow.add_color_stop_rgba(0, 0, 0, 0, 0.15)
    shadow.add_color_stop_rgba(1, 0, 0, 0, 0.0)
    ctx.arc(cx, cy, radius * 1.05, 0, 2 * math.pi)
    ctx.set_source(shadow)
    ctx.fill()


def set_white(ctx, alpha=1.0):
    ctx.set_source_rgba(1, 1, 1, alpha)


def surface_to_ico(surface, output_path):
    """Convert cairo surface to multi-size .ico via Pillow."""
    buf = io.BytesIO()
    surface.write_to_png(buf)
    buf.seek(0)
    img = Image.open(buf).convert("RGBA")

    # Generate multiple sizes with high-quality downsampling
    images = []
    for s in ICO_SIZES:
        resized = img.resize(s, Image.LANCZOS)
        images.append(resized)

    # Save as ICO
    images[-1].save(str(output_path), format="ICO", sizes=ICO_SIZES, append_images=images[:-1])

    # Also save 512px PNG for preview
    png_path = output_path.with_suffix('.png')
    img.save(str(png_path))
    print(f"  -> {output_path}")
    print(f"  -> {png_path}")


# =============================================================================
# ICON 1: QuickTranslate — "QT" letters, Blue→Cyan
# =============================================================================
def generate_quicktranslate():
    print("Generating QuickTranslate icon (QT, Blue→Cyan)...")
    surface, ctx = create_surface()
    draw_shadow(ctx)
    # Blue to Cyan gradient
    draw_gradient_circle(ctx, None, 0.15, 0.05, 0.45, 0.75, 0.90, 0.95)

    # "QT" text
    set_white(ctx)
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(220)
    text = "QT"
    extents = ctx.text_extents(text)
    x = (SIZE - extents.width) / 2 - extents.x_bearing
    y = (SIZE - extents.height) / 2 - extents.y_bearing + 8
    ctx.move_to(x, y)
    ctx.show_text(text)

    # Small transfer arrows under the text
    set_white(ctx, 0.6)
    ctx.set_line_width(4)
    arrow_y = y + 30
    arrow_cx = SIZE / 2
    # Right arrow
    ctx.move_to(arrow_cx - 50, arrow_y)
    ctx.line_to(arrow_cx + 10, arrow_y)
    ctx.line_to(arrow_cx + 2, arrow_y - 8)
    ctx.move_to(arrow_cx + 10, arrow_y)
    ctx.line_to(arrow_cx + 2, arrow_y + 8)
    ctx.stroke()
    # Left arrow
    ctx.move_to(arrow_cx + 50, arrow_y + 18)
    ctx.line_to(arrow_cx - 10, arrow_y + 18)
    ctx.line_to(arrow_cx - 2, arrow_y + 10)
    ctx.move_to(arrow_cx - 10, arrow_y + 18)
    ctx.line_to(arrow_cx - 2, arrow_y + 26)
    ctx.stroke()

    out = SCRIPT_DIR / "QuickTranslate" / "images" / "QTico.ico"
    surface_to_ico(surface, out)


# =============================================================================
# ICON 2: QACompiler — Stacked layers + checkmark, Green→Emerald
# =============================================================================
def generate_qacompiler():
    print("Generating QACompiler icon (layers+check, Green→Emerald)...")
    surface, ctx = create_surface()
    draw_shadow(ctx)
    # Green to Emerald
    draw_gradient_circle(ctx, None, 0.20, 0.08, 0.72, 0.55, 0.35, 0.30)

    set_white(ctx)
    cx, cy = SIZE / 2, SIZE / 2

    # Stacked document layers
    ctx.set_line_width(6)
    layer_w, layer_h = 140, 90
    offsets = [(-15, 25), (0, 0), (15, -25)]
    for ox, oy in offsets:
        x0 = cx - layer_w / 2 + ox - 25
        y0 = cy - layer_h / 2 + oy
        # Rounded rectangle
        r = 12
        ctx.new_path()
        ctx.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
        ctx.arc(x0 + layer_w - r, y0 + r, r, 1.5 * math.pi, 0)
        ctx.arc(x0 + layer_w - r, y0 + layer_h - r, r, 0, 0.5 * math.pi)
        ctx.arc(x0 + r, y0 + layer_h - r, r, 0.5 * math.pi, math.pi)
        ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, 0.3)
        ctx.fill_preserve()
        set_white(ctx, 0.8)
        ctx.stroke()

    # Checkmark (bottom-right)
    set_white(ctx)
    ctx.set_line_width(14)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    check_x, check_y = cx + 55, cy + 20
    ctx.move_to(check_x - 35, check_y)
    ctx.line_to(check_x - 10, check_y + 30)
    ctx.line_to(check_x + 35, check_y - 35)
    ctx.stroke()

    out = SCRIPT_DIR / "QACompilerNEW" / "images" / "QACompilericon.ico"
    surface_to_ico(surface, out)


# =============================================================================
# ICON 3: ExtractAnything — Scalpel/blade, Orange→Amber
# =============================================================================
def generate_extractanything():
    print("Generating ExtractAnything icon (scalpel, Orange→Amber)...")
    surface, ctx = create_surface()
    draw_shadow(ctx)
    # Orange to Amber
    draw_gradient_circle(ctx, None, 0.95, 0.80, 0.55, 0.35, 0.10, 0.05)

    set_white(ctx)
    cx, cy = SIZE / 2, SIZE / 2

    # Document shape (background)
    ctx.set_line_width(5)
    doc_x, doc_y = cx - 70, cy - 80
    doc_w, doc_h = 130, 160
    r = 10
    ctx.new_path()
    ctx.arc(doc_x + r, doc_y + r, r, math.pi, 1.5 * math.pi)
    ctx.arc(doc_x + doc_w - r, doc_y + r, r, 1.5 * math.pi, 0)
    ctx.arc(doc_x + doc_w - r, doc_y + doc_h - r, r, 0, 0.5 * math.pi)
    ctx.arc(doc_x + r, doc_y + doc_h - r, r, 0.5 * math.pi, math.pi)
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, 0.35)
    ctx.fill_preserve()
    set_white(ctx, 0.7)
    ctx.stroke()

    # Text lines on document
    set_white(ctx, 0.5)
    ctx.set_line_width(4)
    for i in range(4):
        ly = doc_y + 35 + i * 28
        ctx.move_to(doc_x + 20, ly)
        ctx.line_to(doc_x + doc_w - 20, ly)
        ctx.stroke()

    # Scalpel/blade cutting diagonally across
    set_white(ctx)
    ctx.set_line_width(3)
    # Blade body
    ctx.move_to(cx + 80, cy - 80)
    ctx.line_to(cx - 20, cy + 40)
    ctx.line_to(cx - 30, cy + 35)
    ctx.line_to(cx + 70, cy - 85)
    ctx.close_path()
    ctx.fill()
    # Handle
    ctx.set_line_width(8)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(cx + 80, cy - 80)
    ctx.line_to(cx + 115, cy - 115)
    ctx.stroke()

    # Extract sparkle
    set_white(ctx, 0.9)
    sparkle_x, sparkle_y = cx - 50, cy + 65
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        length = 18 if angle % 90 == 0 else 10
        ctx.move_to(sparkle_x, sparkle_y)
        ctx.line_to(sparkle_x + math.cos(rad) * length, sparkle_y + math.sin(rad) * length)
    ctx.set_line_width(3)
    ctx.stroke()

    out = SCRIPT_DIR / "ExtractAnything" / "images" / "EAico.ico"
    surface_to_ico(surface, out)


# =============================================================================
# ICON 4: LanguageDataExporter — "LDE" letters, Teal→Sea Green
# =============================================================================
def generate_languagedataexporter():
    print("Generating LanguageDataExporter icon (LDE, Teal→SeaGreen)...")
    surface, ctx = create_surface()
    draw_shadow(ctx)
    # Teal to Sea Green
    draw_gradient_circle(ctx, None, 0.05, 0.02, 0.65, 0.50, 0.60, 0.45)

    set_white(ctx)
    cx, cy = SIZE / 2, SIZE / 2

    # "LDE" text — slightly smaller to fit 3 letters
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(170)
    text = "LDE"
    extents = ctx.text_extents(text)
    x = (SIZE - extents.width) / 2 - extents.x_bearing
    y = (SIZE - extents.height) / 2 - extents.y_bearing

    ctx.move_to(x, y)
    ctx.show_text(text)

    # Export arrow underneath
    set_white(ctx, 0.6)
    ctx.set_line_width(5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    arrow_y = y + 30
    # Down-right arrow
    ctx.move_to(cx - 40, arrow_y)
    ctx.line_to(cx + 40, arrow_y)
    ctx.line_to(cx + 30, arrow_y - 10)
    ctx.move_to(cx + 40, arrow_y)
    ctx.line_to(cx + 30, arrow_y + 10)
    ctx.stroke()

    out = SCRIPT_DIR / "LanguageDataExporter" / "images" / "LDEico.ico"
    surface_to_ico(surface, out)


# =============================================================================
# ICON 5: QuickCheck — Shield + checkmark, Red→Crimson
# =============================================================================
def generate_quickcheck():
    print("Generating QuickCheck icon (shield+check, Red→Crimson)...")
    surface, ctx = create_surface()
    draw_shadow(ctx)
    # Red to Crimson
    draw_gradient_circle(ctx, None, 0.85, 0.55, 0.15, 0.08, 0.15, 0.12)

    set_white(ctx)
    cx, cy = SIZE / 2, SIZE / 2

    # Shield shape
    ctx.set_line_width(6)
    shield_top = cy - 95
    shield_bottom = cy + 100
    shield_w = 100

    ctx.new_path()
    ctx.move_to(cx, shield_top - 10)  # top point
    ctx.curve_to(cx + shield_w, shield_top + 10,
                 cx + shield_w, cy + 20,
                 cx, shield_bottom)       # right curve to bottom
    ctx.curve_to(cx - shield_w, cy + 20,
                 cx - shield_w, shield_top + 10,
                 cx, shield_top - 10)     # left curve back to top
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, 0.25)
    ctx.fill_preserve()
    set_white(ctx, 0.9)
    ctx.stroke()

    # Checkmark inside shield
    set_white(ctx)
    ctx.set_line_width(16)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(cx - 40, cy + 5)
    ctx.line_to(cx - 10, cy + 40)
    ctx.line_to(cx + 45, cy - 40)
    ctx.stroke()

    out = SCRIPT_DIR / "QuickCheck" / "images" / "QCico.ico"
    surface_to_ico(surface, out)


# =============================================================================
# ICON 6: MapDataGenerator — Map pin on grid, Indigo→Deep Blue
# =============================================================================
def generate_mapdatagenerator():
    print("Generating MapDataGenerator icon (map pin, Indigo→DeepBlue)...")
    surface, ctx = create_surface()
    draw_shadow(ctx)
    # Indigo to Deep Blue
    draw_gradient_circle(ctx, None, 0.25, 0.10, 0.20, 0.10, 0.70, 0.55)

    set_white(ctx)
    cx, cy = SIZE / 2, SIZE / 2

    # Grid lines (subtle)
    ctx.set_line_width(2)
    set_white(ctx, 0.2)
    grid_start = cx - 120
    grid_end = cx + 120
    for i in range(7):
        pos = grid_start + i * 40
        ctx.move_to(pos, cy - 100)
        ctx.line_to(pos, cy + 110)
        ctx.stroke()
        ctx.move_to(cx - 120, cy - 100 + i * 35)
        ctx.line_to(cx + 120, cy - 100 + i * 35)
        ctx.stroke()

    # Map pin
    set_white(ctx)
    pin_cx, pin_cy = cx, cy - 15
    pin_r = 55

    # Pin body (teardrop shape)
    ctx.new_path()
    ctx.arc(pin_cx, pin_cy - 10, pin_r, math.pi * 0.85, math.pi * 0.15)
    ctx.line_to(pin_cx, pin_cy + pin_r + 40)
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, 0.9)
    ctx.fill()

    # Inner circle (hole in pin)
    ctx.arc(pin_cx, pin_cy - 10, pin_r * 0.4, 0, 2 * math.pi)
    ctx.set_source_rgba(0.15, 0.12, 0.55, 0.8)  # dark indigo
    ctx.fill()

    out = SCRIPT_DIR / "MapDataGenerator" / "images" / "MDGico.ico"
    surface_to_ico(surface, out)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("NewScripts Icon Generator — pycairo + Pillow")
    print("=" * 60)

    generate_quicktranslate()
    generate_qacompiler()
    generate_extractanything()
    generate_languagedataexporter()
    generate_quickcheck()
    generate_mapdatagenerator()

    print("\n✓ All 6 icons generated!")
    print("Check the .png files for preview before triggering builds.")
