"""The charging dock's tray, and the dock PCB's shape and feature positions (docs/ARCHITECTURE.md,
"Dock").

The dock frame is the left half's CAD frame; the right half sits DX to its right, so the two
cases' inner edges are DIVIDER plus two POCKET_CLEARs apart. The pocket floor is at Z_DOCK:
there the cases' undersides rest, and the dock PCB's top lies flush with it in a recess, so
the pogo pins reach each half's pads through the case's window. The tray prints as two
pieces split on the centre line between the pockets.

pcb_geometry() is what the dock board is built from (dock-pcb/geometry.json, via
`mech dock-geometry`): the board follows the tray, never the other way round.
"""

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from build123d import Axis, Circle, Kind, Pos, Rectangle, Vector, chamfer, offset

from . import params as P
from .board import Board, xy
from .case import box, cyl, piece_containing, prism, union

PLACEMENT = Path(__file__).resolve().parents[3] / "dock-pcb" / "placement.json"  # the dock's other parts


def hull(points):
    """Convex hull of 2D points (monotone chain), counter-clockwise."""
    pts = sorted(set(points))

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out

    lower, upper = half(pts), half(reversed(pts))
    return lower[:-1] + upper[:-1]


def poly_face(points):
    """A face from CAD-frame points (no y flip)."""
    from build123d import Face, Wire
    return Face(Wire.make_polygon([Vector(x, y, 0) for x, y in points], close=True))


