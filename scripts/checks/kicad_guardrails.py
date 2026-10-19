#!/usr/bin/env python3
"""Fail if KiCad files hold anything the pinned toolchain can't round-trip.

    python3 scripts/checks/kicad_guardrails.py hardware/layouts/left/left.kicad_pcb hardware/parts [...]

CLAUDE.md rule 5. Arguments are files or directories (searched recursively for
.kicad_pcb, .kicad_mod and .kicad_sym). Plain python3 (no pcbnew), so it reads
the files exactly as written.

Every file:
  - format version not newer than MAX_PCB_FORMAT / MAX_SYM_FORMAT (toolchain.env):
    atopile 0.15.7 can't parse KiCad 10 boards, and KiCad 9 can't load newer libraries.
Footprints (library files and footprints on boards):
  - only content atopile models (faebryk/core/zig/src/sexp/kicad/pcb.zig). atopile
    silently drops everything else on the next build: locks, footprint zones
    (keep-outs), fp_curve, text boxes, groups, ...
  - no two items atopile would match as one. It re-syncs footprints from their
    library on every build, matching items by type and geometry only (not layer),
    and merges such items, moving one onto the other's layer.
Boards, together with the .kicad_pro and fp-lib-table next to them:
  - top-level items, tracks, vias and zones hold only content atopile models
    (e.g. locked tracks come back unlocked; a zone keeps one outline)
  - every footprint is on the same side as its library footprint. atopile flips a
    footprint to its library side and back on every build, and the flip corrupts
    text rotations; bottom-side parts need bottom-side library footprints.
  - no IPC-4761 via protection: covering / plugging / capping / filling set to
    anything but "no" at board level, or present at all on a via or pad
  - no design variants ((variants ...) / (variant ...) blocks)
  - no time-domain tuning: tuning profiles in the project, or a netclass using one
"""

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import sexp  # noqa: E402
from lib.toolchain import pinned  # noqa: E402
from lib.atopile_model import ATOPILE_SCHEMA, SINGLE, ATOPILE_IDENTITY, DUPLICATE_REF_TEXTS  # noqa: E402

VIA_PROTECTION = ("covering", "plugging", "capping", "filling")

def schema_problems(node, kind, where):
    problems = []
    allowed = ATOPILE_SCHEMA[kind]
    counts = {}
    for c in node[1:]:
        if not isinstance(c, list):
            continue
        h = sexp.head(c)
        counts[h] = counts.get(h, 0) + 1
        if h not in allowed:
            problems.append("%s: atopile drops (%s ...) on the next build" % (where, h))
    for parent, h in SINGLE:
        if parent == kind and counts.get(h, 0) > 1:
            problems.append("%s: %d (%s ...) entries; atopile keeps one" % (where, counts[h], h))
    return problems


def footprint_problems(fp, where):
    problems = schema_problems(fp, "footprint", where)
    for c in fp[1:]:
        h = sexp.head(c)
        if h == "pad":
            problems += schema_problems(c, "pad", "%s pad %s" % (where, c[1]))
        elif h == "property" or (h == "fp_text" and not (len(c) > 2 and c[2] in DUPLICATE_REF_TEXTS)):
            problems += schema_problems(c, h, "%s %s %s" % (where, h, c[1]))
    return problems + atopile_collisions(fp, where)


def atopile_collisions(fp, where):
    seen, problems = {}, []
    for item in fp[1:]:
        kind = sexp.head(item)
        if kind not in ATOPILE_IDENTITY:
            continue
        if kind == "fp_text" and len(item) > 2 and item[2] in DUPLICATE_REF_TEXTS:
            continue
        ident = (kind, ATOPILE_IDENTITY[kind](item))
        layer = sexp.child(item, "layer") or sexp.child(item, "layers")
        layer = " ".join(str(x) for x in layer[1:]) if layer else "?"
        if ident in seen:
            problems.append("%s: atopile can't tell apart two %s items at %s (layers %s / %s) and merges them "
                            "on rebuild; make their geometry differ or drop one" % (where, kind, ident[1], seen[ident], layer))
        else:
            seen[ident] = layer
    return problems


