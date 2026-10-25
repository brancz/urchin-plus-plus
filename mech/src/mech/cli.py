"""Build every printed part, export it, render it and check its fit.

    uv run mech build --boards DIR [--out DIR]
    uv run mech preview --boards DIR [--out FILE.html]

DIR holds kicad-cli's STEP exports of the halves and the dock PCB, {left,right,dock}.step
(scripts/mech/build.sh makes them). Outputs, under --out (default mech/build):

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

from . import checks, dock_checks
from . import params as P
from .board import Board
from .case import box, case, cover
from .tray import Dock

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
              "fit": [], "bed": [], "hardware": [], "insertion": [], "dock_pins": []}
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
        for name, shape in checks.moved_posts(board):
            report["fit"] += checks.fit(name, shape, board_parts + above, touching=("pcb",))
        report["hardware"] += [dict(r, side=side) for r in checks.screw_stacks(board) + checks.antenna_metal(board)
                               + checks.cell_rows(board) + checks.lip_rows(board)]
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

    # The dock: the tray in two pieces, checked with the dock PCB and both cased halves seated.
    dock = Dock.load()
    tray = dock.tray()
    pieces = dock.pieces(tray)
    for name, part in zip(("tray_left", "tray_right"), pieces):
        export_step(part, out / "step" / f"{name}.step")
        printable = on_bed(part)
        export_stl(printable, out / "stl" / f"{name}.stl", tolerance=0.01, angular_tolerance=0.1)
        report["bed"].append(checks.bed_fit(name, printable))
    rows, shapes = dock_checks.checks(dock, tray, pieces, args.boards)
    report["fit"] += rows["fit"]
    report["hardware"] += [dict(r, side="dock") for r in rows["hardware"]]
    report["dock_pins"] = rows["pins"]
    if not args.no_render:
        dock_render(out / "render", dock, pieces, shapes)

    failed = [r for r in report["fit"] + report["bed"] + report["hardware"] + report["insertion"] + report["dock_pins"]
              if not r["ok"]]
    report["ok"] = not failed
    (out / "checks.json").write_text(json.dumps(report, indent=1) + "\n")
    for r in failed:
        print("FAIL", json.dumps(r))
    print(f"mech: {len(report['fit'])} fit checks, {len(report['bed'])} bed checks, "
          f"{len(report['hardware'])} hardware checks, {len(report['insertion'])} insertion checks, "
          f"{len(report['dock_pins'])} dock pin checks, {len(failed)} failed; outputs in {out}")
    return 0 if not failed else 1


def dock_render(out, dock, pieces, shapes):
    from .render import render  # VTK: only when rendering
    trays = [(p, "tray", 1.0) for p in pieces]
    dock_pcb = [(s, "dock" if n == "dock pcb" else "pins" if " pin" in n else "parts", 1.0) for n, s in shapes["dock"]]
    cases = [(s, "case", 1.0) for _, s in shapes["cases"]]
    covers = [(Pos(dx, 0, P.Z_DOCK) * cover(b), "cover", 1.0) for b, dx in dock.halves()]
    boards = [(s, "board" if n.endswith(" pcb") else "parts", 1.0) for n, s in shapes["halves"]
              if n.endswith(" pcb") or n.endswith("3D model")]
    render(trays + dock_pcb, out / "tray-iso.png", "iso")
    render(trays + dock_pcb, out / "tray-top.png", "top")
    render(trays, out / "tray-under.png", "under")
    render(trays + dock_pcb + cases + covers + boards, out / "dock-iso.png", "iso")
    # A section through the left half's pin row, seen from the front: tray, dock PCB, the
    # compressed pins, the case's floor and window, and the half's PCB with its pads.
    x, y = dock.pins[1][0], dock.pins[1][1]
    keep = box(x - 14, x + 14, y, y + 30, -1, 40)
    cut = [(s & keep, c, o) for s, c, o in trays + dock_pcb + cases + boards]
    render([i for i in cut if i[0] is not None and i[0].solids()], out / "dock-pin-section.png", "front")


def dock_geometry(args):
    """Write (or with --check, compare) dock-pcb/geometry.json: the dock board follows the tray."""
    from .tray import Dock
    path = Path(args.out)
    text = json.dumps(Dock.load().pcb_geometry(), indent=1) + "\n"
    if args.check:
        if not path.exists() or path.read_text() != text:
            print(f"FAIL {path} is not what the tray CAD gives; run `mech dock-geometry`")
            return 1
        print(f"{path}: up to date")
        return 0
    path.write_text(text)
    print(f"wrote {path}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--boards", required=True, help="directory with left.step and right.step from kicad-cli")
    b.add_argument("--out", default=str(ROOT / "build"))
    b.add_argument("--no-render", action="store_true", help="skip the PNG renders (VTK needs a display or EGL)")
    g = sub.add_parser("dock-geometry", help="the dock board's outline and feature positions, from the tray")
    g.add_argument("--out", default=str(ROOT.parent / "dock-pcb" / "geometry.json"))
    g.add_argument("--check", action="store_true")
    v = sub.add_parser("preview", help="a 3D preview of the finished keyboard and dock, as one HTML page")
    v.add_argument("--boards", required=True, help="directory with left.step, right.step and dock.step from kicad-cli")
    v.add_argument("--out", default=str(ROOT / "build" / "preview.html"))
    args = ap.parse_args()
    if args.cmd == "preview":
        from . import preview
        sys.exit(preview.build(args.boards, args.out))
    sys.exit(build(args) if args.cmd == "build" else dock_geometry(args))


if __name__ == "__main__":
    main()
