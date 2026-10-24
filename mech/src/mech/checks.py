"""Fit checks between the printed parts and the real board (kicad-cli's STEP export of the
routed half, with every 3D model), plus what the STEP lacks: the hotswap sockets, the
battery, the switches and the keycaps, modelled from the board data. Also the hardware: the
screws, washers and nuts as solids, their thread engagement, no metal in the antenna
keep-out, the cover's posts where its play can put them, the largest cell against the board,
and the lips over the board's outer edge."""

import math

from build123d import (Align, Box, Circle, Kind, Pos, Rectangle, RegularPolygon, Vector, Vertex, import_step,
                       offset)

from . import params as P
from .board import Board, polygon_face, rect_face, rotated_rect_face, xy
from .case import cover_holes, cyl, openings, outer_edge, prism, screwed

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
    parts.append(("battery", prism(rect_face(cell_box(board)), P.Z_PCB_TOP, P.Z_PCB_TOP + P.FOAM_T + P.CELL[2])))
    return parts


def cell_box(board: Board):
    """(x0, y0, x1, y1), KiCad frame, of the largest cell (P.CELL) where mech/README.md puts it:
    centred on the battery's outline (BT2), its antenna-side end on the outline's end, its extra
    length toward the wire pads (BT1)."""
    x0, y0, x1, y1 = board["battery"]["outline"]
    w, length, _ = P.CELL
    cx = (x0 + x1) / 2
    if board["battery_pads"]["y"] > (y0 + y1) / 2:
        return (cx - w / 2, y0, cx + w / 2, y0 + length)
    return (cx - w / 2, y1 - length, cx + w / 2, y1)


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
    `touching` names parts the printed part is meant to touch (the PCB on its standoffs and
    under the cover's posts)."""
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
        if local is None or not local.solids():  # None, not an empty shape, for a STEP part
            continue
        common = local & other
        overlap = common.volume if common is not None else 0.0
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
    """[(name, shape)] of the screw heads, washers and nuts that sit beside board parts."""
    out = []
    z = P.Z_PCB_TOP
    for ref, x, y in pcb_screws(board):
        washer_d, washer_t = P.WASHER
        head_d, head_h = P.PCB_SCREW_HEAD
        out.append((f"{ref} washer and screw head",
                    cyl(x, y, washer_d, z, z + washer_t) + cyl(x, y, head_d, z + washer_t, z + washer_t + head_h)))
    roof = P.Z_ROOF_BOTTOM + P.ROOF_T
    for h in cover_holes(board):
        # The nut turned with a flat toward the keycap beside it (mech/README.md), grown by its
        # screw's play in the PCB's hole: every place it can be.
        x, y = xy((h["x"], h["y"]))
        play = screw_play(h)
        hexagon = RegularPolygon(P.NUT[0] / 2, 6, rotation=toward_keycap(board, x, y) + 30).faces()[0]
        nut = offset(Pos(x, y) * hexagon, play, kind=Kind.ARC)
        out.append((f"{h['ref']} nylon nut and screw tip",
                    prism(nut, roof, roof + P.NUT[1])
                    + cyl(x, y, 2.0 + 2 * play, roof + P.NUT[1], P.HEAD_DEPTH + P.COVER_SCREW_L)))
    return out


def screw_play(hole):
    """How far a nylon M2 can sit off the centre of the PCB's hole."""
    return (hole["d"] - P.M2_MIN_D) / 2


def cover_play(hole):
    """How far the cover's post at a hole can sit off the hole's centre: its screw off the PCB
    hole's centre, and its bore off the screw."""
    return screw_play(hole) + (P.COVER_BORE_D - P.M2_MIN_D) / 2


def toward_keycap(board: Board, x, y):
    """The direction (degrees, CAD frame) from (x, y) to the nearest keycap."""
    p = Vertex(x, y, 0)
    a, b = min((p.closest_points(f) for f in board.keycaps(0.0)), key=lambda ab: (ab[1] - ab[0]).length)
    return math.degrees(math.atan2(b.Y - a.Y, b.X - a.X))


def moved_posts(board: Board):
    """[(name, shape)] of the cover's posts grown by the cover's play on its screws: every place
    a post can be. The roof and skirt keep P.KEYCAP_MARGIN from the keycaps, more than the play."""
    return [(f"{h['ref']} cover post, moved by its play",
             cyl(*xy((h["x"], h["y"])), P.COVER_POST_D + 2 * cover_play(h), P.Z_PCB_TOP, P.Z_ROOF_BOTTOM + P.ROOF_T))
            for h in cover_holes(board)]


def cell_rows(board: Board):
    """The largest cell (cell_box) against what its foam and the board leave room for: the
    antenna keep-out, the wire pads it can reach over (it lies on its foam above their solder
    joints), and the LEDs' light holes beside its end (at least half of each stays open)."""
    x0, y0, x1, y1 = cell_box(board)
    cell = rect_face((x0, y0, x1, y1))
    keepout = polygon_face(board["rule_areas"]["ANTENNA_KEEPOUT"])
    gap = keepout.distance_to(cell)
    over_pads = max(min(y1, p["y"] + p["h"] / 2) - max(y0, p["y"] - p["h"] / 2)
                    for p in board["battery_pads"]["pads"] if x0 < p["x"] + p["w"] / 2 and p["x"] - p["w"] / 2 < x1)
    covered = {}
    for led in board["leds"]:
        for h in led["holes"]:
            hole = Pos(*xy((h["x"], h["y"]))) * Circle(h["d"] / 2).faces()[0]
            common = hole & cell
            covered[led["ref"]] = round((common.area if common is not None else 0.0) / hole.area, 2)
    return [{"stack": f"the largest cell ({' x '.join(f'{v:g}' for v in P.CELL)} mm) on the battery's outline",
             "gap_to_antenna_keepout_mm": round(gap, 2), "over_wire_pads_mm": round(max(over_pads, 0.0), 2),
             "above_solder_joints_mm": round(P.FOAM_T - P.JOINT_H, 2), "led_hole_covered": covered,
             "ok": gap >= P.CELL_KEEPOUT_GAP and P.FOAM_T >= P.JOINT_H and all(v <= 0.5 for v in covered.values())}]


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
    # A nut needs its whole height engaged (DIN 934 sizes it for the screw's strength), not
    # MIN_THREAD; the tip still has to clear it with a board PCB_T_TOL thick.
    tip = P.HEAD_DEPTH + P.COVER_SCREW_L
    nut_bottom = P.Z_ROOF_BOTTOM + P.ROOF_T
    nut_top = nut_bottom + P.NUT[1]
    rows.append({"stack": f"nylon M2 x {P.COVER_SCREW_L:g} from below, through the PCB and the cover's post, "
                          "into a nylon nut on the roof",
                 "nut_thread_mm": round(min(tip, nut_top) - nut_bottom, 2),
                 "tip_above_nut_mm": round(tip - nut_top, 2),
                 "tip_above_nut_thick_board_mm": round(tip - nut_top - P.PCB_T_TOL, 2),
                 "head_above_underside_mm": round(P.HEAD_DEPTH - P.NYLON_HEAD_H, 2),
                 "ok": tip - P.PCB_T_TOL >= nut_top and P.HEAD_DEPTH - P.NYLON_HEAD_H >= 0})
    return rows


def lip_rows(board: Board):
    """The lips over the board's outer edge: their underside on a layer boundary and clear of
    a board PCB_T_TOL too thick; how far a board can tilt in under them, pushed against the
    outer wall (about its bottom edge on the standoffs); and how far they stay over its edge
    with the board's play in its case (play.Play) and JLC's +-0.2 mm outline."""
    from .play import Play  # scipy: only when checking

    z0 = P.Z_PCB_TOP + P.LIP_PLAY
    layers = z0 / P.LAYER_H
    over_thick = z0 - (P.Z_PCB_TOP + P.PCB_T_TOL)
    room, reach = P.PCB_T + P.LIP_PLAY, P.FIT + P.LIP_OVER

    def tilt(t):
        """The largest angle (degrees) with t cos(a) + reach sin(a) <= room."""
        r = math.hypot(t, reach)
        if room >= r:
            return 90.0
        return round(math.degrees(math.atan2(reach, t) - math.acos(room / r)), 1) if room >= t else 0.0

    rows = [{"stack": "lips over the board's outer edge", "underside_mm": round(z0, 2),
             "on_layer_boundary": abs(layers - round(layers)) < 1e-6, "clear_of_thick_board_mm": round(over_thick, 2),
             "tilt_deg": {"nominal board": tilt(P.PCB_T), "thick board": tilt(P.PCB_T + P.PCB_T_TOL)},
             "ok": abs(layers - round(layers)) < 1e-6 and over_thick >= 0 and tilt(P.PCB_T) >= P.MIN_LIP_TILT}]
    in_case = Play(board.outline(), P.BOARD_WALL_PLAY,
                   pins=[(xy((h["x"], h["y"])), P.BOARD_SCREW_PLAY) for h in cover_holes(board)])
    a, b, n = outer_edge(board)
    along = (b - a).normalized()
    outline_tol = 0.2
    for i in range(P.LIP_COUNT):
        c = a + (b - a) * ((i + 0.5) / P.LIP_COUNT)
        ends = [c + along * s * P.LIP_LEN / 2 for s in (-1, 1)]
        play = max(in_case.reach((q.X, q.Y), (-n.X, -n.Y)) for q in ends)
        rss = P.LIP_OVER - math.hypot(play, outline_tol)
        worst = P.LIP_OVER - play - outline_tol
        rows.append({"stack": f"lip {i + 1} holds the board's edge", "over_mm": P.LIP_OVER,
                     "board_play_inward_mm": round(play, 2), "outline_tol_mm": outline_tol,
                     "holds_rss_mm": round(rss, 2), "holds_worst_case_mm": round(worst, 2),
                     "ok": rss >= P.MIN_LIP_HOLD and worst > 0})
    return rows


def antenna_metal(board: Board):
    """Metal hardware (steel screws and washers, brass inserts, the steel washers for the dock's
    magnets) must stay out of the antenna keep-out (CLAUDE.md rule 6)."""
    keepout = polygon_face(board["rule_areas"]["ANTENNA_KEEPOUT"])
    metal = [(f"{ref} screw, washer and insert", x, y, P.WASHER[0]) for ref, x, y in pcb_screws(board)]
    metal += [(f"{m['ref']} steel washer", *xy((m["x"], m["y"])), P.DISC_D) for m in board["steel_discs"]]
    rows = []
    for name, x, y, d in metal:
        gap = keepout.distance_to(Vector(x, y, 0)) - d / 2
        rows.append({"metal": name, "gap_to_antenna_keepout_mm": round(gap, 2), "ok": gap > 0})
    return rows
