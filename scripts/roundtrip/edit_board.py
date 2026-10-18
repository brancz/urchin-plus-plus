#!/usr/bin/env python3
"""Hand-edit stand-in for the phase 0 round-trip: change the board through pcbnew.

    "$KICAD_PY" scripts/roundtrip/edit_board.py BOARD

Sets JLC-like design rules, adds a 30 x 20 mm outline, moves and rotates every
footprint (one at 15 degrees), routes VCC and MID on B.Cu (the parts are
bottom-side, CLAUDE.md rule 2), adds a GND via and a filled two-layer GND zone,
then saves with KiCad's own writer. Prints the edit as JSON.
"""

import json
import sys

import pcbnew

X0, Y0 = 100.0, 100.0
PLACEMENT = {  # atopile_address -> (x, y, rotation) in mm / degrees, relative to X0, Y0
    "r_top": (10.0, 5.0, 270.0),
    "r_bot": (10.0, 10.0, 15.0),
    "c_dec": (16.0, 5.0, 270.0),
    "hole": (25.0, 5.0, 0.0),
}


def at(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(X0 + x), pcbnew.FromMM(Y0 + y))


def field(fp, name):
    for f in fp.GetFields():
        if f.GetName() == name:
            return f.GetText()
    return None


def track(board, start, end, net, width=0.25):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(start)
    t.SetEnd(end)
    t.SetWidth(pcbnew.FromMM(width))
    t.SetLayer(pcbnew.B_Cu)
    t.SetNet(board.FindNet(net))
    board.Add(t)
    return t


def main():
    path = sys.argv[1]
    board = pcbnew.LoadBoard(path)

    rules = board.GetDesignSettings()  # stored in the .kicad_pro next to the board
    rules.m_MinClearance = pcbnew.FromMM(0.127)
    rules.m_TrackMinWidth = pcbnew.FromMM(0.127)
    rules.m_ViasMinSize = pcbnew.FromMM(0.45)
    rules.m_MinThroughDrill = pcbnew.FromMM(0.2)
    rules.m_CopperEdgeClearance = pcbnew.FromMM(0.3)

    outline = pcbnew.PCB_SHAPE(board)
    outline.SetShape(pcbnew.SHAPE_T_RECT)
    outline.SetStart(at(0, 0))
    outline.SetEnd(at(30, 20))
    outline.SetLayer(pcbnew.Edge_Cuts)
    outline.SetWidth(pcbnew.FromMM(0.1))
    board.Add(outline)

    fps = {field(fp, "atopile_address"): fp for fp in board.GetFootprints()}
    if set(fps) != set(PLACEMENT):
        raise SystemExit("unexpected footprints: %s" % sorted(fps))
    placed = {}
    for addr, fp in fps.items():
        x, y, rot = PLACEMENT[addr]
        fp.SetPosition(at(x, y))
        fp.SetOrientationDegrees(rot)
        placed[addr] = {"pos": [X0 + x, Y0 + y], "rot": rot}

    def pad(addr, num):
        return fps[addr].FindPadByNumber(num).GetPosition()

    track(board, pad("r_top", "1"), pad("c_dec", "1"), "VCC")
    track(board, pad("r_top", "2"), pad("r_bot", "1"), "MID")

    via = pcbnew.PCB_VIA(board)
    via.SetPosition(at(25, 15))
    via.SetDrill(pcbnew.FromMM(0.3))
    via.SetWidth(pcbnew.FromMM(0.6))
    via.SetNet(board.FindNet("GND"))
    board.Add(via)

    zone = pcbnew.ZONE(board)
    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    layers.AddLayer(pcbnew.B_Cu)
    zone.SetLayerSet(layers)
    zone.SetNet(board.FindNet("GND"))
    zone.SetZoneName("GND")
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    poly = zone.Outline()
    poly.NewOutline()
    for x, y in ((0.5, 0.5), (29.5, 0.5), (29.5, 19.5), (0.5, 19.5)):
        p = at(x, y)
        poly.Append(p.x, p.y)
    board.Add(zone)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    pcbnew.SaveBoard(path, board)
    print(json.dumps({"placed": placed, "tracks": 2, "vias": 1, "zones": 1}, indent=2))


if __name__ == "__main__":
    main()