def library_layers(board_path):
    """lib_id -> footprint layer of the library footprint, via the fp-lib-table next to the board."""
    table = board_path.parent / "fp-lib-table"
    if not table.exists():
        return None
    libs = {}
    for lib in sexp.children(sexp.load(table), "lib"):
        uri = sexp.child(lib, "uri")[1].replace("${KIPRJMOD}", str(board_path.parent))
        libs[sexp.child(lib, "name")[1]] = Path(uri)

    def layer(lib_id):
        nick, _, name = lib_id.partition(":")
        f = libs.get(nick, Path("/nonexistent")) / (name + ".kicad_mod")
        if not f.exists():
            return None
        lay = sexp.child(sexp.load(f), "layer")
        return lay[1] if lay else "F.Cu"
    return layer


def check_pcb(path, max_format, prebuild=False):
    problems = []
    root = sexp.load(path)
    version = sexp.child(root, "version")
    if version is None or int(version[1]) > max_format:
        problems.append("file format %s is newer than the pinned maximum %d" % (version and version[1], max_format))
        return problems  # a newer format has other syntax; the rest would be noise

    problems += schema_problems(root, "kicad_pcb", "board")
    seen = collections.Counter(n[1] for _p, n in sexp.walk(root) if sexp.head(n) == "uuid")
    dupes = sum(c - 1 for c in seen.values() if c > 1)
    if dupes:
        problems.append("%d duplicated item UUIDs (run scripts/placement/unique_uuids.py)" % dupes)
    lib_layer = library_layers(path)
    if lib_layer is None:
        problems.append("no fp-lib-table next to the board; can't check footprint sides")
    for c in root[1:]:
        h = sexp.head(c)
        if h in ("segment", "arc", "via", "zone"):
            uuid = sexp.child(c, "uuid")
            problems += schema_problems(c, h, "%s %s" % (h, uuid[1][:8] if uuid else "?"))
        elif h == "footprint":
            ref = next((p[2] for p in sexp.children(c, "property") if p[1] == "Reference"), c[1])
            problems += footprint_problems(c, "footprint %s" % ref)
            if lib_layer is not None:
                want = lib_layer(c[1])
                have = sexp.child(c, "layer")[1]
                if want is None:
                    if not prebuild:  # before a build the part may have been swapped; the build replaces it
                        problems.append("footprint %s: library footprint %s not found via fp-lib-table" % (ref, c[1]))
                elif want != have:
                    problems.append("footprint %s is on %s but its library footprint %s is on %s; atopile would "
                                    "flip it on every build. Use a %s-side library footprint."
                                    % (ref, have, c[1], want, "bottom" if have == "B.Cu" else "top"))

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
    elif sexp.head(root) == "footprint":
        problems += footprint_problems(root, "footprint %s" % root[1])
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
    ap.add_argument("--prebuild", action="store_true",
                    help="boards are about to be rebuilt: a footprint whose library part is gone is not an error")
    args = ap.parse_args(argv)
    max_pcb = int(pinned("MAX_PCB_FORMAT"))
    max_sym = int(pinned("MAX_SYM_FORMAT"))
    print("limits: board/footprint format <= %d, symbol format <= %d" % (max_pcb, max_sym))
    files = []
    for arg in args.paths:
        if arg.is_dir():
            files += sorted(f for ext in ("*.kicad_pcb", "*.kicad_mod", "*.kicad_sym") for f in arg.rglob(ext))
        elif arg.exists():
            files.append(arg)
        else:
            print("FAIL %s: no such file or directory" % arg)
            return 1
    failed = False
    for f in files:
        if f.suffix == ".kicad_pcb":
            problems = ["%s: %s" % (f, p) for p in check_pcb(f, max_pcb, args.prebuild)]
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
