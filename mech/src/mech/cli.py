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

from build123d import Pos, export_step, export_stl

from . import checks, dock_checks
from . import params as P
from . import pins
from .board import Board
from .case import box, case, shell
from .tray import Dock

ROOT = Path(__file__).resolve().parents[2]


def on_bed(part):
    """The part moved to its print orientation (as it sits: every part prints that way), resting
    on z = 0, centred on the origin."""
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
        parts = {f"case_{side}": case(board), f"shell_{side}": shell(board)}
        for name, part in parts.items():
            export_step(part, out / "step" / f"{name}.step")
            printable = on_bed(part)  # the case floor down, the shell upright
            export_stl(printable, out / "stl" / f"{name}.stl", tolerance=0.01, angular_tolerance=0.1)
            report["bed"].append(checks.bed_fit(name, printable))

        board_parts = checks.board_parts(board, Path(args.boards) / f"{side}.step")
        sw = checks.switches(board)
        above = sw + checks.keycaps(board)
        c, v = parts[f"case_{side}"], parts[f"shell_{side}"]
        report["fit"] += checks.fit(f"case_{side}", c, board_parts + above, touching=("pcb",))
        # The shell sits on the PCB and holds the switches in its plate.
        report["fit"] += checks.fit(f"shell_{side}", v, board_parts + above,
                                    touching=("pcb",) + tuple(n for n, _ in sw))
        report["fit"] += checks.fit(f"shell_{side}", v, [(f"case_{side}", c)], touching=(f"case_{side}",))
        # The shell moved by its play on the switches, against the keycaps.
        report["fit"] += [dict(r, part=f"shell_{side}, moved by its play")
                          for r in checks.fit(f"shell_{side}", v, checks.keycaps(board, P.SHELL_PLAY))]
        # Hardware against the board's parts and the printed parts. The PCB and the printed
        # parts are what it screws into and passes through.
        printed = [(f"case_{side}", c), (f"shell_{side}", v)]
        # The puck's screw heads sit between the switches, which may come close but not overlap.
        for name, shape in checks.hardware(board):
            report["fit"] += checks.fit(name, shape, board_parts + above + printed,
                                        touching=("pcb", f"case_{side}", f"shell_{side}")
                                        + (tuple(n for n, _ in sw) if name.startswith("tenting puck") else ()))
        report["hardware"] += [dict(r, side=side) for r in checks.screw_stacks(board, v) + checks.antenna_metal(board)
                               + checks.cell_rows(board) + checks.lid_rows(board) + checks.lip_rows(board)
                               + checks.usb_rows(board, board_parts)]
        report["insertion"] += [dict(r, side=side) for r in checks.insertion(board, board_parts)]
        # The pogo pins on the charging pads, free, out through the case's window; and the jig
        # that holds them while they're soldered.
        report["fit"] += checks.fit(f"case_{side}", c, pins.pins(board))
        jig = pins.jig(board)
        export_step(jig, out / "step" / f"pin_jig_{side}.step")
        printable = on_bed(jig)  # the plate down, the legs up
        export_stl(printable, out / "stl" / f"pin_jig_{side}.stl", tolerance=0.01, angular_tolerance=0.1)
        report["bed"].append(checks.bed_fit(f"pin_jig_{side}", printable))
        rows, hw = dock_checks.jig_checks(board, jig, board_parts)
        report["fit"] += rows
        report["hardware"] += hw

        if args.no_render:
            continue
        from .render import render  # VTK: only when rendering
        pcb_and_parts = [(s, "parts" if n != "pcb" else "board", 1.0) for n, s in board_parts
                         if n == "pcb" or n.endswith("3D model")]
        switch_parts = [(s, "switch", 1.0) for _, s in sw]
        assembled = [(c, "case", 1.0), (v, "shell", 1.0)] + switch_parts + pcb_and_parts
        render(assembled, out / "render" / f"{side}-assembly-iso.png", "iso")
        render(assembled, out / "render" / f"{side}-assembly-top.png", "top")
        render([(c, "case", 1.0)] + pcb_and_parts, out / "render" / f"case_{side}-iso.png", "iso")
        render([(c, "case", 1.0)], out / "render" / f"case_{side}-under.png", "under")
        render(assembled, out / "render" / f"{side}-inner-edge.png", "inner" if board.inner_dir > 0 else "outer")
        render(assembled, out / "render" / f"{side}-outer-edge.png", "outer" if board.inner_dir > 0 else "inner")
        render([(v, "shell", 1.0)], out / "render" / f"shell_{side}-iso.png", "iso")
        render([(v, "shell", 1.0)], out / "render" / f"shell_{side}-under.png", "under")
        render([(jig, "cover", 1.0)] + [(s, "pins", 1.0) for _, s in pins.pins(board)] + pcb_and_parts,
               out / "render" / f"pin_jig_{side}-under.png", "under")

    # The dock: the tray in two pieces, the cover over the dock PCB's parts and the plate over
    # each pocket's floor, checked with the dock PCB and both cased halves seated.
    dock = Dock.load()
    tray = dock.tray()
    pieces = dock.pieces(tray)
    plates = dock.floor_plates()
    dparts = dock_checks.dock_parts(dock, Path(args.boards) / "dock.step")
    cover = dock.cover([(n.split()[1], s) for n, s in dparts[1:]])
    for name, part in zip(("tray_left", "tray_right", "dock_cover", "dock_floor_left", "dock_floor_right"),
                          pieces + (cover,) + plates):
        export_step(part, out / "step" / f"{name}.step")
        printable = on_bed(part)
        export_stl(printable, out / "stl" / f"{name}.stl", tolerance=0.01, angular_tolerance=0.1)
        report["bed"].append(checks.bed_fit(name, printable))
    rows, shapes = dock_checks.checks(dock, tray, pieces, cover, plates, dparts, args.boards)
    report["fit"] += rows["fit"]
    report["hardware"] += [dict(r, side="dock") for r in rows["hardware"]]
    report["dock_pins"] = rows["pins"]
    if not args.no_render:
        dock_render(out / "render", dock, pieces, cover, plates, shapes)

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


