"""
Spectr PDF — Icon Generator
Produces spectr_pdf.ico (multi-resolution) and spectr_pdf.png (256px)
using Pillow only. No external dependencies.

Run once before building:
    python icon_gen.py

SPECTR color palette (from H3x-Dash):
  Background : #0A0E1A  (deep navy-black)
  Primary    : #00F0FF  (cyan)
  Secondary  : #7B2FFF  (violet)
  Accent     : #FF2D6B  (hot pink)
  Surface    : #111827  (panel dark)
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# ── SPECTR Palette ────────────────────────────────────────────────────────────
BG          = (10,  14,  26,  255)   # #0A0E1A
CYAN        = (0,   240, 255, 255)   # #00F0FF
VIOLET      = (123, 47,  255, 255)   # #7B2FFF
PINK        = (255, 45,  107, 255)   # #FF2D6B
SURFACE     = (17,  24,  39,  255)   # #111827
WHITE       = (220, 230, 255, 255)   # off-white
CYAN_DIM    = (0,   180, 200, 180)   # translucent cyan for glow


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4))


def draw_icon(size: int) -> Image.Image:
    """Draw a single Spectr PDF icon at the given square size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = max(2, size // 16)
    s = size

    # ── Rounded rect background ───────────────────────────────────────────────
    radius = max(4, s // 8)
    d.rounded_rectangle([pad, pad, s - pad, s - pad],
                        radius=radius, fill=BG)

    # ── Document shape (white page with folded corner) ────────────────────────
    doc_x0 = s * 0.18
    doc_y0 = s * 0.10
    doc_x1 = s * 0.82
    doc_y1 = s * 0.90
    fold   = s * 0.22   # fold size

    # Page body (clipped to fold)
    page_pts = [
        (doc_x0, doc_y0),
        (doc_x1 - fold, doc_y0),
        (doc_x1, doc_y0 + fold),
        (doc_x1, doc_y1),
        (doc_x0, doc_y1),
    ]
    d.polygon(page_pts, fill=SURFACE)

    # Page border — cyan glow
    d.line(page_pts + [page_pts[0]], fill=CYAN, width=max(1, s // 40))

    # Folded corner triangle
    corner_pts = [
        (doc_x1 - fold, doc_y0),
        (doc_x1, doc_y0 + fold),
        (doc_x1 - fold, doc_y0 + fold),
    ]
    d.polygon(corner_pts, fill=BG)
    d.line([
        (doc_x1 - fold, doc_y0),
        (doc_x1 - fold, doc_y0 + fold),
        (doc_x1, doc_y0 + fold),
    ], fill=CYAN, width=max(1, s // 40))

    # ── "S" letterform (violet → cyan gradient approximation) ─────────────────
    # Draw as thick text if size is large enough, else a simplified block
    cx = s * 0.50
    cy = s * 0.52
    font_size = max(8, int(s * 0.42))

    try:
        # Try to use a system font
        from PIL import ImageFont
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    # Shadow/glow layer (violet, offset)
    glow_offset = max(1, s // 32)
    if size >= 32:
        d.text((cx + glow_offset, cy + glow_offset), "S",
               font=font, fill=(*VIOLET[:3], 160), anchor="mm")
        # Second glow pass
        d.text((cx - glow_offset, cy - glow_offset), "S",
               font=font, fill=(*CYAN[:3], 80), anchor="mm")

    # Main "S" in cyan
    d.text((cx, cy), "S", font=font, fill=CYAN, anchor="mm")

    # ── "PDF" label bar at bottom ─────────────────────────────────────────────
    if size >= 48:
        bar_h = max(8, s // 8)
        bar_y0 = s - pad - bar_h
        bar_y1 = s - pad
        d.rounded_rectangle([pad * 2, bar_y0, s - pad * 2, bar_y1],
                             radius=max(2, bar_h // 4),
                             fill=(*VIOLET[:3], 200))

        label_font_size = max(6, bar_h - 4)
        try:
            lf = ImageFont.truetype("arial.ttf", label_font_size)
        except Exception:
            try:
                lf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", label_font_size)
            except Exception:
                lf = ImageFont.load_default()

        label_cx = s / 2
        label_cy = bar_y0 + bar_h / 2
        d.text((label_cx, label_cy), "PDF", font=lf,
               fill=WHITE, anchor="mm")

    # ── Scan line overlay (subtle, only on large sizes) ───────────────────────
    if size >= 128:
        for y in range(pad, s - pad, 4):
            d.line([(pad, y), (s - pad, y)],
                   fill=(0, 240, 255, 12), width=1)

    return img


def generate_ico(output_path: str):
    """Generate a multi-resolution .ico file."""
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [draw_icon(sz) for sz in sizes]

    # ICO needs RGB or RGBA — keep RGBA
    images[0].save(
        output_path,
        format="ICO",
        sizes=[(sz, sz) for sz in sizes],
        append_images=images[1:],
    )
    print(f"  ✓ {output_path}  ({len(sizes)} sizes: {sizes})")


def generate_png(output_path: str, size: int = 256):
    """Generate a single PNG for use in the installer header/sidebar."""
    img = draw_icon(size)
    img.save(output_path, format="PNG")
    print(f"  ✓ {output_path}  ({size}x{size})")


def generate_banner(output_path: str):
    """
    Generate a 164x314 installer sidebar banner (Inno Setup WizardImageFile).
    Dark cyberpunk gradient with Spectr PDF text.
    """
    w, h = 164, 314
    img = Image.new("RGBA", (w, h), BG)
    d = ImageDraw.Draw(img)

    # Gradient overlay — vertical cyan to violet
    for y in range(h):
        t = y / h
        color = lerp_color((*VIOLET[:3], 60), (*CYAN[:3], 30), t)
        d.line([(0, y), (w, y)], fill=color)

    # Scan lines
    for y in range(0, h, 3):
        d.line([(0, y), (w, y)], fill=(0, 240, 255, 8))

    # Icon centered top
    icon = draw_icon(80)
    img.paste(icon, ((w - 80) // 2, 20), icon)

    # App name
    try:
        tf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        sf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except Exception:
        tf = sf = ImageFont.load_default()

    d.text((w // 2, 118), "Spectr", font=tf, fill=CYAN, anchor="mm")
    d.text((w // 2, 137), "PDF", font=tf, fill=WHITE, anchor="mm")
    d.line([(20, 152), (w - 20, 152)], fill=(*CYAN[:3], 120), width=1)
    d.text((w // 2, 165), "Free. Local.", font=sf, fill=(*WHITE[:3], 180), anchor="mm")
    d.text((w // 2, 180), "No cloud. No BS.", font=sf, fill=(*WHITE[:3], 180), anchor="mm")

    img = img.convert("RGB")
    img.save(output_path, format="BMP")
    print(f"  ✓ {output_path}  ({w}x{h} installer banner)")


def generate_header(output_path: str):
    """
    Generate a 497x55 installer top banner (Inno Setup WizardSmallImageFile).
    """
    w, h = 497, 55
    img = Image.new("RGBA", (w, h), BG)
    d = ImageDraw.Draw(img)

    # Subtle gradient
    for x in range(w):
        t = x / w
        color = lerp_color((*BG[:3], 255), (*VIOLET[:3], 60), t)
        d.line([(x, 0), (x, h)], fill=color)

    # Scan lines
    for y in range(0, h, 3):
        d.line([(0, y), (w, y)], fill=(0, 240, 255, 10))

    # Bottom border line
    d.line([(0, h - 1), (w, h - 1)], fill=CYAN, width=1)

    # Small icon left
    icon = draw_icon(40)
    img.paste(icon, (10, (h - 40) // 2), icon)

    # App name
    try:
        tf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        sf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except Exception:
        tf = sf = ImageFont.load_default()

    d.text((60, h // 2 - 2), "Spectr PDF", font=tf, fill=CYAN, anchor="lm")
    d.text((60, h // 2 + 14), "Free PDF Suite  ·  No cloud  ·  No subscriptions",
           font=sf, fill=(*WHITE[:3], 160), anchor="lm")

    img = img.convert("RGB")
    img.save(output_path, format="BMP")
    print(f"  ✓ {output_path}  ({w}x{h} installer header)")


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(out_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    print("\nGenerating Spectr PDF assets...\n")
    generate_ico(os.path.join(assets_dir, "spectr_pdf.ico"))
    generate_png(os.path.join(assets_dir, "spectr_pdf.png"), 256)
    generate_banner(os.path.join(assets_dir, "installer_sidebar.bmp"))
    generate_header(os.path.join(assets_dir, "installer_header.bmp"))
    print("\nAll assets generated in ./assets/\n")
