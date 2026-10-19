#!/usr/bin/env bash
# Copper views of a routed half for reports and review (kicad-cli SVG -> PNG via PyMuPDF).
#
#   scripts/render/copper_views.sh BOARD OUT_PREFIX
#     OUT_PREFIX-F_Cu.png, OUT_PREFIX-B_Cu.png   each copper layer with the outline (top view)
#     OUT_PREFIX-both.png                        both layers together (top view)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BOARD="${1:?usage: copper_views.sh BOARD OUT_PREFIX}"
OUT="${2:?usage: copper_views.sh BOARD OUT_PREFIX}"
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# zones are refilled on a copy: the committed boards may carry unfilled pours after atopile
cp "$BOARD" "$TMP/b.kicad_pcb"
"$KICAD_PY" -c "
import os, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[1])
sys.stdout.flush(); os._exit(0)" "$TMP/b.kicad_pcb" 2>/dev/null
for spec in "F_Cu:F.Cu,Edge.Cuts" "B_Cu:B.Cu,Edge.Cuts" "both:F.Cu,B.Cu,Edge.Cuts"; do
  name="${spec%%:*}"; layers="${spec#*:}"
  kicad-cli pcb export svg --mode-single --page-size-mode 2 --exclude-drawing-sheet --layers "$layers" \
    -o "$TMP/$name.svg" "$TMP/b.kicad_pcb" >/dev/null
  uv run --no-project --with pymupdf==1.26.4 python "$ROOT/scripts/render/svg_to_png.py" "$TMP/$name.svg" "$OUT-$name.png" --px-per-mm 14
done
