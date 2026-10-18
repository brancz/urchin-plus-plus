#!/usr/bin/env bash
# Render a board from the top and the bottom (3D, orthographic) for reports and review.
#
#   scripts/render.sh BOARD OUT_PREFIX      -> OUT_PREFIX-top.png, OUT_PREFIX-bottom.png
set -euo pipefail
BOARD="${1:?usage: render.sh BOARD OUT_PREFIX}"
OUT="${2:?usage: render.sh BOARD OUT_PREFIX}"
mkdir -p "$(dirname "$OUT")"
for side in top bottom; do
  kicad-cli pcb render --side "$side" --width 2000 --height 1400 --quality high --background opaque \
    -o "$OUT-$side.png" "$BOARD" >/dev/null
  echo "$OUT-$side.png"
done
