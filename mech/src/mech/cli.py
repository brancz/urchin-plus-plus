"""Build every printed part, export it, render it and check its fit.

    uv run mech build --boards DIR [--out DIR]

DIR holds kicad-cli's STEP exports of the halves, {left,right}.step (scripts/mech/build.sh
makes them). Outputs, under --out (default mech/build):

    step/*.step   for CAD, and for a machined case later
    stl/*.stl     each part in its print orientation, on the bed
    render/*.png  assembly and part renders
    checks.json   every fit check; the command fails if any check fails
"""

import argparse
import json
import sys
from pathlib import Path

from build123d import Axis, Pos, Rot, export_step, export_stl

from . import checks
from .board import Board
from .case import case, cover

ROOT = Path(__file__).resolve().parents[2]


def on_bed(part, flip=False):
    """The part moved to its print orientation: flipped upside down if asked, resting on z = 0,
    centred on the origin."""
    if flip:
        part = Rot(180, 0, 0) * part
    bb = part.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * part


def build(args):
    out = Path(args.out)
    for sub in ("step", "stl") + (() if args.no_render else ("render",)):
        (out / sub).mkdir(parents=True, exist_ok=True)
    report = {"note": "fit rows only list pairs within MIN_GAP + 0.05 mm of each other's bounding box; "
                      "every other pair is farther apart",
              "fit": [], "bed": [], "hardware": [], "insertion": []}
    for side in ("left", "right"):
        board = Board.load(side)
        parts = {f"case_{side}": (case(board), False), f"cover_{side}": (cover(board), True)}
        for name, (part, flip) in parts.items():
            export_step(part, out / "step" / f"{name}.step")
            printable = on_bed(part, flip)
            export_stl(printable, out / "stl" / f"{name}.stl", tolerance=0.01, angular_tolerance=0.1)
            report["bed"].append(checks.bed_fit(name, printable))

        board_parts = checks.board_parts(board, Path(args.boards) / f"{side}.step")
        above = checks.switches(board) + checks.keycaps(board)
        c, v = parts[f"case_{side}"][0], parts[f"cover_{side}"][0]
        report["fit"] += checks.fit(f"case_{side}", c, board_parts + above, touching=("pcb",))
        report["fit"] += checks.fit(f"cover_{side}", v, board_parts + above, touching=("pcb",))
        report["fit"] += checks.fit(f"cover_{side}", v, [(f"case_{side}", c)], touching=(f"case_{side}",))
        # Hardware against the board's parts and the printed parts. The PCB and the printed
        # parts are what it screws to and passes through.
        printed = [(f"case_{side}", c), (f"cover_{side}", v)]
        for name, shape in checks.hardware(board):
            report["fit"] += checks.fit(name, shape, board_parts + above + printed,
                                        touching=("pcb", f"case_{side}", f"cover_{side}"))
        report["hardware"] += [dict(r, side=side) for r in checks.screw_stacks(board) + checks.antenna_metal(board)]
        report["insertion"] += [dict(r, side=side) for r in checks.insertion(board, board_parts)]

        if args.no_render:
            continue
        from .render import render  # VTK: only when rendering
        pcb_and_parts = [(s, "parts" if n != "pcb" else "board", 1.0) for n, s in board_parts
                         if n == "pcb" or n.endswith("3D model")]
        render([(c, "case", 1.0), (v, "cover", 1.0)] + pcb_and_parts, out / "render" / f"{side}-assembly-iso.png", "iso")
        render([(c, "case", 1.0), (v, "cover", 1.0)] + pcb_and_parts, out / "render" / f"{side}-assembly-top.png", "top")
        render([(c, "case", 1.0)], out / "render" / f"case_{side}-iso.png", "iso")
        render([(c, "case", 1.0)], out / "render" / f"case_{side}-under.png", "under")
        render([(c, "case", 1.0), (v, "cover", 1.0)] + pcb_and_parts, out / "render" / f"{side}-inner-edge.png", "inner" if board.inner_dir > 0 else "outer")
        render([(c, "case", 1.0), (v, "cover", 1.0)] + pcb_and_parts, out / "render" / f"{side}-outer-edge.png", "outer" if board.inner_dir > 0 else "inner")
        render([(v, "cover", 1.0)], out / "render" / f"cover_{side}-iso.png", "iso")

    failed = [r for r in report["fit"] + report["bed"] + report["hardware"] + report["insertion"] if not r["ok"]]
    report["ok"] = not failed
    (out / "checks.json").write_text(json.dumps(report, indent=1) + "\n")
    for r in failed:
        print("FAIL", json.dumps(r))
    print(f"mech: {len(report['fit'])} fit checks, {len(report['bed'])} bed checks, "
          f"{len(report['hardware'])} hardware checks, {len(report['insertion'])} insertion checks, "
          f"{len(failed)} failed; outputs in {out}")
    return 0 if not failed else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--boards", required=True, help="directory with left.step and right.step from kicad-cli")
    b.add_argument("--out", default=str(ROOT / "build"))
    b.add_argument("--no-render", action="store_true", help="skip the PNG renders (VTK needs a display or EGL)")
    args = ap.parse_args()
    sys.exit(build(args))


if __name__ == "__main__":
    main()
