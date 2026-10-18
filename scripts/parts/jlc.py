#!/usr/bin/env python3
"""Live JLCPCB / LCSC part data (CLAUDE.md rule 3).

    python3 scripts/parts/jlc.py search "BQ24075"                 # JLC assembly library search
    python3 scripts/parts/jlc.py check C25744 C1525 [--json OUT]   # stock + basic/extended, now
    python3 scripts/parts/jlc.py datasheet C25744 [--name R0402]   # -> docs/datasheets/C25744_R0402.pdf

`check` exits 1 if any part is out of stock at JLC or missing from its assembly
library. Stdlib only; reads public JLC/LCSC web endpoints, read-only.
"""

import argparse
import datetime
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UA = {"User-Agent": "Mozilla/5.0 (urchin++ part check)", "Content-Type": "application/json"}
JLC_SEARCH = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
LCSC_DETAIL = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=%s"


def _get(url, data=None, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def jlc_search(keyword, page_size=25):
    body = {"keyword": keyword, "currentPage": 1, "pageSize": page_size, "searchSource": "search",
            "componentAttributes": [], "stockFlag": None, "stockSort": None, "firstSortName": None,
            "secondSortName": None, "componentBrand": None, "componentSpecification": None,
            "componentLibraryType": None, "preferredComponentFlag": None, "searchType": 2}
    d = json.loads(_get(JLC_SEARCH, body))
    return ((d.get("data") or {}).get("componentPageInfo") or {}).get("list") or []


def jlc_part(lcsc):
    for c in jlc_search(lcsc, 5):
        if c.get("componentCode") == lcsc:
            return c
    return None


def lcsc_part(lcsc):
    d = json.loads(_get(LCSC_DETAIL % lcsc))
    return d.get("result") or None


def summarize(c):
    return {
        "lcsc": c.get("componentCode"),
        "mpn": c.get("componentModelEn"),
        "manufacturer": c.get("componentBrandEn"),
        "package": c.get("componentSpecificationEn"),
        "jlc_stock": c.get("stockCount"),
        "library": {"base": "basic", "expand": "extended"}.get(c.get("componentLibraryType"), c.get("componentLibraryType")),
        "preferred": c.get("preferredComponentFlag"),
        "description": (c.get("describe") or c.get("erpComponentName") or "")[:120],
    }


def cmd_search(args):
    for c in jlc_search(args.keyword, args.n):
        s = summarize(c)
        print("%-9s %-9s stock %-8s %-28s %-22s %s" % (s["lcsc"], s["library"], s["jlc_stock"], (s["mpn"] or "")[:28],
                                                       (s["package"] or "")[:22], s["description"][:70]))
    return 0


def cmd_check(args):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows, bad = [], 0
    for lcsc in args.lcsc:
        c = jlc_part(lcsc)
        if c is None:
            rows.append({"lcsc": lcsc, "checked_utc": now, "error": "not in JLC assembly library"})
            bad += 1
            continue
        s = summarize(c)
        s["checked_utc"] = now
        if not s["jlc_stock"] or s["jlc_stock"] < args.need:
            s["error"] = "JLC stock %s < needed %d" % (s["jlc_stock"], args.need)
            bad += 1
        rows.append(s)
    for r in rows:
        print("%-9s %-9s stock %-9s %-30s %s" % (r["lcsc"], r.get("library", "-"), r.get("jlc_stock", "-"),
                                                 (r.get("mpn") or "")[:30], r.get("error", "ok")))
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2) + "\n")
    print("checked %d parts at %s: %d problem(s)" % (len(rows), now, bad))
    return 1 if bad else 0


JLC_FILE = "https://jlcpcb.com/api/file/downloadByFileSystemAccessId/%s"


def datasheet_url(lcsc):
    c = jlc_part(lcsc)
    # JLC's file store serves the PDF; the lcsc.com datasheet links answer bots with a JS page.
    if c and c.get("dataManualFileAccessId"):
        return JLC_FILE % c["dataManualFileAccessId"], c.get("componentModelEn")
    if c and c.get("dataManualUrl"):
        return c["dataManualUrl"], c.get("componentModelEn")
    p = lcsc_part(lcsc)
    if p and p.get("pdfUrl"):
        return p["pdfUrl"], p.get("productModel")
    return None, None


def cmd_datasheet(args):
    url, model = datasheet_url(args.lcsc)
    if not url:
        sys.exit("%s: no datasheet URL from JLC or LCSC" % args.lcsc)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", args.name or model or "part")
    out = ROOT / "docs" / "datasheets" / ("%s_%s.pdf" % (args.lcsc, name))
    pdf = _get(url, timeout=120)
    if not pdf.startswith(b"%PDF"):
        sys.exit("%s: %s did not return a PDF" % (args.lcsc, url))
    out.write_bytes(pdf)
    print("%s -> %s (%d kB)" % (args.lcsc, out.relative_to(ROOT), len(pdf) // 1024))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("keyword")
    s.add_argument("-n", type=int, default=25)
    c = sub.add_parser("check")
    c.add_argument("lcsc", nargs="+")
    c.add_argument("--need", type=int, default=1, help="minimum JLC stock per part")
    c.add_argument("--json")
    d = sub.add_parser("datasheet")
    d.add_argument("lcsc")
    d.add_argument("--name")
    args = ap.parse_args()
    return {"search": cmd_search, "check": cmd_check, "datasheet": cmd_datasheet}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
