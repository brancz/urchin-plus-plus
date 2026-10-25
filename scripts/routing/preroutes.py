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
On the dock, DOCK_5V runs on F.Cu from the fuse across the tab, down the middle of each arm
of the U-shaped board and along its bar's back strip, between the edge and the magnet
cutout, to the 5 V contact (Freerouting doesn't find those strips). F.Cu has nothing else
there, and B.Cu stays one unbroken ground pour. The CC pull-downs' GND pads, boxed in by
J1's VBUS tracks, join through a via between them to that pour.
Used by route.py: the routes go in locked (fixed for Freerouting) before the DSN export.
Python 3.9, KiCad's pcbnew.
"""

import json
import math
import os

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


def dock_contacts(board):
    """{half: pad} of the dock's 5 V contacts (TP1 left, TP2 right); empty on a keyboard half."""
    out = {}
    for ref, half in (("TP1", "left"), ("TP2", "right")):
        fp = board.FindFootprintByReference(ref)
        pads = [p for p in fp.Pads() if p.GetNetname() == "DOCK_5V"] if fp is not None else []
        if pads:
            out[half] = pads[0]
    return out


def applies(board):
    return usb_receptacle(board) or bool(dock_contacts(board))


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
CC_GND = 0.25        # mm; the CC pull-downs' GND link


def add_dock(board):
    """The dock's 5 V trunk on F.Cu: fuse -> TVS; from the fuse down to the trunk's run across
    the tab (placement.json "trunk_y"), out to each spine, down its middle to the bar, along
    the bar's back strip (geometry.json "trunks") and onto the 5 V contact. Any other 5 V pad
    gets a straight stub to the trunk's run across the tab."""
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dock-pcb")
    geo = json.load(open(os.path.join(root, "geometry.json")))
    y = nm(json.load(open(os.path.join(root, "placement.json")))["trunk_y"])
    net = board.FindNet("DOCK_5V")
    pad = {ref: [p for p in board.FindFootprintByReference(ref).Pads() if p.GetNetname() == "DOCK_5V"]
           for ref in ("F1", "D1")}
    if any(len(v) != 1 for v in pad.values()):
        raise RuntimeError("expected one DOCK_5V pad on each of F1 and D1")
    fuse, tvs = pad["F1"][0].GetPosition(), pad["D1"][0].GetPosition()
    tee = pcbnew.VECTOR2I(fuse.x, y)
    items = [track(board, net, fuse, tvs, DOCK_TRUNK), track(board, net, fuse, tee, DOCK_TRUNK)]
    # every other 5 V pad on the tab (the LED's resistor) gets a straight stub to the trunk
    for fp in board.GetFootprints():
        if fp.GetReference() in ("F1", "D1") or fp.GetReference().startswith("TP"):
            continue
        for p in fp.Pads():
            if p.GetNetname() == "DOCK_5V":
                q = p.GetPosition()
                items.append(track(board, net, q, pcbnew.VECTOR2I(q.x, y), DOCK_TRUNK))
    for t in geo["trunks"]:
        contact = dock_contacts(board)[t["half"]]
        q = contact.GetPosition()
        pts = [tee, pcbnew.VECTOR2I(nm(t["x"]), y), pcbnew.VECTOR2I(nm(t["x"]), nm(t["y"])),
               pcbnew.VECTOR2I(q.x, nm(t["y"])), q]
        items += [track(board, net, a, b, DOCK_TRUNK) for a, b in zip(pts, pts[1:])]
    # The CC pull-downs stand between J1's two VBUS pads, whose tracks join below them at the
    # fuse: their GND pads are joined on F.Cu through a via between them, down to B.Cu's pour.
    gnd = board.FindNet("GND")
    ends = [p.GetPosition() for ref in ("R1", "R2") for p in board.FindFootprintByReference(ref).Pads()
            if p.GetNetname() == "GND"]
    if len(ends) != 2:
        raise RuntimeError("expected one GND pad on each of R1 and R2")
    items.append(track(board, gnd, ends[0], ends[1], CC_GND))
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I((ends[0].x + ends[1].x) // 2, (ends[0].y + ends[1].y) // 2))
    v.SetWidth(nm(VIA[0]))
    v.SetDrill(nm(VIA[1]))
    v.SetNet(gnd)
    v.SetLocked(True)
    board.Add(v)
    items.append(v)
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
