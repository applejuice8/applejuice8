"""ASCII portrait of the profile photo, written into two SVGs.

Reads assets/source/profile.jpeg (kept local, git-ignored) and writes:

  assets/ascii/portrait.svg   typing-animation portrait (README "ASCII Profile")
  assets/ascii/card.svg       replaces only the figure on the left of the profile
                              card; the stats panel on the right is left as-is

    python scripts/ascii/portrait.py              # both
    python scripts/ascii/portrait.py portrait     # only portrait.svg
    python scripts/ascii/portrait.py card         # only card.svg

Environment: PHOTO (other image path), STATIC=1 (no animation in portrait.svg).
Requires Pillow and numpy.

The photo has a bright projector screen behind the head, which would turn into a
solid block of characters. SILHOUETTE outlines the person (pixel coordinates in
the 702x724 original) and everything outside it is rendered blank. If you swap in
another photo, redraw SILHOUETTE and CROP.
"""

import html
import os
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[2]
PHOTO = Path(os.environ.get("PHOTO", ROOT / "assets/source/profile.jpeg"))
PORTRAIT_OUT = ROOT / "assets/ascii/portrait.svg"
CARD_OUT = ROOT / "assets/ascii/card.svg"
USER = os.environ.get("GH_USER", "applejuice8")
STATIC = bool(os.environ.get("STATIC"))

SILHOUETTE = [
    (360, 88), (318, 100), (290, 130), (281, 170), (285, 210), (292, 232), (305, 258),
    (318, 282), (322, 300), (250, 320), (215, 340), (175, 390), (150, 470), (148, 520),
    (165, 562), (205, 590), (213, 640), (216, 724), (482, 724), (484, 670), (500, 650),
    (540, 630), (558, 600), (560, 545), (540, 490), (520, 420), (500, 368), (470, 338),
    (436, 318), (416, 296), (418, 262), (432, 236), (436, 190), (432, 150), (415, 112),
    (390, 92),
]
CROP = (165, 80, 525, 590)  # head and shoulders
RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
GAMMA = 0.7
CONTRAST = 1.2
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"


def figure(cols, char_w, line_h):
    """Return the ASCII rows for the photo, background blanked out."""
    img = ImageOps.exif_transpose(Image.open(PHOTO)).convert("RGB")
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).polygon(SILHOUETTE, fill=255)
    # Pull the edge in so bright background pixels do not leak around the hair.
    mask = mask.filter(ImageFilter.MinFilter(7)).filter(ImageFilter.GaussianBlur(1.5))

    gray = np.asarray(ImageOps.grayscale(img)).astype(float)
    inside = np.asarray(mask) > 128
    lo, hi = np.percentile(gray[inside], [1, 99.5])
    gray = np.clip((gray - lo) / (hi - lo), 0, 1)
    g = Image.fromarray((gray * 255).astype("uint8"))
    g = ImageEnhance.Contrast(g).enhance(CONTRAST)
    g = g.filter(ImageFilter.UnsharpMask(radius=6, percent=150, threshold=2))
    g = Image.composite(g, Image.new("L", g.size, 0), mask).crop(CROP)

    rows = round(cols * g.height / g.width * (char_w / line_h))
    small = np.asarray(g.resize((cols, rows), Image.BOX)).astype(float) / 255
    idx = ((small ** GAMMA) * (len(RAMP) - 1)).astype(int)
    return ["".join(RAMP[i] for i in row).rstrip() for row in idx]


def write_portrait():
    cols, font_size, pad = 80, 9, 18
    char_w, line_h = font_size * 0.6, font_size * 1.15
    lines = figure(cols, char_w, line_h)
    width = round(cols * char_w + pad * 2)
    height = round(len(lines) * line_h + pad * 2 + 22)
    row_w = cols * char_w

    clips, texts = [], []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        y = pad + 22 + i * line_h
        clips.append(
            f'<clipPath id="r{i}"><rect class="w" x="{pad}" y="{y - font_size:.1f}" '
            f'width="{row_w:.1f}" height="{line_h:.1f}" style="animation-delay:{i * 0.05:.2f}s"/></clipPath>'
        )
        clip = "" if STATIC else f' clip-path="url(#r{i})"'
        texts.append(f'<text x="{pad}" y="{y:.1f}" xml:space="preserve"{clip}>{html.escape(line, quote=False)}</text>')

    css = (
        f"text{{font:{font_size}px {FONT};fill:#c9d1d9;white-space:pre}}"
        f".p{{font:12px {FONT};fill:#58a6ff}}"
        ".w{transform-box:fill-box;transform-origin:left;animation:type .55s steps(24,end) both;transform:scaleX(0)}"
        "@keyframes type{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
        "@media (prefers-reduced-motion:reduce){.w{animation:none;transform:scaleX(1)}}"
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="ASCII portrait of {USER}"><style>{css}</style>'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="#0d1117" stroke="#30363d"/>'
        f'<text x="{pad}" y="{pad + 6}" class="p">$ cat portrait.txt</text>'
        f"<defs>{''.join(clips)}</defs>" + "".join(texts) + "</svg>"
    )
    PORTRAIT_OUT.write_text(svg, encoding="utf-8")
    print(f"Wrote {PORTRAIT_OUT.relative_to(ROOT)} ({len(svg):,} bytes, {len(lines)} rows x {cols} cols)")


def write_card():
    font_size, x, y0, step = 8, 28, 34.6, 9.6
    lines = figure(88, font_size * 0.6, step)
    svg = CARD_OUT.read_text(encoding="utf-8")
    # Drop the old figure: every <text> at the left margin. The panel starts at x=458.4.
    svg = re.sub(rf'[ \t]*<text x="{x}" [^>]*>.*?</text>\n', "", svg, flags=re.S)
    attrs = ("fill=\"#c9d1d9\" font-family=\"'Consolas', 'Menlo', 'DejaVu Sans Mono', monospace\" "
             f'xml:space="preserve" font-size="{font_size}"')
    out = [
        f'  <text x="{x}" y="{y0 + i * step:.1f}" {attrs}>{html.escape(line, quote=False)}</text>\n'
        for i, line in enumerate(lines) if line.strip()
    ]
    marker = re.search(r'<rect [^>]*/>\n', svg)
    svg = svg[:marker.end()] + "".join(out) + svg[marker.end():]
    CARD_OUT.write_text(svg, encoding="utf-8")
    print(f"Wrote {CARD_OUT.relative_to(ROOT)} (figure: {len(lines)} rows x 88 cols)")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "portrait"):
        write_portrait()
    if which in ("all", "card"):
        write_card()
