#!/usr/bin/env python3
"""Write each board's KiCad project file with JLCPCB design rules and net classes.

    python3 scripts/placement/board_setup.py [--check]

Writes hardware/layouts/<half>/<half>.kicad_pro and dock-pcb/layouts/dock/dock.kicad_pro
(atopile creates only the board).
kicad-cli reads the rules from it for DRC; Freerouting gets them via the DSN export.

JLCPCB 2-layer, 1 oz, standard process (jlcpcb.com/capabilities, checked 2026-10-18),
with margin where it costs nothing:
  trace / space             0.127 mm min      -> 0.127 mm min trace (router neck-downs at
                                                 pads only), 0.15 mm min space, 0.15-0.3 mm tracks
  via                       0.3 mm drill, 0.15 mm annular ring -> 0.3 / 0.7 mm (0.2 mm ring;
                                                 keeps via holes 0.5 mm apart at 0.15 mm clearance)
  PTH / NPTH hole           0.3 mm min (vias) / 0.5 mm hole-to-hole
  hole to copper            0.25 mm
  copper to board edge      0.3 mm (routed edge)
  silkscreen text           0.8 mm height, 0.12 mm stroke min
Net classes: Power (0.3 mm; the input is limited to ~100 mA, and 0.3 mm still leaves
the BQ24073's 0.5 mm-pitch QFN pads) for the supply nets and ground; USB
(0.2 mm, 0.15 mm gap) for the data pair. The settings are merged into an existing
file, keeping what KiCad adds when it saves the project (its defaults); --check
fails if any setting here differs from the file.
Python 3.9.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RULES = {
    "min_clearance": 0.15,
    "min_track_width": 0.127,
    "min_connection": 0.15,
    "min_via_annular_width": 0.15,
    "min_via_diameter": 0.6,
    "min_through_hole_diameter": 0.3,
    "min_microvia_diameter": 0.2,
    "min_microvia_drill": 0.1,
    "min_hole_to_hole": 0.5,
    "min_hole_clearance": 0.25,
    "min_copper_edge_clearance": 0.3,
    "min_silk_clearance": 0.0,
    "min_text_height": 0.8,
    "min_text_thickness": 0.12,
    "min_groove_width": 0.0,
    "min_resolved_spokes": 2,
    "solder_mask_to_copper_clearance": 0.0,
    "allow_blind_buried_vias": False,
    "allow_microvias": False,
    "use_height_for_length_calcs": True,
}
# Everything is an error unless listed here. Silkscreen issues are warnings: JLC clips
# silkscreen off pads, and the EasyEDA footprints' silkscreen touches their own pads.
SEVERITIES = {
    "silk_over_copper": "warning",
    "silk_overlap": "warning",
    "silk_edge_clearance": "warning",
    "text_height": "warning",
    "text_thickness": "warning",
    "lib_footprint_issues": "ignore",      # atopile's per-part libraries; checked by kicad_guardrails.py
    "lib_footprint_mismatch": "ignore",
    "footprint_symbol_mismatch": "ignore",  # atopile writes no schematic
    "missing_courtyard": "warning",
    "courtyards_overlap": "error",
    "unconnected_items": "error",
    "isolated_copper": "warning",
    "starved_thermal": "warning",
    "footprint_type_mismatch": "ignore",    # mechanical parts are board-only
    "hole_to_hole": "error",                # drill breakage risk at JLC (0.5 mm minimum)
}
POWER = ["VIN", "VSYS", "VDDH", "VBAT", "VBUS", "DOCK_5V", "GND"]
BOARDS = [("hardware/layouts", "left"), ("hardware/layouts", "right"), ("dock-pcb/layouts", "dock")]


def netclass(name, track, clearance, **extra):
    d = {"name": name, "bus_width": 12, "clearance": clearance, "diff_pair_gap": 0.15, "diff_pair_via_gap": 0.25,
         "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1, "pcb_color":
         "rgba(0, 0, 0, 0.000)", "priority": 2147483647 if name == "Default" else 0, "schematic_color":
         "rgba(0, 0, 0, 0.000)", "track_width": track, "via_diameter": 0.7, "via_drill": 0.3, "wire_width": 6}
    d.update(extra)
    return d


def project(half):
    return {
        "board": {
            "design_settings": {
                "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.0,
                             "copper_text_size_v": 1.0, "copper_text_thickness": 0.15, "silk_line_width": 0.12,
                             "silk_text_size_h": 0.8, "silk_text_size_v": 0.8, "silk_text_thickness": 0.12,
                             "zones": {"min_clearance": 0.2}},
                "rule_severities": SEVERITIES,
                "rules": RULES,
                "track_widths": [0.0, 0.2, 0.3, 0.4, 0.6],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.7, "drill": 0.3}],
                "diff_pair_dimensions": [{"gap": 0.0, "via_gap": 0.0, "width": 0.0}],
                "zones_allow_external_fillets": False,
            },
        },
        "meta": {"filename": "%s.kicad_pro" % half, "version": 3},
        "net_settings": {
            "classes": [netclass("Default", 0.2, 0.15), netclass("Power", 0.3, 0.15),
                        netclass("USB", 0.2, 0.15, priority=1)],
            "meta": {"version": 4},
            "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in POWER] +
                                 [{"netclass": "USB", "pattern": n} for n in ("USB_DP", "USB_DN")],
        },
    }


def merge(base, ours):
    for k, v in ours.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            merge(base[k], v)
        else:
            base[k] = v
    return base


def differences(have, ours, path=""):
    out = []
    for k, v in ours.items():
        if isinstance(v, dict) and isinstance(have.get(k), dict):
            out += differences(have[k], v, path + "/" + k)
        elif have.get(k) != v:
            out.append(path + "/" + k)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    bad = 0
    for layouts, half in BOARDS:
        path = ROOT / layouts / half / ("%s.kicad_pro" % half)
        have = json.loads(path.read_text()) if path.exists() else {}
        if args.check:
            diff = differences(have, project(half)) if have else ["(missing)"]
            if diff:
                print("FAIL %s differs from board_setup.py at %s" % (path.relative_to(ROOT), ", ".join(diff[:5])))
                bad = 1
        else:
            path.write_text(json.dumps(merge(have, project(half)), indent=2) + "\n")
            print("wrote %s" % path.relative_to(ROOT))
    return bad


if __name__ == "__main__":
    sys.exit(main())
