#!/usr/bin/env python3
"""Slice every printed part with Bambu Studio for the owner's printer (phase 7).

    python3 scripts/mech/slice.py STL_DIR OUT_DIR [--filament "Bambu PLA Basic @BBL A1M"]

Uses Bambu Studio's own system profiles: Bambu Lab A1 mini, 0.4 mm nozzle, "0.20mm Standard
@BBL A1M", and the given filament. Those profiles inherit from parents, which Bambu Studio's
command line doesn't resolve, so this script flattens them first. Each part is sliced on its
own plate as exported (already in print orientation, no supports); the shells and the dock's
floor plates, the parts you see most, get their top surfaces ironed. The result per part is its sliced 3MF (open it in Bambu
Studio to print), plus print time, filament use and any slicer warning in OUT_DIR/slice.json.
Exits 1 if a part fails to slice.

Local only: needs Bambu Studio (/Applications/BambuStudio.app or $BAMBU_STUDIO).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

APP = Path(os.environ.get("BAMBU_STUDIO", "/Applications/BambuStudio.app"))
BIN = APP / "Contents" / "MacOS" / "BambuStudio"
PROFILES = APP / "Contents" / "Resources" / "profiles" / "BBL"
MACHINE = "Bambu Lab A1 mini 0.4 nozzle"
PROCESS = "0.20mm Standard @BBL A1M"


def find(kind, name):
    for p in (PROFILES / kind).rglob("*.json"):
        try:
            d = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        if d.get("name") == name:
            return d
    sys.exit(f"slice: no {kind} profile named {name!r} in {PROFILES}")


def flatten(kind, name):
    d = find(kind, name)
    parent = d.get("inherits")
    merged = flatten(kind, parent) if parent else {}
    merged.update({k: v for k, v in d.items() if k != "inherits"})
    return merged


def write_flat(kind, name, out, suffix="", **overrides):
    d = flatten(kind, name)
    d.update(overrides)
    d["from"] = "system"
    d.setdefault("type", {"machine": "machine", "process": "process", "filament": "filament"}[kind])
    path = out / f"{kind}{suffix}.json"
    path.write_text(json.dumps(d, indent=1))
    return path


def slice_info(threemf):
    with zipfile.ZipFile(threemf) as z:
        text = z.read("Metadata/slice_info.config").decode()
    get = lambda key: (re.search(rf'key="{key}" value="([^"]*)"', text) or [None, None])[1]
    warnings = re.findall(r'<warning msg="([^"]*)"', text)
    return {"prediction_s": int(float(get("prediction") or 0)), "weight_g": float(get("weight") or 0),
            "warnings": warnings}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stl_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--filament", default="Bambu PLA Basic @BBL A1M")
    args = ap.parse_args()
    if not BIN.exists():
        sys.exit(f"slice: Bambu Studio not found at {APP} (set BAMBU_STUDIO)")
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    settings = out / "settings"
    settings.mkdir(exist_ok=True)
    machine = write_flat("machine", MACHINE, settings)
    process = write_flat("process", PROCESS, settings)
    ironed = write_flat("process", PROCESS, settings, "-ironed", ironing_type="top")
    filament = write_flat("filament", args.filament, settings)

    results, failed = {}, []
    for stl in sorted(Path(args.stl_dir).glob("*.stl")):
        target = out / f"{stl.stem}.3mf"
        iron = stl.stem.startswith(("shell_", "dock_floor_"))
        cmd = [str(BIN), "--slice", "0", "--arrange", "1", "--orient", "0",
               "--load-settings", f"{machine};{ironed if iron else process}", "--load-filaments", str(filament),
               "--export-3mf", target.name, "--outputdir", str(out), str(stl.resolve())]
        # cwd: Bambu Studio also writes a result.json into the working directory.
        run = subprocess.run(cmd, capture_output=True, text=True, cwd=out)
        if run.returncode != 0 or not target.exists():
            failed.append(stl.stem)
            tail = "\n".join((run.stdout + run.stderr).splitlines()[-15:])
            results[stl.stem] = {"ok": False, "returncode": run.returncode, "log_tail": tail}
            continue
        info = slice_info(target)
        results[stl.stem] = dict(info, ok=True, machine=MACHINE, process=PROCESS, ironing=iron, filament=args.filament)
        print(f"{stl.stem}: {info['prediction_s'] // 60} min, {info['weight_g']:.1f} g, warnings: {info['warnings'] or 'none'}")
    (out / "slice.json").write_text(json.dumps(results, indent=1) + "\n")
    if failed:
        sys.exit(f"slice: failed: {', '.join(failed)} (see {out / 'slice.json'})")


if __name__ == "__main__":
    main()
