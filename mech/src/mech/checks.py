"""Fit checks between the printed parts and the real board (kicad-cli's STEP export of the
routed half, with every 3D model), plus what the STEP lacks: the hotswap sockets, the
battery, the switches and the keycaps, modelled from the board data. Also the hardware: the
screws, washers and standoffs as solids, their thread engagement, and no metal in the
antenna keep-out."""

from build123d import Align, Box, Kind, Pos, Rectangle, Vector, import_step, offset

from . import params as P
from .board import Board, polygon_face, rect_face, rotated_rect_face, xy
from .case import cover_holes, cyl, openings, prism, screwed

# kicad-cli puts the board's dielectric at z = 0 and seats bottom parts at z = -0.085 (the
# copper and solder mask): that plane is the PCB's underside.
STEP_UNDERSIDE = -0.085

MIN_GAP = 0.25        # printed part to any board part, where they aren't meant to touch
VOLUME_EPS = 1e-3     # mm^3


def board_parts(board: Board, step_path):
    """[(name, shape)] of the half's physical parts, placed in the case's frame."""
    step = Pos(0, 0, P.Z_PCB_BOTTOM - STEP_UNDERSIDE) * import_step(str(step_path))
    children = list(step)
    pcb = max(children, key=lambda c: c.bounding_box().size.X * c.bounding_box().size.Y)
    parts = [("pcb", pcb)] + [(f"{model_ref(board, c, i)} 3D model", c) for i, c in enumerate(children) if c is not pcb]
    for k in board["keys"]:
        parts.append((f"{k['ref']} socket", prism(polygon_face(k["socket"]), P.Z_PCB_BOTTOM - P.SOCKET_H, P.Z_PCB_BOTTOM)))
        # A keycap pressed down (Choc: 3 mm travel) reaches this low; up to its top.
    bt = board["battery"]["courtyard"]
    parts.append(("battery", prism(rect_face(bt, -0.25), P.Z_PCB_TOP, P.Z_PCB_TOP + P.BATTERY_H)))
    return parts


def model_ref(board: Board, shape, i):
    """The reference of the bottom footprint whose courtyard holds a STEP part's centre (the
    STEP carries no names), else its index."""
    c = shape.bounding_box().center()
    for cy in board["bottom_courtyards"]:
        if polygon_face(cy["polygon"]).is_inside(Vector(c.X, c.Y, 0)):
            return cy["ref"]
    return f"part {i}"


def switches(board: Board):
    return [(f"{k['ref']} switch", prism(rotated_rect_face(k["x"], k["y"], P.SWITCH_BODY, P.SWITCH_BODY, k["rot"]),
                                         P.Z_PCB_TOP, P.Z_PCB_TOP + P.SWITCH_BODY_H))
            for k in board["keys"]]


def keycaps(board: Board):
    # Choc keycaps sit about 5 mm above the PCB and travel 3 mm: they sweep 2 to 8 mm above it.
    return [(f"{k['ref']} keycap", prism(f, P.Z_PCB_TOP + 2.0, P.Z_PCB_TOP + 8.0))
            for k, f in zip(board["keys"], board.keycaps(0.0))]


def fit(part_name, part, others, touching=()):
    """Interference volume and minimum gap of a printed part against each board part.
    `touching` names parts the printed part is meant to touch (the PCB on its standoffs)."""
    rows = []
    for name, other in others:
        # Only the printed part's material within MIN_GAP of the other part's bounding box can
        # touch it or come closer than MIN_GAP: clip to that box first (distances against full
        # 3D models are slow).
        ob = other.bounding_box()
        m = MIN_GAP + 0.05
        window = Pos(ob.min.X - m, ob.min.Y - m, ob.min.Z - m) * Box(
            ob.size.X + 2 * m, ob.size.Y + 2 * m, ob.size.Z + 2 * m, align=Align.MIN)
        local = part & window
        if not local.solids():
            continue
        overlap = (local & other).volume
        gap = local.distance_to(other)
        ok = overlap <= VOLUME_EPS and (name in touching or gap >= MIN_GAP)
        rows.append({"part": part_name, "against": name, "overlap_mm3": round(overlap, 4),
                     "gap_mm": round(gap, 3), "ok": ok})
    return rows


def bed_fit(name, part):
    s = part.bounding_box().size
    dims = sorted([s.X, s.Y])
    bed = sorted(P.BED[:2])
    ok = dims[0] <= bed[0] and dims[1] <= bed[1] and s.Z <= P.BED[2]
    return {"part": name, "size_mm": [round(s.X, 2), round(s.Y, 2), round(s.Z, 2)], "bed_mm": list(P.BED), "ok": ok}


