#!/usr/bin/env bash
# Compare every board each commit in a range changed with the parent's version (CI).
#
#   scripts/checks/board_history.sh RANGE        e.g. origin/main..HEAD
#
# scripts/ato_build.sh guards each build; this guards what actually got committed
# (a bare `ato build`, a pcbnew edit that lost copper). Per non-merge commit and
# changed .kicad_pcb, scripts/checks/board_diff.py --mode commit against the
# parent's version (following renames; .kicad_pro/.kicad_dru come along so both
# sides load with their own design rules). Merge commits are skipped: the commits
# they bring in are checked one by one. A commit declares intended removals or net
# changes with lines anywhere in its message, one pattern each, e.g.:
#
#     Board-Diff-Allow: track:*
#     Board-Diff-Allow: footprint:led_old
#
# A deleted board needs "Board-Diff-Allow: board:PATH". Boards under reports/ are
# evidence (e.g. a KiCad 10-saved board) and are skipped.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RANGE="${1:?usage: board_history.sh RANGE}"
: "${KICAD_PY:?set KICAD_PY to the KiCad bundled Python}"
NOISE='Debug: Adding duplicate image handler|create wxApp before calling this|swig/python detected a memory leak'
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# git show REV:PATH.kicad_pcb (plus its .kicad_pro/.kicad_dru) into DIR/board.kicad_pcb
extract() {
  local rev="$1" path="$2" dir="$3" ext
  rm -rf "$dir"
  mkdir -p "$dir"
  git show "$rev:$path" >"$dir/board.kicad_pcb"
  for ext in kicad_pro kicad_dru; do
    git show "$rev:${path%.kicad_pcb}.$ext" >"$dir/board.$ext" 2>/dev/null || rm -f "$dir/board.$ext"
  done
}

commits="$(git rev-list --reverse --no-merges "$RANGE")" || { echo "board_history: FAIL bad range $RANGE (shallow clone?)"; exit 2; }
status=0
checked=0
while IFS= read -r c; do
  [ -n "$c" ] || continue
  title="$(git log -1 --format='%h %s' "$c")"
  parent="$(git rev-parse --verify --quiet "$c^" || true)"
  if [ -z "$parent" ]; then
    echo "$title: root commit, nothing to compare"
    continue
  fi
  patterns=()
  while IFS= read -r pat; do
    [ -n "$pat" ] && patterns+=("$pat")
  done < <(git log -1 --format=%B "$c" | sed -n 's/^Board-Diff-Allow:[[:space:]]*//p' | sed 's/[[:space:]]*$//')
  allow=()
  for pat in ${patterns[@]+"${patterns[@]}"}; do allow+=(--allow "$pat"); done
  while IFS=$'\t' read -r kind old new; do
    case "$kind" in
      A) echo "$title: new board $old"; continue ;;
      D)
        ok=""
        for pat in ${patterns[@]+"${patterns[@]}"}; do
          # shellcheck disable=SC2053  # $pat is a glob on purpose
          [[ "board:$old" == $pat ]] && ok=1
        done
        if [ -n "$ok" ]; then
          echo "$title: deleted board $old (allowed)"
        else
          echo "$title: FAIL board $old deleted without 'Board-Diff-Allow: board:$old'"
          status=1
        fi
        continue ;;
      R*) ;;
      *) new="$old" ;;
    esac
    extract "$parent" "$old" "$TMP/old"
    extract "$c" "$new" "$TMP/new"
    echo "== $title: $new"
    checked=$((checked + 1))
    if ! "$KICAD_PY" "$ROOT/scripts/checks/board_diff.py" "$TMP/new/board.kicad_pcb" --against "$TMP/old/board.kicad_pcb" \
      --mode commit ${allow[@]+"${allow[@]}"} 2>"$TMP/stderr"; then
      status=1
    fi
    grep -vE "$NOISE" "$TMP/stderr" >&2 || true
  done < <(git diff --name-status -M20% "$parent" "$c" -- '*.kicad_pcb' ':!reports/')
done <<<"$commits"

echo "board_history: $checked board version(s) checked in $RANGE"
[ "$status" -eq 0 ] && echo "board_history: OK" || echo "board_history: FAIL"
exit "$status"
