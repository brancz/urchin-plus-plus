"""Scripted critical routes: the USB-C receptacle's paired pins (phase 4), and the dock's
5 V trunk (phase 7).

On a keyboard half, the 16-pin receptacle carries D+ on A6 and B6 and D- on A7 and B7, interleaved
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
On the dock, DOCK_5V runs from the fuse past the TVS to the 5 V pogo pin at each end of
the bar, on F.Cu, along the middle of the strip between the magnet cutouts and the bar's
lower edge (Freerouting doesn't find that strip). F.Cu has nothing else there, and B.Cu
stays one unbroken ground pour.
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


def usb_receptacle(board):
    """Whether the board has the keyboard's USB 2.0 receptacle (the dock's J1 is power-only)."""
    j1 = board.FindFootprintByReference("J1")
    return j1 is not None and any(p.GetNumber() == "A6" for p in j1.Pads())


def dock_pins(board):
    """The dock's DOCK_5V pogo-pin pads, left to right; empty on a keyboard half."""
    pads = [p for fp in board.GetFootprints() if fp.GetReference().startswith("P")
            for p in fp.Pads() if p.GetNetname() == "DOCK_5V"]
    return sorted(pads, key=lambda p: p.GetPosition().x)


def applies(board):
    return usb_receptacle(board) or bool(dock_pins(board))


def track(board, net, a, b, width, layer=pcbnew.F_Cu):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(a)
    t.SetEnd(b)
    t.SetWidth(nm(width))
    t.SetLayer(layer)
    t.SetNet(net)
    t.SetLocked(True)
    board.Add(t)
    return t


DOCK_TRUNK = 0.5     # mm; two halves draw about 0.2 A in all
DOCK_TRUNK_ROOM = 1.5  # mm the strip must at least have: the trunk and 0.5 mm either side


def dock_trunk_y(board):
    """The middle of the strip between the magnet cutouts and the bar's lower edge (nm)."""
    circles, edges = [], []
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts or not isinstance(d, pcbnew.PCB_SHAPE):
            continue
        if d.GetShape() == pcbnew.SHAPE_T_CIRCLE:
            circles.append((d.GetCenter(), d.GetRadius()))
        elif d.GetShape() == pcbnew.SHAPE_T_SEGMENT and d.GetStart().y == d.GetEnd().y:
            edges.append(d)
    ys = set()
    for c, r in circles:
        below = [e.GetStart().y for e in edges if e.GetStart().y > c.y
                 and min(e.GetStart().x, e.GetEnd().x) <= c.x - r and max(e.GetStart().x, e.GetEnd().x) >= c.x + r]
        if not below:
            raise RuntimeError("no board edge below the cutout at (%.2f, %.2f)" % (c.x / 1e6, c.y / 1e6))
        if min(below) - (c.y + r) < nm(DOCK_TRUNK_ROOM):
            raise RuntimeError("the strip below the cutout at (%.2f, %.2f) is too narrow for the 5 V trunk"
                               % (c.x / 1e6, c.y / 1e6))
        ys.add((c.y + r + min(below)) // 2)
    if len(circles) != 2 or len(ys) != 1:
        raise RuntimeError("expected two magnet cutouts at the same height, found %d" % len(circles))
    return ys.pop()


def add_dock(board):
    """The dock's 5 V trunk: fuse -> TVS -> along the strip -> each 5 V pin."""
    net = board.FindNet("DOCK_5V")
    src = [p for ref in ("F1", "D1") for p in board.FindFootprintByReference(ref).Pads() if p.GetNetname() == "DOCK_5V"]
    if len(src) != 2:
        raise RuntimeError("expected one DOCK_5V pad on each of F1 and D1")
    fuse, tvs = (p.GetPosition() for p in src)
    y = dock_trunk_y(board)
    tee = pcbnew.VECTOR2I(tvs.x, y)
    items = [track(board, net, fuse, tvs, DOCK_TRUNK), track(board, net, tvs, tee, DOCK_TRUNK)]
    for pad in dock_pins(board):
        q = pad.GetPosition()
        corner = pcbnew.VECTOR2I(q.x, y)
        items += [track(board, net, tee, corner, DOCK_TRUNK), track(board, net, corner, q, DOCK_TRUNK)]
    return items


def add(board):
    """Add the pre-routes, locked. Returns the items added."""
    if not usb_receptacle(board):
        return add_dock(board)
    at = frame(board)
    items = []
    for net_name, spec in ROUTES.items():
        net = board.FindNet(net_name)
        for layer, pts in spec["tracks"]:
            for a, b in zip(pts, pts[1:]):
                items.append(track(board, net, at(*a), at(*b), WIDTH[net_name],
                                   pcbnew.B_Cu if layer == "B" else pcbnew.F_Cu))
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
