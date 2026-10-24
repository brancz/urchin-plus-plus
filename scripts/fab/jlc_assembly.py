#!/usr/bin/env python3
"""JLCPCB assembly files for the panel: BOM and CPL, with sanity checks (phase 6).

    "$KICAD_PY" scripts/fab/jlc_assembly.py PANEL.kicad_pcb OUT_DIR
    "$KICAD_PY" scripts/fab/jlc_assembly.py --dock DOCK.kicad_pcb OUT_DIR      (phase 7)

KiKit's `fab jlcpcb --assembly` needs a schematic, which atopile doesn't write, so the
BOM and CPL come from the panel's footprints directly:
  - BOM (bom.csv): Comment, Designator, Footprint, LCSC Part #: one line per LCSC part,
    from each footprint's LCSC field (atopile writes it from hardware/parts.json).
  - CPL (positions.csv): Designator, Mid X, Mid Y, Layer, Rotation, computed with the
    same functions `kikit fab jlcpcb` uses (kikit.fab.common, MirrorBottom: Y negated,
    bottom-side rotation = 180 - KiCad angle). The footprints are JLC's own (EasyEDA)
    footprints in KiCad's native bottom-side form, so no per-part corrections apply;
    every rotation is still checked in JLC's placement preview (fab checklist).
Checks (exit 1 on failure): every footprint in the position file has an LCSC number;
nothing assembled is on the top; per-side quantities equal hardware/parts.json for each
half; every LCSC number in the BOM is in parts.json. Runs under KiCad's Python.
With --dock, the dock board: dock-pcb/parts.json, quantities per board, and everything
assembled on the top (the dock's single assembled side, docs/ARCHITECTURE.md "Dock").
"""

import collections
import csv
import json
import os
import sys
from pathlib import Path

import pcbnew
import re

from kikit.fab.common import (FootprintOrientationHandling, defaultFootprintX, defaultFootprintY,
                               footprintOrientation, layerToSide)

ROOT = Path(__file__).resolve().parents[2]


def main():
    args = sys.argv[1:]
    dock = args[:1] == ["--dock"]
    panel_path, out = Path(args[-2]), Path(args[-1])
    out.mkdir(parents=True, exist_ok=True)
    board = pcbnew.LoadBoard(str(panel_path))
    manifest = "dock-pcb/parts.json" if dock else "hardware/parts.json"
    parts = {p["lcsc"]: p for p in json.loads((ROOT / manifest).read_text())["parts"]}
    side, side_rule = ("T", "the dock is assembled on its top") if dock else ("B", "rule 2")
    problems = []

    # KiKit's panel fiducials and tooling holes are footprints too, but not components
    placed = [fp for fp in board.GetFootprints() if not fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES
              and not fp.GetReference().startswith("KiKit_")]
    bom_rows = collections.defaultdict(list)
    per_half = collections.Counter()
    for fp in placed:
        ref = fp.GetReference()
        lcsc = fp.GetFieldText("LCSC") if fp.HasFieldByName("LCSC") else ""
        if not lcsc:
            problems.append("%s is placed but has no LCSC number" % ref)
            continue
        if lcsc not in parts:
            problems.append("%s carries %s, which %s doesn't list" % (ref, lcsc, manifest))
        if layerToSide(fp.GetLayer()) != side:
            problems.append("%s is assembled on the wrong side (%s)" % (ref, side_rule))
        if fp.IsExcludedFromBOM():
            problems.append("%s is in the position file but excluded from the BOM" % ref)
        value = fp.GetFieldText("Partnumber") if fp.HasFieldByName("Partnumber") else fp.GetValue()
        bom_rows[(lcsc, value, fp.GetFPID().GetLibItemName().wx_str())].append(ref)
        per_half[("board" if dock else ref.rsplit("_", 1)[-1], lcsc)] += 1
    for lcsc, p in parts.items():
        for half in (("board",) if dock else ("L", "R")):
            if per_half[(half, lcsc)] != p["qty"]:
                problems.append("%s: %d on the %s, parts.json says %d" % (lcsc, per_half[(half, lcsc)],
                                                                          "board" if dock else half + " half", p["qty"]))

    with open(out / "bom.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (lcsc, value, footprint), refs in sorted(bom_rows.items()):
            w.writerow([value, ",".join(sorted(refs)), footprint, lcsc])

    origin = board.GetDesignSettings().GetAuxOrigin()  # what kikit.fab.common.collectPosData does
    pos = [(fp.GetReference(), defaultFootprintX(fp, origin, (0, 0, 0)), defaultFootprintY(fp, origin, (0, 0, 0)),
            layerToSide(fp.GetLayer()),
            footprintOrientation(fp, (0, 0, 0), FootprintOrientationHandling.MirrorBottom)) for fp in placed]
    # kikit.fab.common.posDataToFile's format; its sort can't parse the R1_L designators
    key = lambda r: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", r[0])]
    with open(out / "positions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for ref, x, y, side, rot in sorted(pos, key=key):
            w.writerow([ref, "%.2f" % x, "%.2f" % y, side, "%.2f" % rot])

    print("assembly: %d placements, %d BOM lines -> %s" % (len(pos), len(bom_rows), out))
    for p in problems:
        print("FAIL " + p)
    print("assembly: %s" % ("OK" if not problems else "FAIL (%d)" % len(problems)))
    sys.stdout.flush()
    os._exit(1 if problems else 0)


if __name__ == "__main__":
    main()
