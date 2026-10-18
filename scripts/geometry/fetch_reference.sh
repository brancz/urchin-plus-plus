#!/usr/bin/env bash
# Put the original Urchin at reference/urchin, at the commit hardware/geometry/urchin.json
# was extracted from, and verify main.kicad_pcb's SHA-256 (CLAUDE.md rule 1).
#
#   scripts/geometry/fetch_reference.sh       # no-op if reference/urchin is already right
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
read -r REPO COMMIT SHA < <(python3 -c '
import json, sys
s = json.load(open(sys.argv[1]))["source"]
print(s["repository"], s["commit"], s["sha256"])' "$ROOT/hardware/geometry/urchin.json")
DEST="$ROOT/reference/urchin"
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
if [ ! -f "$DEST/main.kicad_pcb" ]; then
  mkdir -p "$DEST"
  git -C "$DEST" init -q
  git -C "$DEST" fetch -q --depth 1 "$REPO" "$COMMIT"
  git -C "$DEST" checkout -q FETCH_HEAD
fi
GOT="$(sha "$DEST/main.kicad_pcb")"
[ "$GOT" = "$SHA" ] || { echo "reference: main.kicad_pcb is $GOT, expected $SHA"; exit 1; }
echo "reference: $REPO@$COMMIT, main.kicad_pcb sha256 OK"
