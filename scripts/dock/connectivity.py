#!/usr/bin/env python3
"""Check that the dock board has exactly the intended connections (phase 7).

    "$KICAD_PY" scripts/dock/connectivity.py [BOARD] [--json OUT]    default dock-pcb/layouts/dock/dock.kicad_pcb

The expected netlist below is written from the datasheets' pin numbers, not from
dock-pcb/dock.ato, so it is an independent second reading of the circuit: every
numbered pad of every footprint must be on the expected net, every assembled
footprint must carry the LCSC number listed here, and the board must have no other
nets. A pad no rule covers is a failure. Runs under KiCad's Python (pcbnew); 3.9.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]

EXPECTED = {
    # USB-TYPE-C-009 (C2927029) pin assignments: A5 CC1, B5 CC2, A9/B9 VBUS, A12/B12 GND;
    # pad 7 is the shell's four legs, grounded
    "J1": {"A5": "CC1", "B5": "CC2", "A9": "VBUS", "B9": "VBUS", "A12": "GND", "B12": "GND", "7": "GND"},
    # SMF6.0A (C123790): pad 1 cathode, pad 2 anode
    "D1": {"1": "DOCK_5V", "2": "GND"},
    # KT-0805G (C2297) p.2: pin 1 is + (anode), pin 2 the cathode
    "LED1": {"1": "LED_A", "2": "GND"},
    # pogo pins on each half's pads in order: GND, 5V, GND (the halves' TP1)
    "P1": {"1": "GND"}, "P2": {"1": "DOCK_5V"}, "P3": {"1": "GND"},
    "P4": {"1": "GND"}, "P5": {"1": "DOCK_5V"}, "P6": {"1": "GND"},
}
TWO_TERMINAL = {  # either orientation
    "F1": ("VBUS", "DOCK_5V"), "R1": ("CC1", "GND"), "R2": ("CC2", "GND"), "R3": ("DOCK_5V", "LED_A"),
}
LCSC = {"J1": "C2927029", "D1": "C123790", "LED1": "C2297", "F1": "C75464", "R1": "C25905", "R2": "C25905",
        "R3": "C25879", **{"P%d" % i: "C5221284" for i in range(1, 7)}}
MECHANICAL = {"H1", "H2"}  # screw holes: no numbered pads, not assembled
NETS = {"GND", "VBUS", "DOCK_5V", "CC1", "CC2", "LED_A"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board", nargs="?", default=str(ROOT / "dock-pcb/layouts/dock/dock.kicad_pcb"))
    ap.add_argument("--json")
    args = ap.parse_args()
    board = pcbnew.LoadBoard(args.board)
    problems, checked, seen = [], 0, set()
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        seen.add(ref)
        lcsc = fp.GetFieldText("LCSC") if fp.HasFieldByName("LCSC") else ""
        if ref in MECHANICAL:
            if any(p.GetNumber() for p in fp.Pads()) or lcsc:
                problems.append("%s: a screw hole with numbered pads or an LCSC number" % ref)
            continue
        if LCSC.get(ref) != lcsc:
            problems.append("%s carries LCSC %r, expected %r" % (ref, lcsc, LCSC.get(ref)))
        pads = [(p.GetNumber(), p.GetNetname()) for p in fp.Pads() if p.GetNumber()]
        if ref in TWO_TERMINAL:
            got = sorted(net for _n, net in pads)
            if got != sorted(TWO_TERMINAL[ref]):
                problems.append("%s pads on %s, expected %s" % (ref, got, sorted(TWO_TERMINAL[ref])))
            checked += len(pads)
            continue
        want = EXPECTED.get(ref)
        if want is None:
            problems.append("%s: no rule covers this footprint" % ref)
            continue
        for number, net in pads:
            checked += 1
            if number not in want:
                problems.append("%s pad %s: no rule" % (ref, number))
            elif net != want[number]:
                problems.append("%s pad %s on %r, expected %r" % (ref, number, net, want[number]))
        missing = set(want) - {n for n, _ in pads}
        if missing:
            problems.append("%s: pads %s missing" % (ref, sorted(missing)))
    for ref in sorted((set(EXPECTED) | set(TWO_TERMINAL) | MECHANICAL) - seen):
        problems.append("%s: not on the board" % ref)
    nets = {str(n) for n in board.GetNetsByName().keys()} - {""}
    if nets != NETS:
        problems.append("nets %s, expected %s" % (sorted(nets), sorted(NETS)))
    if args.json:
        report = {"board": os.path.relpath(args.board, ROOT), "pads_checked": checked, "problems": problems}
        Path(args.json).write_text(json.dumps(report, indent=1) + "\n")
    print("dock connectivity %s: %d numbered pads checked" % (args.board, checked))
    for p in problems:
        print("FAIL", p)
    print("dock connectivity: %s" % ("OK" if not problems else "FAIL (%d)" % len(problems)))
    sys.stdout.flush()
    os._exit(1 if problems else 0)  # KiCad 9's SWIG objects segfault in destructors at exit


if __name__ == "__main__":
    main()
