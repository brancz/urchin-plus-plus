#!/usr/bin/env python3
"""Rasterize a kicad-cli SVG export to PNG, optionally cropped (PyMuPDF renders SVG).

    uv run --no-project --with pymupdf==1.26.4 python scripts/render/svg_to_png.py IN.svg OUT.png \
        [--px-per-mm 20] [--clip X0 Y0 X1 Y1]       # clip in the SVG's mm coordinates
"""

import argparse

import fitz


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg")
    ap.add_argument("png")
    ap.add_argument("--px-per-mm", type=float, default=20.0)
    ap.add_argument("--clip", type=float, nargs=4)
    args = ap.parse_args()
    doc = fitz.open(args.svg)
    page = doc[0]
    mm = page.rect.width / float(doc.metadata.get("width", 0) or 0) if False else None
    # The page is sized in points from the SVG's mm width: 1 mm = 72 / 25.4 pt.
    pt_per_mm = 72 / 25.4
    zoom = args.px_per_mm / pt_per_mm
    clip = None
    if args.clip:
        x0, y0, x1, y1 = args.clip
        clip = fitz.Rect(x0 * pt_per_mm, y0 * pt_per_mm, x1 * pt_per_mm, y1 * pt_per_mm)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
    pix.save(args.png)
    print("%s %dx%d" % (args.png, pix.width, pix.height))


if __name__ == "__main__":
    main()
