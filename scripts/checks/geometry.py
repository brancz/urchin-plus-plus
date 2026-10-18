#!/usr/bin/env python3
"""Check a half's board against the original Urchin board: zero deviation (CLAUDE.md rule 1).

    "$KICAD_PY" scripts/checks/geometry.py BOARD --half left [--json OUT]

Compares against reference/urchin/main.kicad_pcb directly (not against the
extracted geometry file), so it checks the whole chain: extraction, generated
parts, placement. For the half:
  - every original switch, tenting puck and case-hole footprint has a footprint
    on BOARD at the same position and rotation, and every hole and pad of the
    original footprint is on that footprint at the same absolute position, with
    the same drill and size (to the nanometre)
  - BOARD's Edge.Cuts is exactly the half's original outline plus the tab
    closures recorded in hardware/geometry/urchin.json, nothing more or less
Exit 1 on any deviation. Runs under KiCad's Python (pcbnew); Python 3.9.
"""

import argparse
import json
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
SPLIT_X = 128.397
MECHANICAL = ("SW_Hotswap_Kailh_Choc", "Tenting_Puck", "M2_hole")


def nm(v):
    return int(v)


def half_of(fp):
    return "left" if pcbnew.ToMM(fp.GetPosition().x) > SPLIT_X else "right"


def holes(fp):
    """Every pad/hole as (x, y, drill_x, drill_y, size_x, size_y, layers, is_smd) in nm, sorted."""
    out = []
    for p in fp.Pads():
        pos, drill, size = p.GetPosition(), p.GetDrillSize(), p.GetSize(pcbnew.F_Cu)
        out.append((nm(pos.x), nm(pos.y), nm(drill.x), nm(drill.y), nm(size.x), nm(size.y),
                    p.GetLayerSet().FmtHex(), p.GetAttribute()))
    return sorted(out)


def edge(board):
    out = []
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        s = d.Cast()
        if s.GetShapeStr() == "Arc":
            pts = (s.GetStart(), s.GetArcMid(), s.GetEnd())
        else:
            pts = (s.GetStart(), s.GetEnd())
        key = tuple((nm(p.x), nm(p.y)) for p in pts)
        out.append((s.GetShapeStr(), min(key, tuple(reversed(key)))))
    return sorted(out)


def mm_key(prim):
    pts = [prim["start"]] + ([prim["mid"]] if "mid" in prim else []) + [prim["end"]]
    key = tuple((int(round(x * 1e6)), int(round(y * 1e6))) for x, y in pts)
    return ("Arc" if "mid" in prim else "Line", min(key, tuple(reversed(key))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--half", required=True, choices=("left", "right"))
    ap.add_argument("--reference", default=str(ROOT / "reference/urchin/main.kicad_pcb"))
    ap.add_argument("--geometry", default=str(ROOT / "hardware/geometry/urchin.json"))
    ap.add_argument("--json")
    args = ap.parse_args()

    ref = pcbnew.LoadBoard(args.reference)
    board = pcbnew.LoadBoard(args.board)
    geo = json.loads(Path(args.geometry).read_text())["halves"][args.half]
    problems, checked = [], {"footprints": 0, "holes_and_pads": 0, "edges": 0}

    candidates = [f for f in board.GetFootprints() if any(k in f.GetFPIDAsString() for k in MECHANICAL)]
    used = set()
    for rf in ref.GetFootprints():
        lib = rf.GetFPIDAsString()
        if half_of(rf) != args.half or not any(k in lib for k in MECHANICAL):
            continue
        want = holes(rf)
        match = [f for f in candidates if id(f) not in used and f.GetPosition() == rf.GetPosition()]
        if not match:
            problems.append("%s %s at (%.6f, %.6f): no footprint at that position" % (
                rf.GetReference(), lib, pcbnew.ToMM(rf.GetPosition().x), pcbnew.ToMM(rf.GetPosition().y)))
            continue
        f = match[0]
        used.add(id(f))
        checked["footprints"] += 1
        checked["holes_and_pads"] += len(want)
        if abs(f.GetOrientationDegrees() - rf.GetOrientationDegrees()) % 360 > 1e-9 and \
                abs(abs(f.GetOrientationDegrees() - rf.GetOrientationDegrees()) - 360) > 1e-9:
            problems.append("%s: rotation %.6f, original %.6f" % (rf.GetReference(), f.GetOrientationDegrees(),
                                                                rf.GetOrientationDegrees()))
        got = holes(f)
        # Original footprints on B.Cu (some case holes) are front-side parts here; a round
        # plated hole is the same hole either side, so compare without the layer mask.
        strip = lambda hs: sorted(h[:6] + (h[7],) for h in hs)
        if strip(got) != strip(want):
            problems.append("%s %s: holes/pads differ: missing %s, extra %s" % (
                rf.GetReference(), lib, sorted(set(strip(want)) - set(strip(got)))[:4],
                sorted(set(strip(got)) - set(strip(want)))[:4]))

    want_edges = sorted(mm_key(p) for p in geo["outline"] + geo["closures"])
    ref_edges = set(edge(ref))
    for p in geo["outline"]:
        if mm_key(p) not in ref_edges:
            problems.append("geometry outline primitive %s is not on the original board" % (mm_key(p),))
    got_edges = edge(board)
    checked["edges"] = len(got_edges)
    if got_edges != want_edges:
        problems.append("Edge.Cuts differs: missing %s, extra %s" % (
            sorted(set(want_edges) - set(got_edges))[:3], sorted(set(got_edges) - set(want_edges))[:3]))

    result = {"board": args.board, "half": args.half, "checked": checked, "problems": problems,
              "max_deviation_nm": 0 if not problems else None}
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2) + "\n")
    print("geometry %s (%s): %d footprints, %d holes/pads, %d edge primitives checked against the original"
          % (args.board, args.half, checked["footprints"], checked["holes_and_pads"], checked["edges"]))
    for p in problems:
        print("FAIL " + p)
    print("geometry: %s" % ("OK, zero deviation" if not problems else "FAIL (%d)" % len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
