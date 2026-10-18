#!/usr/bin/env python3
"""Small pcbnew operations for the round-trip steps (KiCad's Python).

    "$KICAD_PY" scripts/roundtrip/pcb_ops.py BOARD via NET X Y     add a via (no pad contact) and save
    "$KICAD_PY" scripts/roundtrip/pcb_ops.py BOARD via-net X Y     print the net of the via at X Y
    "$KICAD_PY" scripts/roundtrip/pcb_ops.py BOARD foreign X Y     add a footprint atopile doesn't own and save
    "$KICAD_PY" scripts/roundtrip/pcb_ops.py BOARD place-offboard  move footprints left at the origin onto free spots
    "$KICAD_PY" scripts/roundtrip/pcb_ops.py BOARD flip ADDRESS    flip a footprint to the other side and save
    "$KICAD_PY" scripts/roundtrip/pcb_ops.py BOARD lock ADDRESS    lock a footprint and save
    "$KICAD_PY" scripts/roundtrip/pcb_ops.py BOARD drop-track      delete the first track and save

Coordinates in mm. Every write goes through pcbnew.SaveBoard, like a human or a
placement script would.
"""

import sys

import pcbnew

FREE_SPOTS = [(120.0, 112.0), (124.0, 112.0), (124.0, 116.0), (120.0, 116.0)]


def at(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(float(x)), pcbnew.FromMM(float(y)))


def main():
    path, op, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    board = pcbnew.LoadBoard(path)
    if op == "via":
        net, x, y = args
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(at(x, y))
        v.SetDrill(pcbnew.FromMM(0.3))
        v.SetWidth(pcbnew.FromMM(0.6))
        v.SetNet(board.FindNet(net))
        board.Add(v)
    elif op == "via-net":
        want = at(*args)
        nets = [t.GetNetname() for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetPosition() == want]
        print(",".join(nets) if nets else "<no via>")
        return
    elif op == "foreign":
        fp = pcbnew.FOOTPRINT(board)
        fp.SetReference("H9")
        fp.SetValue("not_from_atopile")
        fp.SetPosition(at(*args))
        board.Add(fp)
    elif op == "place-offboard":
        def taken(x, y):
            return any(abs(pcbnew.ToMM(f.GetPosition().x) - x) < 2 and abs(pcbnew.ToMM(f.GetPosition().y) - y) < 2
                       for f in board.GetFootprints())
        for fp in board.GetFootprints():
            if pcbnew.ToMM(fp.GetPosition().x) < 100:
                spot = next((s for s in FREE_SPOTS if not taken(*s)), None)
                if spot is None:
                    sys.exit("no free spot left for %s" % fp.GetReference())
                fp.SetPosition(at(*spot))
                fp.SetOrientationDegrees(270)
    elif op in ("flip", "lock"):
        fp = next(f for f in board.GetFootprints()
                  if any(x.GetName() == "atopile_address" and x.GetText() == args[0] for x in f.GetFields()))
        if op == "flip":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        else:
            fp.SetLocked(True)
    elif op == "drop-track":
        board.Delete(next(t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"))
    else:
        sys.exit("unknown op %s" % op)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(path, board)


if __name__ == "__main__":
    main()
