#!/usr/bin/env python3
"""Check a half's board against the original Urchin board: zero deviation (CLAUDE.md rule 1).

    "$KICAD_PY" scripts/checks/geometry.py BOARD --half left [--json OUT]

Everything is derived from reference/urchin/main.kicad_pcb itself; the extracted
geometry file is only checked for agreement, never trusted:
  - switches and the tenting puck: every original footprint has exactly one
    footprint on BOARD at the same position and rotation, with every pad
    identical: position, size, shape, orientation, drill, plating, copper and
    mask layers of the 2-layer stack (to the nanometre). Paste layers are not
    compared: the hand-soldered socket pads deliberately carry none.
  - case holes: each original case hole is on BOARD at the same position with
    the same drill, except holes whose drill overlaps a puck hole or a larger
    case hole (those must be absent). Plating and pad size are not compared.
  - no other switch, puck or case-hole footprint on BOARD.
  - outline: BOARD's Edge.Cuts (board drawings and footprint graphics) is exactly
    the original half's outline, without the panel's tab stubs and slot ends, plus
    the straight closures across the two tab openings, derived here from the
    original's open ends (each must be vertical, i.e. collinear with the edge).
  - hardware/geometry/urchin.json agrees with all of the above.
Exit 1 on any deviation. Runs under KiCad's Python (pcbnew); Python 3.9.
"""

import argparse
import collections
import json
import math
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
SPLIT_X = 128397000  # nm, centre of the panel gap
GAP = (127200000, 129600000)  # nm, strictly inside the gap
ARC_MID_TOL = 50  # nm: KiCad recomputes an arc's midpoint from its centre
KINDS = {"SW_Hotswap_Kailh_Choc": "switch", "Tenting_Puck": "puck", "M2_hole": "case hole"}
TWO_LAYER = (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.F_Mask, pcbnew.B_Mask)  # a 2-layer board: *.Cu == F&B.Cu


def kind_of(fp):
    lib = fp.GetFPIDAsString()
    return next((k for key, k in KINDS.items() if key in lib), None)


def half_of_x(x):
    return "left" if x > SPLIT_X else "right"


def pad_sig(p, full):
    pos, size, drill = p.GetPosition(), p.GetSize(pcbnew.F_Cu), p.GetDrillSize()
    if not full:
        return (int(pos.x), int(pos.y), int(drill.x), int(drill.y))
    layers = tuple(l for l in TWO_LAYER if p.GetLayerSet().Contains(l))
    return (int(pos.x), int(pos.y), int(size.x), int(size.y), int(drill.x), int(drill.y),
            p.ShowPadShape(pcbnew.F_Cu), round(p.GetOrientationDegrees() % 360, 6), p.GetAttribute(), layers)


def edges(board):
    """Edge.Cuts as (kind, endpoints sorted, mid) in nm, from drawings and footprints."""
    items = list(board.GetDrawings())
    for fp in board.GetFootprints():
        items += list(fp.GraphicalItems())
    out = []
    for d in items:
        if d.GetLayer() != pcbnew.Edge_Cuts or d.GetClass() != "PCB_SHAPE":
            continue
        s = d.Cast()
        a, b = (int(s.GetStart().x), int(s.GetStart().y)), (int(s.GetEnd().x), int(s.GetEnd().y))
        mid = (int(s.GetArcMid().x), int(s.GetArcMid().y)) if s.GetShapeStr() == "Arc" else None
        out.append((s.GetShapeStr(), tuple(sorted((a, b))), mid))
    return out


def in_gap(e):
    xs = [p[0] for p in e[1]] + ([e[2][0]] if e[2] else [])
    return min(xs) < SPLIT_X < max(xs) or any(GAP[0] < x < GAP[1] for x in xs)


def reference_outline(ref, half):
    kept = [e for e in edges(ref) if not in_gap(e) and half_of_x(e[1][0][0]) == half]
    ends = collections.Counter(p for e in kept for p in e[1])
    dangling = sorted((p for p, n in ends.items() if n == 1), key=lambda p: p[1])
    closures, problems = [], []
    if len(dangling) % 2:
        problems.append("original %s outline has %d open ends" % (half, len(dangling)))
    for a, b in zip(dangling[::2], dangling[1::2]):
        if a[0] != b[0]:
            problems.append("tab opening %s-%s is not vertical" % (a, b))
        closures.append(("Line", tuple(sorted((a, b))), None))
    return kept, closures, problems


def same_edges(want, got):
    """Match edges exactly (lines) or with the arc midpoint within ARC_MID_TOL."""
    pool = list(got)
    missing = []
    for w in want:
        hit = next((g for g in pool if g[0] == w[0] and g[1] == w[1] and
                    (w[2] is None or math.hypot(g[2][0] - w[2][0], g[2][1] - w[2][1]) <= ARC_MID_TOL)), None)
        if hit is None:
            missing.append(w)
        else:
            pool.remove(hit)
    return missing, pool


