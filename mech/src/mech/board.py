"""A half's mechanical data (mech/data/<side>.json, from scripts/mech/board_data.py) in the
CAD frame: x as in KiCad, y flipped to point up, z = 0 at the case's underside."""

import json
import math
from dataclasses import dataclass
from pathlib import Path

from build123d import Face, Plane, Polygon, Vector, Wire

from . import params as P

DATA = Path(__file__).resolve().parents[2] / "data"


def xy(p):
    """KiCad (x, y) to the CAD frame."""
    return (p[0], -p[1])


def polygon_face(points):
    return Face(Wire.make_polygon([Vector(*xy(p)) for p in points], close=True))


def rect_face(box, margin=0.0):
    x0, y0, x1, y1 = box
    return polygon_face([(x0 - margin, y0 - margin), (x1 + margin, y0 - margin),
                         (x1 + margin, y1 + margin), (x0 - margin, y1 + margin)])


def rotated_rect_face(cx, cy, w, h, rot_deg, margin=0.0):
    """A w x h rectangle centred on KiCad (cx, cy), rotated like a KiCad footprint."""
    a = math.radians(rot_deg)
    hw, hh = w / 2 + margin, h / 2 + margin
    pts = []
    for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        # KiCad rotates counter-clockwise on screen with y down: in the CAD frame (y up) a
        # footprint rotated by +a turns counter-clockwise too.
        x = cx + dx * math.cos(a) + dy * math.sin(a)
        y = cy - dx * math.sin(a) + dy * math.cos(a)
        pts.append((x, y))
    return polygon_face(pts)


@dataclass
class Board:
    side: str
    data: dict

    @classmethod
    def load(cls, side):
        data = json.loads((DATA / f"{side}.json").read_text())
        if abs(data["thickness"] - P.PCB_T) > 1e-6:
            raise SystemExit(f"mech: {side}: board is {data['thickness']} mm thick, params.PCB_T is {P.PCB_T}")
        return cls(side, data)

    def __getitem__(self, key):
        return self.data[key]

    def outline(self):
        return polygon_face(self["outline"])

    @property
    def bbox(self):
        """(xmin, ymin, xmax, ymax) in the CAD frame."""
        x0, y0, x1, y1 = self["bbox"]
        return (x0, -y1, x1, -y0)

    @property
    def inner_dir(self):
        """+1 if the inner edge (USB-C, power switch, controller) is at +x, else -1."""
        cx = (self["bbox"][0] + self["bbox"][2]) / 2
        return 1 if self["usb"]["x"] > cx else -1

    def bottom_keepouts(self):
        """Faces a standoff must stay clear of: every bottom part's courtyard and every socket."""
        faces = [polygon_face(c["polygon"]) for c in self["bottom_courtyards"]]
        faces += [polygon_face(k["socket"]) for k in self["keys"]]
        return faces

    def keycaps(self, margin):
        return [rotated_rect_face(k["x"], k["y"], *P.KEYCAP, k["rot"], margin) for k in self["keys"]]


def plane_at(z):
    return Plane.XY.offset(z)
