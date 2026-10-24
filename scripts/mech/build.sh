#!/usr/bin/env bash
# The printed parts (phase 7): a case and a battery cover per half, built from the routed
# boards and checked against their 3D models.
#
#   scripts/mech/build.sh [OUT_DIR]      default mech/build
#
#   OUT_DIR/boards/{left,right}.step   the halves with every 3D model (kicad-cli)
#   OUT_DIR/step, stl, render          the parts (mech/README.md), renders unless RENDER=0
#   OUT_DIR/checks.json                fit and bed-size checks; any failure fails the build
#   OUT_DIR/slice/                     Bambu Studio slices for the A1 mini, if Bambu Studio
#                                      is installed and SLICE isn't 0 (local only)
#
# Fails if mech/data/*.json no longer matches the boards (scripts/mech/board_data.py).
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

render=""
[ "${RENDER:-1}" = 0 ] && render="--no-render"
(cd mech && uv run --locked mech build --boards "$OUT/boards" --out "$OUT" $render)

if [ "${SLICE:-1}" != 0 ] && [ -x "${BAMBU_STUDIO:-/Applications/BambuStudio.app}/Contents/MacOS/BambuStudio" ]; then
  python3 scripts/mech/slice.py "$OUT/stl" "$OUT/slice"
fi
