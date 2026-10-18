#!/usr/bin/env python3
"""Route a half: rip up, Freerouting, import, ground pour on both layers (phase 4).

    "$KICAD_PY" scripts/routing/route.py BOARD WORK_DIR [--passes 40] [--keep]

  1. Remove every track and via and the GND pours (--keep keeps existing tracks and
     vias as fixed pre-routes; Freerouting routes around them).
  2. Export a Specctra DSN (net classes and the antenna keep-out come along from the
     board and its .kicad_pro), with the routing boundary inset by 0.35 mm so the
     router keeps the 0.3 mm copper-to-edge clearance it otherwise ignores, and
     run Freerouting 2.5.0 headless
     ($FREEROUTING_JAR, java 25+ on PATH); its log goes to WORK_DIR/freerouting.log.
  3. Import the session; widen the router's neck-downs below 0.15 mm (JLC's 2-layer
     minimum is 0.127 mm) to 0.15 mm; then pour GND on F.Cu and B.Cu over the whole outline
     (zones GND_TOP/GND_BOTTOM: 0.3 mm clearance, 0.25 mm minimum width, thermal
     reliefs on pads, islands removed). The antenna keep-out rule area forbids pour
     inside it. GND is also routed as a net, so connectivity never depends on a pour.
  4. Fill the zones and save.
Prints a JSON summary. Runs under KiCad's Python; Python 3.9.
"""

import argparse
import json
import os
import re
import subprocess
import sys

import pcbnew

POURS = {"GND_TOP": pcbnew.F_Cu, "GND_BOTTOM": pcbnew.B_Cu}
EDGE_KEEPOUT = 0.35  # mm: board_setup.py's 0.3 mm copper-to-edge plus margin
MIN_WIDTH = 0.15     # mm


def nm(v):
    return int(round(v * 1e6))


def shrink_boundary(dsn, board, inset):
    """Replace the DSN's routing boundary with the outline inset by `inset` mm.

    Freerouting ignores copper-to-edge clearance; a smaller boundary keeps its tracks
    and vias that far inside. Pads near or past the edge (USB-C, switch, the original's
    overhanging socket pads) stay where they are and are still reached from inside."""
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline)
    outline.Inflate(-nm(inset), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, nm(0.005))
    if outline.OutlineCount() != 1:
        sys.exit("inset outline has %d parts" % outline.OutlineCount())
    o = outline.Outline(0)
    pts = ["%.1f %.1f" % (o.CPoint(i).x / 1000.0, -o.CPoint(i).y / 1000.0) for i in range(o.PointCount())]
    pts.append(pts[0])
    text = open(dsn).read()
    new, n = re.subn(r"\(boundary\s*\(path pcb 0[^)]*\)\s*\)", "(boundary\n      (path pcb 0  %s)\n    )" % "  ".join(pts),
                     text, count=1)
    if n != 1:
        sys.exit("no boundary in %s" % dsn)
    open(dsn, "w").write(new)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("work")
    ap.add_argument("--passes", type=int, default=40)
    ap.add_argument("--keep", action="store_true", help="keep existing tracks and vias as fixed pre-routes")
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    dsn, ses = os.path.join(args.work, "board.dsn"), os.path.join(args.work, "board.ses")

    board = pcbnew.LoadBoard(args.board)
    # Take every wrapper before the first edit (KiCad 9's SWIG loses types afterwards).
    tracks = list(board.GetTracks())
    pours = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetZoneName() in POURS]
    for z in pours:
        board.Remove(z)
    if args.keep:
        for t in tracks:
            t.SetLocked(True)  # exported as fixed wiring; unlocked again below (atopile drops locks)
    else:
        for t in tracks:
            board.Remove(t)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        sys.exit("DSN export failed")
    shrink_boundary(dsn, board, EDGE_KEEPOUT)

    with open(os.path.join(args.work, "freerouting.log"), "w") as log:
        res = subprocess.run(["java", "-jar", os.environ["FREEROUTING_JAR"], "-de", dsn, "-do", ses,
                              "-mp", str(args.passes)], stdout=log, stderr=subprocess.STDOUT)
    if res.returncode != 0 or not os.path.exists(ses):
        sys.exit("Freerouting failed (see %s/freerouting.log)" % args.work)
    if not pcbnew.ImportSpecctraSES(board, ses):
        sys.exit("SES import failed")
    widened = 0
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < nm(MIN_WIDTH):
            t.SetWidth(nm(MIN_WIDTH))
            widened += 1

    gnd = board.FindNet("GND")
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline)
    for name, layer in POURS.items():
        z = pcbnew.ZONE(board)
        z.SetZoneName(name)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetLocalClearance(nm(0.3))
        z.SetMinThickness(nm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(nm(0.3))
        z.SetThermalReliefSpokeWidth(nm(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetAssignedPriority(0)
        o = outline.Outline(0)
        z.Outline().NewOutline()
        for i in range(o.PointCount()):
            p = o.CPoint(i)
            z.Outline().Append(p.x, p.y)
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    routed = list(board.GetTracks())
    for t in routed:
        t.SetLocked(False)
    board.BuildConnectivity()
    unrouted = board.GetConnectivity().GetUnconnectedCount(False)
    board.Save(args.board)
    print(json.dumps({"board": args.board, "tracks": sum(1 for t in routed if t.GetClass() == "PCB_TRACK"),
                      "vias": sum(1 for t in routed if t.GetClass() == "PCB_VIA"), "widened": widened,
                      "unrouted": unrouted}))
    sys.stdout.flush()
    os._exit(0)  # KiCad 9's SWIG objects segfault in destructors at exit


if __name__ == "__main__":
    main()
