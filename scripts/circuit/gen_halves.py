#!/usr/bin/env python3
"""Generate the per-half wiring: hardware/halves.ato and hardware/pinmap.json.

    python3 scripts/circuit/gen_halves.py [--check] [--md OUT]

Both halves use the same circuit (hardware/core.ato) and the same module
orientation (antenna up, into the old nice!nano notch), but the keys sit on the
module's left on the left half and on its right on the right half. So each half
gets its own GPIO map, chosen from geometry:
  - every key's socket has two pads; the one nearer the module is the GPIO, the
    other goes to ground (a switch has no polarity);
  - the 17 keys and the five GPIO functions of the core (status LED R/G/B, CHG and
    PGOOD sense) are matched to the module's free GPIOs by a minimum-total-distance
    assignment (Hungarian algorithm). The distance is the shortest path from the
    module pad's side to the target around the module: nothing may cross the module
    body or the antenna end, and there is no board beyond the antenna, so paths to
    the far side go round the module's bottom corners. Pads on the module's inner
    rows cost a little more (they need a via to escape), and so do the pads next to
    the antenna end.
Excluded GPIOs: P0.18 (reset), P0.09/P0.10 (NFC pins; free as GPIOs only after a
UICR change). Positions come from hardware/geometry/urchin.json (keys) and
hardware/placement.json (module, LEDs' resistors, sense diodes). --check fails
if the generated files differ from the committed ones. Python 3.9.
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from lib import sexp  # noqa: E402

HW = ROOT / "hardware"
EXCLUDED = {"P0_18", "P0_09", "P0_10"}
INNER_PENALTY = 1.5      # mm: inner-row module pads need a via or a squeeze to escape
ANTENNA_PENALTY = 3.0    # mm: pads within 2 mm of the module's first pad row by the antenna
FUNCTIONS = {  # core signal -> part whose position is the target
    "led_r": "R8", "led_g": "R9", "led_b": "R10", "chg_sense": "D4", "pgood_sense": "D5",
}


def rotate(x, y, deg):
    """KiCad footprint rotation (counter-clockwise on screen, y down)."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return x * c + y * s, -x * s + y * c


def pads(path):
    node = sexp.load(path)
    out = {}
    for p in sexp.children(node, "pad"):
        if p[1]:
            at = sexp.child(p, "at")
            out.setdefault(p[1], (float(at[1]), float(at[2])))
    return out


def module_pins():
    """GPIO name -> (pad number, local x, local y) from the part's .ato and footprint."""
    part = HW / "parts/C356849"
    pos = pads(next(part.glob("*.kicad_mod")))
    pins = {}
    for line in (part / "C356849.ato").read_text().splitlines():
        m = re.match(r"\s+(?:signal )?(P\d_\d\d) ~ pin (\d+)$", line)
        if m and m.group(1) not in EXCLUDED:
            pins[m.group(1)] = (int(m.group(2)),) + pos[m.group(2)]
    return pins


OBSTACLE = (-7.5, 7.5, -30.0, 8.0)  # module-local box the paths go around; open only at the bottom


def _crosses(a, b, box):
    """Does segment a-b pass through the box's interior? (Liang-Barsky clipping)"""
    x0, x1, y0, y1 = box[0] + 1e-6, box[1] - 1e-6, box[2] + 1e-6, box[3] - 1e-6
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q <= 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 >= t1:
            return False
    return True


def path_length(a, b, box):
    """Shortest path from a to b around the box via its two bottom corners (module-local coordinates)."""
    if not _crosses(a, b, box):
        return math.hypot(b[0] - a[0], b[1] - a[1])
    corners = [(box[0], box[3]), (box[1], box[3])]
    best = float("inf")
    for route in ([corners[0]], [corners[1]], corners, corners[::-1]):
        pts = [a] + route + [b]
        if all(not _crosses(pts[i], pts[i + 1], box) for i in range(len(pts) - 1)):
            best = min(best, sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                                 for i in range(len(pts) - 1)))
    return best


def escape(lx, ly):
    """Where a module pad's trace leaves the obstacle box: straight out of its side."""
    if ly > 4.0:
        return (lx, OBSTACLE[3])
    return (OBSTACLE[0] if lx < 0 else OBSTACLE[1], ly)


