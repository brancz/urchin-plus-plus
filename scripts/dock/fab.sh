#!/usr/bin/env bash
# JLCPCB fabrication and assembly bundle for the dock board (phase 7).
#
#   scripts/dock/fab.sh [OUT_DIR]          default fab/dock
#
#   OUT_DIR/jlc/urchin-dock-gerbers.zip   Gerbers and drill files (kikit fab jlcpcb --no-assembly)
#   OUT_DIR/jlc/bom.csv, positions.csv   BOM and CPL, top side (scripts/fab/jlc_assembly.py --dock)
#   OUT_DIR/checks/                  placement, unique UUIDs, connectivity and DRC of the board
#   OUT_DIR/render/                  top and bottom renders (RENDER=0 skips them)
#   OUT_DIR/step/dock.step           3D model
# The board is the routed dock-pcb/layouts/dock/dock.kicad_pcb, unpanelised (JLC adds rails
# if its assembly line needs them). Fails if any step or check fails. Needs KICAD_PY with KiKit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$ROOT/fab/dock}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
: "${KICAD_PY:?set KICAD_PY to the KiCad bundled Python}"
kpy() { "$KICAD_PY" "$@" 2> >(grep -vE 'Debug: Adding duplicate image handler|create wxApp before calling this|swig/python detected a memory leak' >&2); }
BOARD=dock-pcb/layouts/dock/dock.kicad_pcb
rm -rf "$OUT/jlc" "$OUT/checks" "$OUT/render" "$OUT/step"
mkdir -p "$OUT/jlc" "$OUT/checks" "$OUT/render" "$OUT/step"
cd "$ROOT"
kpy scripts/dock/place.py --check | tee "$OUT/checks/placement.txt"
python3 scripts/placement/unique_uuids.py "$BOARD" --check
kpy scripts/dock/connectivity.py --json "$OUT/checks/connectivity.json"
python3 scripts/checks/drc.py "$BOARD" --half dock --json "$OUT/checks/drc.json" --md "$OUT/checks/drc.md"
kpy -m kikit.ui fab jlcpcb --no-drc --no-assembly --nametemplate "urchin-dock-{}" "$BOARD" "$OUT/jlc"
kpy scripts/fab/jlc_assembly.py --dock "$BOARD" "$OUT/jlc"
if [ "${RENDER:-1}" = 1 ]; then  # kicad-cli's 3D renderer needs a display; CI sets RENDER=0
  scripts/render.sh "$BOARD" "$OUT/render/dock"
fi
kicad-cli pcb export step --subst-models -f -o "$OUT/step/dock.step" "$BOARD" >/dev/null
ls -la "$OUT/jlc"
