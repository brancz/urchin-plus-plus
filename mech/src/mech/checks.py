"""Fit checks between the printed parts and the real board (kicad-cli's STEP export of the
routed half, with every 3D model), plus what the STEP lacks: the hotswap sockets, the
battery, the switches and the keycaps, modelled from the board data. Also the hardware: the
screws as solids, their thread engagement and the plastic round them, no metal in the antenna
keep-out, the printed pins, the largest cell against the board and the lid, and the lips over
the board's outer edge."""

import math

from build123d import Align, Box, Circle, Kind, Pos, Rectangle, Vector, import_step, offset

from . import params as P
from .board import Board, polygon_face, rect_face, rotated_rect_face, xy
from .case import (battery_cavity, board_pins, box, cell_box, cyl, lid_region, openings, outer_edge, pilot_top,
                   pin_holes, prism, screw_holes)

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
    parts.append(("battery", prism(rect_face(cell_box(board)), P.Z_PCB_TOP, P.Z_PCB_TOP + P.FOAM_T + P.CELL[2])))
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
    """Each Choc switch above the PCB: the housing below the flange, the clips under the plate,
    the flange on the plate, the housing above it."""
    out = []
    for k in board["keys"]:
        def sq(w, h=None):
            return rotated_rect_face(k["x"], k["y"], w, h or w, k["rot"])
        z = P.Z_PCB_TOP
        flange_w, flange_t = P.SWITCH_FLANGE
        clips_w, clips_h = P.SWITCH_CLIPS
        body = (prism(sq(P.SWITCH_HOUSING), z, z + 2.2) + prism(sq(P.SWITCH_HOUSING, clips_w), z, z + clips_h)
                + prism(sq(flange_w), z + 2.2, z + 2.2 + flange_t)
                + prism(sq(P.SWITCH_HOUSING), z + 2.2 + flange_t - 0.01, z + P.SWITCH_BODY_H))
        out.append((f"{k['ref']} switch", body))
    return out


def keycaps(board: Board, grow=0.0):
    """Each keycap, from its lowest point pressed to its top at rest; grown by `grow` to stand
    for the shell's play against it."""
    return [(f"{k['ref']} keycap", prism(f, P.Z_PCB_TOP + P.KEYCAP_LOW, P.Z_PCB_TOP + P.KEYCAP_TOP))
            for k, f in zip(board["keys"], board.keycaps(grow))]


def fit(part_name, part, others, touching=()):
    """Interference volume and minimum gap of a printed part against each board part.
    `touching` names parts the printed part is meant to touch (the PCB on its standoffs and
    under the shell, the switches in the shell's plate)."""
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


def hardware(board: Board):
    """[(name, shape)] of the screws: each shell screw from its head in the case's underside to
    its tip in the shell (its shank at the thread's root, where it cuts into the pilot hole), and
    the tenting puck's screw heads on the PCB."""
    out = []
    head_d, head_h = P.SHELL_SCREW_HEAD
    for h in screw_holes(board):
        x, y = xy((h["x"], h["y"]))
        out.append((f"{h['ref']} M2 x {P.SHELL_SCREW_L:g} screw",
                    cyl(x, y, head_d, P.HEAD_DEPTH - head_h, P.HEAD_DEPTH)
                    + cyl(x, y, P.PILOT_D - 0.1, P.HEAD_DEPTH - 0.01, P.HEAD_DEPTH + P.SHELL_SCREW_L)))
    for i, ph in enumerate(board["puck"]["holes"]):
        out.append((f"tenting puck screw head {i + 1}",
                    cyl(*xy((ph["x"], ph["y"])), P.PUCK_HEAD[0], P.Z_PCB_TOP, P.Z_PCB_TOP + P.PUCK_HEAD[1])))
    return out


def boss_wall(part, x, y, z, bore_d):
    """The least plastic round a vertical hole at height z: the distance from its axis to the
    nearest space outside the part, less its radius (looked for within 6 mm)."""
    cut = part & box(x - 6, x + 6, y - 6, y + 6, z - 0.005, z + 0.005)
    tops = [Pos(0, 0, -f.center().Z) * f for f in (cut.faces() if cut is not None else [])
            if abs(f.center().Z - (z + 0.005)) < 1e-4]
    solid = Pos(x, y) * Circle(bore_d / 2 + 0.01)
    for f in tops:
        solid = solid + f
    space = Pos(x, y) * Rectangle(12, 12) - solid
    if space is None or space.area < 1e-6:
        return 6.0 - bore_d / 2
    return space.distance_to(Vector(x, y, 0)) - bore_d / 2


