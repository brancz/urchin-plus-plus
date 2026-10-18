#!/usr/bin/env python3
"""Place every footprint of a half and draw its outline and antenna keep-out (phase 3).

    "$KICAD_PY" scripts/placement/place.py BOARD --half left|right [--check]

  - Edge.Cuts: the half's outline and tab closures from hardware/geometry/urchin.json
    (board drawings on Edge.Cuts are replaced).
  - Keys, the tenting puck and the case holes: exactly at their urchin.json position
    and rotation (rule 1); designators SW*, H1 (puck), H2.. (case holes, in file order).
  - Everything else: hardware/placement.json (left half; mirrored for the right half).
    A part's side must match its library footprint's side: footprints are never
    flipped here (atopile re-syncs footprints from the library on every build).
  - The antenna keep-out: a board-level rule area named ANTENNA_KEEPOUT on both copper
    layers forbidding tracks, vias and copper pour (pads are allowed only so that the NPTH
    case holes in the old notch's ears pass; clearance.py rejects any copper pad in it),
    drawn from U1's position: the
    module's antenna end (local y -10.98 .. -7.58, i.e. up to 0.06 mm short of the first
    pad row; E73 datasheet p.5 drawing) widened to the old notch's ears, x +-9.4 mm, and
    extended 5 mm past the board edge. Parts and the battery are kept out by
    scripts/checks/clearance.py.
Unknown or missing footprints are errors. --check changes nothing and fails if any
footprint is not where the geometry file and placement.json put it. Runs under KiCad's Python; Python 3.9.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
KEEPOUT_NAME = "ANTENNA_KEEPOUT"
KEEPOUT_LOCAL = (-9.4, 9.4, -15.98, -7.58)  # x0, x1, y0, y1 in U1's frame (mm)


def nm(v):
    return int(round(v * 1e6))  # pcbnew.FromMM truncates


def at(x, y):
    return pcbnew.VECTOR2I(nm(x), nm(y))


def rotate(x, y, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return x * c + y * s, -x * s + y * c


def half_parts(placement, half):
    out = {}
    for ref, r in placement["parts"].items():
        if half == "left":
            out[ref] = dict(r)
        else:
            out[ref] = dict(r, x=2 * placement["mirror_x"] - r["x"], rot=r.get("rot_right", (-r["rot"]) % 360))
    return out


def keepout_polygon(u1):
    x0, x1, y0, y1 = KEEPOUT_LOCAL
    pts = []
    for lx, ly in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        dx, dy = rotate(lx, ly, u1["rot"])
        pts.append((u1["x"] + dx, u1["y"] + dy))
    return pts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--half", required=True, choices=("left", "right"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    geo = json.loads((ROOT / "hardware/geometry/urchin.json").read_text())["halves"][args.half]
    parts = half_parts(json.loads((ROOT / "hardware/placement.json").read_text()), args.half)
    targets = {}
    for s in geo["switches"]:
        targets[s["ref"]] = dict(x=s["x"], y=s["y"], rot=s["rot"], side="top")
    targets["H1"] = dict(x=geo["tenting_puck"]["x"], y=geo["tenting_puck"]["y"], rot=geo["tenting_puck"]["rot"], side="top")
    for i, h in enumerate(geo["case_holes"]):
        targets["H%d" % (i + 2)] = dict(x=h["x"], y=h["y"], rot=h["rot"], side="top")
    for ref, r in parts.items():
        if ref in targets:
            sys.exit("placement.json places %s, which comes from the geometry file" % ref)
        targets[ref] = r

    board = pcbnew.LoadBoard(args.board)
    # Take every wrapper before changing anything: after the first edit KiCad 9's SWIG can
    # hand back untyped objects from the board's item lists.
    footprints = list(board.GetFootprints())
    zones = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName() == KEEPOUT_NAME]
    edges = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    if not args.check:
        for item in zones + edges:
            board.Remove(item)
    problems = []
    seen = set()
    for fp in footprints:
        ref = fp.GetReference()
        t = targets.get(ref)
        if t is None:
            problems.append("%s: no placement" % ref)
            continue
        seen.add(ref)
        side = "bottom" if fp.GetLayer() == pcbnew.B_Cu else "top"
        if side != t["side"]:
            problems.append("%s: library footprint is %s side, placement wants %s" % (ref, side, t["side"]))
            continue
        if args.check:
            dr = (fp.GetOrientationDegrees() - t["rot"]) % 360
            if fp.GetPosition() != at(t["x"], t["y"]) or min(dr, 360 - dr) > 1e-6:
                problems.append("%s at (%.4f, %.4f) %.3f deg, placement says (%.4f, %.4f) %.3f deg" % (
                    ref, fp.GetPosition().x / 1e6, fp.GetPosition().y / 1e6, fp.GetOrientationDegrees(), t["x"], t["y"], t["rot"]))
            continue
        fp.SetPosition(at(t["x"], t["y"]))
        fp.SetOrientationDegrees(t["rot"])
    for ref in sorted(set(targets) - seen):
        problems.append("%s: placed but not on the board" % ref)
    if args.check:
        if len(zones) != 1:
            problems.append("%d %s rule areas, expected 1" % (len(zones), KEEPOUT_NAME))
        else:
            got = sorted((p.x, p.y) for p in [zones[0].Outline().COutline(0).CPoint(i)
                                               for i in range(zones[0].Outline().COutline(0).PointCount())])
            if got != sorted((nm(x), nm(y)) for x, y in keepout_polygon(parts["U1"])):
                problems.append("%s outline differs from the one drawn from U1" % KEEPOUT_NAME)
        print("placement %s (%s): %s" % (args.board, args.half, "OK" if not problems else "FAIL (%d)" % len(problems)))
    if problems:
        for p in problems:
            print("FAIL " + p)
        sys.stdout.flush()
        os._exit(1)
    if args.check:
        sys.stdout.flush()
        os._exit(0)

    for p in geo["outline"] + geo["closures"]:
        s = pcbnew.PCB_SHAPE(board)
        if p["type"] == "arc":
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetArcGeometry(at(*p["start"]), at(*p["mid"]), at(*p["end"]))
        else:
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(at(*p["start"]))
            s.SetEnd(at(*p["end"]))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(nm(0.1))
        board.Add(s)

    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(KEEPOUT_NAME)
    z.SetLayerSet(pcbnew.LSET().AddLayer(pcbnew.F_Cu).AddLayer(pcbnew.B_Cu))
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)  # the NPTH case holes in the ears; clearance.py rejects copper pads
    z.SetDoNotAllowCopperPour(True)
    z.SetDoNotAllowFootprints(False)  # U1's own body reaches into it; clearance.py checks the others
    outline = z.Outline()
    outline.NewOutline()
    for x, y in keepout_polygon(parts["U1"]):
        outline.Append(nm(x), nm(y))
    board.Add(z)

    board.Save(args.board)
    print("placed %d footprints on %s (%s), outline %d primitives, %s" % (
        len(seen), args.board, args.half, len(geo["outline"]) + len(geo["closures"]), KEEPOUT_NAME))
    sys.stdout.flush()
    os._exit(0)  # KiCad 9's SWIG objects segfault in destructors at exit


if __name__ == "__main__":
    main()
