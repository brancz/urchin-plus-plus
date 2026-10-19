"""Scripted critical routes: the USB-C receptacle's paired pins (phase 4).

The 16-pin receptacle carries D+ on A6 and B6 and D- on A7 and B7, interleaved
(B7 A6 A7 B6), so that a plug works both ways round, and VBUS on two pads at either
end. Each pair must be joined right at the connector, where Freerouting gives up in
the crowded space behind it. The joins, in J1's own frame (x along the pad row, y
from the receptacle's front toward its pads; pad centres at y = 2.47):
  - D- (B7 at x -0.75, A7 at x 0.25): a U on B.Cu under the receptacle body, through
    y = 1.55, clear of A6 between them (0.17 mm).
  - D+ (A6 at x -0.25, B6 at x 0.75): B.Cu stubs to vias behind the pads at
    (-0.25, 3.9) and (0.75, 4.75), joined on F.Cu.
  - VBUS (A4B9 at x -2.4, B4A9 at x 2.4): B.Cu stubs to vias at (+-2.4, 3.9), joined on
    F.Cu through y = 5.6 (0.35 mm clear of the D+ via).
The frame comes from the pads themselves (origin = J1's position, x = from A6 toward B6,
y = from the origin toward the pad row), so it holds for any rotation and both halves.
Used by route.py: the routes go in locked (fixed for Freerouting) before the DSN export.
Python 3.9, KiCad's pcbnew.
"""

import math

import pcbnew

ROUTES = {  # net -> list of (layer, [points]) and vias; points in J1's frame (mm)
    "USB_DN": {"tracks": [("B", [(-0.75, 2.47), (-0.75, 1.55), (0.25, 1.55), (0.25, 2.47)])], "vias": []},
    "USB_DP": {"tracks": [("B", [(-0.25, 2.47), (-0.25, 3.9)]), ("B", [(0.75, 2.47), (0.75, 4.75)]),
                          ("F", [(-0.25, 3.9), (0.75, 4.75)])],
               "vias": [(-0.25, 3.9), (0.75, 4.75)]},
    "VBUS": {"tracks": [("B", [(-2.4, 2.47), (-2.4, 3.9)]), ("B", [(2.4, 2.47), (2.4, 3.9)]),
                        ("F", [(-2.4, 3.9), (-2.4, 5.6), (2.4, 5.6), (2.4, 3.9)])],
             "vias": [(-2.4, 3.9), (2.4, 3.9)]},
}
WIDTH = {"USB_DN": 0.2, "USB_DP": 0.2, "VBUS": 0.3}
VIA = (0.7, 0.3)


def nm(v):
    return int(round(v * 1e6))


def frame(board):
    j1 = board.FindFootprintByReference("J1")
    pads = {p.GetNumber(): p.GetPosition() for p in j1.Pads()}
    o = j1.GetPosition()
    a6, b6 = pads["A6"], pads["B6"]
    vx, vy = (b6.x - a6.x), (b6.y - a6.y)
    n = math.hypot(vx, vy)
    vx, vy = vx / n, vy / n
    row = ((a6.x + b6.x) / 2 - o.x, (a6.y + b6.y) / 2 - o.y)
    ux, uy = -vy, vx
    if ux * row[0] + uy * row[1] < 0:
        ux, uy = -ux, -uy
    # sanity: the frame reproduces the pads' positions
    for name, lx in (("A6", -0.25), ("B6", 0.75), ("A4B9", -2.4), ("B4A9", 2.4), ("B7", -0.75), ("A7", 0.25)):
        p = pads[name]
        q = (o.x + nm(lx) * vx + nm(2.47) * ux, o.y + nm(lx) * vy + nm(2.47) * uy)
        if math.hypot(p.x - q[0], p.y - q[1]) > nm(0.01):
            raise RuntimeError("J1 pad %s is not where the pre-route frame expects it" % name)
    return lambda x, y: pcbnew.VECTOR2I(int(round(o.x + nm(x) * vx + nm(y) * ux)), int(round(o.y + nm(x) * vy + nm(y) * uy)))


def add(board):
    """Add the pre-routes, locked. Returns the items added."""
    at = frame(board)
    items = []
    for net_name, spec in ROUTES.items():
        net = board.FindNet(net_name)
        for layer, pts in spec["tracks"]:
            for a, b in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(at(*a))
                t.SetEnd(at(*b))
                t.SetWidth(nm(WIDTH[net_name]))
                t.SetLayer(pcbnew.B_Cu if layer == "B" else pcbnew.F_Cu)
                t.SetNet(net)
                t.SetLocked(True)
                board.Add(t)
                items.append(t)
        for x, y in spec["vias"]:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(at(x, y))
            v.SetWidth(nm(VIA[0]))
            v.SetDrill(nm(VIA[1]))
            v.SetNet(net)
            v.SetLocked(True)
            board.Add(v)
            items.append(v)
    return items
