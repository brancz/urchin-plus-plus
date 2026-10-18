#!/usr/bin/env bash
# Phase 0 toolchain proof: atopile <-> pcbnew round-trip through scripts/ato_build.sh.
#
#   scripts/roundtrip/run.sh [WORK_DIR] [REPORT_DIR]     defaults: scratch/roundtrip, scratch/roundtrip-report
#
# Builds scripts/roundtrip/fixture in a throwaway git repo and checks, step by step:
#    1 first build through the wrapper
#    2 pcbnew edit (outline, moves, tracks, via, zone, mechanical part placed), DRC clean
#    3 rebuild: every edit survives (board_diff --strict), DRC identical
#    4 rebuild again and --frozen: no-ops
#    5 add a part: exactly one footprint added; atopile's re-created nets repaired
#    6 rebuild again and --frozen: no-ops
#    7 more net churn, then an uncommitted pcbnew save (KiCad renumbers nets), then
#      rebuild: no copper changes net (a free MID via stays MID)
#    8 rename net MID -> MIDPOINT: copper follows the rename
#    9 things atopile would lose are refused before it runs, and the board is left as
#      it was: a footprint it doesn't own, one flipped against its library side, a lock
#   10 board_history over this repo's commits; a commit that drops a track fails
#      unless its message allows it; merge commits are skipped
#   11 Freerouting: rip up, autoroute, SES import, DRC 0 errors / 0 unconnected
#   12 KiKit: JLC Gerbers
# Exits non-zero on the first failure.
#
# Needs: ato, kicad-cli, java on PATH; KICAD_PY (KiCad's Python, with KiKit);
# FREEROUTING_JAR. All at the versions in toolchain.env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="${1:-$ROOT/scratch/roundtrip}"
OUT="${2:-$ROOT/scratch/roundtrip-report}"
: "${KICAD_PY:?set KICAD_PY to the KiCad bundled Python}"
: "${FREEROUTING_JAR:?set FREEROUTING_JAR to the pinned Freerouting jar}"

BOARD=layouts/default/default.kicad_pcb
rm -rf "$WORK" "$OUT"
mkdir -p "$WORK" "$OUT"
WORK="$(cd "$WORK" && pwd)"
OUT="$(cd "$OUT" && pwd)"
PROJ="$WORK/proj"
cp -R "$ROOT/scripts/roundtrip/fixture" "$PROJ"
mv "$PROJ/variants" "$WORK/variants"

