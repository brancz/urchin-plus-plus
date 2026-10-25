"""The charging dock: its tray, the cover over its electronics, and the dock PCB's shape and
feature positions (docs/ARCHITECTURE.md, "Dock").

The dock frame is the left half's CAD frame; the right half sits DX to its right, so the two
cases' inner edges are DIVIDER plus two POCKET_CLEARs apart. The pocket floor is at Z_DOCK:
there the cases' undersides rest, and the dock PCB's top lies flush with it in a recess. The
pogo pins soldered on each half's charging pads come down through the case's window onto flat
pads on the dock PCB.

The dock PCB is a U: under each half a bar along its pads and an arm back along the half's
inner wall, both in the pocket's floor; at the back, between the halves, a tab that joins the
arms and carries the USB-C receptacle (its mouth flush with the tray's back face) and the
small parts. A printed cover fills the tray over the tab, flush with its top. The tray prints
as two pieces split on the centre line between the pockets.

pcb_geometry() is what the dock board is built from (dock-pcb/geometry.json, via
`mech dock-geometry`): the board follows the tray, never the other way round.
"""

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from build123d import Axis, Circle, Kind, Pos, Vector, chamfer, offset

from . import params as P
from .board import Board, xy
from .case import box, cyl, piece_containing, prism

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
    from build123d import Face, Vector, Wire
    return Face(Wire.make_polygon([Vector(x, y, 0) for x, y in points], close=True))


def rect(x0, x1, y0, y1):
    return box(x0, x1, y0, y1, 0, 1).faces().sort_by(Axis.Z)[0]


