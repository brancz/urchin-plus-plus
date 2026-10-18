#!/usr/bin/env bash
# Rule 1, end to end (local and CI):
#   1. the original Urchin is present at the recorded commit (fetched if missing)
#   2. re-extracting it reproduces hardware/geometry/urchin.json byte for byte
#   3. regenerating the mechanical parts reproduces hardware/parts/{KEY_CHOC,PUCK,HOLE_*}
#   4. boards built from the geometry file pass scripts/checks/geometry.py
#   5. the real boards (hardware/layouts/{left,right}/*.kicad_pcb), if present, pass it too
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
: "${KICAD_PY:?set KICAD_PY to the KiCad bundled Python}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
kpy() { "$KICAD_PY" "$@" 2> >(grep -vE 'Debug: Adding duplicate image handler|create wxApp before calling this' >&2); }

"$ROOT/scripts/geometry/fetch_reference.sh"
kpy "$ROOT/scripts/geometry/extract.py" --out "$TMP/urchin.json" >/dev/null
cmp "$TMP/urchin.json" "$ROOT/hardware/geometry/urchin.json" || { echo "geometry: urchin.json is not what extract.py produces"; exit 1; }
echo "geometry: urchin.json reproduces"
kpy "$ROOT/scripts/geometry/mechanical_parts.py" --parts-dir "$TMP/parts" >/dev/null
for p in KEY_CHOC PUCK HOLE_M2_4_2 HOLE_M2_3_5; do
  diff -r "$TMP/parts/$p" "$ROOT/hardware/parts/$p" >/dev/null || { echo "geometry: hardware/parts/$p is not what mechanical_parts.py produces"; exit 1; }
done
echo "geometry: mechanical parts reproduce"
kpy "$ROOT/scripts/geometry/preview.py" "$TMP/preview" >/dev/null
status=0
for half in left right; do
  kpy "$ROOT/scripts/checks/geometry.py" "$TMP/preview/$half.kicad_pcb" --half "$half" | tail -1 | sed "s/^/preview $half: /" || status=1
  "$KICAD_PY" "$ROOT/scripts/checks/geometry.py" "$TMP/preview/$half.kicad_pcb" --half "$half" >/dev/null 2>&1 || status=1
  board="$ROOT/hardware/layouts/$half/$half.kicad_pcb"
  if [ -f "$board" ]; then
    kpy "$ROOT/scripts/checks/geometry.py" "$board" --half "$half" || status=1
  fi
done
exit "$status"
