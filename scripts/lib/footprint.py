"""Edit library footprints at the S-expression level: datasheet fixups and atopile safety.

fixups(node, spec)   apply corrections taken from a part's datasheet (hardware/parts.json):
                       move_pads  {"1": [x, y], ...}   pad centre in footprint coordinates
                       add_npth   [[x, y, drill], ...] non-plated holes (e.g. reverse-mount LEDs)
sanitize(node)       make unnumbered plated holes without copper (locating pegs) non-plated;
                     remove what atopile would drop or merge anyway, where that is cosmetic:
                       pad sub-items atopile doesn't model (e.g. thermal_bridge_angle),
                       ${REFERENCE}/%R texts (atopile strips them),
                       graphics that duplicate another item's geometry on another layer
                       (keep courtyard, then silkscreen, then fab).
                     Anything substantive atopile would drop (zones, curves, text boxes, groups,
                     unknown footprint items) raises ValueError instead.
Both return a list of human-readable changes. Python 3.9.
"""

import uuid

from . import sexp
from .atopile_model import ATOPILE_IDENTITY, ATOPILE_SCHEMA, DUPLICATE_REF_TEXTS

A = sexp.Atom
KEEP_ORDER = ("CrtYd", "SilkS", "Fab")  # which duplicate survives, by layer suffix


def _num(v):
    return A(("%.6f" % v).rstrip("0").rstrip("."))


def fixups(node, spec):
    changes = []
    pads = {p[1]: p for p in sexp.children(node, "pad")}
    for name, (x, y) in sorted((spec.get("move_pads") or {}).items()):
        at = sexp.child(pads[name], "at")
        old = (at[1], at[2])
        at[1], at[2] = _num(x), _num(y)
        changes.append("pad %s moved from (%s, %s) to (%s, %s)" % (name, old[0], old[1], x, y))
    for x, y, d in spec.get("add_npth") or []:
        node.append([A("pad"), "", A("np_thru_hole"), A("circle"), [A("at"), _num(x), _num(y)],
                     [A("size"), _num(d), _num(d)], [A("drill"), _num(d)], [A("layers"), "*.Cu", "*.Mask"],
                     [A("uuid"), str(uuid.uuid4())]])
        changes.append("non-plated hole %.2f mm added at (%s, %s)" % (d, x, y))
    return changes


def _rank(item):
    layer = sexp.child(item, "layer")
    name = layer[1] if layer else ""
    for i, suffix in enumerate(KEEP_ORDER):
        if name.endswith(suffix):
            return i
    return len(KEEP_ORDER)


def sanitize(node):
    if sexp.head(node) != "footprint":
        return []
    changes = []
    for c in node[1:]:
        h = sexp.head(c)
        if isinstance(c, list) and h and h not in ATOPILE_SCHEMA["footprint"]:
            raise ValueError("footprint %s has (%s ...), which atopile drops; fix the footprint by hand" % (node[1], h))
        if h == "pad":
            for sub in list(c[1:]):
                sh = sexp.head(sub)
                if isinstance(sub, list) and sh and sh not in ATOPILE_SCHEMA["pad"]:
                    if sh in ("thermal_bridge_angle",):
                        c.remove(sub)
                        changes.append("pad %s: dropped (%s %s), which atopile doesn't keep" % (c[1], sh, sub[1]))
                    else:
                        raise ValueError("pad %s has (%s ...), which atopile drops" % (c[1], sh))
    for c in sexp.children(node, "pad"):
        # An unnumbered plated hole without copper around it is a locating peg: make it non-plated.
        size, drill = sexp.child(c, "size"), sexp.child(c, "drill")
        if not c[1] and c[2] == "thru_hole" and drill and len(drill) == 2 and \
                max(float(size[1]), float(size[2])) <= float(drill[1]):
            c[2] = A("np_thru_hole")
            changes.append("unnumbered %s mm plated hole without annular ring made non-plated" % drill[1])
    for t in [c for c in node[1:] if sexp.head(c) == "fp_text" and len(c) > 2 and c[2] in DUPLICATE_REF_TEXTS]:
        node.remove(t)
        changes.append("dropped fp_text %s (atopile strips duplicate designators)" % t[2])
    groups = {}
    for c in node[1:]:
        h = sexp.head(c)
        if h in ATOPILE_IDENTITY and h != "pad":
            groups.setdefault((h, ATOPILE_IDENTITY[h](c)), []).append(c)
    for (h, ident), items in groups.items():
        if len(items) < 2:
            continue
        items.sort(key=_rank)
        for c in items[1:]:
            node.remove(c)
            changes.append("dropped %s on %s duplicating one on %s at %s" % (
                h, sexp.child(c, "layer")[1], sexp.child(items[0], "layer")[1], ident))
    return changes
