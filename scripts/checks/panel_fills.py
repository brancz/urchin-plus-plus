#!/usr/bin/env python3
"""Check that the panel's GND pours are the halves' pours, apart from the mouse bites.

    "$KICAD_PY" scripts/checks/panel_fills.py PANEL LEFT RIGHT

KiKit refills the zones when it panelizes (hardware/panel.json), so that the pours keep
clear of the mouse-bite holes. A refill can also drop copper: where a mouse-bite row cuts
the only link of a piece of pour, island removal deletes the piece, and DRC can't see
that. This check refills each half on a copy, takes the GND fill of every copper layer,
and subtracts the panel's fill of the same half (moved back by the half's offset in the
panel). Whatever is missing must lie within 1.5 mm of a mouse-bite hole; anything more
than 0.05 mm² elsewhere fails. The other way round, the panel may add at most 1 mm² of
GND copper per layer (refill slivers along pour edges), and none inside the antenna
keep-out (rule 6; below 0.001 mm² is arithmetic dust on its boundary). Runs under KiCad's Python (pcbnew, shapely from KiKit);
one board load per process (KiCad 9's SWIG).
"""

import argparse
import json
import os
import subprocess
import sys

import pcbnew
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

NEAR_BITE = 1.5   # mm around a mouse-bite hole where the panel may have less copper
TOLERANCE = 0.05  # mm² of missing copper allowed elsewhere
EXTRA = 1.0       # mm² of extra copper allowed per layer (refill slivers)
IN_KEEPOUT = 0.001  # mm²: polygon arithmetic leaves dust along the keep-out's boundary
LAYERS = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}


def polys(poly_set):
    """SHAPE_POLY_SET -> list of ([outline], [[hole], ...]) in mm."""
    out = []
    for i in range(poly_set.OutlineCount()):
        o = poly_set.Outline(i)
        outline = [(o.CPoint(j).x / 1e6, o.CPoint(j).y / 1e6) for j in range(o.PointCount())]
        holes = []
        for k in range(poly_set.HoleCount(i)):
            h = poly_set.Hole(i, k)
            holes.append([(h.CPoint(j).x / 1e6, h.CPoint(j).y / 1e6) for j in range(h.PointCount())])
        out.append((outline, holes))
    return out


def dump(board_path, net, refill, out):
    """Child process: the fill of every zone on `net`, per layer, as JSON."""
    board = pcbnew.LoadBoard(board_path)
    zones = list(board.Zones())
    if refill:
        pcbnew.ZONE_FILLER(board).Fill(zones)
    fills = {name: [] for name in LAYERS}
    for z in zones:
        if z.GetIsRuleArea() or z.GetNetname() != net:
            continue
        for name, layer in LAYERS.items():
            if z.IsOnLayer(layer) and z.HasFilledPolysForLayer(layer):
                fills[name] += polys(z.GetFilledPolysList(layer))
    u1 = {fp.GetReference(): (fp.GetPosition().x / 1e6, fp.GetPosition().y / 1e6) for fp in board.GetFootprints()
          if fp.GetReference().startswith("U1")}
    bites = [(fp.GetPosition().x / 1e6, fp.GetPosition().y / 1e6) for fp in board.GetFootprints()
             if fp.GetReference().startswith("KiKit_MB")]
    keepouts = [polys(z.Outline()) for z in zones if z.GetIsRuleArea() and z.GetZoneName() == "ANTENNA_KEEPOUT"]
    json.dump({"fills": fills, "u1": u1, "bites": bites, "keepouts": keepouts}, open(out, "w"))


def shape(parts, dx=0.0, dy=0.0):
    return unary_union([Polygon([(x - dx, y - dy) for x, y in o], [[(x - dx, y - dy) for x, y in h] for h in hs]).buffer(0)
                        for o, hs in parts])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("panel")
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--dump", nargs=3, metavar=("NET", "REFILL", "OUT"), help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.dump:
        dump(args.panel, args.dump[0], args.dump[1] == "1", args.dump[2])
        sys.stdout.flush()
        os._exit(0)

    me = [sys.executable, os.path.abspath(__file__)]
    work = os.path.join(os.path.dirname(os.path.abspath(args.panel)), "fills")
    os.makedirs(work, exist_ok=True)

    def run(board, net, refill):
        out = os.path.join(work, "%s-%s.json" % (os.path.basename(board), net))
        child = subprocess.run(me + [board, "x", "x", "--dump", net, "1" if refill else "0", out],
                               capture_output=True, text=True)
        if child.returncode != 0:
            sys.exit("dump failed for %s:\n%s" % (board, child.stderr[-2000:]))
        return json.load(open(out))

    problems = []
    for side, path in (("L", args.left), ("R", args.right)):
        half = run(path, "GND", True)
        panel = run(args.panel, side + "-GND", False)
        hx, hy = half["u1"]["U1"]
        px, py = panel["u1"]["U1_" + side]
        dx, dy = px - hx, py - hy
        near = unary_union([Point(x - dx, y - dy).buffer(NEAR_BITE) for x, y in panel["bites"]])
        keepout = unary_union([shape(k) for k in half["keepouts"]])
        if keepout.is_empty:
            problems.append("%s: no ANTENNA_KEEPOUT rule area on the half" % side)
        for layer in LAYERS:
            in_panel = shape(panel["fills"][layer], dx, dy)
            extra = in_panel.difference(shape(half["fills"][layer])).area
            in_keepout = in_panel.intersection(keepout).area
            if extra > EXTRA:
                problems.append("%s %s: the panel adds %.2f mm² of GND pour the half doesn't have" % (side, layer, extra))
            if in_keepout > IN_KEEPOUT:
                problems.append("%s %s: %.4f mm² of GND pour inside the antenna keep-out" % (side, layer, in_keepout))
            print("panel fills %s %s: %.3f mm² extra, %.4f mm² inside the keep-out" % (side, layer, extra, in_keepout))
            missing = shape(half["fills"][layer]).difference(in_panel).difference(near)
            area = missing.area
            where = ""
            if area > TOLERANCE:
                c = missing.centroid
                where = ", around (%.2f, %.2f) in the half's coordinates" % (c.x, c.y)
                problems.append("%s %s: the panel lacks %.2f mm² of the half's GND pour away from the mouse bites%s"
                                % (side, layer, area, where))
            print("panel fills %s %s: %.3f mm² of the half's pour missing away from the mouse bites" % (side, layer, area))
    print("panel fills: %s" % ("OK" if not problems else "FAIL (%d)" % len(problems)))
    for p in problems:
        print("FAIL " + p)
    sys.stdout.flush()
    os._exit(1 if problems else 0)


if __name__ == "__main__":
    main()
