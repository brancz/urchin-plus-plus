#!/usr/bin/env python3
"""Freerouting smoke test for the round-trip board: rip up, autoroute, import.

    "$KICAD_PY" scripts/roundtrip/autoroute_smoke.py BOARD WORK_DIR

Deletes all tracks and vias (zones stay), exports a
Specctra DSN, runs Freerouting headless ($FREEROUTING_JAR, java on PATH),
imports the session and saves. The caller runs DRC on the result.
"""

import json
import os
import subprocess
import sys

import pcbnew


def main():
    board_path, work = sys.argv[1], sys.argv[2]
    os.makedirs(work, exist_ok=True)
    dsn, ses = os.path.join(work, "board.dsn"), os.path.join(work, "board.ses")

    board = pcbnew.LoadBoard(board_path)
    for t in list(board.GetTracks()):
        board.Delete(t)
    off = [fp.GetReference() for fp in board.GetFootprints() if pcbnew.ToMM(fp.GetPosition().x) < 100]
    if off:
        raise SystemExit("footprints off the board: %s (run pcb_ops.py place-offboard first)" % off)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit("DSN export failed")

    with open(os.path.join(work, "freerouting.log"), "w") as log:
        res = subprocess.run(["java", "-jar", os.environ["FREEROUTING_JAR"], "-de", dsn, "-do", ses,
                              "--router.autorouter.max_passes=20"], stdout=log, stderr=subprocess.STDOUT)
    if res.returncode != 0 or not os.path.exists(ses):
        raise SystemExit("Freerouting failed (see %s/freerouting.log)" % work)
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit("SES import failed")

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(board_path, board)
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    print(json.dumps({"tracks": len(tracks), "vias": len(vias)}))


if __name__ == "__main__":
    main()