@dataclass
class Dock:
    left: Board
    right: Board

    @classmethod
    def load(cls):
        return cls(Board.load("left"), Board.load("right"))

    @cached_property
    def dx(self):
        """x offset of the right half in the dock frame."""
        if self.left.inner_dir < 0 or self.right.inner_dir > 0:
            raise SystemExit("mech: dock: expected the left half's inner edge at +x and the right's at -x")
        left_outer = self.left.bbox[2] + P.FIT + P.WALL
        right_outer = self.right.bbox[0] - P.FIT - P.WALL
        return left_outer + 2 * P.POCKET_CLEAR + P.DIVIDER - right_outer

    def halves(self):
        """[(board, x offset)]"""
        return [(self.left, 0.0), (self.right, self.dx)]

    def at(self, board, dx, p):
        """A KiCad point of a half in the dock frame."""
        x, y = xy(p)
        return (x + dx, y)

    @cached_property
    def x_c(self):
        """The centre line between the pockets, where the tray splits."""
        return self.left.bbox[2] + P.FIT + P.WALL + P.POCKET_CLEAR + P.DIVIDER / 2

    def case_outline(self, board, dx, grow=0.0):
        return Pos(dx, 0) * offset(board.outline(), P.FIT + P.WALL + grow, kind=Kind.ARC)

    @cached_property
    def pockets(self):
        return [piece_containing(self.case_outline(b, dx, P.POCKET_CLEAR), *self.at(b, dx, (b["usb"]["x"], b["usb"]["y"])))
                for b, dx in self.halves()]

    @cached_property
    def outline(self):
        pts = [self.at(b, dx, p) for b, dx in self.halves() for p in b["outline"]]
        grow = P.FIT + P.WALL + P.POCKET_CLEAR + P.TRAY_WALL
        return offset(poly_face(hull(pts)), grow, kind=Kind.ARC).faces()[0]

    @cached_property
    def y_front(self):
        """y of the front wall's inner face on the centre line (the V between the thumb clusters)."""
        inner = offset(self.outline, -P.TRAY_WALL, kind=Kind.ARC).faces()[0]
        bb = inner.bounding_box()
        line = box(self.x_c - 0.01, self.x_c + 0.01, bb.min.Y - 1, bb.max.Y + 1, 0, 1).faces().sort_by(Axis.Z)[0]
        return (inner & line).bounding_box().min.Y

    # --- the dock PCB -------------------------------------------------------------------------

    @cached_property
    def pins(self):
        """[(x, y, net, half)] of the pogo pins, at the halves' pad centres."""
        return [(*self.at(b, dx, (p["x"], p["y"])), p["net"], b.side)
                for b, dx in self.halves() for p in b["dock_pads"]["pads"]]

    @cached_property
    def magnets(self):
        """[(x, y, ref, half)] under every steel washer (the boards' MK1/MK2 markers)."""
        return [(*self.at(b, dx, (m["x"], m["y"])), m["ref"], b.side) for b, dx in self.halves() for m in b["steel_discs"]]

    @property
    def magnet_hole_d(self):
        """Hole in the dock PCB around a magnet it passes over: the magnet's pocket, its wall,
        and the PCB's clearance around that boss."""
        return P.MAGNET[0] + P.MAGNET_FIT + 2 * P.MAGNET_WALL + 2 * P.BOSS_CLEAR

    @cached_property
    def bar(self):
        """(x0, x1, y0, y1) of the dock PCB's bar along the pin rows."""
        r = P.PIN_PAD_D / 2
        xs = [x for x, _, _, _ in self.pins]
        x0, x1 = min(xs) - r - P.BAR_END, max(xs) + r + P.BAR_END
        ys = [y for _, y, _, _ in self.pins]
        y0, y1 = min(ys) - r, max(ys) + r
        for x, y, _, _ in self.magnets:
            if x0 < x < x1:
                y0, y1 = min(y0, y - self.magnet_hole_d / 2), max(y1, y + self.magnet_hole_d / 2)
        return (x0, x1, y0 - P.BAR_RIM, y1 + P.BAR_RIM)

    @cached_property
    def pcb_magnets(self):
        """The magnets the dock PCB passes over: it has a hole around each."""
        x0, x1, _, _ = self.bar
        return [m for m in self.magnets if x0 < m[0] < x1]

    @cached_property
    def usb(self):
        """(x, y) of the dock's USB-C receptacle footprint origin: its front face (local
        y = USB_BODY depth minus 2.18 from the legs, datasheet) on the PCB's front edge."""
        return (self.x_c, self.y_front + (P.USB_BODY[1] - 2.18))

    @cached_property
    def screws(self):
        """The two M2 screws holding the dock PCB, beside the receptacle."""
        y = self.y_front + P.USB_BODY[1] / 2
        return [(self.x_c - P.DOCK_SCREW_DX, y), (self.x_c + P.DOCK_SCREW_DX, y)]

    def placed(self, ref):
        """(x, y) of a dock PCB part placed by dock-pcb/placement.json."""
        r = json.loads(PLACEMENT.read_text())["parts"][ref]
        return self.from_kicad(r["x"], r["y"])

    @cached_property
    def pcb_outline(self):
        x0, x1, y0, y1 = self.bar
        bar = box(x0, x1, y0, y1, 0, 1).faces().sort_by(Axis.Z)[0]
        tab = box(self.x_c - P.TAB_HALF_W, self.x_c + P.TAB_HALF_W, self.y_front, y0 + 0.01, 0, 1).faces().sort_by(Axis.Z)[0]
        face = (bar + tab).faces()[0]
        for x, y, _, _ in self.pcb_magnets:
            face = face - Pos(x, y) * Circle(self.magnet_hole_d / 2)
        return face.faces()[0] if hasattr(face, "faces") else face

    @cached_property
    def parts_area(self):
        """Where the dock PCB may carry parts: on the board, away from the pockets (a case rests
        on the board everywhere else)."""
        area = self.pcb_outline
        for pk in self.pockets:
            area = area - offset(pk, P.PARTS_CLEAR, kind=Kind.ARC)
        return piece_containing(area, *self.usb)

    # --- the tray -----------------------------------------------------------------------------

    def finger_notches(self):
        """(x, y) of the notch in each pocket's outer wall: the middle of the pocket's outermost
        stretch of wall."""
        out = []
        for pk, (b, _) in zip(self.pockets, self.halves()):
            bb = pk.bounding_box()
            x = bb.min.X if b.inner_dir > 0 else bb.max.X
            strip = box(x - 1, x + 1, bb.min.Y - 1, bb.max.Y + 1, 0, 1).faces().sort_by(Axis.Z)[0]
            sb = (pk & strip).bounding_box()
            out.append((x, (sb.min.Y + sb.max.Y) / 2))
        return out

    @cached_property
    def relief(self):
        """(x0, x1, y0, y1) of the hollow under the dock PCB at the receptacle: its shell legs
        stand out below the board, and the fuse (F1), hot when tripped, has air under it."""
        ux, uy = self.usb
        _, fy = self.placed("F1")
        return (ux - P.USB_BODY[0] / 2 - 0.5, ux + P.USB_BODY[0] / 2 + 0.5, uy - 4.62 - 0.3,
                max(uy + 2.18 + 0.8, fy + P.FUSE_RELIEF))

    def tray(self):
        top = P.Z_DOCK + P.POCKET_DEPTH
        part = prism(self.outline, 0, top)
        part = chamfer(part.faces().sort_by(Axis.Z)[-1].edges(), P.TRAY_EDGE_TOP)
        part = chamfer(part.faces().sort_by(Axis.Z)[0].edges(), P.TRAY_EDGE_BOTTOM)

        # Pockets, with a 45° funnel at the top of their walls, and a notch in each outer wall
        # to get a finger to the case's side.
        for pk in self.pockets:
            part -= prism(pk, P.Z_DOCK, top + 1)
            lead = prism(offset(pk, P.FUNNEL, kind=Kind.ARC), top - P.FUNNEL, top + 1)
            part -= chamfer(lead.faces().sort_by(Axis.Z)[0].edges(), P.FUNNEL - 0.01)
        r, h = P.FINGER_NOTCH
        for x, y in self.finger_notches():
            part -= cyl(x, y, 2 * r, P.Z_DOCK + h, top + 1)

        # The dock PCB: a recess its top lies flush in, open above it, except the bosses that
        # hold the magnets it passes over and locate it.
        recess = offset(self.pcb_outline, P.DOCK_PCB_CLEAR, kind=Kind.ARC)
        for x, y, _, _ in self.pcb_magnets:
            recess = recess - Pos(x, y) * Circle(self.magnet_hole_d / 2 - P.BOSS_CLEAR)
        part -= prism(recess, P.Z_DOCK - P.DOCK_PCB_T, top + 1)

        # Under the USB-C receptacle and the fuse: room below the PCB.
        x0, x1, y0, y1 = self.relief
        part -= box(x0, x1, y0, y1, P.Z_DOCK - P.DOCK_PCB_T - P.RELIEF_DEPTH, P.Z_DOCK)
        ux, uy = self.usb
        # The plug's way in through the front wall.
        plug_z0 = P.Z_DOCK + P.DOCK_USB_AXIS - P.USB_PLUG[1] / 2 - 0.5
        part -= box(ux - P.USB_PLUG[0] / 2 - 0.3, ux + P.USB_PLUG[0] / 2 + 0.3, self.y_front - P.TRAY_WALL - 2,
                    self.y_front + 0.5, plug_z0, top + 1)

        # Heat-set inserts for the dock PCB's screws.
        for x, y in self.screws:
            part -= cyl(x, y, P.INSERT_D, P.Z_DOCK - P.DOCK_PCB_T - P.INSERT_DEPTH, P.Z_DOCK - P.DOCK_PCB_T + 0.1)

        for b, dx in self.halves():
            # Magnets, from below, under MAGNET_SKIN.
            for m in b["steel_discs"]:
                x, y = self.at(b, dx, (m["x"], m["y"]))
                part -= cyl(x, y, P.MAGNET[0] + P.MAGNET_FIT, -0.1, P.Z_DOCK - P.MAGNET_SKIN)
            # The case's rubber feet: holes right through, so any foot height fits.
            for f in b["feet"]:
                x, y = self.at(b, dx, (f["x"], f["y"]))
                part -= cyl(x, y, f["d"] + P.FOOT_POCKET, -0.1, P.Z_DOCK + 0.1)
            # A tenting puck, if one is mounted, goes through.
            pk = b["puck"]
            x, y = self.at(b, dx, (pk["x"], pk["y"]))
            part -= cyl(x, y, 2 * (pk["radius"] + P.PUCK_CLEAR) + 1.0, -0.1, P.Z_DOCK + 0.1)
        return part

    def pieces(self, tray):
        """The tray split on its centre line, SPLIT_GAP apart: (left piece, right piece)."""
        bb = tray.bounding_box()
        g = P.SPLIT_GAP / 2
        left = tray & box(bb.min.X - 1, self.x_c - g, bb.min.Y - 1, bb.max.Y + 1, -1, bb.max.Z + 1)
        right = tray & box(self.x_c + g, bb.max.X + 1, bb.min.Y - 1, bb.max.Y + 1, -1, bb.max.Z + 1)
        return left, right

    # --- what the dock PCB is built from --------------------------------------------------------

    def to_kicad(self, x, y):
        """Dock frame -> the dock board's KiCad coordinates (y down), centred on DOCK_PCB_ORIGIN."""
        y_pads = self.pins[0][1]
        ox, oy = P.DOCK_PCB_ORIGIN
        return (round(x - self.x_c + ox, 4), round(-(y - y_pads) + oy, 4))

    def from_kicad(self, x, y):
        """The dock board's KiCad coordinates -> dock frame (to_kicad's inverse)."""
        ox, oy = P.DOCK_PCB_ORIGIN
        return (x - ox + self.x_c, self.pins[0][1] + oy - y)

    def pcb_geometry(self):
        def loop(wire, step=0.5):
            """The wire's points in order, KiCad coordinates; curved edges sampled every `step` mm."""
            pts = []
            for e in wire.order_edges():
                n = 1 if e.geom_type.name == "LINE" else max(2, int(e.length / step))
                pts += [self.to_kicad(q.X, q.Y) for q in (e.position_at(i / n) for i in range(n))]
            return pts

        outline = self.pcb_outline
        return {
            "_doc": "GENERATED by `mech dock-geometry` from the tray CAD (mech/src/mech/tray.py). "
                    "KiCad coordinates (mm, y down). Do not edit by hand.",
            "thickness": P.DOCK_PCB_T,
            "outline": loop(outline.outer_wire()),
            "cutouts": [{"x": self.to_kicad(x, y)[0], "y": self.to_kicad(x, y)[1], "d": round(self.magnet_hole_d, 3),
                         "ref": f"{half} {ref}"} for x, y, ref, half in self.pcb_magnets],
            "pins": [{"x": self.to_kicad(x, y)[0], "y": self.to_kicad(x, y)[1], "net": net, "half": half}
                     for x, y, net, half in self.pins],
            "screws": [{"x": self.to_kicad(x, y)[0], "y": self.to_kicad(x, y)[1], "d": 2.2, "head_d": P.DOCK_SCREW_HEAD[0]}
                       for x, y in self.screws],
            "usb": {"x": self.to_kicad(*self.usb)[0], "y": self.to_kicad(*self.usb)[1], "rot": 0.0},
            "parts_area": loop(self.parts_area.outer_wire()),
        }
