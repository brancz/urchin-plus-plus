"""The printed tray case for one half, and the shell over it (docs/ARCHITECTURE.md, Case).
Built from the half's own data, so the left and right parts are generated separately, never
mirrored."""

import math

from build123d import (Align, Axis, Box, Circle, Cone, Cylinder, Face, Kind, Pos, RectangleRounded,
                       Vector, Wire, chamfer, extrude, offset)

from . import params as P
from .board import Board, polygon_face, rect_face, rotated_rect_face, xy


def prism(face, z0, z1):
    """A face in the XY plane extruded from z0 to z1."""
    return extrude(Pos(0, 0, z0) * face, z1 - z0, dir=(0, 0, 1))


def cyl(x, y, d, z0, z1):
    return Pos(x, y, z0) * Cylinder(d / 2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def box(x0, x1, y0, y1, z0, z1):
    return Pos(min(x0, x1), min(y0, y1), z0) * Box(abs(x1 - x0), abs(y1 - y0), z1 - z0, align=Align.MIN)


def union(faces):
    out = faces[0]
    for f in faces[1:]:
        out = out + f
    return out


def piece_containing(shape, x, y):
    """The face of a 2D result that contains (x, y) in the CAD frame."""
    for f in shape.faces():
        if f.is_inside(Vector(x, y, 0)):
            return f
    raise SystemExit(f"mech: no face contains ({x:.2f}, {y:.2f})")


def inner_edge_x(board):
    """x of the board's inner edge (USB-C side) in the CAD frame."""
    x0, _, x1, _ = board.bbox
    return x1 if board.inner_dir > 0 else x0


def usb_rect(board):
    """(x0, x1, y0, y1) of the USB-C notch through the inner wall."""
    u = board["usb"]
    _, yc = xy((u["x"], (u["courtyard"][1] + u["courtyard"][3]) / 2))
    d, edge = board.inner_dir, inner_edge_x(board)
    return (edge - d * 0.5, edge + d * (P.FIT + P.WALL + 2), yc - P.USB_OPENING_W / 2, yc + P.USB_OPENING_W / 2)


def usb_opening(board, z0, z1):
    return box(*usb_rect(board), z0, z1)


def switch_rect(board):
    """(x0, x1, y0, y1) of the slot through the inner wall at the power switch."""
    s = board["power_switch"]
    _, sy0 = xy((0, s["courtyard"][3]))
    _, sy1 = xy((0, s["courtyard"][1]))
    d, edge = board.inner_dir, inner_edge_x(board)
    return (edge - d * 1.0, edge + d * (P.FIT + P.WALL + 1), sy0 - P.SWITCH_SLOT_MARGIN, sy1 + P.SWITCH_SLOT_MARGIN)


def openings(board):
    """The full-height openings in the wall, as faces: whatever sticks out of the board's
    outline must drop through one of them when the board goes in."""
    return [box(*r, 0, 1).faces().sort_by(Axis.Z)[0] for r in (usb_rect(board), switch_rect(board))]


def standoff_face(board, x, y, keepout):
    """The standoff's footprint: a BOSS_D circle, cut back around nearby bottom parts."""
    boss = Pos(x, y) * Circle(P.BOSS_D / 2)
    return piece_containing(boss - keepout, x, y)


def in_keepout(board, hole):
    keepout = polygon_face(board["rule_areas"]["ANTENNA_KEEPOUT"])
    return keepout.distance_to(Vector(*xy((hole["x"], hole["y"])), 0)) < P.SHELL_SCREW_HEAD[0] / 2


def keycap_distance(board, hole):
    v = Vector(*xy((hole["x"], hole["y"])), 0)
    return min(f.distance_to(v) for f in board.keycaps(0.0))


def screw_holes(board):
    """The holes that take a screw from below into the shell: outside the antenna keep-out,
    with room round them."""
    return [h for h in board["case_holes"]
            if not in_keepout(board, h) and keycap_distance(board, h) >= P.SHELL_SCREW_MIN_KEYCAP]


def pin_holes(board):
    """The holes inside the antenna keep-out: a printed pin on the standoff, no hardware."""
    return [h for h in board["case_holes"] if in_keepout(board, h)]


def controller_holes(board):
    """The 2.2 mm case holes around the controller: the shell's lid has a post at each."""
    return [h for h in board["case_holes"] if h["d"] <= P.SCREW_CLEAR_D]


def board_pins(board):
    """[((x, y), play)]: what holds the PCB in place in the case besides its walls, and how far
    it lets the PCB move (play.Play)."""
    out = []
    for h in screw_holes(board):
        out.append((xy((h["x"], h["y"])), P.BOARD_SCREW_PLAY + (h["d"] - 2.2) / 2))
    for h in pin_holes(board):
        out.append((xy((h["x"], h["y"])), P.BOARD_PIN_PLAY))
    return out


def outer_edge(board):
    """The longest straight run of the outline facing away from the controller:
    (start, end, outward normal), in the CAD frame."""
    pts = [Vector(*xy(p)) for p in board["outline"]]
    area = sum(a.X * b.Y - b.X * a.Y for a, b in zip(pts, pts[1:] + pts[:1])) / 2
    runs = []
    for a, b in zip(pts, pts[1:] + pts[:1]):
        d = (b - a).normalized()
        n = Vector(d.Y, -d.X) if area > 0 else Vector(-d.Y, d.X)
        if runs and (runs[-1][1] - runs[-1][0]).normalized().dot(d) > math.cos(math.radians(0.5)):
            runs[-1] = (runs[-1][0], b, n)
        else:
            runs.append((a, b, n))
    outward = [r for r in runs if r[2].X * -board.inner_dir > 0.95]
    best = max(outward, key=lambda r: (r[1] - r[0]).length)
    if (best[1] - best[0]).length < P.LIP_MIN_EDGE:
        raise SystemExit(f"mech: {board.side}: the longest straight outer edge is {(best[1] - best[0]).length:.1f} mm")
    return best


def lip_faces(board, inner, outer, grow=0.0):
    """Each lip's footprint, from `inner` inside the PCB's outer edge to `outer` beyond it,
    LIP_LEN long, all grown by `grow`."""
    a, b, n = outer_edge(board)
    along = (b - a).normalized()
    out = []
    for i in range(P.LIP_COUNT):
        c = a + (b - a) * ((i + 0.5) / P.LIP_COUNT)
        corners = [c + along * s * (P.LIP_LEN / 2 + grow) + n * t
                   for s, t in ((-1, -inner - grow), (1, -inner - grow), (1, outer + grow), (-1, outer + grow))]
        out.append(Face(Wire.make_polygon(corners, close=True)))
    return out


def lips(board):
    """Lips over the PCB's outer edge: each reaches LIP_OVER over the board, LIP_PLAY above it,
    and stands on the wall's inner part."""
    z0 = P.Z_PCB_TOP + P.LIP_PLAY
    out = None
    for lip, foot in zip(lip_faces(board, P.LIP_OVER, P.FIT + P.LIP_ANCHOR),
                         lip_faces(board, -P.FIT, P.FIT + P.LIP_ANCHOR)):
        part = prism(lip, z0, z0 + P.LIP_T) + prism(foot, P.Z_WALL_TOP - 0.01, z0 + 0.01)
        out = part if out is None else out + part
    return out


def pin(x, y):
    """A printed pin on a standoff, up through the PCB's hole into the shell's post."""
    top = P.Z_PCB_TOP + P.PIN_INTO_SHELL
    c = P.PIN_CHAMFER
    return (cyl(x, y, P.PIN_D, P.Z_PCB_BOTTOM - 0.01, top - c)
            + Pos(x, y, top - c) * Cone(P.PIN_D / 2, P.PIN_D / 2 - c, c, align=(Align.CENTER, Align.CENTER, Align.MIN)))


def case(board: Board):
    outline = board.outline()
    inner = offset(outline, P.FIT, kind=Kind.ARC)
    outer = offset(outline, P.FIT + P.WALL, kind=Kind.ARC)
    shell = prism(outer, 0, P.Z_WALL_TOP)
    shell = chamfer(shell.faces().sort_by(Axis.Z)[-1].edges(), P.EDGE_TOP)
    shell = chamfer(shell.faces().sort_by(Axis.Z)[0].edges(), P.EDGE_BOTTOM)
    part = shell - prism(inner, P.FLOOR, P.Z_WALL_TOP + 1)

    pk = board["puck"]
    px, py = xy((pk["x"], pk["y"]))
    puck = Pos(px, py) * Circle(pk["radius"] + P.PUCK_CLEAR)
    keepout = union([offset(f, P.PART_CLEAR, kind=Kind.ARC) for f in board.bottom_keepouts()] + [puck])
    screws = [h["ref"] for h in screw_holes(board)]
    pins = [h["ref"] for h in pin_holes(board)]
    for h in board["case_holes"]:
        x, y = xy((h["x"], h["y"]))
        if puck.is_inside(Vector(x, y, 0)) or (Pos(x, y) * Circle(P.BOSS_D / 2) & puck).area > 0:
            # The tenting puck covers this hole's surroundings: no standoff (the puck's own
            # three screws hold the PCB there).
            continue
        part += prism(standoff_face(board, x, y, keepout), P.FLOOR - 0.01, P.Z_PCB_BOTTOM)
        if h["ref"] in screws:
            # A screw from the underside, up through the PCB into the shell.
            part -= cyl(x, y, P.SCREW_CLEAR_D, -0.1, P.Z_PCB_BOTTOM + 0.1)
            part -= cyl(x, y, P.HEAD_D, -0.1, P.HEAD_DEPTH)
        elif h["ref"] in pins:
            part += pin(x, y)

    part += lips(board)

    # USB-C: a notch through the wall, the full height of the plug's overmold.
    part -= usb_opening(board, -0.1, P.Z_WALL_TOP + 0.1)

    # Power switch: a slot in the wall around the side-actuated switch, up to the wall's top
    # (its actuator reaches past the board's edge, so the board can only go in through it),
    # and a finger scoop below it.
    x0, x1, sy0, sy1 = switch_rect(board)
    d, edge = board.inner_dir, inner_edge_x(board)
    z0 = P.Z_PCB_BOTTOM - P.SWITCH_H - 1.0
    part -= box(x0, x1, sy0, sy1, z0, P.Z_WALL_TOP + 0.1)
    outer_face_x = edge + d * (P.FIT + P.WALL)
    part -= cyl(outer_face_x + d * (P.SWITCH_SCOOP_R - P.SWITCH_SCOOP_DEPTH), (sy0 + sy1) / 2,
                2 * P.SWITCH_SCOOP_R, z0 - 1.0, P.Z_WALL_TOP + 0.1)

    # Floor openings: reset button, charging pads, tenting puck.
    rx, ry = xy((board["reset"]["x"], board["reset"]["y"]))
    part -= cyl(rx, ry, P.RESET_HOLE_D, -0.1, P.FLOOR + 0.1)
    part -= prism(dock_window(board), -0.1, P.FLOOR + 0.1)
    part -= cyl(px, py, 2 * (pk["radius"] + P.PUCK_CLEAR), -0.1, P.FLOOR + 0.1)

    # Underside: recesses for the steel washers the dock's magnets pull on, seats for the
    # rubber feet.
    for m in board["steel_discs"]:
        part -= cyl(*xy((m["x"], m["y"])), P.DISC_D + 0.3, -0.1, P.DISC_T)
    for m in board["feet"]:
        part -= cyl(*xy((m["x"], m["y"])), m["d"] + P.FOOT_SEAT, -0.1, P.FOOT_RECESS)
    return part


def dock_window(board):
    pads = board["dock_pads"]["pads"]
    x0 = min(p["x"] - p["w"] / 2 for p in pads) - P.DOCK_WINDOW_MARGIN
    x1 = max(p["x"] + p["w"] / 2 for p in pads) + P.DOCK_WINDOW_MARGIN
    y0 = min(p["y"] - p["h"] / 2 for p in pads) - P.DOCK_WINDOW_MARGIN
    y1 = max(p["y"] + p["h"] / 2 for p in pads) + P.DOCK_WINDOW_MARGIN
    cx, cy = xy(((x0 + x1) / 2, (y0 + y1) / 2))
    return Pos(cx, cy) * RectangleRounded(x1 - x0, y1 - y0, 1.0)


def lid_region(board):
    """The lid's outline: the case's outer outline over the controller area, LID_MARGIN away
    from every keycap."""
    outer = offset(board.outline(), P.FIT + P.WALL, kind=Kind.ARC)
    holes = [xy((h["x"], h["y"])) for h in controller_holes(board)]
    d = board.inner_dir
    x_from = (min(x for x, _ in holes) - 4) if d > 0 else (max(x for x, _ in holes) + 4)
    y0 = min(y for _, y in holes) - P.LID_BEYOND_HOLES
    y1 = max(y for _, y in holes) + P.LID_BEYOND_HOLES
    zone = box(x_from, x_from + d * 200, y0, y1, 0, 1).faces().sort_by(Axis.Z)[0]
    region = outer & zone
    region -= union(board.keycaps(P.LID_MARGIN))
    bx, by = xy((board["battery"]["x"], board["battery"]["y"]))
    return piece_containing(region, bx, by)


def cell_box(board):
    """(x0, y0, x1, y1), KiCad frame, of the largest cell (P.CELL) where mech/README.md puts it:
    centred on the battery's outline (BT2), its antenna-side end on the outline's end, its extra
    length toward the wire pads (BT1)."""
    x0, y0, x1, y1 = board["battery"]["outline"]
    w, length, _ = P.CELL
    cx = (x0 + x1) / 2
    if board["battery_pads"]["y"] > (y0 + y1) / 2:
        return (cx - w / 2, y0, cx + w / 2, y0 + length)
    return (cx - w / 2, y1 - length, cx + w / 2, y1)


def battery_cavity(board):
    """Under the lid: the lid's inside less LID_WALL, and round the largest cell CELL_CLEAR,
    where the lid is thinner."""
    inside = offset(lid_region(board) & offset(board.outline(), P.FIT, kind=Kind.ARC), -P.LID_WALL, kind=Kind.ARC)
    bx, by = xy((board["battery"]["x"], board["battery"]["y"]))
    return piece_containing(inside + rect_face(cell_box(board), P.CELL_CLEAR), bx, by)


def wells(board):
    """Round the keys down to the plate: the keycaps grown by KEYCAP_MARGIN (round corners),
    inside the walls, less the lid. Any strip of rim left between them narrower than RIM_MIN goes too."""
    inner = offset(board.outline(), P.FIT, kind=Kind.ARC)
    caps = union(board.keycaps(0.0))
    rim = inner - offset(caps, P.KEYCAP_MARGIN, kind=Kind.ARC)
    # An opening of the rim: shrink it by r (the outline in by r, the keycaps out by r), grow
    # what's left back by r.
    r = P.RIM_MIN / 2
    core = offset(board.outline(), P.FIT - r, kind=Kind.ARC) - offset(caps, P.KEYCAP_MARGIN + r, kind=Kind.ARC)
    # The rim round a screw's pilot hole stays, whatever its shape.
    keep = core.faces() + [Pos(*xy((h["x"], h["y"]))) * Circle(P.SHELL_SCREW_MIN_KEYCAP + 0.5)
                           for h in screw_holes(board)]
    out = inner
    for f in (union([offset(f, r, kind=Kind.ARC) for f in keep]) & rim).faces():
        out -= f
    return out - lid_region(board)


def pilot_top():
    """Where a shell screw's pilot hole ends."""
    return P.HEAD_DEPTH + P.SHELL_SCREW_L + P.SCREW_TIP_ROOM


def shell(board: Board):
    z0 = P.Z_PCB_TOP
    outline = board.outline()
    outer = offset(outline, P.FIT + P.WALL, kind=Kind.ARC)
    lid = lid_region(board)

    # The outside: the case's walls carried up to the rim, the lid above it.
    body = prism(outer, z0, P.Z_RIM)
    body = chamfer(body.faces().sort_by(Axis.Z)[-1].edges(), P.SHELL_EDGE)
    body = chamfer(body.faces().sort_by(Axis.Z)[0].edges(), P.SHELL_EDGE)
    top = prism(lid, P.Z_RIM - 1.0, P.Z_LID_TOP)
    part = body + chamfer(top.faces().sort_by(Axis.Z)[-1].edges(), P.SHELL_EDGE)

    # The keys: a well round each down to the plate, a cutout in the plate for the switch, and
    # room below the plate for its clips.
    part -= prism(wells(board), P.Z_PLATE_TOP, P.Z_LID_TOP + 1)
    for k in board["keys"]:
        part -= prism(rotated_rect_face(k["x"], k["y"], P.PLATE_CUTOUT, P.PLATE_CUTOUT, k["rot"]),
                      z0 - 0.1, P.Z_PLATE_TOP + 0.1)
        part -= prism(rotated_rect_face(k["x"], k["y"], P.CLIP_RELIEF, P.CLIP_RELIEF, k["rot"]),
                      z0 - 0.1, P.Z_PLATE_BOTTOM)

    # The battery under the lid, and the posts round the controller holes.
    part -= prism(battery_cavity(board), z0 - 0.1, P.Z_ROOF_BOTTOM)
    for h in controller_holes(board):
        x, y = xy((h["x"], h["y"]))
        part += prism(Pos(x, y) * Circle(P.POST_D / 2) & lid, z0, P.Z_ROOF_BOTTOM + 0.01)
    for h in pin_holes(board):
        x, y = xy((h["x"], h["y"]))
        top = z0 + P.PIN_INTO_SHELL + P.PIN_BORE_ROOM
        part -= cyl(x, y, P.PIN_BORE_D, z0 - 0.1, top)
        c = P.PIN_CHAMFER
        part -= Pos(x, y, z0 - 0.01) * Cone(P.PIN_BORE_D / 2 + c + 0.01, P.PIN_BORE_D / 2, c + 0.01,
                                            align=(Align.CENTER, Align.CENTER, Align.MIN))
    for h in screw_holes(board):
        part -= cyl(*xy((h["x"], h["y"])), P.PILOT_D, z0 - 0.1, pilot_top())

    # Pockets over the tenting puck's screw heads and round the case's lips.
    pk = board["puck"]
    for ph in pk["holes"]:
        part -= cyl(*xy((ph["x"], ph["y"])), P.PUCK_HEAD[0] + 2 * P.PUCK_HEAD_CLEAR, z0 - 0.1,
                    z0 + P.PUCK_HEAD[1] + P.PUCK_HEAD_CLEAR)
    lip_top = P.Z_PCB_TOP + P.LIP_PLAY + P.LIP_T + P.LIP_CLEAR
    for f in lip_faces(board, P.LIP_OVER, P.FIT + P.LIP_ANCHOR, P.LIP_CLEAR):
        part -= prism(f, z0 - 0.1, lip_top)

    # The inner edge: a window over the USB-C plug, and the power switch's finger scoop carried
    # up the wall.
    part -= usb_opening(board, z0 - 0.1, P.USB_WINDOW_TOP)
    x0, x1, sy0, sy1 = switch_rect(board)
    d, edge = board.inner_dir, inner_edge_x(board)
    outer_face_x = edge + d * (P.FIT + P.WALL)
    part -= cyl(outer_face_x + d * (P.SWITCH_SCOOP_R - P.SWITCH_SCOOP_DEPTH), (sy0 + sy1) / 2,
                2 * P.SWITCH_SCOOP_R, z0 - 0.1, P.Z_LID_TOP + 0.1)

    # Windows over the LEDs.
    cavity = battery_cavity(board)
    for led in board["leds"]:
        for h in led["holes"]:
            x, y = xy((h["x"], h["y"]))
            if cavity.is_inside(Vector(x, y, 0)):
                part -= cyl(x, y, P.LED_WINDOW_D, P.Z_ROOF_BOTTOM - 0.1, P.Z_LID_TOP + 0.1)
    return part
