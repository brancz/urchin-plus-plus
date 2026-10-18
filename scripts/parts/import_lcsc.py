#!/usr/bin/env python3
"""Import LCSC parts as atopile atomic parts, without atopile's part server.

    python3 scripts/parts/import_lcsc.py --parts-dir hardware/parts C25744 C1525

For each LCSC number:
  1. easyeda2kicad fetches the symbol, footprint and 3D model from EasyEDA/LCSC.
  2. kicad-cli upgrades the symbol and footprint to the current KiCad format
     (easyeda2kicad writes KiCad 5/6-era files).
  3. The footprint's 3D model path is pointed at the STEP file in the part dir,
     and with --side bottom (the default; CLAUDE.md rule 2) the footprint is
     rewritten as a bottom-side footprint (scripts/parts/footprint_to_bottom.py).
  4. <parts-dir>/<LCSC>/<LCSC>.ato is written with is_atomic_part,
     has_part_picked (LCSC supplier number) and one signal per named pin,
     following the conventions of atopile's own part generator.
  5. source.json records where and when the part came from.

Stock is NOT checked here; that is the BOM check's job (CLAUDE.md rule 3).
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import footprint as fplib  # noqa: E402
from lib import sexp  # noqa: E402
from lib.toolchain import pinned  # noqa: E402

# Relative to the KiCad project atopile writes (<project>/layouts/<build>/).
DEFAULT_MODEL_BASE = "${KIPRJMOD}/../../parts"


def run(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(cmd)}\n{res.stdout}\n{res.stderr}")
    return res.stdout


def tool_version(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
        return out.splitlines()[0] if out else "unknown"
    except OSError:
        return "unknown"


def prop(sym, name):
    for p in sexp.children(sym, "property"):
        if p[1] == name:
            return p[2]
    return None


def sanitize(pin_name):
    """Mirror faebryk.libs.ato_part._sanitize + pycodegen.sanitize_name."""
    if re.fullmatch(r"[0-9]+", pin_name):
        return None
    for opts, pre, suf in ((("~", "#"), "n", ""), (("+",), "", "pos"), (("-", "–"), "", "neg")):
        for o in opts:
            if pin_name.startswith(o):
                pin_name = pre + pin_name[len(o):] + suf
                break
            if pin_name.endswith(o):
                pin_name = pre + pin_name[: -len(o)] + suf
                break
        else:
            continue
        break
    name = re.sub(r"[^A-Za-z0-9_]", "_", pin_name)
    if name and name[0].isdigit():
        name = "_" + name
    return name or None


def clean_manufacturer(m):
    # EasyEDA appends the Chinese brand name in parentheses: "UNI-ROYAL(厚声)".
    return re.sub(r"\s*[(（][^)）]*[)）]\s*$", "", m or "").strip() or "unknown"


def import_part(lcsc, parts_dir, model_base, side, fixups=None, pin_names=None):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for attempt in range(5):  # EasyEDA's API answers 403 to bursts of requests; back off and retry
            res = subprocess.run(["easyeda2kicad", "--full", "--lcsc_id", lcsc, "--output", str(tmp / "lib")],
                                 capture_output=True, text=True)
            if res.returncode == 0 and "[ERROR]" not in res.stdout + res.stderr:
                break
            if "403" not in res.stdout + res.stderr or attempt == 4:
                raise SystemExit(f"easyeda2kicad failed for {lcsc}:\n{res.stdout}\n{res.stderr}")
            time.sleep(20 * (attempt + 1))
        run(["kicad-cli", "fp", "upgrade", "-o", str(tmp / "up.pretty"), str(tmp / "lib.pretty")])
        run(["kicad-cli", "sym", "upgrade", "-o", str(tmp / "up.kicad_sym"), str(tmp / "lib.kicad_sym")])

        fps = sorted((tmp / "up.pretty").glob("*.kicad_mod"))
        if len(fps) != 1:
            raise SystemExit(f"{lcsc}: expected one footprint, got {[f.name for f in fps]}")
        lib = sexp.load(tmp / "up.kicad_sym")
        syms = sexp.children(lib, "symbol")
        if len(syms) != 1:
            raise SystemExit(f"{lcsc}: expected one symbol, got {len(syms)}")
        sym = syms[0]
        sym_name = sym[1]
        steps = sorted((tmp / "lib.3dshapes").glob("*.step"))

        out = parts_dir / lcsc
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)

        fp_text = fps[0].read_text(encoding="utf-8")
        if steps:
            shutil.copy(steps[0], out / steps[0].name)
            model_path = f"{model_base}/{lcsc}/{steps[0].name}"
            fp_text, n = re.subn(r'\(model\s+"[^"]*"', f'(model "{model_path}"', fp_text, count=1)
            if n != 1:
                raise SystemExit(f"{lcsc}: footprint has no model entry to rewrite")
        changes = []
        if fixups:  # in the datasheet's (front-side) coordinates, so before any flip
            node = sexp.parse(fp_text)[0]
            changes += fplib.fixups(node, fixups)
            fp_text = "\n".join(sexp.dump_lines(node)) + "\n"
        (out / fps[0].name).write_text(fp_text, encoding="utf-8")
        if side == "bottom":
            run([os.environ["KICAD_PY"], str(Path(__file__).resolve().parent / "footprint_to_bottom.py"),
                 str(out), fps[0].stem])
        node = sexp.load(out / fps[0].name)
        try:
            changes += fplib.sanitize(node)
        except ValueError as e:
            raise SystemExit("%s: %s" % (lcsc, e))
        (out / fps[0].name).write_text("\n".join(sexp.dump_lines(node)) + "\n", encoding="utf-8")
        sym_file = f"{sym_name}.kicad_sym"
        shutil.copy(tmp / "up.kicad_sym", out / sym_file)

    manufacturer = clean_manufacturer(prop(sym, "Manufacturer"))
    mpn = prop(sym, "MPN") or prop(sym, "Value") or sym_name
    datasheet = prop(sym, "Datasheet") or ""
    designator = prop(sym, "Reference") or "U"
    if prop(sym, "LCSC Part") not in (None, lcsc):
        raise SystemExit(f"{lcsc}: symbol says LCSC Part {prop(sym, 'LCSC Part')}")

    pins = []
    for _, node in sexp.walk(sym):
        if sexp.head(node) == "pin":
            name = sexp.child(node, "name")[1]
            number = sexp.child(node, "number")[1]
            pins.append((name, number))
    if pin_names:  # datasheet names from hardware/parts.json override EasyEDA's symbol
        symbol_numbers = {n for _, n in pins}
        if set(pin_names) != symbol_numbers:
            raise SystemExit(f"{lcsc}: pin_names cover {sorted(pin_names)}, symbol has {sorted(symbol_numbers)}")
        pins = [(pin_names[n], n) for _, n in pins]
    numbers = {n for _, n in pins}

    lines = [
        '#pragma experiment("TRAITS")',
        "import is_atomic_part",
        "import has_part_picked",
        "import has_designator_prefix",
        "",
        f"component {lcsc}_package:",
        f'    """{manufacturer} {mpn} (LCSC {lcsc}). Generated by scripts/parts/import_lcsc.py."""',
        f'    trait is_atomic_part<manufacturer="{manufacturer}", partnumber="{mpn}", '
        f'footprint="{fps[0].name}", symbol="{sym_file}"'
        + (f', model="{steps[0].name}"' if steps else "")
        + ">",
        f'    trait has_part_picked::by_supplier<supplier_id="lcsc", supplier_partno="{lcsc}", '
        f'manufacturer="{manufacturer}", partno="{mpn}">',
        f'    trait has_designator_prefix<prefix="{designator}">',
    ]
    # No has_datasheet trait: ato build tries to download it, and LCSC's URL is a
    # product page, not a PDF. Datasheets live in docs/datasheets/ (rule 3).
    lines.append("")
    declared = set()
    pin_map = []
    for name, number in sorted(pins, key=lambda p: (p[0], [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p[1])])):
        if name.upper() == "NC":
            continue
        sig = sanitize(name)
        if sig is None:
            lines.append(f"    pin {number}")
            pin_map.append({"pin": number, "name": name, "signal": None})
            continue
        if sig in numbers:
            sig = f"SIG_{sig}"
        kw = "" if sig in declared else "signal "
        lines.append(f"    {kw}{sig} ~ pin {number}")
        declared.add(sig)
        pin_map.append({"pin": number, "name": name, "signal": sig})
    (out / f"{lcsc}.ato").write_text("\n".join(lines) + "\n", encoding="utf-8")

    source = {
        "lcsc": lcsc,
        "manufacturer": manufacturer,
        "mpn": mpn,
        "datasheet_url": datasheet,
        "symbol": sym_file,
        "footprint": fps[0].name,
        "side": side,
        "footprint_changes": changes,
        "fixups_source": (fixups or {}).get("source"),
        "pin_names": pin_names,
        "model": steps[0].name if steps else None,
        "pins": pin_map,
        "fetched_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "easyeda2kicad": tool_version(["easyeda2kicad", "--version"]),
        "kicad_cli": tool_version(["kicad-cli", "version"]),
    }
    (out / "source.json").write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return source


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parts-dir", required=True, type=Path)
    ap.add_argument("--model-base", default=DEFAULT_MODEL_BASE,
                    help="3D model path prefix written into footprints (default: %(default)s)")
    ap.add_argument("--side", choices=("bottom", "top"), default="bottom",
                    help="side of the library footprint (default: bottom, CLAUDE.md rule 2)")
    ap.add_argument("--manifest", type=Path, help="import every part listed in this JSON (hardware/parts.json)")
    ap.add_argument("lcsc", nargs="*")
    args = ap.parse_args()
    # kicad-cli upgrade writes its own format; a newer KiCad makes files the pinned one can't load.
    kicad = tool_version(["kicad-cli", "version"])
    if kicad != pinned("KICAD_VERSION"):
        raise SystemExit("kicad-cli is %s, pinned is %s (see docs/SETUP.md)" % (kicad, pinned("KICAD_VERSION")))
    todo = [(c, args.side, None, None) for c in args.lcsc]
    if args.manifest:
        for part in json.loads(args.manifest.read_text())["parts"]:
            todo.append((part["lcsc"], part.get("side", "bottom"), part.get("fixups"), part.get("pin_names")))
    if not todo:
        raise SystemExit("nothing to import: give LCSC numbers or --manifest")
    for lcsc, side, fixups, pin_names in todo:
        if not re.fullmatch(r"C[0-9]+", lcsc):
            raise SystemExit(f"not an LCSC number: {lcsc}")
        if side == "bottom" and not os.environ.get("KICAD_PY"):
            raise SystemExit("--side bottom needs KICAD_PY (KiCad's Python) to flip the footprint")
        s = import_part(lcsc, args.parts_dir, args.model_base, side, fixups, pin_names)
        print(f"{lcsc}: {s['manufacturer']} {s['mpn']} ({side}) -> {args.parts_dir / lcsc}"
              + "".join(f"\n    {c}" for c in s["footprint_changes"]))


if __name__ == "__main__":
    main()
