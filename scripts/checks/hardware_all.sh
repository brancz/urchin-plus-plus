#!/usr/bin/env bash
# The keyboard halves, end to end (local and CI):
#   1. hardware/halves.ato and hardware/pinmap.json are what gen_halves.py produces
#   2. scripts/ato_build.sh hardware [ARGS...]   (CI passes --frozen: the committed boards
#      must already be what the build produces)
#   3. per half: every intended connection and nothing else (connectivity.py)
# Reports go to OUT_DIR (default build/reports) as JSON.
#
#   scripts/checks/hardware_all.sh [--out DIR] [ato build args...]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
: "${KICAD_PY:?set KICAD_PY to the KiCad bundled Python}"
OUT="$ROOT/hardware/build/reports"
if [ "${1:-}" = "--out" ]; then OUT="$2"; shift 2; fi
mkdir -p "$OUT"
kpy() { "$KICAD_PY" "$@" 2> >(grep -vE 'Debug: Adding duplicate image handler|create wxApp before calling this' >&2); }

python3 "$ROOT/scripts/circuit/gen_halves.py" --check
"$ROOT/scripts/ato_build.sh" "$ROOT/hardware" "$@"
status=0
for half in left right; do
  board="$ROOT/hardware/layouts/$half/$half.kicad_pcb"
  kpy "$ROOT/scripts/checks/connectivity.py" "$board" --half "$half" --json "$OUT/connectivity-$half.json" || status=1
done
exit "$status"
