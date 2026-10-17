#!/usr/bin/env bash
# The only way to run `ato build` in this repo (CLAUDE.md rule 5).
#
#   scripts/ato_build.sh PROJECT_DIR [ato build args...]     e.g. scripts/ato_build.sh hardware --frozen
#
#   1. Preflight: KiCad on PATH/KICAD_PY is the pinned version; guardrails pass on the
#      existing boards and PROJECT_DIR/parts (a KiCad 10 save gets a clear message here,
#      not atopile's parse error).
#   2. Snapshot every board, then `ato build`.
#   3. Per board, against its pre-build snapshot:
#        scripts/fix_stale_nets.py         re-point copper at nets atopile re-created
#        scripts/checks/kicad_guardrails.py
#        scripts/checks/board_diff.py --mode build   atopile may add footprints, update
#                                          fields and pad nets, rename nets; nothing else
#   Fails if the project has no board after the build.
#
# BOARD_DIFF_ARGS is passed to board_diff, e.g. BOARD_DIFF_ARGS="--allow footprint:old_led"
# for a part you removed from the circuit, or "--strict" to demand no change at all.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${1:?usage: scripts/ato_build.sh PROJECT_DIR [ato build args...]}"
shift
: "${KICAD_PY:?set KICAD_PY to the KiCad bundled Python}"

NOISE='Debug: Adding duplicate image handler|create wxApp before calling this|swig/python detected a memory leak'
kpy() {  # KiCad's Python with wx's debug chatter removed from stderr
  local err rc
  err="$(mktemp)"
  if "$KICAD_PY" "$@" 2>"$err"; then rc=0; else rc=$?; fi
  grep -vE "$NOISE" "$err" >&2 || true
  rm -f "$err"
  return "$rc"
}
boards() {
  find "$PROJECT" -name '*.kicad_pcb' -not -path '*/build/*' -not -path '*-backups/*' -not -path '*/.ato/*' | sort
}

"$ROOT/scripts/checks/toolchain.sh" --kicad
BEFORE="$(boards)"
check_paths=()
while IFS= read -r b; do [ -n "$b" ] && check_paths+=("$b"); done <<<"$BEFORE"
[ -d "$PROJECT/parts" ] && check_paths+=("$PROJECT/parts")
if [ "${#check_paths[@]}" -gt 0 ] && ! pre="$(python3 "$ROOT/scripts/checks/kicad_guardrails.py" "${check_paths[@]}")"; then
  grep -v '^ok ' <<<"$pre"
  echo "ato_build: FAIL guardrails failed before the build; not running ato build"
  exit 1
fi

SNAP="$(mktemp -d)"
trap 'rm -rf "$SNAP"' EXIT
while IFS= read -r b; do
  [ -n "$b" ] || continue
  mkdir -p "$SNAP/$(dirname "$b")"
  cp "$b" "$SNAP/$b"
done <<<"$BEFORE"

(cd "$PROJECT" && ato build "$@")

AFTER="$(boards)"
[ -n "$AFTER" ] || { echo "ato_build: FAIL no .kicad_pcb under $PROJECT after the build"; exit 1; }

status=0
while IFS= read -r board; do
  echo "== $board"
  if [ -f "$SNAP/$board" ]; then
    python3 "$ROOT/scripts/fix_stale_nets.py" "$board" --against "$SNAP/$board" || status=1
  else
    echo "new board (no pre-build version); no net repair or diff"
  fi
  python3 "$ROOT/scripts/checks/kicad_guardrails.py" "$board" | grep -v '^limits:' || status=1
  if [ -f "$SNAP/$board" ]; then
    # shellcheck disable=SC2086  # BOARD_DIFF_ARGS is a list of flags
    kpy "$ROOT/scripts/checks/board_diff.py" "$board" --against "$SNAP/$board" --mode build ${BOARD_DIFF_ARGS:-} || status=1
  fi
done <<<"$AFTER"
[ "$status" -eq 0 ] && echo "ato_build: OK" || echo "ato_build: FAIL"
exit "$status"
