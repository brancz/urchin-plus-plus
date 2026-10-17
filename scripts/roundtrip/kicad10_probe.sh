#!/usr/bin/env bash
# Evidence for the KiCad 10 -> 9 fallback: can atopile rebuild a board KiCad 10 has saved?
#
#   scripts/roundtrip/kicad10_probe.sh KICAD10_APP [OUT_DIR]
#   e.g. scripts/roundtrip/kicad10_probe.sh /Applications/KiCad/KiCad.app reports/phase0/kicad10-probe
#
# Builds the round-trip fixture with atopile, edits and saves the board with KiCad 10's
# pcbnew (scripts/roundtrip/edit_board.py), then runs `ato build` again with the pinned
# atopile and with atopile 0.15.9 (the last CLI release, via uvx). Writes logs and a
# summary; exits 0 when the probe ran, whatever atopile did.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="${1:?usage: kicad10_probe.sh KICAD10_APP [OUT_DIR]}"
OUT="${2:-$ROOT/scratch/kicad10-probe}"
K10PY="$APP/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
rm -rf "$OUT"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
BOARD=layouts/default/default.kicad_pcb
board_format() { sed -n 's/^	(version \([0-9]*\))/\1/p' "$1"; }
first_error() { grep -m1 -E 'UnexpectedType|Error|✗' "$1" | sed 's/[│ ]*$//; s/^[│ ]*//'; }

cp -R "$ROOT/scripts/roundtrip/fixture" "$WORK/proj"
cd "$WORK/proj" || exit 1
{
  echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "kicad (edit/save): $("$APP/Contents/MacOS/kicad-cli" version)"
  echo "atopile: $(ato --version 2>/dev/null | tail -1)"
} >"$OUT/summary.txt"

ato build >"$OUT/ato_1-build.log" 2>&1
echo "1 ato build (pinned atopile): exit $?, board format $(board_format "$BOARD")" >>"$OUT/summary.txt"
"$K10PY" "$ROOT/scripts/roundtrip/edit_board.py" "$BOARD" >"$OUT/edit.json" 2>/dev/null
echo "2 KiCad 10 pcbnew edit + save: exit $?, board format $(board_format "$BOARD")" >>"$OUT/summary.txt"
cp "$BOARD" "$OUT/kicad10-saved.kicad_pcb"

ato build >"$OUT/ato_3-rebuild.log" 2>&1
echo "3 ato build (pinned atopile) on the KiCad 10 board: exit $? -- $(first_error "$OUT/ato_3-rebuild.log")" >>"$OUT/summary.txt"

cp "$OUT/kicad10-saved.kicad_pcb" "$BOARD"
sed -i.bak 's/requires-atopile: "[0-9.]*"/requires-atopile: "0.15.9"/' ato.yaml
uvx --python 3.14 --from atopile==0.15.9 ato build >"$OUT/ato_4-rebuild-0.15.9.log" 2>&1
echo "4 ato build (atopile 0.15.9) on the KiCad 10 board: exit $? -- $(first_error "$OUT/ato_4-rebuild-0.15.9.log")" >>"$OUT/summary.txt"
cat "$OUT/summary.txt"
