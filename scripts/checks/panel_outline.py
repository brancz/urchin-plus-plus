#!/usr/bin/env python3
"""Check that the panel keeps each half's outline (CLAUDE.md rule 1) apart from the tabs.

    "$KICAD_PY" scripts/checks/panel_outline.py PANEL LEFT RIGHT [--tolerance 0.002]

KiKit rebuilds the outline when it panelizes: it turns arcs into chords (made fine by
scripts/fab/panel_layout.py), rounds inside corners to the mill radius, and replaces a
stretch of edge with each tab. Every half's Edge.Cuts is sampled every 0.1 mm (arcs
exactly), and each sample must lie on the panel's Edge.Cuts within the tolerance, 2 um by
default: the 0.5 mm mill fillets on the original's 0.5 mm corners are polygons. Samples within 1.6 mm of a mouse-bite
hole are skipped: that is where a tab joins the edge, and the edge there is what's left
after the tab is broken off. Every mouse-bite hole must also keep at least 0.8 mm of board
to every other hole (edge to edge), so breaking a tab can't crack into a case-screw ear. The halves themselves are checked against the original by
scripts/checks/geometry.py. Runs under KiCad's Python (pcbnew, shapely from KiKit).
"""

import argparse
import math
import os
import sys

import pcbnew
from shapely.geometry import LineString, MultiLineString, Point
from shapely.strtree import STRtree

STEP = 0.1          # mm between samples on a half's outline
TAB_ZONE = 1.6      # mm around a mouse-bite hole
BITE_TO_HOLE = 0.8  # mm of board between a mouse-bite hole and any other hole
PANEL_ARC_STEP = 0.01  # mm, panel arcs are compared as polylines this fine


def mm(v):
    return v / 1e6


def arc_points(shape, step):
    c = shape.GetCenter()
    r = mm(shape.GetRadius())
    a0 = math.atan2(mm(shape.GetStart().y - c.y), mm(shape.GetStart().x - c.x))
    sweep = math.radians(shape.GetArcAngle().AsDegrees())
    n = max(2, int(abs(sweep) * r / step) + 1)
    return [(mm(c.x) + r * math.cos(a0 + sweep * i / n), mm(c.y) + r * math.sin(a0 + sweep * i / n))
            for i in range(n + 1)]


def edge_lines(board, step):
    """Edge.Cuts of BOARD (drawings and footprint graphics) as polylines in mm."""
    shapes = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    for fp in board.GetFootprints():
        shapes += [g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.Edge_Cuts]
    lines = []
    for s in shapes:
        kind = s.GetShape()
        if kind == pcbnew.SHAPE_T_SEGMENT:
            lines.append([(mm(s.GetStart().x), mm(s.GetStart().y)), (mm(s.GetEnd().x), mm(s.GetEnd().y))])
        elif kind == pcbnew.SHAPE_T_ARC:
            lines.append(arc_points(s, step))
        elif kind == pcbnew.SHAPE_T_CIRCLE:
            c, r = s.GetCenter(), mm(s.GetRadius())
            n = max(8, int(2 * math.pi * r / step))
            lines.append([(mm(c.x) + r * math.cos(2 * math.pi * i / n), mm(c.y) + r * math.sin(2 * math.pi * i / n))
                          for i in range(n + 1)])
        elif kind == pcbnew.SHAPE_T_RECT:
            x0, y0, x1, y1 = mm(s.GetStart().x), mm(s.GetStart().y), mm(s.GetEnd().x), mm(s.GetEnd().y)
            lines.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
        elif kind == pcbnew.SHAPE_T_POLY:
            poly = s.GetPolyShape()
            for i in range(poly.OutlineCount()):
                o = poly.Outline(i)
                pts = [(mm(o.CPoint(j).x), mm(o.CPoint(j).y)) for j in range(o.PointCount())]
                lines.append(pts + pts[:1])
        else:
            sys.exit("unsupported Edge.Cuts shape %s" % s.GetShapeStr())
    return lines


def samples(lines):
    out = []
    for pts in lines:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / STEP))
            out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n)]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("panel")
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--tolerance", type=float, default=0.002, help="mm")
    args = ap.parse_args()

    panel = pcbnew.LoadBoard(args.panel)
    segs = [LineString(p) for p in edge_lines(panel, PANEL_ARC_STEP)]
    tree = STRtree(segs)
    bites = [fp.GetPosition() for fp in panel.GetFootprints() if fp.GetReference().startswith("KiKit_MB")]
    bites = [(mm(p.x), mm(p.y)) for p in bites]
    panel_refs = {fp.GetReference(): fp.GetPosition() for fp in panel.GetFootprints()}
    problems = []
    for side, path in (("L", args.left), ("R", args.right)):
        half = pcbnew.LoadBoard(path)
        u1 = half.FindFootprintByReference("U1").GetPosition()
        moved = panel_refs["U1_" + side]
        dx, dy = mm(moved.x - u1.x), mm(moved.y - u1.y)  # the half's offset in the panel
        worst, checked, skipped = 0.0, 0, 0
        for x, y in samples(edge_lines(half, STEP)):
            x, y = x + dx, y + dy
            if any(math.hypot(x - bx, y - by) < TAB_ZONE for bx, by in bites):
                skipped += 1
                continue
            p = Point(x, y)
            d = min((segs[i].distance(p) for i in tree.query(p.buffer(1.0))), default=float("inf"))  # shapely 2
            checked += 1
            if d > worst:
                worst, where = d, (x, y)
            if d > args.tolerance:
                problems.append("%s: outline at (%.3f, %.3f) is %.3f mm from the panel's edge" % (side, x, y, d))
        print("panel outline %s: %d samples, %d skipped at tabs, worst %.4f mm at (%.2f, %.2f)" % (
            side, checked, skipped, worst, where[0], where[1]))
    holes = [(mm(p.GetPosition().x), mm(p.GetPosition().y), mm(max(p.GetDrillSize().x, p.GetDrillSize().y)) / 2, fp.GetReference())
             for fp in panel.GetFootprints() if not fp.GetReference().startswith("KiKit_MB")
             for p in fp.Pads() if p.GetDrillSize().x > 0]
    bite_r = [mm(p.GetDrillSize().x) / 2 for fp in panel.GetFootprints() if fp.GetReference().startswith("KiKit_MB")
              for p in fp.Pads()][:1] or [0.25]
    closest = min(((math.hypot(bx - hx, by - hy) - hr - bite_r[0], ref, (bx, by)) for bx, by in bites for hx, hy, hr, ref in holes),
                  default=(float("inf"), "", (0, 0)))
    print("panel mouse bites: closest other hole %.2f mm of board away (%s, bite at (%.2f, %.2f))" % (
        closest[0], closest[1], closest[2][0], closest[2][1]))
    if closest[0] < BITE_TO_HOLE:
        problems.append("a mouse bite at (%.2f, %.2f) leaves %.2f mm of board to a hole of %s (minimum %.1f)" % (
            closest[2][0], closest[2][1], closest[0], closest[1], BITE_TO_HOLE))
    print("panel outline: %s" % ("OK" if not problems else "FAIL (%d)" % len(problems)))
    for p in problems[:20]:
        print("FAIL " + p)
    sys.stdout.flush()
    os._exit(1 if problems else 0)


if __name__ == "__main__":
    main()
