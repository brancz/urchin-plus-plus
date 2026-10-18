#!/usr/bin/env bash
# The only way to run `ato build` in this repo (CLAUDE.md rule 5).
#
#   scripts/ato_build.sh PROJECT_DIR [ato build args...]     e.g. scripts/ato_build.sh hardware --frozen
#
#   1. Preflight: KiCad on PATH/KICAD_PY is the pinned version; guardrails pass on the
#      existing boards and PROJECT_DIR/parts (a KiCad 10 save gets a clear message here,
#      not atopile's parse error).
#   2. Snapshot every board with its .kicad_pro/.kicad_dru, then `ato build`.
#   3. Per board, against its pre-build snapshot:
#        scripts/fix_stale_nets.py         put copper back on the nets atopile moved it off
#        scripts/checks/kicad_guardrails.py
#        scripts/checks/board_diff.py --mode build   atopile may add footprints, update
#                                          fields and pad nets, rename nets; nothing else
#   All or nothing: if `ato build` or any check fails, the boards are restored to the
#   snapshot and the failed result is kept in PROJECT_DIR/build/ato_build-failed/, so a
#   rerun fails the same way instead of accepting the damage. Fails if the project has
#   no board after the build.
#
# BOARD_DIFF_ARGS is passed to board_diff, e.g. BOARD_DIFF_ARGS="--allow footprint:old_led"
# for a part you removed from the circuit, or "--strict" to demand no change at all.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${1:?usage: scripts/ato_build.sh PROJECT_DIR [ato build args...]}"
shift
: "${KICAD_PY:?set KICAD_PY to the KiCad bundled Python}"
read -r -a DIFF_ARGS <<<"${BOARD_DIFF_ARGS:-}"  # word-split only; read does no globbing

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
companions() { for ext in kicad_pro kicad_dru; do [ -f "${1%.kicad_pcb}.$ext" ] && echo "${1%.kicad_pcb}.$ext"; done; return 0; }

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
while IFS= read -r f; do
  [ -n "$f" ] || continue
  mkdir -p "$SNAP/$(dirname "$f")"
  cp "$f" "$SNAP/$f"
done < <(while IFS= read -r b; do [ -n "$b" ] && echo "$b" && companions "$b"; done <<<"$BEFORE")

rollback() {
  local failed="$PROJECT/build/ato_build-failed"
  rm -rf "$failed"
  mkdir -p "$failed"
  while IFS= read -r b; do
    [ -n "$b" ] || continue
    cp "$b" "$failed/" 2>/dev/null || true
    if [ -f "$SNAP/$b" ]; then
      cp "$SNAP/$b" "$b"
      for ext in kicad_pro kicad_dru; do
        if [ -f "$SNAP/${b%.kicad_pcb}.$ext" ]; then cp "$SNAP/${b%.kicad_pcb}.$ext" "${b%.kicad_pcb}.$ext"; fi
      done
    fi
  done < <(boards)
  echo "ato_build: FAIL ($1). Boards restored to their pre-build state; the failed result is in $failed"
  exit 1
}

if ! (cd "$PROJECT" && ato build "$@"); then
  rollback "ato build failed"
fi

AFTER="$(boards)"
[ -n "$AFTER" ] || rollback "no .kicad_pcb under $PROJECT after the build"

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
    kpy "$ROOT/scripts/checks/board_diff.py" "$board" --against "$SNAP/$board" --mode build \
      ${DIFF_ARGS[@]+"${DIFF_ARGS[@]}"} || status=1
  fi
done <<<"$AFTER"
[ "$status" -eq 0 ] || rollback "checks failed"
echo "ato_build: OK"
