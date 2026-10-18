#!/usr/bin/env python3
"""Pad tables of every assembled part's footprint, for review against the datasheets.

    python3 scripts/parts/footprint_report.py OUT_DIR

Writes OUT_DIR/footprints.md and one SVG per footprint (kicad-cli fp export svg).
Bottom-side library footprints are shown as their front-side land pattern (x
mirrored back), which is how datasheets draw recommended land patterns (top view
of the board, component side). Pads with the same number are listed separately.
Python 3.9; needs kicad-cli on PATH.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from lib import sexp  # noqa: E402

CUSTOM = ("BAT_PADS", "DOCK_PADS", "SWD_PADS")


def table(fp_path):
    node = sexp.load(fp_path)
    bottom = sexp.child(node, "layer")[1] == "B.Cu"
    rows = []
    for p in sexp.children(node, "pad"):
        at = sexp.child(p, "at")
        x, y = float(at[1]), float(at[2])
        r = float(at[3]) if len(at) > 3 else 0.0
        if bottom:
            x, r = -x, (180 - r) % 360 if r else 0.0
        size = sexp.child(p, "size")
        drill = sexp.child(p, "drill")
        rows.append((p[1] or "(hole)", p[2], p[3], x, y, r, float(size[1]), float(size[2]),
                     " ".join(str(d) for d in drill[1:]) if drill else ""))
    return bottom, rows


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    parts = json.loads((ROOT / "hardware/parts.json").read_text())["parts"]
    entries = [(p["lcsc"], p["role"], p.get("fixups", {}).get("source")) for p in parts] + \
              [(c, "custom pads (scripts/parts/custom_parts.py)", None) for c in CUSTOM]
    md = ["# Footprints", "",
          "Every assembled part's footprint as used on the boards (`hardware/parts/`), shown as the front-side "
          "land pattern (component side, top view) for comparison with each datasheet's recommended land "
          "pattern. Coordinates in mm relative to the footprint origin; rotation in degrees. The boards use "
          "the bottom-side versions (x mirrored). SVGs show the copper of each footprint. The reverse-mount "
          "LED (C409782) is drawn here front-side too, which is the mirror of the datasheet's 'Reverse Type' "
          "pad drawing: that drawing is seen from the light side, i.e. from the top of this board.", ""]
    tmp = Path(tempfile.mkdtemp())
    for lcsc, role, fix in entries:
        fp_path = next((ROOT / "hardware/parts" / lcsc).glob("*.kicad_mod"))
        bottom, rows = table(fp_path)
        sheets = sorted((ROOT / "docs/datasheets").glob("%s_*.pdf" % lcsc))
        md += ["## %s — %s" % (lcsc, fp_path.stem), "", role + ".",
               ("Datasheet: [%s](../../%s)." % (sheets[0].name, sheets[0].relative_to(ROOT))) if sheets else "No datasheet (custom pads).",
               ("Corrected from the datasheet: %s" % fix) if fix else "", "",
               "| Pad | Type | Shape | x | y | Rot | Width | Height | Drill |", "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            md.append("| %s | %s | %s | %.3f | %.3f | %g | %.3f | %.3f | %s |" % r)
        lib = tmp / (lcsc + ".pretty")
        lib.mkdir()
        shutil.copy(fp_path, lib / fp_path.name)
        svg_dir = tmp / (lcsc + "-svg")
        subprocess.run(["kicad-cli", "fp", "export", "svg", "--output", str(svg_dir), "--footprint", fp_path.stem,
                        "--layers", "F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Courtyard,B.Courtyard,Edge.Cuts",
                        str(lib)], check=True, capture_output=True)
        svg = next(svg_dir.glob("*.svg"))
        shutil.copy(svg, out / ("%s.svg" % lcsc))
        md += ["", "![%s](%s.svg)" % (lcsc, lcsc), ""]
    (out / "footprints.md").write_text("\n".join(md))
    shutil.rmtree(tmp)
    print("wrote %s (%d footprints)" % (out / "footprints.md", len(entries)))


if __name__ == "__main__":
    main()