STEP=""
NOISE='Debug: Adding duplicate image handler|create wxApp before calling this|swig/python detected a memory leak'
fail() { echo "ROUNDTRIP FAIL [$STEP]: $*" | tee -a "$OUT/summary.txt"; exit 1; }
ok() { echo "ok   [$STEP] $*" | tee -a "$OUT/summary.txt"; }
# Throwaway repo: fixed identity, never sign (a signing prompt would block headless runs).
GIT=(git -c user.name=roundtrip -c user.email=roundtrip@localhost -c commit.gpgsign=false -c tag.gpgsign=false)
commit() { "${GIT[@]}" commit -qam "$1"; }
kpy() {  # KiCad's Python; wx debug chatter dropped, real errors kept
  local err rc
  err="$(mktemp)"
  if "$KICAD_PY" "$@" 2>"$err"; then rc=0; else rc=$?; fi
  grep -vE "$NOISE" "$err" >>"$OUT/kicad_stderr.log" || true
  rm -f "$err"
  return "$rc"
}
# wrapper LOGNAME BOARD_DIFF_ARGS [ato args...]: scripts/ato_build.sh, output in $OUT/LOGNAME.log
wrapper() {
  local log="$OUT/$1.log" diffargs="$2"
  shift 2
  BOARD_DIFF_ARGS="$diffargs" "$ROOT/scripts/ato_build.sh" "$PROJ" "$@" >"$log" 2>&1
}
fixes() { grep '^fix_stale_nets:' "$OUT/$1.log" | sed 's/^fix_stale_nets: //'; }
no_fixes() {
  [ "$(fixes "$1")" = "0 fixed, 0 renamed, 0 orphaned" ] \
    || fail "unexpected net repair: $(grep -E '^(fixed|renamed|orphaned)' "$OUT/$1.log")"
}
guardrails() {
  python3 "$ROOT/scripts/checks/kicad_guardrails.py" "$BOARD" parts >"$OUT/guardrails_$STEP.txt" \
    || fail "guardrails: $(grep FAIL "$OUT/guardrails_$STEP.txt")"
}
drc() {  # writes drc_$STEP.json; fails on errors or unconnected items
  kicad-cli pcb drc --format json --severity-all -o "$OUT/drc_$STEP.json" "$BOARD" >/dev/null
  python3 - "$OUT/drc_$STEP.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
errs = [v for v in d["violations"] if v["severity"] == "error"]
print("%d violations (%d errors), %d unconnected" % (len(d["violations"]), len(errs), len(d["unconnected_items"])))
sys.exit(1 if errs or d["unconnected_items"] else 0)
EOF
}
drc_signature() {
  python3 - "$1" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
for v in sorted(d["violations"] + d["unconnected_items"], key=lambda v: (v["type"], v["description"], str(v["items"]))):
    print(v["severity"], v["type"], sorted(i["description"] for i in v["items"]))
EOF
}
via_net() { kpy "$ROOT/scripts/roundtrip/pcb_ops.py" "$BOARD" via-net "$@"; }
sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
pyval() { "$KICAD_PY" -c "$1" 2>/dev/null; }
board_format() { sed -n 's/^	(version \([0-9]*\))/\1/p' "$BOARD"; }

"$ROOT/scripts/checks/toolchain.sh" >"$OUT/toolchain.txt" || fail "toolchain mismatch: $(grep FAIL "$OUT/toolchain.txt")"
{
  echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "kicad-cli: $(kicad-cli version)"
  echo "pcbnew: $(pyval 'import pcbnew; print(pcbnew.Version())')"
  echo "kikit: $(pyval 'import kikit; print(kikit.__version__)')"
  echo "atopile: $(ato --version 2>/dev/null | tail -1)"
  echo "freerouting.jar sha256: $(sha256 "$FREEROUTING_JAR")"
  echo "java: $(java -version 2>&1 | head -1)"
  echo "bash: $BASH_VERSION"
} >"$OUT/versions.txt"

cd "$PROJ"
git init -q
printf 'build/\n*.kicad_prl\n*-backups/\n.ato/\n' >.gitignore
git add -A
commit "fixture"

STEP=1-build
wrapper ato_build_1 "" || fail "wrapper (see ato_build_1.log)"
[ -f "$BOARD" ] || fail "no $BOARD"
guardrails
git add -A && commit "ato build"
ok "first build: $(grep -c '^	(footprint ' "$BOARD") footprints, format $(board_format)"

STEP=2-edit
kpy "$ROOT/scripts/roundtrip/edit_board.py" "$BOARD" >"$OUT/edit.json" || fail "pcbnew edit"
guardrails
drc >"$OUT/drc_$STEP.txt" || fail "DRC after edit: $(cat "$OUT/drc_$STEP.txt")"
git add -A && commit "pcbnew edit"
ok "pcbnew edit saved as format $(board_format); DRC $(cat "$OUT/drc_$STEP.txt")"

STEP=3-rebuild
wrapper ato_build_3 "--strict --json $OUT/board_diff_3.json" || fail "rebuild changed the edited board (see ato_build_3.log)"
no_fixes ato_build_3
drc >"$OUT/drc_$STEP.txt" || fail "DRC after rebuild: $(cat "$OUT/drc_$STEP.txt")"
diff <(drc_signature "$OUT/drc_2-edit.json") <(drc_signature "$OUT/drc_$STEP.json") >"$OUT/drc_delta_2_3.txt" \
  || fail "DRC results changed across the rebuild (see drc_delta_2_3.txt)"
git add -A
git diff --cached --quiet || commit "ato rebuild"
ok "rebuild kept every edit (strict: semantic diff empty, normalized text identical); DRC identical to step 2"

