#!/usr/bin/env python3
"""Hand-specified track edits that the router can't make (phase 4).

    "$KICAD_PY" scripts/routing/joins.py BOARD --half left|right [--joins hardware/routing_joins.json]

hardware/routing_joins.json lists, per half, track segments to remove and segments to add,
each as [net, layer, x1, y1, x2, y2(, width)] in mm (board coordinates). They repair the
few places where a footprint change after routing (the LED pads moved outward with the
2.1 mm lens hole) put existing copper too close, and where Freerouting's completion passes
couldn't reconnect the short gap. A removed segment must exist (same net, layer and end
points within 1 um, in either direction); added segments get the net's existing copper.
Run once on the routed board; if every removal is already gone and every addition is
present, it reports "already applied" and changes nothing. DRC (scripts/checks/drc.py)
and scripts/checks/connectivity.py check the result. Runs under KiCad's Python; Python 3.9.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
TOL = 1000  # nm
LAYERS = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}


def nm(v):
    return int(round(v * 1e6))


def same(t, net, layer, x1, y1, x2, y2):
    if t.GetClass() != "PCB_TRACK" or t.GetNetname() != net or t.GetLayer() != LAYERS[layer]:
        return False
    a, b = (t.GetStart(), t.GetEnd())
    close = lambda p, x, y: abs(p.x - nm(x)) <= TOL and abs(p.y - nm(y)) <= TOL
    return (close(a, x1, y1) and close(b, x2, y2)) or (close(a, x2, y2) and close(b, x1, y1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--half", required=True, choices=("left", "right"))
    ap.add_argument("--joins", default=str(ROOT / "hardware/routing_joins.json"))
    args = ap.parse_args()
    spec = json.load(open(args.joins))[args.half]
    board = pcbnew.LoadBoard(args.board)
    tracks = list(board.GetTracks())  # every wrapper before the first edit (KiCad 9 SWIG)
    nets = {n: board.FindNet(n) for n in {e[0] for e in spec["add"]}}
    removes = [[t for t in tracks if same(t, *e[:6])] for e in spec["remove"]]
    adds = [[t for t in tracks if same(t, *e[:6])] for e in spec["add"]]
    if not any(removes) and all(adds):
        print("joins %s (%s): already applied" % (args.board, args.half))
        sys.stdout.flush()
        os._exit(0)
    missing = [e for e, found in zip(spec["remove"], removes) if not found]
    if missing:
        print("joins %s: FAIL, segments to remove not found: %s" % (args.board, missing))
        sys.stdout.flush()
        os._exit(1)
    for found in removes:
        for t in found:
            board.Remove(t)
    for net, layer, x1, y1, x2, y2, width in spec["add"]:
        if nets[net] is None:
            print("joins %s: FAIL, no net %s" % (args.board, net))
            sys.stdout.flush()
            os._exit(1)
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(nm(x1), nm(y1)))
        t.SetEnd(pcbnew.VECTOR2I(nm(x2), nm(y2)))
        t.SetLayer(LAYERS[layer])
        t.SetWidth(nm(width))
        t.SetNet(nets[net])
        board.Add(t)
    board.Save(args.board)
    print("joins %s (%s): removed %d, added %d segments" % (args.board, args.half, len(spec["remove"]), len(spec["add"])))
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
