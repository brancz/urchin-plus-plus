#!/usr/bin/env python3
"""Generate the parts that have no LCSC number: contact pads and mechanical outlines.

    "$KICAD_PY" scripts/parts/custom_parts.py [--parts-dir hardware/parts]

  BAT_PADS   top:    two 2.0 x 3.0 mm pads, 4.0 mm apart, for the battery's wires
                     (POS, NEG); hand-soldered, so no paste
  DOCK_PADS  bottom: three 2.5 x 4.0 mm pads at 4.0 mm pitch, GND / 5V / GND, the
                     charging contacts for the dock's pogo pins (symmetric, so a
                     half can't be connected the wrong way round); bare ENIG, no paste
  SWD_PADS   bottom: five 1.5 mm round pads at 2.54 mm pitch: VDD, SWDIO, SWDCLK,
                     RESET, GND, for the one-time bootloader flash; no paste
  BATTERY_401730  top: no pads; the outline of a 401730 LiPo cell (4.0 x 17 x 30 mm,
                     protection board included) on courtyard, fab and silkscreen, so
                     courtyard checks keep the cell clear of everything else on top
  STEEL_DISC bottom: no pads; a 10 mm self-adhesive steel disc for the dock magnets
  RUBBER_FOOT bottom: no pads; a 6 mm rubber foot, at least 3.5 mm tall: taller than
                     the tallest bottom part (USB-C receptacle 3.26 mm, module 3.0 mm);
                     the bottom has no room for wider feet near the corners
All are excluded from the BOM and position files. Bottom-side parts are written as
bottom-side library footprints (scripts/parts/footprint_to_bottom.py), then
sanitized like imported parts (scripts/lib/footprint.py). UUIDs are derived from
the part name, so reruns are byte-identical. KiCad's Python; Python 3.9.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from lib import footprint as fplib  # noqa: E402
from lib import sexp  # noqa: E402

PARTS = {
    "BAT_PADS": dict(side="top", prefix="BT", doc="Battery wire pads (hand-soldered).",
                     pads=[("1", "POS", -2.0, 0, "rect", 2.0, 3.0), ("2", "NEG", 2.0, 0, "rect", 2.0, 3.0)],
                     labels=[("+", -2.0, -2.6), ("-", 2.0, -2.6)]),
    "DOCK_PADS": dict(side="bottom", prefix="TP", doc="Dock charging contacts: GND / 5V / GND (bare ENIG).",
                      pads=[("1", "GND", -4.0, 0, "rect", 2.5, 4.0), ("2", "V5", 0, 0, "rect", 2.5, 4.0),
                            ("3", "GND", 4.0, 0, "rect", 2.5, 4.0)],
                      labels=[("GND", -4.0, 2.9), ("5V", 0, 2.9), ("GND", 4.0, 2.9)]),
    "BATTERY_401730": dict(side="top", prefix="BT", doc="Outline of the 401730 LiPo cell (hand-fitted).",
                           pads=[], labels=[("401730", 0, 0)], body=("rect", 17.0, 30.0)),
    "STEEL_DISC": dict(side="bottom", prefix="MK", doc="Steel disc position for the dock magnets (hand-fitted).",
                       pads=[], labels=[], body=("circle", 10.0)),
    "RUBBER_FOOT": dict(side="bottom", prefix="MK", doc="Rubber foot position, 6 mm, at least 3.5 mm tall (hand-fitted).",
                        pads=[], labels=[], body=("circle", 6.0)),
    "SWD_PADS": dict(side="bottom", prefix="TP", doc="SWD pads for the one-time bootloader flash.",
                     pads=[("1", "VDD", -5.08, 0, "circle", 1.5, 1.5), ("2", "SWDIO", -2.54, 0, "circle", 1.5, 1.5),
                           ("3", "SWDCLK", 0, 0, "circle", 1.5, 1.5), ("4", "RESET", 2.54, 0, "circle", 1.5, 1.5),
                           ("5", "GND", 5.08, 0, "circle", 1.5, 1.5)],
                     labels=[("V", -5.08, 1.6), ("IO", -2.54, 1.6), ("CK", 0, 1.6), ("RS", 2.54, 1.6), ("G", 5.08, 1.6)]),
}

SYMBOL = '''(kicad_symbol_lib
	(version 20241209)
	(generator "urchin++")
	(symbol "{name}"
		(in_bom no)
		(on_board yes)
		(property "Reference" "{prefix}" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
		(property "Value" "{name}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
		(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(property "Description" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(symbol "{name}_1_1"
{pins}		)
	)
)
'''
PIN = ('\t\t\t(pin passive line (at {x} 0 90) (length 2.54) (name "{sig}" (effects (font (size 1.27 1.27)))) '
       '(number "{num}" (effects (font (size 1.27 1.27)))))\n')


def mm(v):
    return pcbnew.FromMM(v)


def footprint(name, spec):
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("", name))
    fp.SetReference(spec["prefix"] + "**")
    fp.SetValue(name)
    fp.SetAttributes((pcbnew.FP_SMD if spec["pads"] else pcbnew.FP_BOARD_ONLY) |
                     pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    for num, _sig, x, y, shape, w, h in spec["pads"]:
        p = pcbnew.PAD(fp)
        p.SetNumber(num)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetShape(pcbnew.F_Cu, pcbnew.PAD_SHAPE_RECT if shape == "rect" else pcbnew.PAD_SHAPE_CIRCLE)
        p.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(mm(w), mm(h)))
        p.SetLayerSet(pcbnew.LSET().AddLayer(pcbnew.F_Cu).AddLayer(pcbnew.F_Mask))  # no paste: nothing is placed
        p.SetFPRelativePosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.Add(p)
    for text, x, y in spec["labels"]:
        t = pcbnew.PCB_TEXT(fp)
        t.SetText(text)
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        t.SetTextThickness(mm(0.12))
        t.SetFPRelativePosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.Add(t)
    body = spec.get("body")
    if body and body[0] == "circle":
        for layer, d, width in ((pcbnew.F_CrtYd, body[1] + 0.5, 0.05), (pcbnew.F_SilkS, body[1], 0.12)):
            c = pcbnew.PCB_SHAPE(fp)
            c.SetShape(pcbnew.SHAPE_T_CIRCLE)
            c.SetCenter(pcbnew.VECTOR2I(0, 0))
            c.SetEnd(pcbnew.VECTOR2I(mm(d / 2), 0))
            c.SetLayer(layer)
            c.SetWidth(mm(width))
            fp.Add(c)
        for a, b in (((-1, 0), (1, 0)), ((0, -1), (0, 1))):  # atopile crashes on silkscreen of circles only
            s = pcbnew.PCB_SHAPE(fp)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
            s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
            s.SetLayer(pcbnew.F_SilkS)
            s.SetWidth(mm(0.12))
            fp.Add(s)
        return fp
    if body:  # rectangle centred on the origin: courtyard 0.25 mm outside the silkscreen outline
        rects = [(pcbnew.F_CrtYd, body[1] / 2 + 0.25, body[2] / 2 + 0.25, 0.05),
                 (pcbnew.F_SilkS, body[1] / 2, body[2] / 2, 0.12)]
    else:
        xs = [x + s * w / 2 for _n, _s, x, _y, _sh, w, _h in spec["pads"] for s in (-1, 1)]
        ys = [y + s * h / 2 for _n, _s, _x, y, _sh, _w, h in spec["pads"] for s in (-1, 1)]
        rects = [(pcbnew.F_CrtYd, (max(xs) - min(xs)) / 2 + 0.5, (max(ys) - min(ys)) / 2 + 0.5, 0.05)]
        centre = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
    for layer, hx, hy, width in rects:
        cx, cy = (0, 0) if body else centre
        left, right, top, bottom = cx - hx, cx + hx, cy - hy, cy + hy
        for a, b in (((left, top), (right, top)), ((right, top), (right, bottom)),
                     ((right, bottom), (left, bottom)), ((left, bottom), (left, top))):
            s = pcbnew.PCB_SHAPE(fp)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
            s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
            s.SetLayer(layer)
            s.SetWidth(mm(width))
            fp.Add(s)
    return fp


def one(parts_dir, name):
    spec = PARTS[name]
    # KiCad orders a footprint's items partly by UUID: seed the generator so reruns match
    pcbnew.KIID.SeedGenerator(sum(ord(c) * 31 ** i for i, c in enumerate(name)) % 2 ** 31)
    out = parts_dir / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    tmp = tempfile.mkdtemp()
    lib = os.path.join(tmp, "lib.pretty")
    os.mkdir(lib)
    pcbnew.PCB_IO_KICAD_SEXPR().FootprintSave(lib, footprint(name, spec))
    shutil.copy(os.path.join(lib, name + ".kicad_mod"), out / (name + ".kicad_mod"))
    pins = "".join(PIN.format(x=5.08 * i, sig=sig, num=num) for i, (num, sig, *_r) in enumerate(spec["pads"]))
    (out / (name + ".kicad_sym")).write_text(SYMBOL.format(name=name, prefix=spec["prefix"], pins=pins))
    lines = ['#pragma experiment("TRAITS")', "import is_atomic_part", "import has_designator_prefix", "",
             "component %s_package:" % name,
             '    """%s Generated by scripts/parts/custom_parts.py; not in the JLC BOM."""' % spec["doc"],
             '    trait is_atomic_part<manufacturer="none", partnumber="%s", footprint="%s.kicad_mod", symbol="%s.kicad_sym">'
             % (name, name, name),
             '    trait has_designator_prefix<prefix="%s">' % spec["prefix"], ""]
    declared = set()
    for num, sig, *_r in spec["pads"]:
        lines.append("    %s%s ~ pin %s" % ("" if sig in declared else "signal ", sig, num))
        declared.add(sig)
    (out / (name + ".ato")).write_text("\n".join(lines) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parts-dir", default=str(ROOT / "hardware/parts"))
    ap.add_argument("--one", help=argparse.SUPPRESS)
    args = ap.parse_args()
    parts = Path(args.parts_dir)
    if args.one:
        one(parts, args.one)
        sys.stdout.flush()
        os._exit(0)  # KiCad 9's SWIG objects segfault in destructors at exit
    for name, spec in PARTS.items():
        subprocess.run([sys.executable, __file__, "--parts-dir", str(parts), "--one", name], check=True)
        if spec["side"] == "bottom":
            subprocess.run([sys.executable, str(ROOT / "scripts/parts/footprint_to_bottom.py"), str(parts / name), name],
                           check=True, stdout=subprocess.DEVNULL)
        f = parts / name / (name + ".kicad_mod")
        node = sexp.load(f)
        fplib.sanitize(node)  # e.g. pcbnew's default thermal_bridge_angle, which atopile drops
        n = iter(range(10 ** 6))
        f.write_text(re.sub(r'\(uuid "[0-9a-f-]+"\)', lambda m: '(uuid "%s")' % uuid.uuid5(
            uuid.NAMESPACE_URL, "urchin++/%s/%d" % (name, next(n))), "\n".join(sexp.dump_lines(node)) + "\n"))
        print("%-10s %s" % (name, spec["side"]))


if __name__ == "__main__":
    main()
