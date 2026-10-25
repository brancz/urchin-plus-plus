#!/usr/bin/env bash
# The printed parts (phase 7): a case and a top shell per half, and the dock's tray in two
# pieces, built from the routed boards and checked against their 3D models.
#
#   scripts/mech/build.sh [OUT_DIR]      default mech/build
#
#   OUT_DIR/boards/{left,right,dock}.step   the halves and the dock board with every 3D model
#   OUT_DIR/step, stl, render          the parts (mech/README.md), renders unless RENDER=0
#   OUT_DIR/checks.json                fit and bed-size checks; any failure fails the build
#   OUT_DIR/preview.html               3D preview of the finished keyboard and dock (open in a
#                                      browser), unless PREVIEW=0
#   OUT_DIR/slice/                     Bambu Studio slices for the A1 mini, if Bambu Studio
#                                      is installed and SLICE isn't 0 (local only)
#
# Fails if mech/data/*.json no longer matches the boards (scripts/mech/board_data.py), or
# dock-pcb/geometry.json no longer matches the tray (`mech dock-geometry`).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$ROOT/mech/build}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
cd "$ROOT"

scripts/checks/toolchain.sh --kicad >/dev/null
"$KICAD_PY" scripts/mech/board_data.py --check

mkdir -p "$OUT/boards"
for half in left right; do
  kicad-cli pcb export step --subst-models -f -o "$OUT/boards/$half.step" \
    "hardware/layouts/$half/$half.kicad_pcb" >/dev/null
done
kicad-cli pcb export step --subst-models -f -o "$OUT/boards/dock.step" dock-pcb/layouts/dock/dock.kicad_pcb >/dev/null
(cd mech && uv run --locked mech dock-geometry --check)

render=""
[ "${RENDER:-1}" = 0 ] && render="--no-render"
(cd mech && uv run --locked mech build --boards "$OUT/boards" --out "$OUT" $render)
if [ "${PREVIEW:-1}" != 0 ]; then
  (cd mech && uv run --locked mech preview --boards "$OUT/boards" --out "$OUT/preview.html")
fi

if [ "${SLICE:-1}" != 0 ] && [ -x "${BAMBU_STUDIO:-/Applications/BambuStudio.app}/Contents/MacOS/BambuStudio" ]; then
  python3 scripts/mech/slice.py "$OUT/stl" "$OUT/slice"
fi