STEP=4-idempotent
wrapper ato_build_4 "--strict" || fail "second rebuild not a no-op (see ato_build_4.log)"
no_fixes ato_build_4
wrapper ato_build_4_frozen "--strict" --frozen || fail "--frozen build failed (see ato_build_4_frozen.log)"
git add -A
git diff --cached --quiet || commit "formatting"
ok "second rebuild and --frozen build are no-ops"

STEP=5-add-part
cp "$WORK/variants/add_part.ato" main.ato
wrapper ato_build_5 "--json $OUT/board_diff_5.json" || fail "adding a part broke the layout (see ato_build_5.log)"
python3 - "$OUT/board_diff_5.json" <<'EOF' || fail "unexpected diff after adding a part (see ato_build_5.log)"
import json, sys
d = json.load(open(sys.argv[1]))["diff"]
assert [(a["kind"], a["key"]) for a in d["added"]] == [("footprint", "c_mid")], d["added"]
assert not d["removed"], d["removed"]
assert not d["changed"], d["changed"]
EOF
FIXED5="$(fixes ato_build_5)"
kpy "$ROOT/scripts/roundtrip/pcb_ops.py" "$BOARD" place-offboard || fail "placing c_mid"
git add -A && commit "add c_mid"
ok "adding c_mid added exactly one footprint, nothing else changed (net repair: $FIXED5)"

STEP=6-stable
wrapper ato_build_6 "--strict" || fail "rebuild after placing c_mid not a no-op (see ato_build_6.log)"
no_fixes ato_build_6
wrapper ato_build_6_frozen "--strict" --frozen || fail "--frozen build failed (see ato_build_6_frozen.log)"
git add -A
git diff --cached --quiet || commit "formatting"
ok "rebuild and --frozen build are no-ops"

STEP=7-uncommitted-save
cp "$WORK/variants/net_churn.ato" main.ato
wrapper ato_build_7a "" || fail "net churn build (see ato_build_7a.log)"
FIXED7="$(fixes ato_build_7a)"
grep '^	(net ' "$BOARD" >"$OUT/nets_7_after_build.txt"
kpy "$ROOT/scripts/roundtrip/pcb_ops.py" "$BOARD" place-offboard || fail "placing c_foo"
kpy "$ROOT/scripts/roundtrip/pcb_ops.py" "$BOARD" via MID 103 103 || fail "adding a MID via"
grep '^	(net ' "$BOARD" >"$OUT/nets_7_after_pcbnew_save.txt"
if diff -q "$OUT/nets_7_after_build.txt" "$OUT/nets_7_after_pcbnew_save.txt" >/dev/null; then
  fail "pcbnew didn't renumber nets; this step no longer tests what it should"
fi
wrapper ato_build_7b "--json $OUT/board_diff_7b.json" || fail "rebuild after an uncommitted pcbnew save (see ato_build_7b.log)"
[ "$(via_net 103 103)" = "MID" ] || fail "the free MID via is now on net $(via_net 103 103)"
git add -A && commit "net churn"
ok "net churn ($FIXED7), uncommitted pcbnew save renumbered nets, rebuild: free MID via still MID ($(fixes ato_build_7b))"

STEP=8-rename
cp "$WORK/variants/rename.ato" main.ato
wrapper ato_build_8 "--json $OUT/board_diff_8.json" || fail "net rename (see ato_build_8.log)"
grep -q '^  renamed net MID -> MIDPOINT$' "$OUT/ato_build_8.log" || fail "board_diff didn't see the rename"
[ "$(via_net 103 103)" = "MIDPOINT" ] || fail "the MID via didn't follow the rename: $(via_net 103 103)"
git add -A && commit "rename MID"
ok "net MID renamed to MIDPOINT: copper followed ($(fixes ato_build_8))"

