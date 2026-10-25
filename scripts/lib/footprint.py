"""Edit library footprints at the S-expression level: datasheet fixups and atopile safety.

model_fixups(node, spec)  set the 3D model's offset/rotate (hardware/parts.json "model")
fixups(node, spec)   apply corrections taken from a part's datasheet (hardware/parts.json):
                       move_pads  {"1": [x, y], ...}   pad centre in footprint coordinates
                       add_npth   [[x, y, drill], ...] non-plated holes (e.g. reverse-mount LEDs)
                       paste_pads ["1", ...]          through-hole pads that get paste (pin-in-paste)
                       paste_margin {"17": -0.15}     paste aperture grown (+) or shrunk (-) per side, mm
                       drop_graphics ["F.SilkS"]      remove the graphics on these layers (atopile 0.15.7
                                                      crashes on a silkscreen of circles only)
                       courtyard_rect [w, h]          replace the courtyard with a w x h rectangle centred
                                                      on the origin (for a degenerate library courtyard)
sanitize(node)       make unnumbered plated holes without copper (locating pegs) non-plated, and
                     mark a footprint with no plated through-hole pad as SMD;
                     remove what atopile would drop or merge anyway, where that is cosmetic:
                       pad sub-items atopile doesn't model (e.g. thermal_bridge_angle),
                       ${REFERENCE}/%R texts (atopile strips them),
                       item UUIDs (atopile copies them onto every instance),
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
    for name, (w, h) in sorted((spec.get("resize_pads") or {}).items()):
        size = sexp.child(pads[name], "size")
        old = (size[1], size[2])
        size[1], size[2] = _num(w), _num(h)
        changes.append("pad %s resized from %s x %s to %s x %s" % (name, old[0], old[1], w, h))
    for x, y, d in spec.get("add_npth") or []:
        node.append([A("pad"), "", A("np_thru_hole"), A("circle"), [A("at"), _num(x), _num(y)],
                     [A("size"), _num(d), _num(d)], [A("drill"), _num(d)], [A("layers"), "*.Cu", "*.Mask"],
                     [A("uuid"), str(uuid.uuid4())]])
        changes.append("non-plated hole %.2f mm added at (%s, %s)" % (d, x, y))
    for name in spec.get("paste_pads") or []:
        for pad in [p for p in sexp.children(node, "pad") if p[1] == name]:
            layers = sexp.child(pad, "layers")
            if "F.Paste" not in layers[1:]:
                layers.append("F.Paste")
                changes.append("pad %s gets solder paste (pin-in-paste)" % name)
    for layer in spec.get("drop_graphics") or []:
        for g in [c for c in node[1:] if sexp.head(c) in ("fp_line", "fp_circle", "fp_arc", "fp_rect", "fp_poly")
                  and (sexp.child(c, "layer") or [None, None])[1] == layer]:
            node.remove(g)
            changes.append("%s %s removed" % (sexp.head(g), layer))
    if spec.get("courtyard_rect"):
        w, h = spec["courtyard_rect"]
        old = [c for c in node[1:] if sexp.head(c) in ("fp_line", "fp_circle", "fp_arc", "fp_rect", "fp_poly")
               and str((sexp.child(c, "layer") or [None, ""])[1]).endswith(".CrtYd")]
        layer = sexp.child(old[0], "layer")[1] if old else "F.CrtYd"
        for g in old:
            node.remove(g)
        node.append([A("fp_rect"), [A("start"), _num(-w / 2), _num(-h / 2)], [A("end"), _num(w / 2), _num(h / 2)],
                     [A("stroke"), [A("width"), _num(0.05)], [A("type"), A("solid")]], [A("fill"), A("no")],
                     [A("layer"), layer], [A("uuid"), str(uuid.uuid4())]])
        changes.append("courtyard (%d items) replaced with a %s x %s mm rectangle" % (len(old), w, h))
    for name, margin in sorted((spec.get("paste_margin") or {}).items()):
        for pad in [p for p in sexp.children(node, "pad") if p[1] == name]:
            for old in [c for c in pad[1:] if sexp.head(c) == "solder_paste_margin"]:
                pad.remove(old)
            pad.append([A("solder_paste_margin"), _num(margin)])
            changes.append("pad %s paste aperture %+.2f mm per side" % (name, margin))
    return changes


def model_fixups(node, spec):
    """Set the 3D model's offset/rotation (mm/degrees) on the footprint as stored, i.e. on the
    bottom-side footprint for bottom parts. Checked by exporting STEP and comparing bodies."""
    changes = []
    if not spec:
        return changes
    m = sexp.child(node, "model")
    if m is None:
        raise ValueError("footprint has no 3D model to adjust")
    for key in ("offset", "rotate"):
        if key in spec:
            xyz = sexp.child(sexp.child(m, key), "xyz")
            xyz[1:4] = [_num(v) for v in spec[key]]
            changes.append("3D model %s set to %s" % (key, spec[key]))
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
    attr = sexp.child(node, "attr")
    pads = sexp.children(node, "pad")
    if attr is not None and len(attr) > 1 and attr[1] == "through_hole" and pads and \
            not any(p[2] == "thru_hole" for p in pads):
        attr[1] = A("smd")  # only SMD pads and non-plated pegs: an SMD part (CPL exports may filter on it)
        changes.append("attribute through_hole -> smd (no plated through-hole pads)")
    # Item UUIDs: atopile copies them onto every instance, so a part used twice would put
    # duplicate UUIDs on the board (kicad_guardrails.py refuses those). Bottom-side footprints
    # lose them when pcbnew rewrites them; top-side ones lose them here.
    stripped = 0
    for c in node[1:]:
        if isinstance(c, list):
            for sub in [s for s in c[1:] if sexp.head(s) == "uuid"]:
                c.remove(sub)
                stripped += 1
    if stripped:
        changes.append("dropped %d item UUIDs (atopile would copy them onto every instance)" % stripped)
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
