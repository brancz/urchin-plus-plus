#!/usr/bin/env python3
"""Extract the original Urchin geometry into hardware/geometry/urchin.json (CLAUDE.md rule 1).

    "$KICAD_PY" scripts/geometry/extract.py [--reference reference/urchin/main.kicad_pcb] [--out hardware/geometry/urchin.json]

The reference board is a panel of both halves joined by two mouse-bite tabs at
x = 128.397. Per half this records, in the reference board's own coordinates
(the halves' layouts keep them, so a deviation check is a plain comparison):
  - the 17 switches: footprint position and rotation (= switch centre), with a
    row/column name (col 0 = pinky ... 4 = inner index; t0/t1 = thumbs)
  - the outline: every Edge.Cuts line and arc as drawn, minus the panel's tab
    stubs and slot ends, plus the two "closures" that close each half's edge
    across the tab openings (collinear with that edge)
  - the tenting-puck mount and the case mounting holes (position, rotation,
    footprint, hole positions)
  - the old controller area (nice!nano, nice!view, power switch, reset, battery
    pads) as placement hints
Hand-placed copies of footprints carry over unchanged: library footprints are
written to hardware/parts/<name>/ by scripts/geometry/mechanical_parts.py.
Runs under KiCad's Python (pcbnew); Python 3.9.
"""

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
SPLIT_X = 128.397  # centre of the panel gap between the halves
GAP = (127.2, 129.6)  # strictly inside the gap: tab stubs and slot ends live here
EPS = 1e-4  # mm


def mm(v):
    return round(pcbnew.ToMM(v), 6)


def pt(p):
    return [mm(p.x), mm(p.y)]


def half_of(x):
    # Reading the reference: the half at x > SPLIT_X has its thumb keys and controller
    # at its right-hand side, i.e. at its inner edge when worn on the left hand.
    return "left" if x > SPLIT_X else "right"


def edge_primitives(board):
    prims = []
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        s = d.Cast()
        kind = s.GetShapeStr()
        if kind == "Line":
            prims.append({"type": "line", "start": pt(s.GetStart()), "end": pt(s.GetEnd())})
        elif kind == "Arc":
            prims.append({"type": "arc", "start": pt(s.GetStart()), "mid": pt(s.GetArcMid()), "end": pt(s.GetEnd())})
        else:
            raise SystemExit("unexpected Edge.Cuts shape %s" % kind)
    return prims


def in_gap(p):
    xs = [p["start"][0], p["end"][0]] + ([p["mid"][0]] if "mid" in p else [])
    crosses = min(xs) < SPLIT_X < max(xs)
    return crosses or any(GAP[0] < x < GAP[1] for x in xs)


def close_half(prims, half):
    """Close the openings the tabs leave in this half's edge; return the closures."""
    ends = {}
    for p in prims:
        for e in (tuple(p["start"]), tuple(p["end"])):
            ends[e] = ends.get(e, 0) + 1
    dangling = sorted((e for e, n in ends.items() if n == 1), key=lambda e: e[1])
    if len(dangling) % 2:
        raise SystemExit("%s: odd number of open ends %s" % (half, dangling))
    closures = []
    for a, b in zip(dangling[::2], dangling[1::2]):
        if abs(a[0] - b[0]) > EPS:
            raise SystemExit("%s: tab opening %s-%s is not vertical" % (half, a, b))
        closures.append({"type": "line", "start": list(a), "end": list(b), "derived": "tab closure"})
    return closures


def chain_is_closed(prims):
    ends = {}
    for p in prims:
        for e in (tuple(p["start"]), tuple(p["end"])):
            ends[e] = ends.get(e, 0) + 1
    return all(n == 2 for n in ends.values())


def footprint_record(fp):
    return {
        "ref": fp.GetReference(),
        "footprint": fp.GetFPIDAsString(),
        "x": mm(fp.GetPosition().x),
        "y": mm(fp.GetPosition().y),
        "rot": round(fp.GetOrientationDegrees(), 6),
        "layer": fp.GetLayerName(),
        "holes": [
            {"x": mm(p.GetPosition().x), "y": mm(p.GetPosition().y), "drill": mm(p.GetDrillSize().x),
             "pad": mm(p.GetSize(pcbnew.F_Cu).x), "plated": p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH}
            for p in fp.Pads() if p.GetDrillSize().x > 0
        ],
    }