def dock_render(out, dock, pieces, cover, plates, shapes):
    from .render import render  # VTK: only when rendering
    trays = [(p, "tray", 1.0) for p in pieces]
    lid = [(cover, "cover", 1.0)]
    floors = [(p, "tray", 1.0) for p in plates]
    dock_pcb = [(s, "dock" if n == "dock pcb" else "parts", 1.0) for n, s in shapes["dock"]]
    pins_ = [(s, "pins", 1.0) for _, s in shapes["pins"]]
    cases = [(s, "case", 1.0) for _, s in shapes["cases"]]
    shells = [(s, "shell", 1.0) for _, s in shapes["shells"]]
    boards = [(s, "board" if n.endswith(" pcb") else "parts", 1.0) for n, s in shapes["halves"]
              if n.endswith(" pcb") or n.endswith("3D model")]
    render(trays + dock_pcb, out / "tray-iso.png", "iso")
    render(trays + dock_pcb + lid + floors, out / "tray-top.png", "top")
    render(trays + dock_pcb + lid + floors, out / "tray-finished-iso.png", "iso")
    render(trays + lid + dock_pcb + floors, out / "tray-back.png", "iso-back")
    render(trays + lid, out / "tray-under.png", "under")
    render([(cover, "cover", 1.0)], out / "dock_cover-under.png", "under")
    render(trays + lid + floors + dock_pcb + cases + shells + boards + pins_, out / "dock-iso.png", "iso")
    # A section through the left half's middle pin, seen from the front: tray, dock PCB and its
    # contact, the compressed pin, the case's floor and window, and the half's PCB.
    x, y, *_ = dock.contacts[1]
    keep = box(x - 14, x + 14, y, y + 30, -1, 40)
    cut = [(s & keep, c, o) for s, c, o in trays + floors + dock_pcb + cases + boards + pins_]
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
