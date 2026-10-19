#!/usr/bin/env python3
"""Check that a half's board has exactly the intended connections (verification layer 1).

    "$KICAD_PY" scripts/checks/connectivity.py BOARD --half left|right [--json OUT] [--netlist OUT]

The expected netlist below is written from the datasheets' pin numbers, not from
the .ato sources, so it is an independent second reading of the circuit:
every numbered pad of every footprint must be on the expected net (by name), or
alone on its net where it is meant to be unconnected ("open"). Every assembled
footprint must carry the LCSC number listed here for its designator (catches a
swapped value). The keys and the GPIO functions come from hardware/pinmap.json
(generated per half); each GPIO's module pin is checked against the E73 GPIO table
below (read from the datasheet separately from hardware/parts.json, which must
agree). A pad no rule covers is a failure. --netlist writes the board's nets (every pad,
by net name) as text. Runs under KiCad's Python (pcbnew); Python 3.9.
"""

import argparse
import collections
import json
import os
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
OPEN = None

# designator -> {pad number: net name or OPEN}; "*" applies to pads not listed.
EXPECTED = {
    # E73-2G4M08S1C datasheet pin table (docs/datasheets/C356849_E73-2G4M08S1C.pdf pp.5-7)
    "U1": {"5": "GND", "21": "GND", "24": "GND", "23": "VDDH", "19": "VDD", "27": "VBUS",
           "29": "USB_DN", "31": "USB_DP", "26": "RESET_N", "37": "SWDIO", "39": "SWDCLK",
           "25": OPEN,  # DCCH: REG0 runs as an LDO
           "*": OPEN},  # GPIOs: unconnected unless pinmap.json assigns them (filled in below)
    # BQ24073 (C15220): 1 TS, 2/3 BAT, 4 /CE, 5 EN2, 6 EN1, 7 /PGOOD, 8 VSS, 9 /CHG, 10/11 OUT,
    # 12 ILIM, 13 IN, 14 TMR, 15 TD, 16 ISET, 17 thermal pad
    "U2": {"1": "TS", "2": "VBAT", "3": "VBAT", "4": "GND", "5": "GND", "6": "GND", "7": "PGOOD_N",
           "8": "GND", "9": "CHG_N", "10": "VSYS", "11": "VSYS", "12": "ILIM", "13": "VIN",
           "14": OPEN, "15": "GND", "16": "ISET", "17": "GND"},
    # USBLC6-2SC6: 1/6 I/O1, 2 GND, 3/4 I/O2, 5 VBUS
    "U3": {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "2": "GND", "5": "VBUS"},
    # TYPE-C-31-M-12: A1/B12 and B1/A12 GND, A4/B9 and B4/A9 VBUS, shell 1-4
    "J1": {"A1B12": "GND", "B1A12": "GND", "A4B9": "VBUS", "B4A9": "VBUS", "A5": "CC1", "B5": "CC2",
           "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN", "A8": OPEN, "B8": OPEN,
           "1": "GND", "2": "GND", "3": "GND", "4": "GND"},
    # 1N5819WS, SMF6.0A: pad 1 cathode, pad 2 anode
    "D1": {"1": "VIN", "2": "VBUS"},
    "D2": {"1": "VIN", "2": "DOCK_5V"},
    "D3": {"1": "DOCK_5V", "2": "GND"},
    "D4": {"1": "CHG_N", "2": "CHG_SENSE"},
    "D5": {"1": "PGOOD_N", "2": "PGOOD_SENSE"},
    # MSK12C02: 2 common, 1/3 throws, 4 shell
    "SW35": {"1": "VSYS", "2": "VDDH", "3": OPEN, "4": "GND"},
    "SW36": {"1": "RESET_N", "2": "GND"},
    # MHT151RGBCT: 1 common anode, 2 blue, 3 green, 4 red
    "LED1": {"1": "VDD", "2": "LED_B_K", "3": "LED_G_K", "4": "LED_R_K"},
    "LED2": {"1": "VIN", "2": OPEN, "3": "LED_CHG_G", "4": "LED_CHG_R"},
    "BT1": {"1": "VBAT", "2": "GND"},
    "TP1": {"1": "GND", "2": "DOCK_5V", "3": "GND"},
    "TP2": {"1": "VDD", "2": "SWDIO", "3": "SWDCLK", "4": "RESET_N", "5": "GND"},
}
TWO_TERMINAL = {  # resistors and capacitors: either orientation
    "R1": ("TS", "GND"), "R2": ("CC1", "GND"), "R3": ("CC2", "GND"), "R4": ("ILIM", "GND"),
    "R5": ("ISET", "GND"), "R6": ("LED_CHG_R", "CHG_N"), "R7": ("LED_CHG_G", "PGOOD_N"),
    "R8": ("LED_R_K", "LED_R"), "R9": ("LED_G_K", "LED_G"), "R10": ("LED_B_K", "LED_B"),
    "C1": ("VDD", "GND"), "C2": ("VIN", "GND"), "C3": ("VSYS", "GND"), "C4": ("VBAT", "GND"),
    "C5": ("VBUS", "GND"), "C6": ("VDDH", "GND"), "R11": ("VBUS", "GND"),
}
# E73-2G4M08S1C datasheet p.6 pin table: module pin -> nRF52840 GPIO
E73_GPIO = {1: "P1_11", 2: "P1_10", 3: "P0_03", 4: "P0_28", 6: "P1_13", 7: "P0_02", 8: "P0_29", 9: "P0_31",
            10: "P0_30", 11: "P0_00", 12: "P0_26", 13: "P0_01", 14: "P0_06", 15: "P0_05", 16: "P0_08", 17: "P1_09",
            18: "P0_04", 20: "P0_12", 22: "P0_07", 26: "P0_18", 28: "P0_15", 30: "P0_17", 32: "P0_20", 33: "P0_13",
            34: "P0_22", 35: "P0_24", 36: "P1_00", 38: "P1_02", 40: "P1_04", 41: "P0_09", 42: "P1_06", 43: "P0_10"}