def name_switches(switches, half):
    """col 0 = pinky (outer) ... 4 = inner index, row 0 = top; rotated keys are thumbs."""
    mains = [s for s in switches if abs(s["rot"]) < EPS]
    thumbs = [s for s in switches if abs(s["rot"]) >= EPS]
    xs = sorted({round(s["x"], 1) for s in mains}, reverse=(half == "right"))
    if len(xs) != 5 or len(mains) != 15 or len(thumbs) != 2:
        raise SystemExit("%s: expected 5 columns x 3 rows + 2 thumbs" % half)
    for s in mains:
        col = xs.index(round(s["x"], 1))
        rows = sorted(t["y"] for t in mains if round(t["x"], 1) == round(s["x"], 1))
        s["key"] = "r%dc%d" % (rows.index(s["y"]), col)
    # t0: the thumb nearer the main keys
    centre = (sum(s["x"] for s in mains) / 15, sum(s["y"] for s in mains) / 15)
    for i, s in enumerate(sorted(thumbs, key=lambda s: math.hypot(s["x"] - centre[0], s["y"] - centre[1]))):
        s["key"] = "t%d" % i
    return sorted(switches, key=lambda s: s["key"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", default=str(ROOT / "reference/urchin/main.kicad_pcb"))
    ap.add_argument("--out", default=str(ROOT / "hardware/geometry/urchin.json"))
    args = ap.parse_args()

    ref = Path(args.reference)
    board = pcbnew.LoadBoard(str(ref))
    commit = subprocess.run(["git", "-C", str(ref.parent), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    out = {
        "source": {
            "file": str(ref.relative_to(ROOT)) if ref.is_relative_to(ROOT) else str(ref),
            "repository": "https://github.com/duckyb/urchin",
            "commit": commit,
            "sha256": hashlib.sha256(ref.read_bytes()).hexdigest(),
        },
        "units": "mm, reference board coordinates; rotation in degrees (KiCad, counter-clockwise)",
        "halves": {},
    }

    prims = edge_primitives(board)
    dropped = [p for p in prims if in_gap(p)]
    for half in ("left", "right"):
        outline = [p for p in prims if not in_gap(p) and half_of(p["start"][0]) == half]
        closures = close_half(outline, half)
        if not chain_is_closed(outline + closures):
            raise SystemExit("%s: outline does not close" % half)
        out["halves"][half] = {
            "outline": outline,
            "closures": closures,
            "switches": [],
            "tenting_puck": None,
            "case_holes": [],
            "controller_area": {},
        }

    for fp in board.GetFootprints():
        lib = fp.GetFPIDAsString()
        half = half_of(mm(fp.GetPosition().x))
        h = out["halves"][half]
        rec = footprint_record(fp)
        if "SW_Hotswap_Kailh_Choc" in lib:
            h["switches"].append(rec)
        elif "Tenting_Puck" in lib:
            h["tenting_puck"] = rec
        elif "M2_hole" in lib:
            h["case_holes"].append(rec)
        elif any(k in lib for k in ("nice_nano", "nice_view", "smt-slider-switch", "SW_RESET", "1pin_Battery")):
            bb = fp.GetBoundingBox(False)
            rec["bbox"] = [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]
            h["controller_area"][rec["ref"]] = rec

    for half, h in out["halves"].items():
        h["switches"] = name_switches(h["switches"], half)
        h["case_holes"].sort(key=lambda r: (r["x"], r["y"]))

    out["dropped_panel_features"] = dropped
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    for half, h in out["halves"].items():
        print("%s: %d switches, %d outline primitives + %d closures, puck at (%.3f, %.3f) rot %.1f, %d case holes"
              % (half, len(h["switches"]), len(h["outline"]), len(h["closures"]), h["tenting_puck"]["x"],
                 h["tenting_puck"]["y"], h["tenting_puck"]["rot"], len(h["case_holes"])))
    print("dropped %d panel-only edge primitives (tab stubs, slot ends)" % len(dropped))


if __name__ == "__main__":
    main()
