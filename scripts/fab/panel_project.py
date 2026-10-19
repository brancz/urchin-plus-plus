#!/usr/bin/env python3
"""Give the panel the halves' net classes and rules (phase 6).

    python3 scripts/fab/panel_project.py PANEL.kicad_pro SOURCE.kicad_pro

KiKit renames each half's nets (L-GND, R-VIN, ...), so the panel's project no longer
matches the halves' net-class patterns and KiCad's DRC falls back to its 0.2 mm default
clearance. This copies the source project's rules, severities and net classes into the
panel's project, with every pattern prefixed by "*-" so it matches both halves' nets.
Python 3.9.
"""

import json
import sys


def main():
    panel_path, source_path = sys.argv[1], sys.argv[2]
    panel = json.load(open(panel_path))
    source = json.load(open(source_path))
    ds = panel.setdefault("board", {}).setdefault("design_settings", {})
    sds = source["board"]["design_settings"]
    for key in ("rules", "rule_severities", "track_widths", "via_dimensions"):
        ds[key] = sds[key]
    ns = panel.setdefault("net_settings", {})
    ns["classes"] = source["net_settings"]["classes"]
    ns["netclass_patterns"] = [{"netclass": p["netclass"], "pattern": "*-" + p["pattern"]}
                               for p in source["net_settings"]["netclass_patterns"]]
    json.dump(panel, open(panel_path, "w"), indent=2)
    print("panel project: %d net classes, %d patterns from %s" % (len(ns["classes"]), len(ns["netclass_patterns"]),
                                                                  source_path))


if __name__ == "__main__":
    main()
