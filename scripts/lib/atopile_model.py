"""What atopile 0.15.7 keeps of KiCad files, and how it matches footprint items.

Shared by scripts/checks/kicad_guardrails.py (refuse what atopile would drop or
mangle) and scripts/lib/footprint.py (strip the cosmetic part of it on import).
Source: faebryk/core/zig/src/sexp/kicad/pcb.zig and
faebryk/exporters/pcb/kicad/transformer.py (PCB_Transformer.identify_obj).
"""

from . import sexp

# Child lists atopile 0.15.7 keeps, by parent (field names of the structs in
# faebryk/core/zig/src/sexp/kicad/pcb.zig, mapped to their sexp names).
ATOPILE_SCHEMA = {
    "kicad_pcb": {"version", "generator", "generator_version", "general", "paper", "title_block", "layers",
                  "setup", "net", "footprint", "via", "segment", "arc", "gr_line", "gr_arc", "gr_curve",
                  "gr_circle", "gr_rect", "gr_poly", "gr_text", "gr_text_box", "zone", "image", "dimension",
                  "group", "target", "embedded_fonts", "embedded_files", "table", "generated"},
    "footprint": {"layer", "uuid", "at", "descr", "tags", "path", "sheetname", "sheetfile", "property", "attr",
                  "fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly", "fp_text", "pad", "embedded_fonts",
                  "model",
                  "version", "generator", "generator_version"},  # library-file header
    "pad": {"at", "size", "drill", "layers", "remove_unused_layers", "net", "pinfunction", "pintype",
            "solder_mask_margin", "solder_paste_margin", "solder_paste_margin_ratio", "clearance",
            "zone_connect", "thermal_bridge_width", "thermal_gap", "roundrect_rratio", "chamfer_ratio",
            "chamfer", "properties", "options", "tenting", "uuid", "primitives"},
    "property": {"at", "unlocked", "layer", "hide", "uuid", "effects"},
    "fp_text": {"at", "layer", "hide", "uuid", "effects"},
    "segment": {"start", "end", "width", "layer", "net", "uuid"},
    "arc": {"start", "mid", "end", "width", "layer", "net", "uuid"},
    "via": {"at", "size", "drill", "layers", "net", "remove_unused_layers", "keep_end_layers",
            "zone_layer_connections", "padstack", "teardrops", "tenting", "free", "locked", "uuid"},
    "zone": {"net", "net_name", "layer", "layers", "uuid", "name", "hatch", "priority", "attr", "connect_pads",
             "min_thickness", "filled_areas_thickness", "keepout", "placement", "fill", "polygon",
             "filled_polygon"},
}
SINGLE = {("zone", "polygon")}  # atopile keeps only one


def _xy(node, name):
    c = sexp.child(node, name)
    return (round(float(c[1]), 2), round(float(c[2]), 2)) if c else None


def _pts(node):
    pts = sexp.child(node, "pts")
    return tuple((round(float(p[1]), 2), round(float(p[2]), 2)) for p in sexp.children(pts, "xy")) if pts else ()


# How atopile 0.15.7 matches footprint items when it re-syncs a footprint from its
# library on every build (PCB_Transformer.identify_obj): by type and geometry, not layer.
ATOPILE_IDENTITY = {
    "fp_line": lambda n: (_xy(n, "start"), _xy(n, "end")),
    "fp_rect": lambda n: (_xy(n, "start"), _xy(n, "end")),
    "fp_arc": lambda n: (_xy(n, "start"), _xy(n, "mid"), _xy(n, "end")),
    "fp_circle": lambda n: (_xy(n, "center"), _xy(n, "end")),
    "fp_poly": _pts,
    "fp_text": lambda n: _xy(n, "at"),
    "pad": lambda n: (n[1], _xy(n, "at")),
}
# atopile drops these fp_text entries before matching (fileformats.strip_duplicate_ref_texts).
DUPLICATE_REF_TEXTS = ("${REFERENCE}", "%R")
