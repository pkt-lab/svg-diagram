#!/usr/bin/env python3
"""
SVG to PNG renderer using librsvg + cairo.

Usage:
    python3 scripts/render_svg.py <file.svg>
    python3 scripts/render_svg.py <file.svg> --output out.png
    python3 scripts/render_svg.py <file.svg> --scale 3

Dependencies: gi.repository.Rsvg, cairo (system packages: librsvg2-common, python3-gi, python3-cairo)
"""

import sys
import os
import argparse

import gi
gi.require_version("Rsvg", "2.0")
from gi.repository import Rsvg
import cairo


def render(svg_path: str, png_path: str, scale: float = 2.0) -> str:
    """Render an SVG file to PNG. Returns the output path."""
    handle = Rsvg.Handle.new_from_file(svg_path)

    has_w, width, has_h, height, has_vb, viewbox = handle.get_intrinsic_dimensions()

    if has_w and has_h:
        w = width.length
        h = height.length
    elif has_vb:
        w = viewbox.width
        h = viewbox.height
    else:
        # Fallback to deprecated API
        dim = handle.get_dimensions()
        w = dim.width
        h = dim.height

    out_w = int(w * scale)
    out_h = int(h * scale)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, out_w, out_h)
    ctx = cairo.Context(surface)
    ctx.scale(scale, scale)

    viewport = Rsvg.Rectangle()
    viewport.x = 0
    viewport.y = 0
    viewport.width = w
    viewport.height = h
    handle.render_document(ctx, viewport)

    surface.write_to_png(png_path)
    surface.finish()
    return png_path


def main():
    parser = argparse.ArgumentParser(description="Render SVG to PNG")
    parser.add_argument("svg", help="Path to SVG file")
    parser.add_argument("--output", "-o", help="Output PNG path (default: same name with .png)")
    parser.add_argument("--scale", "-s", type=float, default=2.0, help="Scale factor (default: 2)")
    args = parser.parse_args()

    png_path = args.output or os.path.splitext(args.svg)[0] + ".png"
    try:
        out = render(args.svg, png_path, args.scale)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Rendered: {out}")


if __name__ == "__main__":
    main()