def hungarian(cost):
    """Minimum-cost assignment of every row to a distinct column (rows <= columns)."""
    n, m = len(cost), len(cost[0])
    INF = float("inf")
    u, v, p, way = [0.0] * (n + 1), [0.0] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = [INF] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    return {p[j] - 1: j - 1 for j in range(1, m + 1) if p[j]}


def half_parts(placement, half):
    parts = {}
    for ref, r in placement["parts"].items():
        if half == "left":
            parts[ref] = dict(r)
        else:
            parts[ref] = dict(r, x=round(2 * placement["mirror_x"] - r["x"], 6),
                              rot=r.get("rot_right", (-r["rot"]) % 360))
    return parts


def assign(half, geo, parts, pins, key_pads):
    u1 = parts["U1"]
    pin_xy = {}
    for name, (num, lx, ly) in pins.items():
        dx, dy = rotate(lx, ly, u1["rot"])
        pin_xy[name] = (u1["x"] + dx, u1["y"] + dy)

    def local(x, y):  # board -> module-local
        return rotate(x - u1["x"], y - u1["y"], -u1["rot"])

    top_row = min(ly for _n, _x, ly in pins.values())
    centre = (u1["x"], u1["y"])

    signals = []  # (name, kind, target xy, extra)
    for sw in geo["halves"][half]["switches"]:
        cand = []
        for pad, (lx, ly) in key_pads.items():
            dx, dy = rotate(lx, ly, sw["rot"])
            cand.append((math.hypot(sw["x"] + dx - centre[0], sw["y"] + dy - centre[1]), pad,
                         (sw["x"] + dx, sw["y"] + dy)))
        cand.sort()
        signals.append((sw["key"], "key", cand[0][2], dict(ref=sw["ref"], gpio_pad=cand[0][1],
                                                            gnd_pad=cand[1][1], x=sw["x"], y=sw["y"])))
    for fn, ref in sorted(FUNCTIONS.items()):
        signals.append((fn, "function", (parts[ref]["x"], parts[ref]["y"]), dict(near=ref)))

    names = sorted(pin_xy)
    cost = []
    for _s, _k, (tx, ty), _e in signals:
        row = []
        for n in names:
            num, lx, ly = pins[n]
            e = escape(lx, ly)
            c = math.hypot(e[0] - lx, e[1] - ly) + path_length(e, local(tx, ty), OBSTACLE)
            if abs(abs(lx) - 6.5) > 0.5 and abs(ly - 7.01) > 0.5:  # not on the outer edge rows
                c += INNER_PENALTY
            if ly < top_row + 2.0:
                c += ANTENNA_PENALTY
            row.append(c)
        cost.append(row)
    match = hungarian(cost)
    out = []
    for i, (s, kind, target, extra) in enumerate(signals):
        n = names[match[i]]
        num, lx, ly = pins[n]
        e = escape(lx, ly)
        d = math.hypot(e[0] - lx, e[1] - ly) + path_length(e, local(*target), OBSTACLE)
        out.append(dict(signal=s, kind=kind, gpio=n, module_pin=num, distance_mm=round(d, 2), **extra))
    return out


