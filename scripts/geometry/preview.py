#!/usr/bin/env python3
"""Build a board per half from hardware/geometry/urchin.json and the mechanical parts.

    "$KICAD_PY" scripts/geometry/preview.py OUT_DIR

Writes OUT_DIR/<half>.kicad_pcb with the outline (and tab closures), the 17 key
footprints, the tenting puck and the case holes placed from the geometry file,
using the footprints in hardware/parts/. Phase 1 checks these against the
original with scripts/checks/geometry.py and renders them; phase 3 places the
same way on the real boards. Runs under KiCad's Python (pcbnew); Python 3.9.
"""

import json
import os
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
PARTS = ROOT / "hardware/parts"
LIB_FOR = {"SW_Hotswap_Kailh_Choc_V1_tweaked": "KEY_CHOC", "Tenting_Puck2_no_pads": "PUCK",
           "M2_hole_4.2mm": "HOLE_M2_4_2", "M2_hole_3.5mm": "HOLE_M2_3_5"}


def at(x, y):
    # Round, don't truncate: pcbnew.FromMM(129.886791) is 129886790 nm.
    return pcbnew.VECTOR2I(int(round(x * 1e6)), int(round(y * 1e6)))


def place(board, rec):
    name = rec["footprint"].split(":")[-1]
    part = LIB_FOR[name]
    fp = pcbnew.FOOTPRINT(pcbnew.PCB_IO_KICAD_SEXPR().FootprintLoad(str(PARTS / part), name))
    board.Add(fp)
    fp.SetPosition(at(rec["x"], rec["y"]))
    fp.SetOrientationDegrees(rec["rot"])
    fp.SetReference(rec["ref"])


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    geo = json.loads((ROOT / "hardware/geometry/urchin.json").read_text())
    for half, h in geo["halves"].items():
        board = pcbnew.NewBoard(str(out / (half + ".kicad_pcb")))
        for p in h["outline"] + h["closures"]:
            s = pcbnew.PCB_SHAPE(board)
            if p["type"] == "arc":
                s.SetShape(pcbnew.SHAPE_T_ARC)
                s.SetArcGeometry(at(*p["start"]), at(*p["mid"]), at(*p["end"]))
            else:
                s.SetShape(pcbnew.SHAPE_T_SEGMENT)
                s.SetStart(at(*p["start"]))
                s.SetEnd(at(*p["end"]))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(pcbnew.FromMM(0.1))
            board.Add(s)
        for rec in h["switches"] + [h["tenting_puck"]] + h["case_holes"]:  # case_holes_dropped stay out
            place(board, rec)
        pcbnew.SaveBoard(str(out / (half + ".kicad_pcb")), board)
        print("%s: %s" % (half, out / (half + ".kicad_pcb")))
    sys.stdout.flush()
    os._exit(0)  # KiCad 9's SWIG objects segfault in destructors at exit


if __name__ == "__main__":
    main()