def one_face(shape):
    """The single face of a 2D boolean's result."""
    faces = shape.faces() if hasattr(shape, "faces") else [shape]
    if len(faces) != 1:
        raise SystemExit(f"mech: dock: expected one face, got {len(faces)}")
    return faces[0]


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
    def y_back(self):
        """y of the tray's back face on the centre line."""
        bb = self.outline.bounding_box()
        return (self.outline & rect(self.x_c - 0.01, self.x_c + 0.01, bb.min.Y - 1, bb.max.Y + 1)).bounding_box().max.Y

    @cached_property
    def inner_walls(self):
        """[(x, y0, y1)] per half: the straight run of its pocket's wall that faces the centre line."""
        out = []
        for pk, (b, _) in zip(self.pockets, self.halves()):
            mid = pk.bounding_box().center().X
            runs = [e for e in pk.outer_wire().edges() if e.geom_type.name == "LINE"
                    and abs(e.position_at(0).X - e.position_at(1).X) < 1e-3
                    and (e.position_at(0).X - mid) * b.inner_dir > 0]
            e = max(runs, key=lambda e: e.length)
            ys = sorted((e.position_at(0).Y, e.position_at(1).Y))
            out.append((e.position_at(0).X, *ys))
        return out

    # --- the dock PCB -------------------------------------------------------------------------

    @cached_property
    def contacts(self):
        """[(x, y, net, half)] of the dock PCB's flat pads, under the pins on the halves' pad centres."""
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
    def spines(self):
        """[(x0, x1)] per half: the arm back to the tab, PCB_INSET inside the pocket's inner wall."""
        out = []
        for (b, _), (x, _, _) in zip(self.halves(), self.inner_walls):
            edge = x - b.inner_dir * P.PCB_INSET
            out.append(tuple(sorted((edge, edge - b.inner_dir * P.SPINE_W))))
        return out

    @cached_property
    def tab_front(self):
        """y of the tab's front edge: TAB_LEAD ahead of where the inner walls stop being straight."""
        return min(y1 for _, _, y1 in self.inner_walls) - P.TAB_LEAD

    @cached_property
    def bars(self):
        """[(x0, x1, y0, y1)] per half: the bar along its pads, out to its spine."""
        out = []
        w, h = P.DOCK_CONTACT
        for (b, _), spine in zip(self.halves(), self.spines):
            cs = [c for c in self.contacts if c[3] == b.side]
            xs, ys = [c[0] for c in cs], [c[1] for c in cs]
            x0, x1 = min(xs) - w / 2 - P.BAR_END, max(xs) + w / 2 + P.BAR_END
            x0, x1 = min(x0, spine[0]), max(x1, spine[1])
            y0, y1 = min(ys) - h / 2, max(ys) + h / 2
            for x, y, _, side in self.magnets:
                if side == b.side and x0 < x < x1:
                    y0, y1 = min(y0, y - self.magnet_hole_d / 2), max(y1, y + self.magnet_hole_d / 2)
            out.append((x0, x1, y0 - P.BAR_RIM, y1 + P.BAR_RIM))
        return out

    @cached_property
    def trunks(self):
        """[(x, y)] per half: where the 5 V trunk runs, down the middle of the spine (x) and along
        the bar's back strip (y), between its back edge and the magnet hole or the pads."""
        out = []
        for (b, _), (s0, s1), (_, _, _, y1) in zip(self.halves(), self.spines, self.bars):
            tops = [c[1] + P.DOCK_CONTACT[1] / 2 for c in self.contacts if c[3] == b.side]
            tops += [m[1] + self.magnet_hole_d / 2 for m in self.pcb_magnets if m[3] == b.side]
            out.append(((s0 + s1) / 2, (y1 + max(tops)) / 2))
        return out

    @cached_property
    def pcb_magnets(self):
        """The magnets the dock PCB passes over: it has a hole around each, round the boss that
        holds the magnet and locates the PCB."""
        out = []
        for (x0, x1, _, _), (b, _) in zip(self.bars, self.halves()):
            out += [m for m in self.magnets if m[3] == b.side and x0 < m[0] < x1]
        return out

    @cached_property
    def usb(self):
        """(x, y) of the USB-C receptacle's footprint origin: its mouth on the tray's back face.
        The footprint turns 180 degrees, so its front (local +y) faces the back."""
        return (self.x_c, self.y_back - P.DOCK_USB_FRONT)

    @cached_property
    def pcb_area(self):
        """The dock PCB's outline without its holes and the receptacle's notch."""
        tab = rect(self.x_c - P.TAB_HALF_W, self.x_c + P.TAB_HALF_W, self.tab_front, self.y_back + 5) & self.outline
        face = one_face(tab)
        for pk, (x0, x1, y0, y1), (s0, s1) in zip(self.pockets, self.bars, self.spines):
            arm = rect(x0, x1, y0, y1) + rect(s0, s1, y0, self.tab_front + 1)
            face = one_face(face + (one_face(arm) & offset(pk, -P.PCB_INSET, kind=Kind.ARC)))
        return face

    @cached_property
    def pcb_outline(self):
        ux, uy = self.usb
        w, behind = P.DOCK_USB_NOTCH
        face = self.pcb_area - rect(ux - w / 2, ux + w / 2, uy - behind, self.y_back + 1)
        # A relief behind each inner corner (clear of the legs' pads beside it), so the router's
        # radius doesn't leave a fillet where the housing's corners go.
        r = P.DOCK_USB_NOTCH_RELIEF / 2
        for s in (-1, 1):
            face = face - Pos(ux + s * (w / 2 - r), uy - behind) * Circle(r)
        for x, y, _, _ in self.pcb_magnets:
            face = face - Pos(x, y) * Circle(self.magnet_hole_d / 2)
        return one_face(face)

    def placed(self, ref):
        """(x, y) of a dock PCB part placed by dock-pcb/placement.json."""
        r = json.loads(PLACEMENT.read_text())["parts"][ref]
        return self.from_kicad(r["x"], r["y"])

    @cached_property
    def parts_area(self):
        """Where the dock PCB may carry parts: on the tab, away from the pockets (a case rests
        on the board everywhere else)."""
        area = self.pcb_outline
        for pk in self.pockets:
            area = area - offset(pk, P.PARTS_CLEAR, kind=Kind.ARC)
        return piece_containing(area, self.usb[0], self.usb[1] - P.DOCK_USB_NOTCH[1] - 2.5)

    # --- the tray -----------------------------------------------------------------------------

    @cached_property
    def recess(self):
        """Where the dock PCB lies in the tray: its outline and clearance (the receptacle's notch
        included), less the magnet bosses."""
        face = offset(self.pcb_area, P.DOCK_PCB_CLEAR, kind=Kind.ARC)
        for x, y, _, _ in self.pcb_magnets:
            face = face - Pos(x, y) * Circle(self.magnet_hole_d / 2 - P.BOSS_CLEAR)
        return face

    @cached_property
    def relief(self):
        """[(x0, x1, y0, y1)] of the hollows below the dock PCB: under the receptacle's legs,
        which stand out below the board; under its body, which reaches the board's underside
        (out through the back face, behind the plug); and under the fuse (F1), hot when tripped."""
        ux, uy = self.usb
        fx, fy = self.placed("F1")
        f = P.FUSE_RELIEF
        bw = P.DOCK_USB_BODY[0] / 2 + 0.3
        return [(ux - P.DOCK_USB_LEGS[0] - 0.9, ux + P.DOCK_USB_LEGS[0] + 0.9, uy + P.DOCK_USB_LEGS[1] - 1.5,
                 uy + P.DOCK_USB_LEGS[2] + 1.6),
                (ux - bw, ux + bw, uy - P.DOCK_USB_NOTCH[1] - 0.5, self.y_back + 1),
                (fx - f, fx + f, fy - f, fy + f)]

    @property
    def top(self):
        return P.Z_DOCK + P.POCKET_DEPTH

    def envelope(self):
        """The tray's outer shape, its edges chamfered."""
        part = prism(self.outline, 0, self.top)
        part = chamfer(part.faces().sort_by(Axis.Z)[-1].edges(), P.TRAY_EDGE_TOP)
        return chamfer(part.faces().sort_by(Axis.Z)[0].edges(), P.TRAY_EDGE_BOTTOM)

    def pocket_cuts(self, z0=P.Z_DOCK):
        """The pockets, with a 45° funnel at the top of their walls."""
        cuts = []
        for pk in self.pockets:
            lead = prism(offset(pk, P.FUNNEL, kind=Kind.ARC), self.top - P.FUNNEL, self.top + 1)
            cuts.append(prism(pk, z0, self.top + 1) + chamfer(lead.faces().sort_by(Axis.Z)[0].edges(), P.FUNNEL - 0.01))
        return cuts

    def tray(self):
        part = self.envelope()
        for cut in self.pocket_cuts():
            part -= cut
        # The dock PCB's recess, open above: the cases cover it in the pockets, the cover over the tab.
        part -= prism(self.recess, P.Z_DOCK - P.DOCK_PCB_T, self.top + 1)
        for x0, x1, y0, y1 in self.relief:
            part -= box(x0, x1, y0, y1, P.Z_DOCK - P.DOCK_PCB_T - P.RELIEF_DEPTH, P.Z_DOCK - P.DOCK_PCB_T + 0.01)

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

    def cover(self, parts):
        """The cover over the tab: the tray's shape where the PCB's recess leaves it open
        outside the pockets, resting on the PCB, with a pocket over each part on it and a hole
        over the power LED. `parts` are the dock PCB's parts in the dock frame ([(ref, shape)])."""
        region = offset(self.recess, -P.COVER_CLEAR, kind=Kind.ARC)
        part = self.envelope() & prism(region, P.Z_DOCK, self.top + 1)
        for cut in self.pocket_cuts(P.Z_DOCK - 0.1):
            part -= cut
        c = P.COVER_PART_CLEAR
        for ref, shape in parts:
            bb = shape.bounding_box()
            if bb.max.Z <= P.Z_DOCK or not region.is_inside(Vector(bb.center().X, bb.center().Y, 0)):
                continue
            part -= box(bb.min.X - c, bb.max.X + c, bb.min.Y - c, bb.max.Y + c, P.Z_DOCK - 1, bb.max.Z + c)
            if ref == "LED1":
                part -= cyl(bb.center().X, bb.center().Y, P.LED_HOLE_D, P.Z_DOCK, self.top + 1)
        return max(part.solids(), key=lambda s: s.volume)

    # --- what the dock PCB is built from --------------------------------------------------------

    def to_kicad(self, x, y):
        """Dock frame -> the dock board's KiCad coordinates (y down), centred on DOCK_PCB_ORIGIN."""
        y_pads = self.contacts[0][1]
        ox, oy = P.DOCK_PCB_ORIGIN
        return (round(x - self.x_c + ox, 4), round(-(y - y_pads) + oy, 4))

    def from_kicad(self, x, y):
        """The dock board's KiCad coordinates -> dock frame (to_kicad's inverse)."""
        ox, oy = P.DOCK_PCB_ORIGIN
        return (x - ox + self.x_c, self.contacts[0][1] + oy - y)

    def pcb_geometry(self):
        def loop(wire, step=0.5):
            """The wire's points in order, KiCad coordinates; curved edges sampled every `step` mm."""
            pts = []
            for e in wire.order_edges():
                n = 1 if e.geom_type.name == "LINE" else max(2, int(e.length / step))
                pts += [self.to_kicad(q.X, q.Y) for q in (e.position_at(i / n) for i in range(n))]
            return pts

        def k(x, y):
            kx, ky = self.to_kicad(x, y)
            return {"x": kx, "y": ky}

        return {
            "_doc": "GENERATED by `mech dock-geometry` from the tray CAD (mech/src/mech/tray.py). "
                    "KiCad coordinates (mm, y down). Do not edit by hand.",
            "thickness": P.DOCK_PCB_T,
            "outline": loop(self.pcb_outline.outer_wire()),
            "cutouts": [dict(k(x, y), d=round(self.magnet_hole_d, 3), ref=f"{half} {ref}")
                        for x, y, ref, half in self.pcb_magnets],
            "contacts": [dict(k(x, y), w=P.DOCK_CONTACT[0], h=P.DOCK_CONTACT[1], net=net, half=half)
                         for x, y, net, half in self.contacts],
            "usb": dict(k(*self.usb), rot=180.0),
            "trunks": [dict(k(x, y), half=b.side) for (x, y), (b, _) in zip(self.trunks, self.halves())],
            "parts_area": loop(self.parts_area.outer_wire()),
        }