def ato(halves, geo):
    lines = ['#pragma experiment("TRAITS")', '#pragma experiment("INSTANCE_TRAITS")',
             "# GENERATED by scripts/circuit/gen_halves.py from hardware/geometry/urchin.json and",
             "# hardware/placement.json. Do not edit by hand.", "",
             "import has_net_name_suggestion", "import has_designator",
             'from "core.ato" import Core',
             'from "parts/KEY_CHOC/KEY_CHOC.ato" import KEY_CHOC_package',
             'from "parts/PUCK/PUCK.ato" import PUCK_package',
             'from "parts/HOLE_M2_4_2/HOLE_M2_4_2.ato" import HOLE_M2_4_2_package',
             'from "parts/HOLE_M2_3_5/HOLE_M2_3_5.ato" import HOLE_M2_3_5_package']
    for half, wiring in halves.items():
        h = geo["halves"][half]
        lines += ["", "", "module %sHalf:" % half.capitalize(), "    core = new Core", ""]
        lines.append("    # keys: the socket pad nearer the module is the GPIO, the other is ground")
        for w in (w for w in wiring if w["kind"] == "key"):
            k = w["signal"]
            lines += ["    signal key_%s" % k,
                      '    trait key_%s has_net_name_suggestion<name="KEY_%s", level="EXPECTED">' % (k, k.upper()),
                      "    sw_%s = new KEY_CHOC_package" % k,
                      '    trait sw_%s has_designator<designator="%s">' % (k, w["ref"]),
                      "    sw_%s.%s ~ key_%s" % (k, w["gpio_pad"], k),
                      "    sw_%s.%s ~ core.gnd" % (k, w["gnd_pad"]),
                      "    key_%s ~ core.mcu.%s" % (k, w["gpio"]), ""]
        lines.append("    # core functions on GPIOs")
        for w in (w for w in wiring if w["kind"] == "function"):
            lines.append("    core.%s ~ core.mcu.%s" % (w["signal"], w["gpio"]))
        lines += ["", "    # mechanical", "    puck = new PUCK_package", '    trait puck has_designator<designator="H1">']
        for i, hole in enumerate(h["case_holes"]):
            part = {"M2_hole_4.2mm": "HOLE_M2_4_2", "M2_hole_3.5mm": "HOLE_M2_3_5"}[hole["footprint"].split(":")[-1]]
            lines += ["    hole%d = new %s_package" % (i + 2, part),
                      '    trait hole%d has_designator<designator="H%d">' % (i + 2, i + 2)]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if the outputs differ from the files on disk")
    ap.add_argument("--md", help="also write the pin map as a Markdown table")
    args = ap.parse_args()
    geo = json.loads((HW / "geometry/urchin.json").read_text())
    placement = json.loads((HW / "placement.json").read_text())
    pins = module_pins()
    key_pads = pads(HW / "parts/KEY_CHOC/SW_Hotswap_Kailh_Choc_V1_tweaked.kicad_mod")
    halves = {h: assign(h, geo, half_parts(placement, h), pins, key_pads) for h in ("left", "right")}
    pinmap = {"_doc": "Generated by scripts/circuit/gen_halves.py. Per half: every key and core GPIO function, "
                      "its nRF52840 GPIO and E73 module pin. distance_mm is the shortest path from the module pad "
                      "to the target around the module and its antenna end.", "halves": halves}
    outputs = {HW / "halves.ato": ato(halves, geo), HW / "pinmap.json": json.dumps(pinmap, indent=1) + "\n"}
    bad = 0
    for path, text in outputs.items():
        if args.check:
            if not path.exists() or path.read_text() != text:
                print("FAIL %s is out of date: run scripts/circuit/gen_halves.py" % path.relative_to(ROOT))
                bad = 1
        else:
            path.write_text(text)
    if args.md:
        md = ["# Pin map", "", "Generated by `scripts/circuit/gen_halves.py` (`hardware/pinmap.json`). Keys are named "
              "rRcC (row 0 = top, column 0 = pinky) and t0/t1 (thumbs, t0 nearer the main keys). GPIO pad: the "
              "socket pad wired to the GPIO; the other socket pad is ground. Path: shortest route length from the "
              "module pad around the module, the cost the assignment minimizes.", ""]
        for half, wiring in halves.items():
            md += ["## %s half" % half.capitalize(), "",
                   "| Signal | Switch | GPIO | E73 pin | GPIO pad | Path (mm) |", "|---|---|---|---|---|---|"]
            for w in wiring:
                md.append("| %s | %s | %s | %d | %s | %.1f |" % (
                    w["signal"], w.get("ref", "(near %s)" % w.get("near", "")), w["gpio"].replace("_", "."),
                    w["module_pin"], w.get("gpio_pad", "-"), w["distance_mm"]))
            md.append("")
        Path(args.md).write_text("\n".join(md))
    for half, wiring in halves.items():
        total = sum(w["distance_mm"] for w in wiring)
        print("%s: %d GPIOs, %.0f mm total path length, longest %.1f mm (%s)" % (
            half, len(wiring), total, max(w["distance_mm"] for w in wiring),
            max(wiring, key=lambda w: w["distance_mm"])["signal"]))
    return bad


if __name__ == "__main__":
    sys.exit(main())