STEP=9-refused
refused() {  # NAME EXPECTED_MESSAGE PCB_OPS_ARGS...: the wrapper must refuse and leave the board untouched
  local name="$1" want="$2"
  shift 2
  kpy "$ROOT/scripts/roundtrip/pcb_ops.py" "$BOARD" "$@" || fail "pcb_ops $*"
  cp "$BOARD" "$WORK/before_$name.kicad_pcb"
  if wrapper "ato_build_9_$name" ""; then fail "the wrapper accepted: $name"; fi
  grep -q "$want" "$OUT/ato_build_9_$name.log" || fail "$name: expected '$want' (see ato_build_9_$name.log)"
  cmp -s "$BOARD" "$WORK/before_$name.kicad_pcb" || fail "$name: the wrapper changed the board although it failed"
  git checkout -q -- "$BOARD"
}
refused foreign "not found via fp-lib-table" foreign 127 117
refused flipped "atopile would flip it on every build" flip r_top
refused locked "atopile drops (locked" lock c_dec
ok "refused before atopile ran, board untouched: a foreign footprint, a footprint flipped against its library, a lock"

STEP=10-board-history
"$ROOT/scripts/checks/board_history.sh" "$(git rev-list --max-parents=0 HEAD)..HEAD" >"$OUT/board_history.log" 2>&1 \
  || fail "board_history over the round-trip history (see board_history.log)"
CHECKED="$(sed -n 's/^board_history: \([0-9]*\) board version.*/\1/p' "$OUT/board_history.log")"
[ "${CHECKED:-0}" -gt 0 ] || fail "board_history checked no boards"
"${GIT[@]}" checkout -q -b reroute
kpy "$ROOT/scripts/roundtrip/pcb_ops.py" "$BOARD" drop-track || fail "dropping a track"
commit "drop a track"
if "$ROOT/scripts/checks/board_history.sh" HEAD~1..HEAD >"$OUT/board_history_drop.log" 2>&1; then
  fail "board_history accepted a dropped track without Board-Diff-Allow"
fi
"${GIT[@]}" commit -q --amend -m "reroute" -m "Board-Diff-Allow: track:*" -m "Some trailing paragraph."
"$ROOT/scripts/checks/board_history.sh" HEAD~1..HEAD >"$OUT/board_history_allowed.log" 2>&1 \
  || fail "board_history rejected an allowed removal (see board_history_allowed.log)"
"${GIT[@]}" checkout -q -
"${GIT[@]}" merge -q --no-ff reroute -m "Merge reroute"
"$ROOT/scripts/checks/board_history.sh" HEAD~1..HEAD >"$OUT/board_history_merge.log" 2>&1 \
  || fail "board_history failed on a merge of an allowed change (see board_history_merge.log)"
ok "board_history: $CHECKED board versions OK; a dropped track fails without Board-Diff-Allow, passes with it, merge skipped"

STEP=11-freerouting
kpy "$ROOT/scripts/roundtrip/autoroute_smoke.py" "$BOARD" "$WORK/freerouting" >"$OUT/autoroute.json" \
  || fail "autoroute smoke test"
cp "$WORK/freerouting/freerouting.log" "$OUT/freerouting.log"
drc >"$OUT/drc_$STEP.txt" || fail "DRC after autorouting: $(cat "$OUT/drc_$STEP.txt")"
ok "Freerouting routed the ripped-up board ($(cat "$OUT/autoroute.json")); DRC $(cat "$OUT/drc_$STEP.txt")"

STEP=12-kikit
kpy -m kikit.ui fab jlcpcb --no-drc "$BOARD" "$WORK/fab" >"$OUT/kikit.log" || fail "kikit fab jlcpcb (see kikit.log)"
[ -s "$WORK/fab/gerbers.zip" ] || fail "kikit produced no gerbers.zip"
unzip -Z1 "$WORK/fab/gerbers.zip" | grep -v '/$' >"$OUT/kikit_gerbers.txt"
ok "kikit fab jlcpcb wrote gerbers.zip ($(wc -l <"$OUT/kikit_gerbers.txt" | tr -d ' ') files)"

echo "ROUNDTRIP PASS" | tee -a "$OUT/summary.txt"