NEVER_GPIO = {"P0_18", "P0_09", "P0_10"}  # reset; NFC
# designator -> LCSC part (value and package), from the BOM intent in docs/ARCHITECTURE.md
LCSC = {"U1": "C356849", "U2": "C15220", "U3": "C7519", "J1": "C165948",
        "D1": "C191023", "D2": "C191023", "D4": "C191023", "D5": "C191023", "D3": "C123790",
        "SW35": "C431540", "SW36": "C720477", "LED1": "C409782", "LED2": "C409782",
        "R1": "C25744", "R11": "C25744",                                  # 10 k
        "R2": "C25905", "R3": "C25905", "R4": "C25905", "R5": "C25905",  # 5.1 k
        "R6": "C11702", "R7": "C11702",                                   # 1 k
        "R8": "C25117",                                                   # 470 R
        "R9": "C25091", "R10": "C25091",                                  # 220 R
        "C1": "C23733",                                                   # 4.7 uF
        "C2": "C15849",                                                   # 1 uF 50 V
        "C5": "C19666",                                                   # 4.7 uF
        "C3": "C19702", "C4": "C19702", "C6": "C19702"}                   # 10 uF
FUNCTION_NETS = {"led_r": "LED_R", "led_g": "LED_G", "led_b": "LED_B",
                 "chg_sense": "CHG_SENSE", "pgood_sense": "PGOOD_SENSE"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--half", required=True, choices=("left", "right"))
    ap.add_argument("--json")
    ap.add_argument("--netlist")
    args = ap.parse_args()

    pinmap = json.loads((ROOT / "hardware/pinmap.json").read_text())["halves"][args.half]
    parts = json.loads((ROOT / "hardware/parts.json").read_text())["parts"]
    e73 = next(p for p in parts if p["lcsc"] == "C356849")["pin_names"]
    problems = []

    expected = {ref: dict(pads) for ref, pads in EXPECTED.items()}
    for num, gpio in E73_GPIO.items():
        if e73.get(str(num)) != gpio:
            problems.append("parts.json names E73 pin %d %s, the datasheet table here says %s" % (num, e73.get(str(num)), gpio))
    for w in pinmap:
        pin = str(w["module_pin"])
        if E73_GPIO.get(int(pin)) != w["gpio"]:
            problems.append("pinmap %s: %s is not module pin %s (datasheet: %s)" % (w["signal"], w["gpio"], pin, E73_GPIO.get(int(pin))))
        if w["gpio"] in NEVER_GPIO:
            problems.append("pinmap %s: %s is reserved" % (w["signal"], w["gpio"]))
        if pin in expected["U1"]:
            problems.append("pinmap %s: module pin %s already has a fixed role" % (w["signal"], pin))
        if w["kind"] == "key":
            net = "KEY_" + w["signal"].upper()
            expected[w["ref"]] = {w["gpio_pad"]: net, w["gnd_pad"]: "GND"}
        else:
            net = FUNCTION_NETS[w["signal"]]
        expected["U1"][pin] = net
    keys = {w["ref"] for w in pinmap if w["kind"] == "key"}
    if len(keys) != 17:
        problems.append("pinmap has %d keys, expected 17" % len(keys))

    board = pcbnew.LoadBoard(args.board)
    members = collections.Counter(p.GetNetname() for f in board.GetFootprints() for p in f.Pads() if p.GetNetname())
    seen, checked = set(), 0
    for f in board.GetFootprints():
        ref = f.GetReference()
        seen.add(ref)
        assembled = not (f.IsExcludedFromBOM() or f.IsExcludedFromPosFiles())
        lcsc = f.GetFieldText("LCSC") if f.HasFieldByName("LCSC") else ""
        if assembled and LCSC.get(ref) != lcsc:
            problems.append("%s carries LCSC %r, expected %r" % (ref, lcsc, LCSC.get(ref)))
        if not assembled and ref in LCSC:
            problems.append("%s is excluded from BOM/CPL but should be assembled" % ref)
        for p in f.Pads():
            num, net = p.GetNumber(), p.GetNetname()
            if not num:  # mechanical holes
                if net:
                    problems.append("%s: unnumbered pad on net %s" % (ref, net))
                continue
            checked += 1
            where = "%s.%s" % (ref, num)
            if ref in TWO_TERMINAL:
                want = set(TWO_TERMINAL[ref])
                if net not in want:
                    problems.append("%s on %r, expected one of %s" % (where, net, sorted(want)))
                continue
            rules = expected.get(ref)
            if rules is None:
                problems.append("%s: no rule for this footprint" % where)
                continue
            want = rules[num] if num in rules else rules.get("*", "MISSING")
            if want == "MISSING":
                problems.append("%s: no rule for this pad" % where)
            elif want is OPEN:
                if net and members[net] > 1:
                    problems.append("%s should be unconnected, is on %s with %d pads" % (where, net, members[net]))
            elif net != want:
                problems.append("%s on %r, expected %s" % (where, net, want))
    for ref in TWO_TERMINAL:
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            continue
        nets = sorted(p.GetNetname() for p in fp.Pads())
        if nets != sorted(TWO_TERMINAL[ref]):
            problems.append("%s connects %s, expected %s" % (ref, nets, sorted(TWO_TERMINAL[ref])))
    for ref in sorted(set(expected) | set(TWO_TERMINAL)):
        if ref not in seen:
            problems.append("%s missing from the board" % ref)

    if args.netlist:
        nets = collections.defaultdict(list)
        for f in board.GetFootprints():
            for p in f.Pads():
                if p.GetNumber():
                    nets[p.GetNetname() or "(no net)"].append("%s.%s" % (f.GetReference(), p.GetNumber()))
        key = lambda s: [int(t) if t.isdigit() else t for t in __import__("re").split(r"(\d+)", s)]
        lines = ["# %s: nets by name, every numbered pad (single-pad nets are unconnected pins)" % args.board]
        for n in sorted(nets, key=key):
            lines.append("%-14s %s" % (n, " ".join(sorted(nets[n], key=key))))
        Path(args.netlist).write_text("\n".join(lines) + "\n")

    result = {"board": args.board, "half": args.half, "pads_checked": checked, "problems": problems}
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2) + "\n")
    print("connectivity %s (%s): %d numbered pads checked" % (args.board, args.half, checked))
    for p in problems:
        print("FAIL " + p)
    print("connectivity: %s" % ("OK" if not problems else "FAIL (%d)" % len(problems)))
    sys.stdout.flush()
    os._exit(1 if problems else 0)  # KiCad 9's SWIG objects can segfault in destructors at exit


if __name__ == "__main__":
    main()
