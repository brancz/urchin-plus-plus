#!/usr/bin/env bash
# The keyboard halves, end to end (local and CI):
#   1. hardware/halves.ato and hardware/pinmap.json are what gen_halves.py produces
#   2. scripts/ato_build.sh hardware [ARGS...]   (CI passes --frozen: the committed boards
#      must already be what the build produces)
#   3. per half: placement (place.py --check), designators (silk.py --check), unique UUIDs,
#      every intended connection and nothing else (connectivity.py), placement clearances,
#      sides and the antenna keep-out (clearance.py), and DRC with the documented
#      exceptions on the routed board (drc.py; DRC_ARGS=--unrouted-ok skips unrouted nets)
#   The project files are what board_setup.py writes. Rule 1 geometry is geometry_all.sh.
# Reports go to OUT_DIR (default hardware/build/reports) as JSON.
#
#   scripts/checks/hardware_all.sh [--out DIR] [ato build args...]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
: "${KICAD_PY:?set KICAD_PY to the KiCad bundled Python}"
OUT="$ROOT/hardware/build/reports"
if [ "${1:-}" = "--out" ]; then OUT="$2"; shift 2; fi
mkdir -p "$OUT"
kpy() { "$KICAD_PY" "$@" 2> >(grep -vE 'Debug: Adding duplicate image handler|create wxApp before calling this|swig/python detected a memory leak' >&2); }

python3 "$ROOT/scripts/circuit/gen_halves.py" --check
python3 "$ROOT/scripts/placement/board_setup.py" --check
"$ROOT/scripts/ato_build.sh" "$ROOT/hardware" "$@"
status=0
for half in left right; do
  board="$ROOT/hardware/layouts/$half/$half.kicad_pcb"
  kpy "$ROOT/scripts/placement/place.py" "$board" --half "$half" --check || status=1
  kpy "$ROOT/scripts/placement/silk.py" "$board" --check || status=1
  python3 "$ROOT/scripts/placement/unique_uuids.py" "$board" --check || status=1
  kpy "$ROOT/scripts/checks/connectivity.py" "$board" --half "$half" --json "$OUT/connectivity-$half.json" || status=1
  kpy "$ROOT/scripts/checks/clearance.py" "$board" --half "$half" --json "$OUT/clearance-$half.json" || status=1
  python3 "$ROOT/scripts/checks/drc.py" "$board" --half "$half" ${DRC_ARGS:-} --json "$OUT/drc-$half.json" || status=1
done
exit "$status"
