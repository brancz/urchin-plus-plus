#!/usr/bin/env python3
"""Tidy the designators on a half's silkscreen (phase 4).

    "$KICAD_PY" scripts/placement/silk.py BOARD [--check]

  - Bottom-side designators are mirrored, so they read correctly from below, and set
    to 1.0 mm text with a 0.15 mm stroke (JLC's legible minimum).
  - Designators of the small passives and diodes (R*, C*, D*) are hidden: at 0402/0603
    they only overlap their neighbours; so are the markers' (MK*) and the battery
    outline's (BT2; BT1, the pads, are marked + and -). The parts a person handles keep theirs: the
    module, charger, ESD, connector, switches, LEDs, test and battery pads.
atopile positions designators only for new footprints, so this survives rebuilds;
--check fails if any designator differs from the above. Runs under KiCad's Python.
"""

import argparse
import os
import sys

import pcbnew

HIDE = ("R", "C", "D", "MK", "BT")  # small passives; the marker outlines and the battery outline carry no text
SIZE, STROKE = 1.0, 0.15             # JLC's legible minimum


def nm(v):
    return int(round(v * 1e6))


def wanted(fp):
    ref = fp.GetReference()
    prefix = ref.rstrip("0123456789")
    return {"mirrored": fp.GetLayer() == pcbnew.B_Cu, "visible": prefix not in HIDE}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    board = pcbnew.LoadBoard(args.board)
    footprints = [fp for fp in board.GetFootprints() if fp.GetLayer() == pcbnew.B_Cu
                  or fp.GetReference().startswith("BT")]
    problems, changed = [], 0
    for fp in footprints:
        f = fp.Reference()
        w = wanted(fp)
        state = (f.IsMirrored(), f.IsVisible(), f.GetTextSize().x, f.GetTextThickness())
        want = (w["mirrored"], w["visible"], nm(SIZE), nm(STROKE))
        if state == want:
            continue
        if args.check:
            problems.append("%s designator: mirrored/visible/size/stroke %s, want %s" % (fp.GetReference(), state, want))
            continue
        f.SetMirrored(w["mirrored"])
        f.SetVisible(w["visible"])
        f.SetTextSize(pcbnew.VECTOR2I(nm(SIZE), nm(SIZE)))
        f.SetTextThickness(nm(STROKE))
        changed += 1
    if args.check:
        print("silk %s: %s" % (args.board, "OK" if not problems else "FAIL (%d)" % len(problems)))
        for p in problems:
            print("FAIL " + p)
    else:
        board.Save(args.board)
        print("silk %s: %d designators updated" % (args.board, changed))
    sys.stdout.flush()
    os._exit(1 if problems else 0)


if __name__ == "__main__":
    main()