def drill_overlap(a, b):
    pa, pb = a.GetPosition(), b.GetPosition()
    return math.hypot(pa.x - pb.x, pa.y - pb.y) < (a.GetDrillSize().x + b.GetDrillSize().x) / 2


def mm(nm_pair):
    return "(%.6f, %.6f)" % (nm_pair[0] / 1e6, nm_pair[1] / 1e6)


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
    problems = []
    checked = collections.Counter()

    originals = [f for f in ref.GetFootprints() if kind_of(f) and half_of_x(f.GetPosition().x) == args.half]
    puck_pads = [p for f in originals if kind_of(f) == "puck" for p in f.Pads()]
    wanted, dropped = [], []
    for f in originals:
        if kind_of(f) == "case hole":
            hole = f.Pads()[0]
            bigger = any(o is not f and kind_of(o) == "case hole" and drill_overlap(hole, o.Pads()[0])
                         and o.Pads()[0].GetDrillSize().x > hole.GetDrillSize().x for o in originals)
            if any(drill_overlap(hole, p) for p in puck_pads) or bigger:
                dropped.append(f)
                continue
        wanted.append(f)

    candidates = [f for f in board.GetFootprints() if kind_of(f)]
    used = set()
    for rf in wanted:
        kind = kind_of(rf)
        full = kind != "case hole"
        match = [f for f in candidates if id(f) not in used and kind_of(f) == kind and f.GetPosition() == rf.GetPosition()]
        where = "%s %s at %s" % (kind, rf.GetReference(), mm(rf.GetPosition()))
        if len(match) != 1:
            problems.append("%s: %d footprints at that position" % (where, len(match)))
            continue
        f = match[0]
        used.add(id(f))
        checked[kind] += 1
        dr = (f.GetOrientationDegrees() - rf.GetOrientationDegrees()) % 360
        if full and min(dr, 360 - dr) > 1e-9:
            problems.append("%s: rotation %.6f, original %.6f" % (where, f.GetOrientationDegrees(), rf.GetOrientationDegrees()))
        want = collections.Counter(pad_sig(p, full) for p in rf.Pads())
        got = collections.Counter(pad_sig(p, full) for p in f.Pads())
        checked["pads"] += sum(want.values())
        if want != got:
            problems.append("%s: pads differ: missing %s, extra %s" % (where, list((want - got).elements())[:3],
                                                                      list((got - want).elements())[:3]))
    for f in candidates:
        if id(f) not in used:
            problems.append("extra %s footprint %s at %s" % (kind_of(f), f.GetReference(), mm(f.GetPosition())))
    for f in dropped:
        if any(kind_of(c) == "case hole" and c.GetPosition() == f.GetPosition() for c in candidates):
            problems.append("case hole at %s overlaps another hole and must be absent" % mm(f.GetPosition()))

    kept, closures, prob = reference_outline(ref, args.half)
    problems += prob
    got_edges = edges(board)
    checked["edges"] = len(got_edges)
    missing, extra = same_edges(kept + closures, got_edges)
    for e in missing:
        problems.append("Edge.Cuts missing %s %s-%s" % (e[0], mm(e[1][0]), mm(e[1][1])))
    for e in extra:
        problems.append("Edge.Cuts extra %s %s-%s" % (e[0], mm(e[1][0]), mm(e[1][1])))

    # The geometry file must say the same.
    g = lambda r: (int(round(r["x"] * 1e6)), int(round(r["y"] * 1e6)))
    if sorted(g(s) for s in geo["switches"]) != sorted(tuple(map(int, (f.GetPosition().x, f.GetPosition().y)))
                                                       for f in wanted if kind_of(f) == "switch"):
        problems.append("urchin.json switches disagree with the original")
    if sorted(g(s) for s in geo["case_holes"]) != sorted(tuple(map(int, (f.GetPosition().x, f.GetPosition().y)))
                                                         for f in wanted if kind_of(f) == "case hole"):
        problems.append("urchin.json case holes disagree with the original (minus overlapping ones)")
    as_edge = lambda p: (("Arc" if "mid" in p else "Line"),
                         tuple(sorted((g(dict(x=p["start"][0], y=p["start"][1])), g(dict(x=p["end"][0], y=p["end"][1]))))),
                         g(dict(x=p["mid"][0], y=p["mid"][1])) if "mid" in p else None)
    m2, e2 = same_edges(kept + closures, [as_edge(p) for p in geo["outline"] + geo["closures"]])
    if m2 or e2:
        problems.append("urchin.json outline disagrees with the original: %d missing, %d extra" % (len(m2), len(e2)))

    result = {"board": args.board, "half": args.half, "checked": dict(checked), "problems": problems}
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2) + "\n")
    print("geometry %s (%s): %d switches, %d puck, %d case holes, %d pads, %d edge primitives checked against the original"
          % (args.board, args.half, checked["switch"], checked["puck"], checked["case hole"], checked["pads"], checked["edges"]))
    for p in problems:
        print("FAIL " + p)
    print("geometry: %s" % ("OK, zero deviation" if not problems else "FAIL (%d)" % len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
