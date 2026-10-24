"""The printed tray case for one half, and the battery cover over its controller area
(docs/ARCHITECTURE.md, Case). Built from the half's own data, so the left and right parts
are generated separately, never mirrored."""

import math

from build123d import (Align, Axis, Box, Circle, Cylinder, Face, Kind, Pos, RectangleRounded,
                       Vector, Wire, chamfer, extrude, offset)

from . import params as P
from .board import Board, xy


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


def screwed(board, hole):
    """Whether a 3.8 mm hole takes a screw: its washer must clear every keycap."""
    x, y = xy((hole["x"], hole["y"]))
    return all(f.distance_to(Vector(x, y, 0)) >= P.WASHER[0] / 2 + P.PART_CLEAR for f in board.keycaps(0.0))


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


def lips(board):
    """Lips over the PCB's outer edge: each reaches LIP_OVER over the board, LIP_PLAY above it,
    and sits on the wall's top (inside its chamfer)."""
    a, b, n = outer_edge(board)
    along = (b - a).normalized()
    out = None
    for i in range(P.LIP_COUNT):
        c = a + (b - a) * ((i + 0.5) / P.LIP_COUNT)

        def band(inner, outer):
            corners = [c + along * s * P.LIP_LEN / 2 + n * t for s, t in ((-1, inner), (1, inner), (1, outer), (-1, outer))]
            return Face(Wire.make_polygon(corners, close=True))

        z0 = P.Z_PCB_TOP + P.LIP_PLAY
        lip = prism(band(-P.LIP_OVER, P.FIT + P.WALL - P.EDGE_TOP), z0, z0 + P.LIP_T)
        lip += prism(band(P.FIT, P.FIT + P.WALL - P.EDGE_TOP), P.Z_WALL_TOP - 0.01, z0 + 0.01)
        out = lip if out is None else out + lip
    return out


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
    for h in board["case_holes"]:
        x, y = xy((h["x"], h["y"]))
        if puck.is_inside(Vector(x, y, 0)) or (Pos(x, y) * Circle(P.BOSS_D / 2) & puck).area > 0:
            # The tenting puck covers this hole's surroundings: no standoff (the puck's own
            # three screws hold the PCB there).
            continue
        part += prism(standoff_face(board, x, y, keepout), P.FLOOR - 0.01, P.Z_PCB_BOTTOM)
        if h["d"] > P.SCREW_CLEAR_D:
            # 3.8 mm hole: a heat-set insert for a screw and washer from the top where the
            # washer clears the keycaps; elsewhere just support.
            if screwed(board, h):
                part -= cyl(x, y, P.INSERT_D, P.Z_PCB_BOTTOM - P.INSERT_DEPTH, P.Z_PCB_BOTTOM + 0.1)
        else:
            # Battery cover hole: nylon screw from the underside into the cover's standoff.
            part -= cyl(x, y, P.SCREW_CLEAR_D, -0.1, P.Z_PCB_BOTTOM + 0.1)
            part -= cyl(x, y, P.HEAD_D, -0.1, P.HEAD_DEPTH)

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

    # Underside: steel discs flush for the dock magnets, seats for the rubber feet.
    for m in board["steel_discs"]:
        part -= cyl(*xy((m["x"], m["y"])), P.DISC_D + 0.3, -0.1, P.DISC_T)
    for m in board["feet"]:
        part -= cyl(*xy((m["x"], m["y"])), m["d"] + 0.4, -0.1, P.FOOT_RECESS)
    return part


def dock_window(board):
    pads = board["dock_pads"]["pads"]
    x0 = min(p["x"] - p["w"] / 2 for p in pads) - P.DOCK_WINDOW_MARGIN
    x1 = max(p["x"] + p["w"] / 2 for p in pads) + P.DOCK_WINDOW_MARGIN
    y0 = min(p["y"] - p["h"] / 2 for p in pads) - P.DOCK_WINDOW_MARGIN
    y1 = max(p["y"] + p["h"] / 2 for p in pads) + P.DOCK_WINDOW_MARGIN
    cx, cy = xy(((x0 + x1) / 2, (y0 + y1) / 2))
    return Pos(cx, cy) * RectangleRounded(x1 - x0, y1 - y0, 1.0)


def cover_holes(board):
    """The 2.2 mm case holes around the controller, which hold the battery cover."""
    return [h for h in board["case_holes"] if h["d"] <= P.SCREW_CLEAR_D]


def cover_region(board):
    """The cover's outline: the case's outer outline over the controller area, kept
    KEYCAP_MARGIN away from every keycap."""
    outer = offset(board.outline(), P.FIT + P.WALL, kind=Kind.ARC)
    holes = [xy((h["x"], h["y"])) for h in cover_holes(board)]
    d = board.inner_dir
    x_from = (min(x for x, _ in holes) - 4) if d > 0 else (max(x for x, _ in holes) + 4)
    y0 = min(y for _, y in holes) - P.COVER_BEYOND_HOLES
    y1 = max(y for _, y in holes) + P.COVER_BEYOND_HOLES
    zone = box(x_from, x_from + d * 200, y0, y1, 0, 1).faces().sort_by(Axis.Z)[0]
    region = outer & zone
    region -= union(board.keycaps(P.KEYCAP_MARGIN))
    bx, by = xy((board["battery"]["x"], board["battery"]["y"]))
    return piece_containing(region, bx, by)


def cover(board: Board):
    region = cover_region(board)
    part = prism(region, P.Z_ROOF_BOTTOM, P.Z_ROOF_BOTTOM + P.ROOF_T)
    ring = offset(board.outline(), P.FIT + P.WALL, kind=Kind.ARC) - offset(board.outline(), P.FIT, kind=Kind.ARC)
    skirt = region & ring
    part += prism(skirt, P.Z_WALL_TOP, P.Z_ROOF_BOTTOM + 0.01)
    # The skirt continues the case wall upwards, so it needs the same USB-C opening.
    part -= usb_opening(board, P.Z_WALL_TOP - 0.1, P.Z_ROOF_BOTTOM)
    for h in cover_holes(board):
        x, y = xy((h["x"], h["y"]))
        part -= cyl(x, y, P.SCREW_CLEAR_D, P.Z_ROOF_BOTTOM - 0.1, P.Z_ROOF_BOTTOM + P.ROOF_T + 0.1)
        part -= cyl(x, y, P.HEAD_D, P.Z_ROOF_BOTTOM + P.ROOF_T - P.COVER_HEAD_DEPTH, P.Z_ROOF_BOTTOM + P.ROOF_T + 0.1)
    for led in board["leds"]:
        for h in led["holes"]:
            x, y = xy((h["x"], h["y"]))
            if region.is_inside(Vector(x, y, 0)):
                part -= cyl(x, y, P.LED_WINDOW_D, P.Z_ROOF_BOTTOM - 0.1, P.Z_ROOF_BOTTOM + P.ROOF_T + 0.1)
    return part
