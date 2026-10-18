#!/usr/bin/env bash
# 2D placement views of a half for reports and review (kicad-cli SVG -> PNG via PyMuPDF).
#
#   scripts/render/placement_views.sh BOARD OUT_PREFIX
#     OUT_PREFIX-bottom.png  bottom side seen from below (mirrored): copper, silkscreen, courtyards, fab
#     OUT_PREFIX-top.png     top side: copper, silkscreen, courtyards (battery outline, keys)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BOARD="${1:?usage: placement_views.sh BOARD OUT_PREFIX}"
OUT="${2:?usage: placement_views.sh BOARD OUT_PREFIX}"
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
svg() {  # side layers mirror
  local args=(pcb export svg --mode-single --page-size-mode 2 --exclude-drawing-sheet --layers "$2" -o "$TMP/$1.svg")
  [ "$3" = mirror ] && args+=(--mirror)
  kicad-cli "${args[@]}" "$BOARD" >/dev/null
  uv run --no-project --with pymupdf==1.26.4 python "$ROOT/scripts/render/svg_to_png.py" "$TMP/$1.svg" "$OUT-$1.png" --px-per-mm 16
}
svg bottom B.Cu,B.Mask,B.SilkS,B.CrtYd,B.Fab,Edge.Cuts mirror
svg top F.Cu,F.SilkS,F.CrtYd,Edge.Cuts plain