def screw_stacks(board: Board, shell_part):
    """Thread engagement and clearances of the shell screws, the plastic round their pilot
    holes, and the printed pins' reach into the shell, from the stack's heights. The shell sits
    on the PCB: a thick board lifts it, a thin one lowers it."""
    rows = []
    holes = screw_holes(board)
    tip = P.HEAD_DEPTH + P.SHELL_SCREW_L
    engaged_thick = tip - (P.Z_PCB_TOP + P.PCB_T_TOL)
    to_bottom_thin = pilot_top() - P.PCB_T_TOL - tip
    head_in = P.HEAD_DEPTH - P.SHELL_SCREW_HEAD[1]
    rows.append({"stack": f"M2 x {P.SHELL_SCREW_L:g} from below, through the PCB into the shell "
                          f"({', '.join(h['ref'] for h in holes)})",
                 "thread_thick_board_mm": round(engaged_thick, 2), "tip_to_hole_bottom_thin_board_mm": round(to_bottom_thin, 2),
                 "head_above_underside_mm": round(head_in, 2),
                 "ok": engaged_thick >= P.MIN_THREAD and to_bottom_thin >= P.MIN_TIP_GAP and head_in >= 0})
    for h in holes:
        x, y = xy((h["x"], h["y"]))
        walls = [boss_wall(shell_part, x, y, z, P.PILOT_D)
                 for z in (P.Z_PCB_TOP + 0.3, (P.Z_PCB_TOP + tip) / 2, tip - 0.3)]
        rows.append({"stack": f"{h['ref']}: the shell's plastic round the pilot hole", "wall_mm": round(min(walls), 2),
                     "min_mm": P.MIN_BOSS_WALL, "ok": min(walls) >= P.MIN_BOSS_WALL})
    pins = pin_holes(board)
    if pins:
        top = P.Z_PCB_TOP + P.PIN_INTO_SHELL
        engaged_thick = top - (P.Z_PCB_TOP + P.PCB_T_TOL)
        room_thin = P.PIN_BORE_ROOM - P.PCB_T_TOL
        rows.append({"stack": f"printed pins up through the PCB into the shell ({', '.join(h['ref'] for h in pins)})",
                     "into_shell_thick_board_mm": round(engaged_thick, 2), "tip_room_thin_board_mm": round(room_thin, 2),
                     "ok": engaged_thick >= P.MIN_PIN_ENGAGE and room_thin >= 0.1})
    return rows


def lid_rows(board: Board):
    """The battery's cavity stays LID_WALL_MIN inside the lid (on the keys' side; the outer
    wall is the shell's own), and holds the largest cell."""
    lid = lid_region(board)
    cavity = battery_cavity(board)
    breach = offset(cavity, P.LID_WALL_MIN - 0.005, kind=Kind.ARC) - lid
    area = breach.area if breach is not None else 0.0
    return [{"stack": "the lid's wall round the battery's cavity", "min_mm": P.LID_WALL_MIN,
             "thinner_mm2": round(area, 4), "ok": area <= 1e-3}]


def usb_rows(board: Board, parts):
    """The shell's window over the USB-C plug assumes the receptacle's axis at P.USB_AXIS."""
    j1 = [s for n, s in parts if n.startswith(board["usb"]["ref"] + " ")]
    if not j1:
        return [{"stack": "USB-C receptacle's axis", "ok": False, "error": "no 3D model"}]
    bb = j1[0].bounding_box()
    axis = (bb.min.Z + bb.max.Z) / 2
    return [{"stack": "USB-C receptacle's axis", "model_mm": round(axis, 2), "assumed_mm": round(P.USB_AXIS, 2),
             "ok": abs(axis - P.USB_AXIS) <= 0.05}]


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
    in_case = Play(board.outline(), P.BOARD_WALL_PLAY, pins=board_pins(board))
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
    """Metal hardware (the steel shell screws, the tenting puck's screws, the steel washers for
    the dock's magnets) must stay out of the antenna keep-out (CLAUDE.md rule 6)."""
    keepout = polygon_face(board["rule_areas"]["ANTENNA_KEEPOUT"])
    metal = [(f"{h['ref']} shell screw", *xy((h["x"], h["y"])), P.SHELL_SCREW_HEAD[0]) for h in screw_holes(board)]
    metal += [(f"tenting puck screw {i + 1}", *xy((ph["x"], ph["y"])), P.PUCK_HEAD[0])
              for i, ph in enumerate(board["puck"]["holes"])]
    metal += [(f"{m['ref']} steel washer", *xy((m["x"], m["y"])), P.DISC_D) for m in board["steel_discs"]]
    rows = []
    for name, x, y, d in metal:
        gap = keepout.distance_to(Vector(x, y, 0)) - d / 2
        rows.append({"metal": name, "gap_to_antenna_keepout_mm": round(gap, 2), "ok": gap > 0})
    return rows
