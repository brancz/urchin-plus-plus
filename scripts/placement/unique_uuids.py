#!/usr/bin/env python3
"""Give every item on a board its own UUID (fix duplicates in place).

    python3 scripts/placement/unique_uuids.py BOARD [--check]

atopile copies a library footprint's item UUIDs onto every instance, so parts used
more than once (keys, holes) share pad and graphic UUIDs, and KiCad's DRC then names
the wrong footprint in its reports (phase 3 review). The libraries no longer carry item
UUIDs; this repairs boards built before that. A duplicate is replaced by a UUID derived
from its footprint's UUID and the item's position in the footprint, so reruns agree.
--check only reports. Python 3.9.
"""

import argparse
import collections
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import sexp  # noqa: E402


def uuids(node):
    for _path, n in sexp.walk(node):
        if sexp.head(n) == "uuid":
            yield n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = sexp.load(args.board)
    count = collections.Counter(n[1] for n in uuids(root))
    dupes = {u for u, c in count.items() if c > 1}
    if args.check:
        print("%s: %d duplicated UUIDs (%d extra)" % (args.board, len(dupes), sum(count[u] - 1 for u in dupes)))
        return 1 if dupes else 0
    seen, fixed = set(), 0
    for fp in sexp.children(root, "footprint"):
        own = sexp.child(fp, "uuid")
        base = own[1] if own else "?"
        for i, n in enumerate(n for n in uuids(fp) if n is not own):
            if n[1] in dupes and n[1] in seen:
                n[1] = str(uuid.uuid5(uuid.NAMESPACE_URL, "urchin++/%s/%d" % (base, i)))
                fixed += 1
            seen.add(n[1])
    for n in uuids(root):
        seen.add(n[1])
    Path(args.board).write_text("\n".join(sexp.dump_lines(root)) + "\n")
    print("%s: %d duplicate UUIDs replaced" % (args.board, fixed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
