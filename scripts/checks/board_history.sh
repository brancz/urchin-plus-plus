#!/usr/bin/env bash
# Compare every board each commit in a range changed with the parent's version (CI).
#
#   scripts/checks/board_history.sh RANGE        e.g. origin/main..HEAD
#
# scripts/ato_build.sh guards each build; this guards what actually got committed
# (a bare `ato build`, a pcbnew edit that lost copper). Per commit and changed
# .kicad_pcb, scripts/checks/board_diff.py --mode commit against the parent's
# version (following renames). A commit declares intended removals or net changes
# with trailers, one pattern each, e.g.:
#
#     Board-Diff-Allow: track:*
#     Board-Diff-Allow: footprint:led_old
#
# A deleted board needs "Board-Diff-Allow: board:PATH".
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RANGE="${1:?usage: board_history.sh RANGE}"
: "${KICAD_PY:?set KICAD_PY to the KiCad bundled Python}"
NOISE='Debug: Adding duplicate image handler|create wxApp before calling this|swig/python detected a memory leak'
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

commits="$(git rev-list --reverse "$RANGE")" || { echo "board_history: FAIL bad range $RANGE (shallow clone?)"; exit 2; }
status=0
checked=0
while IFS= read -r c; do
  [ -n "$c" ] || continue
  parent="$(git rev-parse --verify --quiet "$c^" || true)"
  if [ -z "$parent" ]; then
    echo "$(git log -1 --format='%h %s' "$c"): root commit, nothing to compare"
    continue
  fi
  allow=()
  while IFS= read -r pat; do
    [ -n "$pat" ] && allow+=(--allow "$pat")
  done < <(git log -1 --format='%(trailers:key=Board-Diff-Allow,valueonly,separator=%x0A)' "$c")
  while IFS=$'\t' read -r kind old new; do
    title="$(git log -1 --format='%h %s' "$c")"
    case "$kind" in
      A) echo "$title: new board $old"; continue ;;
      D)
        if printf '%s\n' "${allow[@]+"${allow[@]}"}" | grep -qxF "board:$old"; then
          echo "$title: deleted board $old (allowed)"
        else
          echo "$title: FAIL board $old deleted without 'Board-Diff-Allow: board:$old'"
          status=1
        fi
        continue ;;
      R*) ;;
      *) new="$old" ;;
    esac
    git show "$parent:$old" >"$TMP/old.kicad_pcb"
    git show "$c:$new" >"$TMP/new.kicad_pcb"
    echo "== $title: $new"
    checked=$((checked + 1))
    err="$TMP/stderr"
    if ! "$KICAD_PY" "$ROOT/scripts/checks/board_diff.py" "$TMP/new.kicad_pcb" --against "$TMP/old.kicad_pcb" \
      --mode commit ${allow[@]+"${allow[@]}"} 2>"$err"; then
      status=1
    fi
    grep -vE "$NOISE" "$err" >&2 || true
  done < <(git diff --name-status -M "$parent" "$c" -- '*.kicad_pcb')
done <<<"$commits"

echo "board_history: $checked board version(s) checked in $RANGE"
[ "$status" -eq 0 ] && echo "board_history: OK" || echo "board_history: FAIL"
exit "$status"
