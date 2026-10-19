#!/usr/bin/env bash
# JLCPCB fabrication and assembly bundle for both halves in one panel (phase 6).
#
#   scripts/fab/build.sh [OUT_DIR]        default fab/
#
#   OUT_DIR/panel/panel.kicad_pcb   KiKit panel (hardware/panel.json; layout plugin
#                                   scripts/fab/panel_layout.py puts both halves where the
#                                   original panel had them, with a frame, tooling holes,
#                                   fiducials and mouse bites)
#   OUT_DIR/jlc/gerbers.zip         Gerbers and drill files (kikit fab jlcpcb --no-assembly)
#   OUT_DIR/jlc/bom.csv, positions.csv   BOM and CPL (scripts/fab/jlc_assembly.py)
#   OUT_DIR/panel/drc.json, drc.md  DRC of the panel (scripts/checks/drc.py --half panel)
#   OUT_DIR/panel/outline.txt       each half's outline in the panel (scripts/checks/panel_outline.py)
#   OUT_DIR/panel/fills.txt         each half's GND pours in the panel (scripts/checks/panel_fills.py)
#   OUT_DIR/render/                 panel renders, top and bottom (RENDER=0 skips them)
#   OUT_DIR/step/{left,right}.step  3D models of the halves
# Fails if any step or check fails. Needs KICAD_PY with KiKit installed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$ROOT/fab}"
: "${KICAD_PY:?set KICAD_PY to the KiCad bundled Python}"
kpy() { "$KICAD_PY" "$@" 2> >(grep -vE 'Debug: Adding duplicate image handler|create wxApp before calling this|swig/python detected a memory leak' >&2); }
rm -rf "$OUT/panel" "$OUT/jlc" "$OUT/render" "$OUT/step"
mkdir -p "$OUT/panel" "$OUT/jlc" "$OUT/render" "$OUT/step"
cd "$ROOT"
kpy -m kikit.ui panelize -p hardware/panel.json hardware/layouts/left/left.kicad_pcb "$OUT/panel/panel.kicad_pcb"
python3 "$ROOT/scripts/fab/panel_project.py" "$OUT/panel/panel.kicad_pro" hardware/layouts/left/left.kicad_pro
# the panel keeps each half's outline apart from the tabs (rule 1)
kpy "$ROOT/scripts/checks/panel_outline.py" "$OUT/panel/panel.kicad_pcb" hardware/layouts/left/left.kicad_pcb hardware/layouts/right/right.kicad_pcb | tee "$OUT/panel/outline.txt"
# KiKit's zone refill keeps the halves' GND pours, apart from clearance around the mouse bites
kpy "$ROOT/scripts/checks/panel_fills.py" "$OUT/panel/panel.kicad_pcb" hardware/layouts/left/left.kicad_pcb hardware/layouts/right/right.kicad_pcb | tee "$OUT/panel/fills.txt"
# DRC with the documented exceptions (KiKit's own DRC can't excuse the inherited ones)
python3 "$ROOT/scripts/checks/drc.py" "$OUT/panel/panel.kicad_pcb" --half panel --json "$OUT/panel/drc.json" --md "$OUT/panel/drc.md"
kpy -m kikit.ui fab jlcpcb --no-drc --no-assembly --nametemplate "urchin-panel-{}" "$OUT/panel/panel.kicad_pcb" "$OUT/jlc"
kpy "$ROOT/scripts/fab/jlc_assembly.py" "$OUT/panel/panel.kicad_pcb" "$OUT/jlc"
if [ "${RENDER:-1}" = 1 ]; then  # kicad-cli's 3D renderer needs a display; CI sets RENDER=0
  "$ROOT/scripts/render.sh" "$OUT/panel/panel.kicad_pcb" "$OUT/render/panel"
fi
for half in left right; do  # 3D models of each half, for enclosure and dock work (phase 7)
  kicad-cli pcb export step --subst-models -f -o "$OUT/step/$half.step" "hardware/layouts/$half/$half.kicad_pcb" >/dev/null
done
ls -la "$OUT/jlc"
