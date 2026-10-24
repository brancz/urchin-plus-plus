#!/usr/bin/env python3
"""KiCad DRC of a half, or the dock, with the documented exceptions (verification layer 2).

    python3 scripts/checks/drc.py BOARD --half left|right|panel|dock [--unrouted-ok] [--json OUT] [--md OUT]

Runs `kicad-cli pcb drc` on a copy of the board with its zones refilled first
(kicad-cli doesn't refill; needs $KICAD_PY), with the rules from the board's
.kicad_pro (scripts/placement/board_setup.py), and applies hardware/drc_allow.json:
an error is excused only if a rule there names its type and this half, every
footprint it involves matches one of its designators (fnmatch; board-edge items
count as "Edge.Cuts"), and, if the rule has "require", at least one matches that.
With --half panel (the KiKit panel, designators suffixed _L/_R) each designator is
matched without its suffix, against the rules for the half the suffix names.
--half dock is the dock board (phase 7); a rule applies to it only if its "halves" name it.
Every other error fails. Warnings are listed by type and never fail; each type
is dispositioned in the phase report. --unrouted-ok skips unconnected items
(placement phase, before routing). Python 3.9; needs kicad-cli on PATH.
"""

import argparse
import collections
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


SUFFIX = {"L": "left", "R": "right"}


def refs(item):
    """(designator, half or None) of the footprint an item belongs to; board edges are 'Edge.Cuts'."""
    d = item["description"]
    if "Edge.Cuts" in d:
        return [("Edge.Cuts", None)]
    m = re.search(r"\bof ([A-Z]+\d+)(?:_([LR]))?\b", d) or re.search(r"^Footprint ([A-Z]+\d+)(?:_([LR]))?", d)
    return [(m.group(1), SUFFIX.get(m.group(2)))] if m else []


def excused(v, rules, half):
    found_halves = {h for item in v["items"] for _r, h in refs(item) if h}
    if half == "panel":
        if len(found_halves) != 1:
            return None
        half = found_halves.pop()
    for r in rules:
        if r["type"] != v["type"] or half not in r.get("halves", ["left", "right"]):
            continue
        found = [x for item in v["items"] for x, _h in refs(item)]
        match = lambda x, pats: any(fnmatch.fnmatchcase(x, pat) for pat in pats)
        if found and all(match(x, r["refs"] + ["Edge.Cuts"]) for x in found) \
                and any(x != "Edge.Cuts" for x in found) \
                and (not r.get("require") or any(match(x, r["require"]) for x in found)):
            return r
    return None


REFILL = """
import os, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[1])
sys.stdout.flush()
os._exit(0)
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--half", required=True, choices=("left", "right", "panel", "dock"))
    ap.add_argument("--unrouted-ok", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--md")
    args = ap.parse_args()
    rules = json.loads((ROOT / "hardware/drc_allow.json").read_text())["rules"]

    with tempfile.TemporaryDirectory() as tmp:
        # kicad-cli rewrites the .kicad_pro it loads; run on a copy so the working tree stays clean
        src = Path(args.board)
        for ext in (".kicad_pcb", ".kicad_pro", ".kicad_dru"):
            if src.with_suffix(ext).exists():
                shutil.copy(src.with_suffix(ext), Path(tmp) / ("board" + ext))
        subprocess.run([os.environ["KICAD_PY"], "-c", REFILL, str(Path(tmp) / "board.kicad_pcb")], check=True,
                       capture_output=True)
        out = Path(tmp) / "drc.json"
        subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all", "--units", "mm",
                        "-o", str(out), str(Path(tmp) / "board.kicad_pcb")], check=True, capture_output=True)
        report = json.loads(out.read_text())

    errors, excused_list, warnings = [], [], collections.Counter()
    for v in report["violations"]:
        if v["severity"] != "error":
            warnings[v["type"]] += 1
            continue
        r = excused(v, rules, args.half)
        if r:
            excused_list.append((v, r))
        else:
            errors.append(v)
    unconnected = report.get("unconnected_items", [])
    if not args.unrouted_ok:
        errors += unconnected

    def line(v):
        return "%s: %s | %s" % (v["type"], v["description"], " || ".join(
            "%s @(%.2f, %.2f)" % (i["description"], i["pos"]["x"], i["pos"]["y"]) for i in v["items"]))

    result = {"board": args.board, "half": args.half, "errors": [line(v) for v in errors],
              "excused": collections.Counter(r["reason"] for _v, r in excused_list),
              "warnings": dict(warnings), "unconnected": len(unconnected),
              "unrouted_ok": args.unrouted_ok}
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
    if args.md:
        md = ["# DRC: %s (%s)" % (args.board, args.half), "",
              "Errors: %d. Unconnected items: %d%s." % (len(errors), len(unconnected),
                                                         " (not routed yet; not counted)" if args.unrouted_ok else ""), ""]
        md += ["- " + e for e in result["errors"]]
        md += ["", "Excused errors (hardware/drc_allow.json):", ""]
        md += ["- %d x %s" % (n, reason) for reason, n in result["excused"].items()]
        md += ["", "Warnings by type:", ""] + ["- %s: %d" % (t, n) for t, n in sorted(warnings.items())]
        Path(args.md).write_text("\n".join(md) + "\n")
    print("drc %s (%s): %d errors, %d excused, %d warnings, %d unconnected%s" % (
        args.board, args.half, len(errors), len(excused_list), sum(warnings.values()), len(unconnected),
        " (ignored)" if args.unrouted_ok else ""))
    for e in result["errors"]:
        print("FAIL " + e)
    print("drc: %s" % ("OK" if not errors else "FAIL (%d)" % len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
