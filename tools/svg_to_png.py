#!/usr/bin/env python3
"""Convert SVG files to PNG for visual review.

Usage:
    python3 svg_to_png.py input.svg [output.png] [--width W]

If output is omitted, writes to input_stem.png in the same directory.
"""

import sys
from pathlib import Path

import cairosvg


def convert(svg_path: str, png_path: str | None = None, width: int = 800) -> str:
    svg = Path(svg_path)
    if png_path is None:
        png = svg.with_suffix(".png")
    else:
        png = Path(png_path)

    cairosvg.svg2png(
        url=str(svg.resolve()),
        write_to=str(png),
        output_width=width,
    )
    print(f"Written: {png} ({png.stat().st_size / 1024:.1f} KB)")
    return str(png)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 svg_to_png.py input.svg [output.png] [--width W]")
        sys.exit(1)

    svg_file = sys.argv[1]
    png_file = None
    width = 800

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--width" and i + 1 < len(args):
            width = int(args[i + 1])
            i += 2
        elif png_file is None:
            png_file = args[i]
            i += 1
        else:
            i += 1

    convert(svg_file, png_file, width)
