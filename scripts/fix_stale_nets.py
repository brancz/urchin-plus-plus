#!/usr/bin/env python3
"""Put tracks, arcs, vias and zones back on their nets after `ato build`.

    python3 scripts/fix_stale_nets.py BOARD --against BOARD_BEFORE_BUILD
    python3 scripts/fix_stale_nets.py BOARD --rev HEAD          # only if nothing changed since HEAD

When atopile 0.15.7 re-creates a net under a new number (fewer than 80% of its
pads already carried the name, e.g. a third pad on a two-pad net), it leaves the
copper on that net behind: on macOS on the old, now meaningless number, on Linux
on net 0 (reports/phase0/). KiCad recomputes the net of copper touching a pad on
load, but not of free copper (stitching vias, stubs) or zones.

Copper keeps its UUID through a build, so each segment, arc, via and zone is
matched to itself in the board as it was before this build (the baseline;
scripts/ato_build.sh snapshots it):
  - its net number is unchanged and still in the net table -> atopile kept that
    net (maybe renamed it in place); leave it. atopile only hands out numbers
    that were free when it loaded the board, so the number can't mean another net.
  - otherwise (number gone or zeroed) -> the current number of the net it had
    before, by name
  - that name is gone too -> net 0, listed as orphaned (board_diff fails on it)
Copper not in the baseline is left alone. Zones also get (net_name ...)
rewritten, since KiCad resolves zones by name.

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
UUID_LINE = re.compile(r'^\t\t\(uuid "([^"]+)"\)\s*$')


def net_table(text):
    root = sexp.parse(text)[0]
    return {int(n[1]): n[2] for n in sexp.children(root, "net")}


def blocks(lines):
    """Top-level copper blocks: kind, line of the (net N), its number, (net_name) line, uuid."""
    out, cur = [], None
    for i, line in enumerate(lines):
        m = BLOCK_START.match(line)
        if m:
            cur = {"kind": m.group(1), "start": i + 1, "net_line": None, "net": None, "name_line": None, "uuid": None}
            continue
        if cur is None:
            continue
        if line == "\t)":
            out.append(cur)
            cur = None
            continue
        if (m := NET_LINE.match(line)) and cur["net_line"] is None:
            cur["net_line"], cur["net"] = i, int(m.group(2))
        elif (m := NET_NAME_LINE.match(line)) and cur["name_line"] is None:
            cur["name_line"] = i
        elif (m := UUID_LINE.match(line)) and cur["uuid"] is None:
            cur["uuid"] = m.group(1)
    return out


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
    old_lines = old_text.split("\n")
    was = {}  # uuid -> (net number, net name) before the build
    for b in blocks(old_lines):
        if b["uuid"] and b["net"] is not None:
            name = old.get(b["net"], "")
            if not name and b["name_line"] is not None:
                name = NET_NAME_LINE.match(old_lines[b["name_line"]]).group(2)
            was[b["uuid"]] = (b["net"], name)

    lines = text.split("\n")
    fixed, renamed, orphaned = [], [], []
    for b in blocks(lines):
        if b["net_line"] is None or b["uuid"] not in was:
            continue  # no net (graphic-only) or copper that didn't exist before the build
        (before, name), num = was[b["uuid"]], b["net"]
        where = "%s at line %d (%s)" % (b["kind"], b["start"], b["uuid"][:8])
        if not name:
            continue  # had no net before; nothing to restore
        if num == before and num and num in new:
            target = num
            if new[num] != name:
                renamed.append("%s: net %s renamed to %s, number %d kept" % (where, name, new[num], num))
        elif name in new_by_name:
            target = new_by_name[name]
            if target != num:
                fixed.append("%s: net %d -> %d (%s)" % (where, num, target, name))
        else:
            target = 0
            orphaned.append("%s: net %s no longer exists -> 0" % (where, name))
        m = NET_LINE.match(lines[b["net_line"]])
        lines[b["net_line"]] = "%s%d%s" % (m.group(1), target, m.group(3))
        if b["kind"] == "zone" and b["name_line"] is not None:
            m = NET_NAME_LINE.match(lines[b["name_line"]])
            want = quote(new.get(target, "") if target else "")
            if m.group(2) != want:
                lines[b["name_line"]] = '%s"%s"%s' % (m.group(1), want, m.group(3))
                fixed.append("%s: net_name %s -> %s" % (where, m.group(2), want))

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
