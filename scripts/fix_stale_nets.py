#!/usr/bin/env python3
"""Re-point tracks, arcs, vias and zones at the right net after `ato build`.

    python3 scripts/fix_stale_nets.py BOARD --against BOARD_BEFORE_BUILD
    python3 scripts/fix_stale_nets.py BOARD --rev HEAD          # only if nothing changed since HEAD

atopile 0.15.7 re-creates a net under a new number when fewer than 80% of its
pads already carry the net's name (e.g. a third pad added to a two-pad net),
but leaves copper on the old number (reports/phase0/). Net numbers only mean
something relative to the file they came from, so the baseline must be the
board exactly as it was before this build; scripts/ato_build.sh snapshots it.

For every segment, arc, via and zone whose number names a different net now:
  - its old net still exists under another number -> renumber to that
  - its old net is gone and its number now carries a name that didn't exist
    before -> atopile renamed the net in place; keep the number
  - otherwise -> net 0, listed as orphaned (board_diff then fails on it)
Zones also get their (net_name ...) rewritten, since KiCad resolves zones by name.

Edits the file in place, touching only the lines it reports. Plain python3, 3.9+.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import sexp  # noqa: E402

ROUTED = ("segment", "arc", "via", "zone")
BLOCK_START = re.compile(r"^\t\((%s)\s*$" % "|".join(ROUTED))
NET_LINE = re.compile(r"^(\t\t\(net )(\d+)(\)\s*)$")
NET_NAME_LINE = re.compile(r'^(\t\t\(net_name )"((?:[^"\\]|\\.)*)"(\)\s*)$')


def net_table(text):
    root = sexp.parse(text)[0]
    return {int(n[1]): n[2] for n in sexp.children(root, "net")}


def git_show(board, rev):
    path = os.path.realpath(board)
    res = subprocess.run(["git", "-C", os.path.dirname(path), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit("fix_stale_nets: %s is not in a git repository" % board)
    top = os.path.realpath(res.stdout.strip())
    res = subprocess.run(["git", "-C", top, "show", "%s:%s" % (rev, os.path.relpath(path, top))],
                         capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else None


def quote(name):
    return name.replace("\\", "\\\\").replace('"', '\\"')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--against", help="the board file as it was before ato build")
    g.add_argument("--rev", help="git revision holding the pre-build board")
    ap.add_argument("--allow-new", action="store_true", help="exit 0 if there is no baseline (first build)")
    args = ap.parse_args()

    if args.against:
        old_text = Path(args.against).read_text(encoding="utf-8") if os.path.exists(args.against) else None
    else:
        old_text = git_show(args.board, args.rev)
    if old_text is None:
        if args.allow_new:
            print("fix_stale_nets: no baseline for %s (new board); nothing to do" % args.board)
            return 0
        print("fix_stale_nets: FAIL no baseline for %s" % args.board)
        return 2

    text = Path(args.board).read_text(encoding="utf-8")
    old, new = net_table(old_text), net_table(text)
    new_by_name = {name: num for num, name in new.items()}
    old_names = set(old.values())

    lines = text.split("\n")
    block, block_target = None, None
    fixed, renamed, orphaned = [], [], []
    for i, line in enumerate(lines):
        m = BLOCK_START.match(line)
        if m:
            block, block_target = (m.group(1), i + 1), None
            continue
        if line == "\t)":
            block = None
            continue
        if not block:
            continue
        m = NET_LINE.match(line)
        if m:
            num = int(m.group(2))
            old_name = old.get(num)
            if num == 0 or old_name is None or new.get(num) == old_name:
                block_target = num if block[0] == "zone" else None
                continue
            entry = "%s at line %d: net %d (%s)" % (block[0], block[1], num, old_name)
            if old_name in new_by_name:
                target = new_by_name[old_name]
                fixed.append("%s -> %d" % (entry, target))
            elif num in new and new[num] not in old_names:
                target = num
                renamed.append("%s renamed to %s, number kept" % (entry, new[num]))
            else:
                target = 0
                orphaned.append("%s -> 0 (net no longer exists)" % entry)
            lines[i] = "%s%d%s" % (m.group(1), target, m.group(3))
            block_target = target
            continue
        m = NET_NAME_LINE.match(line)
        if m and block[0] == "zone" and block_target is not None:
            want = new.get(block_target, "") if block_target else ""
            if m.group(2) != quote(want):
                lines[i] = '%s"%s"%s' % (m.group(1), quote(want), m.group(3))
                fixed.append("zone at line %d: net_name %s -> %s" % (block[1], m.group(2), want))

    if fixed or renamed or orphaned:
        Path(args.board).write_text("\n".join(lines), encoding="utf-8")
    for e in fixed:
        print("fixed    " + e)
    for e in renamed:
        print("renamed  " + e)
    for e in orphaned:
        print("orphaned " + e)
    print("fix_stale_nets: %d fixed, %d renamed, %d orphaned" % (len(fixed), len(renamed), len(orphaned)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
