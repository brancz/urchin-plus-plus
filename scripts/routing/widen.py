#!/usr/bin/env python3
"""Widen thin tracks where the clearance allows (phase 4).

    "$KICAD_PY" scripts/routing/widen.py BOARD [--to 0.15]

Freerouting's narrowest width variants and the neck-downs at pads leave tracks at JLC's
0.127 mm 2-layer minimum. This widens every track narrower than --to (default 0.15 mm,
the boards' minimum connection width) to that width. It then runs KiCad's DRC (kicad-cli on
a copy with the zones refilled), puts every widened track that takes part in a DRC error
back to its old width, and repeats until the DRC finds no error the board didn't already
have. The zones are refilled and BOARD is saved. Prints a JSON summary. Runs under KiCad's
Python (one board load per process: KiCad 9's SWIG); Python 3.9; needs kicad-cli on PATH.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pcbnew

ROUNDS = 6


def nm(v):
    return int(round(v * 1e6))


def thin_tracks(board_path, width):
    """{uuid: width in nm} of the tracks (not vias) narrower than width."""
    board = pcbnew.LoadBoard(board_path)
    return {t.m_Uuid.AsString(): t.GetWidth() for t in board.GetTracks()
            if t.GetClass() == "PCB_TRACK" and t.GetWidth() < width}


def apply(board_path, widths, out):
    """Child process: set the given track widths, refill the zones, save to out."""
    board = pcbnew.LoadBoard(board_path)
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    zones = list(board.Zones())
    for t in tracks:
        w = widths.get(t.m_Uuid.AsString())
        if w is not None:
            t.SetWidth(w)
    pcbnew.ZONE_FILLER(board).Fill(zones)
    board.Save(out)


def drc_errors(board_path, project):
    """Set of (type, uuids) of the DRC errors of a board (zones already filled)."""
    work = tempfile.mkdtemp()
    try:
        copy = os.path.join(work, "b.kicad_pcb")
        shutil.copy(board_path, copy)
        shutil.copy(project, os.path.join(work, "b.kicad_pro"))  # kicad-cli rewrites the project: use a copy
        report = os.path.join(work, "drc.json")
        subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-error", "-o", report, copy],
                       capture_output=True, check=True)
        d = json.load(open(report))
        return {(v["type"], tuple(sorted(i.get("uuid", "") for i in v["items"]))) for v in d["violations"]
                if v.get("severity") == "error"}
    finally:
        shutil.rmtree(work)


def run(cmd):
    child = subprocess.run(cmd, capture_output=True, text=True)
    if child.returncode != 0:
        sys.exit("failed: %s\n%s" % (" ".join(cmd), child.stderr[-2000:]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--to", type=float, default=0.15, help="mm")
    ap.add_argument("--apply", nargs=2, metavar=("WIDTHS_JSON", "OUT"), help=argparse.SUPPRESS)
    ap.add_argument("--list", metavar="OUT_JSON", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.apply:
        apply(args.board, json.load(open(args.apply[0])), args.apply[1])
        sys.stdout.flush()
        os._exit(0)
    if args.list:
        json.dump(thin_tracks(args.board, nm(args.to)), open(args.list, "w"))
        sys.stdout.flush()
        os._exit(0)

    project = os.path.splitext(args.board)[0] + ".kicad_pro"
    work = tempfile.mkdtemp()
    me = [sys.executable, os.path.abspath(__file__)]
    old_json = os.path.join(work, "old.json")
    run(me + [args.board, "--list", old_json, "--to", str(args.to)])
    old = json.load(open(old_json))
    base = os.path.join(work, "base.kicad_pcb")
    shutil.copy(args.board, base)
    json.dump({}, open(os.path.join(work, "none.json"), "w"))
    run(me + [args.board, "--apply", os.path.join(work, "none.json"), base])
    known = drc_errors(base, project)
    widened = set(old)
    for _ in range(ROUNDS):
        trial = os.path.join(work, "trial.kicad_pcb")
        json.dump({u: nm(args.to) for u in widened}, open(os.path.join(work, "w.json"), "w"))
        run(me + [args.board, "--apply", os.path.join(work, "w.json"), trial])
        new = drc_errors(trial, project) - known
        culprits = {u for _type, uuids in new for u in uuids if u in widened}
        if not new:
            break
        if not culprits:
            sys.exit("widening caused DRC errors not involving a widened track: %s" % sorted(new)[:5])
        widened -= culprits
    else:
        sys.exit("DRC still finds new errors after %d rounds" % ROUNDS)
    shutil.copy(trial, args.board)
    shutil.rmtree(work)
    print(json.dumps({"board": args.board, "to": args.to, "thin": len(old), "widened": len(widened),
                      "kept": len(old) - len(widened)}))
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
