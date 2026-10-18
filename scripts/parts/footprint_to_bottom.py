#!/usr/bin/env python3
"""Rewrite a library footprint as a bottom-side footprint, in place.

    "$KICAD_PY" scripts/parts/footprint_to_bottom.py PART_DIR FOOTPRINT_NAME

CLAUDE.md rule 2 puts every assembled part on the bottom. atopile re-syncs each
footprint from its library on every build by flipping it to the library's side
and back, and that flip corrupts text rotations on bottom-side footprints
(reports/phase0/). A library footprint that is already on B.Cu needs no flip.
KiCad's own library writer always stores footprints front-side, so this script
flips the footprint with pcbnew and writes the board representation of it.
Runs under KiCad's Python (pcbnew); Python 3.9.
"""

import os
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib import sexp  # noqa: E402

BOARD_ONLY = ("net", "uuid", "path")  # board-instance data; library footprints don't carry it


def strip(node):
    if not isinstance(node, list):
        return node
    return [strip(c) for c in node if not (isinstance(c, list) and sexp.head(c) in BOARD_ONLY)]


def main():
    lib, name = sys.argv[1].rstrip("/"), sys.argv[2]
    pcbnew.KIID.SeedGenerator(0)  # new UUIDs decide the order KiCad writes items in; keep reruns identical
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        sys.exit("no footprint %s in %s" % (name, lib))
    if fp.GetLayer() == pcbnew.B_Cu:
        print("%s already bottom-side" % name)
        return
    board = pcbnew.BOARD()
    board.Add(fp)  # Flip needs a parent board
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    tmp = os.path.join(tempfile.mkdtemp(), "t.kicad_pcb")
    pcbnew.SaveBoard(tmp, board)
    root = sexp.load(tmp)
    node = strip(sexp.children(root, "footprint")[0])
    node = [c for c in node if not (isinstance(c, list) and sexp.head(c) == "at")]
    node[2:2] = [[sexp.Atom("version"), sexp.child(root, "version")[1]],
                 [sexp.Atom("generator"), "urchin++ footprint_to_bottom"]]
    with open(os.path.join(lib, name + ".kicad_mod"), "w", encoding="utf-8") as f:
        f.write("\n".join(sexp.dump_lines(node)) + "\n")
    print("%s -> %s" % (name, fp.GetLayerName()))


if __name__ == "__main__":
    main()
