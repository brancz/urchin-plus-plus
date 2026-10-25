"""The pogo pins soldered on each half's charging pads (TP1), and the jig that holds them upright
while they're soldered (docs/ARCHITECTURE.md, Dock).

Both in the case's frame: the pins hang below the PCB, plunger down, out through the case's
window; the jig sits under the PCB as it would on the board's bottom, which faces up on the
bench."""

import math

from build123d import Axis, Circle, Pos, Rectangle, Vector, chamfer

from . import params as P
from .board import Board, xy
from .case import cyl, prism, union


def pad_centres(board: Board):
    """[(x, y)] of the half's charging pads, pad 1 first."""
    return [xy((p["x"], p["y"])) for p in board["dock_pads"]["pads"]]


def pin(x, y, tip_z):
    """A pin soldered on the pad at (x, y): the flange under the pad's solder, the barrel below
    it, and the plunger down to tip_z."""
    z = P.Z_PCB_BOTTOM - P.PIN_SOLDER
    return (cyl(x, y, P.PIN_FLANGE[0], z - P.PIN_FLANGE[1], z) + cyl(x, y, P.PIN_BARREL[0], z - P.PIN_BARREL[1], z)
            + cyl(x, y, P.PIN_TIP_D, tip_z, z - P.PIN_BARREL[1]))


def free_tip_z():
    """The free tips' height (case frame): below the case's underside, at z = 0."""
    return P.Z_PCB_BOTTOM - P.PIN_SOLDER - P.PIN_FREE


def pins(board: Board, tip_z=None):
    """[(name, shape)] of the half's three pins, free unless tip_z puts their tips elsewhere."""
    z = free_tip_z() if tip_z is None else tip_z
    return [(f"{board.side} pin on pad {i + 1}", pin(x, y, z)) for i, (x, y) in enumerate(pad_centres(board))]


def jig_holes(board: Board):
    """The board holes the jig's pegs go into: the nearest one either side of the pads (along
    the pad row), as (x, y, d) in the CAD frame."""
    pads = pad_centres(board)
    cx, cy = sum(x for x, _ in pads) / len(pads), sum(y for _, y in pads) / len(pads)
    holes = [(*xy((h["x"], h["y"])), h["d"]) for h in board["case_holes"]]
    out = []
    for side in (-1, 1):
        cands = [h for h in holes if (h[0] - cx) * side > 0]
        out.append(min(cands, key=lambda h: math.hypot(h[0] - cx, h[1] - cy)))
    return out


def jig_feet(board: Board):
    """[(x, y)] of the jig's two feet: either side of the pins' centre along their row
    (JIG_FOOT_ALONG), out from it away from the line between the legs (JIG_FOOT_OUT)."""
    pads = pad_centres(board)
    c = Vector(sum(x for x, _ in pads) / len(pads), sum(y for _, y in pads) / len(pads))
    along = (Vector(*pads[-1]) - Vector(*pads[0])).normalized()
    n = Vector(-along.Y, along.X)
    (ax, ay, _), (bx, by, _) = jig_holes(board)
    if (c - Vector((ax + bx) / 2, (ay + by) / 2)).dot(n) < 0:
        n = -n
    return [((c + along * s * P.JIG_FOOT_ALONG + n * P.JIG_FOOT_OUT).X, (c + along * s * P.JIG_FOOT_ALONG + n * P.JIG_FOOT_OUT).Y)
            for s in (-1, 1)]


def bar(a, b, w):
    """A flat bar w wide from a to b, round at both ends."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    r = Pos((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) * Rectangle(math.hypot(dx, dy), w).rotate(Axis.Z, math.degrees(math.atan2(dy, dx)))
    return r + Pos(*a) * Circle(w / 2) + Pos(*b) * Circle(w / 2)


def jig_bore():
    return P.PIN_TIP_D + P.JIG_BORE_CLEAR


def jig_plate(board: Board):
    """The jig's plate seen from above: a collar round each bore, a narrow strip joining them
    along the row (inside the flanges, so the pads' ends stay in view), and from the strip's ends,
    past the end pins, an arm to each leg and foot."""
    pads = pad_centres(board)
    along = (Vector(*pads[-1]) - Vector(*pads[0])).normalized()
    ends = [Vector(*pads[0]) - along * P.JIG_STRIP_END, Vector(*pads[-1]) + along * P.JIG_STRIP_END]
    shapes = [bar((ends[0].X, ends[0].Y), (ends[1].X, ends[1].Y), P.JIG_STRIP)]
    shapes += [Pos(x, y) * Circle(jig_bore() / 2 + P.JIG_COLLAR) for x, y in pads]
    for x, y in [(h[0], h[1]) for h in jig_holes(board)] + jig_feet(board):
        e = min(ends, key=lambda v: math.hypot(v.X - x, v.Y - y))
        shapes.append(bar((e.X, e.Y), (x, y), P.JIG_BAR_W))
    return union(shapes)


def jig_z():
    """(bottom, top) of the jig's plate (case frame: its top faces the PCB)."""
    z1 = P.Z_PCB_BOTTOM - P.JIG_GAP
    return z1 - P.JIG_PLATE_T, z1


def jig(board: Board):
    """The soldering jig, in the case frame (below the PCB)."""
    pads = pad_centres(board)
    z0, z1 = jig_z()
    part = prism(jig_plate(board), z0, z1)
    for x, y, d in jig_holes(board):
        part += cyl(x, y, P.JIG_LEG_D, z1 - 0.01, P.Z_PCB_BOTTOM)
        part += cyl(x, y, d - P.JIG_PEG_CLEAR, P.Z_PCB_BOTTOM - 0.01, P.Z_PCB_BOTTOM + P.JIG_PEG_LEN)
    for f in jig_feet(board):
        part += cyl(*f, P.JIG_FOOT_D, z1 - 0.01, P.Z_PCB_BOTTOM)
    bore = jig_bore()
    for x, y in pads:
        cut = cyl(x, y, bore, z0 - 1, z1 + 1)
        lead = prism(Pos(x, y) * Circle(bore / 2 + P.JIG_LEAD), z1 - P.JIG_LEAD, z1 + 1)
        part -= cut + chamfer(lead.faces().sort_by(Axis.Z)[0].edges(), P.JIG_LEAD - 0.01)
    return part