def insertion(board: Board, parts):
    """The board must drop into the case: any part reaching past the cavity (the outline plus
    FIT) must do so inside a full-height opening of the wall. Checked on each part's XY
    bounding box, which is conservative."""
    cavity = offset(board.outline(), P.FIT, kind=Kind.ARC)
    free = cavity
    for f in openings(board):
        free = free + f
    rows = []
    for name, shape in parts:
        if name == "pcb":
            continue
        bb = shape.bounding_box()
        rect = Pos((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2) * Rectangle(bb.size.X, bb.size.Y)
        outside = (rect - cavity).area
        if outside <= VOLUME_EPS:
            continue
        blocked = (rect - free).area
        rows.append({"part": name, "beyond_cavity_mm2": round(outside, 3), "blocked_mm2": round(blocked, 3),
                     "ok": blocked <= VOLUME_EPS})
    return rows


def pcb_screws(board: Board):
    """The 3.8 mm holes that take a screw (case.screwed), as (ref, x, y) in the CAD frame."""
    return [(h["ref"], *xy((h["x"], h["y"]))) for h in board["case_holes"]
            if h["d"] > P.SCREW_CLEAR_D and screwed(board, h)]


def hardware(board: Board):
    """[(name, shape)] of the screw heads, washers and standoffs that sit beside board parts."""
    out = []
    z = P.Z_PCB_TOP
    for ref, x, y in pcb_screws(board):
        washer_d, washer_t = P.WASHER
        head_d, head_h = P.PCB_SCREW_HEAD
        out.append((f"{ref} washer and screw head",
                    cyl(x, y, washer_d, z, z + washer_t) + cyl(x, y, head_d, z + washer_t, z + washer_t + head_h)))
    for h in cover_holes(board):
        x, y = xy((h["x"], h["y"]))
        out.append((f"{h['ref']} nylon standoff", cyl(x, y, P.STANDOFF_D, z, z + P.STANDOFF_LEN)))
    return out


def screw_stacks(board: Board):
    """Thread engagement and clearances of every screw, from the stack's heights."""
    rows = []
    if pcb_screws(board):
        under_head = P.Z_PCB_TOP + P.WASHER[1]
        tip = under_head - P.PCB_SCREW_L
        engaged = P.Z_PCB_BOTTOM - max(tip, P.Z_PCB_BOTTOM - P.INSERT_L)
        to_bottom = tip - (P.Z_PCB_BOTTOM - P.INSERT_DEPTH)
        rows.append({"stack": f"M2 x {P.PCB_SCREW_L:g} into the heat-set insert ({', '.join(r for r, _, _ in pcb_screws(board))})",
                     "thread_mm": round(engaged, 2), "tip_to_hole_bottom_mm": round(to_bottom, 2),
                     "ok": engaged >= P.MIN_THREAD and to_bottom >= P.MIN_TIP_GAP})
    lower_tip = P.HEAD_DEPTH + P.COVER_LOWER_SCREW_L
    upper_tip = P.Z_ROOF_BOTTOM + P.ROOF_T - P.COVER_HEAD_DEPTH - P.COVER_UPPER_SCREW_L
    lower = lower_tip - P.Z_PCB_TOP
    upper = P.Z_ROOF_BOTTOM - upper_tip
    rows.append({"stack": f"nylon M2 x {P.COVER_LOWER_SCREW_L:g} from below and M2 x {P.COVER_UPPER_SCREW_L:g} "
                          f"from the cover, in the {P.STANDOFF_LEN:g} mm standoff",
                 "lower_thread_mm": round(lower, 2), "upper_thread_mm": round(upper, 2),
                 "tip_gap_mm": round(upper_tip - lower_tip, 2),
                 "lower_head_above_underside_mm": round(P.HEAD_DEPTH - P.NYLON_HEAD_H, 2),
                 "ok": min(lower, upper) >= P.MIN_THREAD and upper_tip - lower_tip >= P.MIN_TIP_GAP
                       and P.HEAD_DEPTH - P.NYLON_HEAD_H >= 0})
    return rows


def antenna_metal(board: Board):
    """Metal hardware (steel screws and washers, brass inserts, steel discs) must stay out of
    the antenna keep-out (CLAUDE.md rule 6)."""
    keepout = polygon_face(board["rule_areas"]["ANTENNA_KEEPOUT"])
    metal = [(f"{ref} screw, washer and insert", x, y, P.WASHER[0]) for ref, x, y in pcb_screws(board)]
    metal += [(f"{m['ref']} steel disc", *xy((m["x"], m["y"])), P.DISC_D) for m in board["steel_discs"]]
    rows = []
    for name, x, y, d in metal:
        gap = keepout.distance_to(Vector(x, y, 0)) - d / 2
        rows.append({"metal": name, "gap_to_antenna_keepout_mm": round(gap, 2), "ok": gap > 0})
    return rows
