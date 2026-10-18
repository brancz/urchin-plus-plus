#!/usr/bin/env python3
"""Check the BOM against live JLC stock and against the atopile build (CLAUDE.md rule 3).

    python3 scripts/parts/bom_check.py [--panels 5] [--json OUT] [--md OUT]

For every part in hardware/parts.json (quantities are per half):
  - JLC assembly library stock, checked now, must cover qty x 2 halves x --panels
    (one panel carries both halves; JLC assembles at least 2 panels);
  - a datasheet is saved as docs/datasheets/<LCSC>_*.pdf;
  - the per-half quantity matches atopile's BOM of each half
    (hardware/build/builds/<half>/<half>.bom.csv, so run scripts/ato_build.sh first),
    and that BOM has no part that parts.json lacks.
The check time (UTC) goes into both outputs; the release BOM's notes cite it.
Exits 1 on any problem. Stdlib only; read-only web requests. Python 3.9.
"""

import argparse
import csv
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import jlc  # noqa: E402


def atopile_bom(half):
    path = ROOT / ("hardware/build/builds/%s/%s.bom.csv" % (half, half))
    if not path.exists():
        return None
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["LCSC Part #"]] = out.get(row["LCSC Part #"], 0) + int(row["Quantity"])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panels", type=int, default=5, help="panels to cover with stock (default 5)")
    ap.add_argument("--json")
    ap.add_argument("--md")
    args = ap.parse_args()

    parts = json.loads((ROOT / "hardware/parts.json").read_text())["parts"]
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    problems, rows = [], []
    for p in parts:
        lcsc, qty = p["lcsc"], p["qty"]
        need = qty * 2 * args.panels
        row = {"lcsc": lcsc, "role": p["role"], "qty_per_half": qty, "needed": need, "checked_utc": now}
        c = jlc.jlc_part(lcsc)
        if c is None:
            problems.append("%s: not in the JLC assembly library" % lcsc)
        else:
            s = jlc.summarize(c)
            row.update({k: s[k] for k in ("mpn", "manufacturer", "package", "jlc_stock", "library")})
            if not s["jlc_stock"] or s["jlc_stock"] < need:
                problems.append("%s: JLC stock %s < %d needed" % (lcsc, s["jlc_stock"], need))
        sheets = sorted((ROOT / "docs/datasheets").glob("%s_*.pdf" % lcsc))
        row["datasheet"] = str(sheets[0].relative_to(ROOT)) if sheets else None
        if not sheets:
            problems.append("%s: no datasheet in docs/datasheets/" % lcsc)
        rows.append(row)

    listed = {p["lcsc"]: p["qty"] for p in parts}
    for half in ("left", "right"):
        bom = atopile_bom(half)
        if bom is None:
            problems.append("%s: no atopile BOM (run scripts/ato_build.sh hardware)" % half)
            continue
        for lcsc in sorted(set(bom) | set(listed)):
            if bom.get(lcsc, 0) != listed.get(lcsc, 0):
                problems.append("%s: %s is %d in the atopile BOM, %d in parts.json" % (half, lcsc, bom.get(lcsc, 0),
                                                                                       listed.get(lcsc, 0)))

    result = {"checked_utc": now, "panels": args.panels, "parts": rows, "problems": problems}
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    if args.md:
        lines = ["# BOM stock check", "",
                 "Checked against the JLC assembly library at %s, for %d panels (both halves each). "
                 "Quantities are per half." % (now, args.panels), "",
                 "| LCSC | Part | Manufacturer | Package | Library | Qty/half | Needed | JLC stock | Role | Datasheet |",
                 "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            lines.append("| %s | %s | %s | %s | %s | %d | %d | %s | %s | %s |" % (
                r["lcsc"], r.get("mpn", "?"), r.get("manufacturer", "?"), r.get("package", "?"), r.get("library", "?"),
                r["qty_per_half"], r["needed"], r.get("jlc_stock", "?"), r["role"],
                "[pdf](../../%s)" % r["datasheet"] if r["datasheet"] else "missing"))
        lines += ["", "Problems: %s" % ("none" if not problems else ""), ""] + ["- " + p for p in problems]
        Path(args.md).write_text("\n".join(lines).rstrip() + "\n")
    for r in rows:
        print("%-9s %-9s stock %-8s need %-4d %s" % (r["lcsc"], r.get("library", "-"), r.get("jlc_stock", "-"),
                                                     r["needed"], (r.get("mpn") or "")[:30]))
    for p in problems:
        print("FAIL " + p)
    print("bom_check at %s: %s" % (now, "OK" if not problems else "FAIL (%d)" % len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
