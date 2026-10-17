#!/usr/bin/env python3
"""Fail if KiCad files use formats or features the pinned toolchain can't round-trip.

    python3 scripts/checks/kicad_guardrails.py hardware/layouts/left/left.kicad_pcb hardware/parts [...]

CLAUDE.md rule 5. Arguments are files or directories (searched recursively for
.kicad_pcb, .kicad_mod and .kicad_sym). Footprints and symbols must not be newer
than MAX_PCB_FORMAT / MAX_SYM_FORMAT in toolchain.env (KiCad 9 can't load newer
library files). Footprints must not contain two items atopile would match as one
(same type and geometry on different layers): atopile re-syncs footprints from
their library on every build and merges such items, moving one to the other's
layer (reports/phase0/). Boards are checked further, together with the .kicad_pro next to them:
  - the file format version is not newer than MAX_PCB_FORMAT
    (atopile 0.15.7 can't parse KiCad 10 boards, see reports/phase0/)
  - no IPC-4761 via protection: covering / plugging / capping / filling set
    to anything but "no" at board level, or present at all on a via or pad
  - no design variants ((variants ...) / (variant ...) blocks)
  - no time-domain tuning: tuning profiles in the project, or a netclass
    that references one

Plain python3 (no pcbnew), so it reads the files exactly as written.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import sexp  # noqa: E402
from lib.toolchain import pinned  # noqa: E402

VIA_PROTECTION = ("covering", "plugging", "capping", "filling")


def check_pcb(path, max_format):
    problems = []
    root = sexp.load(path)
    version = sexp.child(root, "version")
    if version is None or int(version[1]) > max_format:
        problems.append("file format %s is newer than the pinned maximum %d" % (version and version[1], max_format))

    for where, node in sexp.walk(root):
        h = sexp.head(node)
        if h in ("variants", "variant"):
            problems.append("design variant block (%s) under %s" % (h, "/".join(where)))
        elif h in VIA_PROTECTION:
            parent = where[-1] if where else ""
            values = [v for v in node[1:] if not isinstance(v, list)]
            values += [c[1] for c in node[1:] if isinstance(c, list) and len(c) > 1]
            if parent == "setup":
                if any(v not in ("no", "none") for v in values):
                    problems.append("board-level via %s enabled: %s" % (h, node))
            else:
                problems.append("per-item via protection (%s) under %s" % (h, "/".join(where)))
    return problems


def check_lib(path, max_format):
    root = sexp.load(path)
    version = sexp.child(root, "version")
    problems = []
    if version is None or int(version[1]) > max_format:
        problems.append("file format %s is newer than the pinned maximum %d" % (version and version[1], max_format))
    if sexp.head(root) == "footprint":
        problems += atopile_collisions(root)
    return problems


def _xy(node, name):
    c = sexp.child(node, name)
    return (round(float(c[1]), 2), round(float(c[2]), 2)) if c else None


def _pts(node):
    pts = sexp.child(node, "pts")
    return tuple((round(float(p[1]), 2), round(float(p[2]), 2)) for p in sexp.children(pts, "xy")) if pts else ()


# How atopile 0.15.7 matches footprint items when it re-syncs a footprint from its
# library on every build (PCB_Transformer.identify_obj): geometry only, no layer.
ATOPILE_IDENTITY = {
    "fp_line": lambda n: (_xy(n, "start"), _xy(n, "end")),
    "fp_rect": lambda n: (_xy(n, "start"), _xy(n, "end")),
    "fp_arc": lambda n: (_xy(n, "start"), _xy(n, "mid"), _xy(n, "end")),
    "fp_circle": lambda n: (_xy(n, "center"), _xy(n, "end")),
    "fp_poly": _pts,
    "fp_curve": _pts,
    "fp_text": lambda n: _xy(n, "at"),
    "pad": lambda n: (n[1], _xy(n, "at")),
}


def atopile_collisions(fp):
    """Items atopile can't tell apart get merged on rebuild (one silently takes the other's layer)."""
    seen, problems = {}, []
    for item in fp[1:]:
        kind = sexp.head(item)
        if kind not in ATOPILE_IDENTITY:
            continue
        ident = (kind, ATOPILE_IDENTITY[kind](item))
        layer = sexp.child(item, "layer") or sexp.child(item, "layers")
        layer = " ".join(str(x) for x in layer[1:]) if layer else "?"
        if ident in seen:
            problems.append("atopile can't tell apart two %s items at %s (layers %s / %s); it would merge them "
                            "on rebuild. Make their geometry differ or drop one." % (kind, ident[1], seen[ident], layer))
        else:
            seen[ident] = layer
    return problems


def check_pro(path):
    problems = []
    pro = json.loads(path.read_text(encoding="utf-8"))
    tp = pro.get("tuning_profiles", {})
    for key, val in tp.items():
        if key != "meta" and val:
            problems.append("tuning profiles defined (%s)" % key)
    for nc in pro.get("net_settings", {}).get("classes", []):
        if nc.get("tuning_profile"):
            problems.append("netclass %s uses tuning profile %s" % (nc.get("name"), nc["tuning_profile"]))
    return problems


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", type=Path)
    args = ap.parse_args(argv)
    max_pcb = int(pinned("MAX_PCB_FORMAT"))
    max_sym = int(pinned("MAX_SYM_FORMAT"))
    print("limits: board/footprint format <= %d, symbol format <= %d" % (max_pcb, max_sym))
    files = []
    for arg in args.paths:
        if arg.is_dir():
            files += sorted(f for ext in ("*.kicad_pcb", "*.kicad_mod", "*.kicad_sym") for f in arg.rglob(ext))
        else:
            files.append(arg)
    failed = False
    for f in files:
        if f.suffix == ".kicad_pcb":
            problems = ["%s: %s" % (f, p) for p in check_pcb(f, max_pcb)]
            pro = f.with_suffix(".kicad_pro")
            if pro.exists():
                problems += ["%s: %s" % (pro, p) for p in check_pro(pro)]
        elif f.suffix == ".kicad_mod":
            problems = ["%s: %s" % (f, p) for p in check_lib(f, max_pcb)]
        elif f.suffix == ".kicad_sym":
            problems = ["%s: %s" % (f, p) for p in check_lib(f, max_sym)]
        else:
            problems = ["%s: not a KiCad board, footprint or symbol file" % f]
        for p in problems:
            print("FAIL " + p)
        if problems:
            failed = True
        else:
            print("ok   %s" % f)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
