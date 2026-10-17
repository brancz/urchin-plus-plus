#!/usr/bin/env python3
"""Compare a .kicad_pcb with a baseline and fail on changes that lose work (CLAUDE.md rule 5).

    "$KICAD_PY" scripts/checks/board_diff.py BOARD --against BEFORE.kicad_pcb --mode build
    "$KICAD_PY" scripts/checks/board_diff.py BOARD [--rev HEAD]          # vs a git revision
    "$KICAD_PY" scripts/checks/board_diff.py BOARD --against OLD --strict

Copper (tracks, arcs, vias) and zones are matched by geometry, not by net, so a
net change on existing copper is visible as such. Footprints are matched by their
atopile_address field (reference designator if absent; duplicates get their UUID).

Failures, by mode:
  commit (default)  removals of footprints, footprint fields, tracks, arcs, vias,
                    zones or board drawings; net changes on copper or zones that
                    are not explained by a net rename (a net whose pads all moved
                    to one new name that didn't exist before).
  build             commit failures, plus anything atopile has no business
                    changing: position/rotation/side/lock of existing footprints;
                    their pads, graphics or attributes while the library footprint
                    is unchanged (atopile re-syncs footprints from the library on
                    every build; allow footprint-lib:KEY after editing a part's
                    .kicad_mod); any zone property; any drawing; board setup.
  --strict          any difference at all: the semantic diff must be empty and
                    both boards must serialize identically after a pcbnew
                    load/save round, with order-free item lists (footprints,
                    graphics, pads, copper) sorted.
Exempt expected removals or net changes with --allow KIND:KEY (fnmatch; KIND is
footprint, field, track, arc, via, zone, drawing, net-change, footprint-lib).

A missing baseline is an error (exit 2), except with --allow-new for a board
that is genuinely new. Must run under KiCad's Python (pcbnew); Python 3.9.
"""

import argparse
import collections
import difflib
import fnmatch
import json
import os
import subprocess
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib import sexp  # noqa: E402

KINDS = ("footprint", "track", "arc", "via", "zone", "drawing")


def mm(v):
    return round(pcbnew.ToMM(v), 4)


def pt(p):
    return (mm(p.x), mm(p.y))


def call(obj, name, *args):
    """Call an optional API method; None if this KiCad doesn't have it."""
    fn = getattr(obj, name, None)
    try:
        return fn(*args) if fn else None
    except Exception:  # noqa: BLE001 - optional attribute, any failure means "unknown"
        return None


def poly(poly_set):
    out = []
    for oi in range(poly_set.OutlineCount()):
        rings = [poly_set.Outline(oi)] + [poly_set.Hole(oi, h) for h in range(poly_set.HoleCount(oi))]
        out.append(tuple(tuple(pt(r.CPoint(i)) for i in range(r.PointCount())) for r in rings))
    return tuple(out)


def fp_base_key(fp):
    for f in fp.GetFields():
        if f.GetName() == "atopile_address" and f.GetText():
            return f.GetText()
    return fp.GetReference()


def unique(keys):
    """Append #2, #3 ... to repeated keys (identical overlapping copper)."""
    seen = collections.Counter()
    out = []
    for k in keys:
        seen[k] += 1
        out.append(k if seen[k] == 1 else "%s #%d" % (k, seen[k]))
    return out


def shape_geom(s):
    name = s.GetShapeStr()
    if name == "Polygon":
        g = str(poly(s.GetPolyShape()))
    elif name == "Arc":
        g = "%s->%s->%s" % (pt(s.GetStart()), pt(s.GetArcMid()), pt(s.GetEnd()))
    elif name == "Circle":
        g = "c=%s r=%s" % (pt(s.GetCenter()), mm(s.GetRadius()))
    elif name == "Bezier":
        g = "%s %s %s %s" % (pt(s.GetStart()), pt(s.GetBezierC1()), pt(s.GetBezierC2()), pt(s.GetEnd()))
    else:
        g = "%s->%s" % (pt(s.GetStart()), pt(s.GetEnd()))
    return "%s %s %s w=%s fill=%s" % (s.GetLayerName(), name, g, mm(s.GetWidth()), call(s, "IsFilled"))


def snapshot(board):
    s = {k: {} for k in KINDS}

    fps = list(board.GetFootprints())
    counts = collections.Counter(fp_base_key(fp) for fp in fps)
    for fp in fps:
        k = fp_base_key(fp)
        if counts[k] > 1:
            k = "%s#%s" % (k, fp.m_Uuid.AsString())
        pads, pad_nets = {}, {}
        for i, (num, p) in enumerate(sorted(((p.GetNumber(), p) for p in fp.Pads()), key=lambda t: t[0])):
            pk = "%s/%d" % (num, i)
            pads[pk] = "%s %s %s drill=%s %s" % (pt(p.GetFPRelativePosition()), pt(p.GetSize(pcbnew.F_Cu)),
                                                p.ShowPadShape(pcbnew.F_Cu), pt(p.GetDrillSize()),
                                                p.GetLayerSet().FmtHex())
            pad_nets[pk] = p.GetNetname()
        graphics = []
        for g in fp.GraphicalItems():
            obj = g.Cast()
            if g.GetClass() == "PCB_SHAPE":
                graphics.append(shape_geom(obj))
            else:
                graphics.append("%s %s %s %r" % (g.GetClass(), g.GetLayerName(), pt(g.GetPosition()), call(obj, "GetText")))
        s["footprint"][k] = {
            "ref": fp.GetReference(),
            "graphics": sorted(graphics),
            "lib_id": fp.GetFPIDAsString(),
            "pos": pt(fp.GetPosition()),
            "rot": round(fp.GetOrientationDegrees(), 3),
            "layer": fp.GetLayerName(),
            "locked": fp.IsLocked(),
            "attributes": fp.GetAttributes(),
            "dnp": call(fp, "IsDNP"),
            "fields": {f.GetName(): f.GetText() for f in fp.GetFields()},
            "pads": pads,
            "pad_nets": pad_nets,
        }

    copper = {"track": [], "arc": [], "via": []}
    for t in board.GetTracks():
        cls = t.GetClass()
        if cls == "PCB_VIA":
            v = t.Cast()
            top, bot = v.TopLayer(), v.BottomLayer()
            key = "via %s %s d=%s w=%s %s-%s" % (pt(v.GetPosition()), v.GetViaType(), mm(v.GetDrillValue()),
                                                 mm(v.GetWidth(top)), board.GetLayerName(top), board.GetLayerName(bot))
            copper["via"].append((key, t.GetNetname()))
        elif cls == "PCB_ARC":
            a = t.Cast()
            key = "%s %s->%s->%s w=%s" % (a.GetLayerName(), pt(a.GetStart()), pt(a.GetMid()), pt(a.GetEnd()), mm(a.GetWidth()))
            copper["arc"].append((key, t.GetNetname()))
        else:
            key = "%s %s->%s w=%s" % (t.GetLayerName(), pt(t.GetStart()), pt(t.GetEnd()), mm(t.GetWidth()))
            copper["track"].append((key, t.GetNetname()))
    for kind, items in copper.items():
        for k, (_, net) in zip(unique(sorted(i[0] for i in items)), sorted(items)):
            s[kind][k] = {"net": net}

    zones = []
    for z in board.Zones():
        layers = ",".join(board.GetLayerName(l) for l in z.GetLayerSet().Seq())
        key = "%s [%s] %s" % ("rule-area" if z.GetIsRuleArea() else "copper", layers, poly(z.Outline()))
        props = {
            "net": None if z.GetIsRuleArea() else z.GetNetname(),
            "name": z.GetZoneName(),
            "priority": z.GetAssignedPriority(),
            "clearance": call(z, "GetLocalClearance"),
            "min_thickness": mm(z.GetMinThickness()),
            "pad_connection": z.GetPadConnection(),
            "thermal_gap": mm(z.GetThermalReliefGap()),
            "thermal_spoke": mm(z.GetThermalReliefSpokeWidth()),
            "fill_mode": call(z, "GetFillMode"),
            "island_removal": call(z, "GetIslandRemovalMode"),
            "keepout": [call(z, m) for m in ("GetDoNotAllowTracks", "GetDoNotAllowVias", "GetDoNotAllowPads",
                                             "GetDoNotAllowZoneFills", "GetDoNotAllowFootprints")],
        }
        zones.append((key, json.loads(json.dumps(props, default=str))))
    for k, (_, props) in zip(unique(sorted(z[0] for z in zones)), sorted(zones, key=lambda z: z[0])):
        s["zone"][k] = props

    drawings = []
    for d in board.GetDrawings():
        obj = d.Cast()
        if d.GetClass() == "PCB_SHAPE":
            drawings.append(shape_geom(obj))
        else:
            drawings.append("%s %s %s %r" % (d.GetClass(), d.GetLayerName(), pt(d.GetPosition()), call(obj, "GetText")))
    for k in unique(sorted(drawings)):
        s["drawing"][k] = {}

    ds = board.GetDesignSettings()
    stackup = call(ds, "GetStackupDescriptor")
    s["setup"] = json.loads(json.dumps({
        "copper_layers": board.GetCopperLayerCount(),
        "thickness": mm(ds.GetBoardThickness()),
        "finish": getattr(stackup, "m_FinishType", None),
        "min_clearance": mm(ds.m_MinClearance),
        "min_track": mm(ds.m_TrackMinWidth),
        "min_via": mm(ds.m_ViasMinSize),
        "min_through_drill": mm(ds.m_MinThroughDrill),
        "hole_clearance": mm(ds.m_HoleClearance),
        "copper_edge_clearance": mm(ds.m_CopperEdgeClearance),
        "mask_expansion": mm(ds.m_SolderMaskExpansion),
    }, default=str))
    return s


def net_renames(old, new):
    """Old net -> new net where every common pad on the old net moved to one new net."""
    seen = collections.defaultdict(set)
    for k in set(old["footprint"]) & set(new["footprint"]):
        a, b = old["footprint"][k]["pad_nets"], new["footprint"][k]["pad_nets"]
        for pad in set(a) & set(b):
            if a[pad]:
                seen[a[pad]].add(b[pad])
    old_nets = {p for f in old["footprint"].values() for p in f["pad_nets"].values()}
    new_nets = {p for f in new["footprint"].values() for p in f["pad_nets"].values()}
    renames = {}
    for a, bs in seen.items():
        if len(bs) == 1:
            b = next(iter(bs))
            if b != a and b and a not in new_nets and b not in old_nets:
                renames[a] = b
    return renames


def diff(old, new):
    out = {"removed": [], "added": [], "changed": [], "renamed_nets": net_renames(old, new)}

    def changed(kind, key, attr, a, b, **extra):
        out["changed"].append(dict({"kind": kind, "key": key, "attr": attr, "old": a, "new": b}, **extra))

    for kind in KINDS:
        o, n = old[kind], new[kind]
        out["removed"] += [{"kind": kind, "key": k} for k in sorted(set(o) - set(n))]
        out["added"] += [{"kind": kind, "key": k} for k in sorted(set(n) - set(o))]

    for k in sorted(set(old["footprint"]) & set(new["footprint"])):
        a, b = old["footprint"][k], new["footprint"][k]
        for attr in ("ref", "lib_id", "pos", "rot", "layer", "locked", "attributes", "dnp", "pads", "graphics",
                     "pad_nets"):
            if a[attr] != b[attr]:
                changed("footprint", k, attr, a[attr], b[attr])
        for name in sorted(set(a["fields"]) - set(b["fields"])):
            out["removed"].append({"kind": "field", "key": "%s/%s" % (k, name), "old": a["fields"][name]})
        for name in sorted(set(b["fields"]) - set(a["fields"])):
            out["added"].append({"kind": "field", "key": "%s/%s" % (k, name), "new": b["fields"][name]})
        for name in sorted(set(a["fields"]) & set(b["fields"])):
            if a["fields"][name] != b["fields"][name]:
                changed("field", "%s/%s" % (k, name), "text", a["fields"][name], b["fields"][name])

    for kind in ("track", "arc", "via", "zone"):
        for k in sorted(set(old[kind]) & set(new[kind])):
            a, b = old[kind][k], new[kind][k]
            for attr in sorted(set(a) | set(b)):
                if a.get(attr) != b.get(attr):
                    rename = attr == "net" and out["renamed_nets"].get(a.get(attr)) == b.get(attr)
                    changed(kind, k, attr, a.get(attr), b.get(attr), rename=rename)

    for attr in sorted(set(old["setup"]) | set(new["setup"])):
        if old["setup"].get(attr) != new["setup"].get(attr):
            changed("setup", "board", attr, old["setup"].get(attr), new["setup"].get(attr))
    return out


def failures(d, mode, allow):
    def allowed(kind, key):
        return any(fnmatch.fnmatchcase("%s:%s" % (kind, key), pat) for pat in allow)

    lib_swapped = {c["key"] for c in d["changed"] if c["kind"] == "footprint" and c["attr"] == "lib_id"}
    bad = [r for r in d["removed"] if not allowed(r["kind"], r["key"])]
    for c in d["changed"]:
        if c["attr"] == "net" and not c.get("rename") and not allowed("net-change", c["key"]):
            bad.append(c)
        elif mode != "build":
            continue
        elif c["kind"] == "footprint" and c["attr"] in ("pos", "rot", "layer", "locked"):
            bad.append(c)
        elif (c["kind"] == "footprint" and c["attr"] in ("pads", "graphics", "attributes")
              and c["key"] not in lib_swapped and not allowed("footprint-lib", c["key"])):
            # Same library footprint, different content: either the part's .kicad_mod was
            # edited (allow with footprint-lib:KEY) or atopile's re-sync mangled it.
            bad.append(c)
        elif (c["kind"] == "zone" and c["attr"] != "net") or c["kind"] == "setup":
            bad.append(c)
    return bad


# Item lists whose order in the file carries no meaning; writers reorder them freely.
UNORDERED = {"footprint", "segment", "arc", "via", "zone", "pad", "group", "fp_line", "fp_circle", "fp_arc",
             "fp_poly", "fp_rect", "fp_curve", "fp_text", "gr_line", "gr_circle", "gr_arc", "gr_poly",
             "gr_rect", "gr_curve", "gr_text", "model"}


def canonical(node):
    if not isinstance(node, list):
        return node
    kids = [canonical(c) for c in node]
    fixed = [c for c in kids if not (isinstance(c, list) and sexp.head(c) in UNORDERED)]
    loose = [c for c in kids if isinstance(c, list) and sexp.head(c) in UNORDERED]
    return fixed + sorted(loose, key=lambda c: "\n".join(sexp.dump_lines(c)))


def normalized_text(path):
    """The board as pcbnew writes it, with order-free item lists sorted."""
    out = os.path.join(tempfile.mkdtemp(), "n.kicad_pcb")
    pcbnew.SaveBoard(out, pcbnew.LoadBoard(path))
    return sexp.dump_lines(canonical(sexp.load(out)))


def git(top, *args):
    return subprocess.run(["git", "-C", top] + list(args), capture_output=True)


def load_rev(board_path, rev):
    """Board at `rev` as a temp file; None if the file doesn't exist there. Exits 2 on a bad rev."""
    path = os.path.realpath(board_path)
    res = git(os.path.dirname(path), "rev-parse", "--show-toplevel")
    if res.returncode != 0:
        sys.exit("board_diff: %s is not in a git repository" % board_path)
    top = os.path.realpath(res.stdout.decode().strip())
    if git(top, "rev-parse", "--verify", "--quiet", rev + "^{commit}").returncode != 0:
        sys.exit("board_diff: revision %s not found (shallow clone?)" % rev)
    rel = os.path.relpath(path, top)
    res = git(top, "show", "%s:%s" % (rev, rel))
    if res.returncode != 0:
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".kicad_pcb", delete=False)
    tmp.write(res.stdout)
    tmp.close()
    return tmp.name


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--rev", default="HEAD", help="git revision to compare with (default: HEAD)")
    g.add_argument("--against", help="compare with this board file instead of a git revision")
    ap.add_argument("--mode", choices=("commit", "build"), default="commit")
    ap.add_argument("--strict", action="store_true", help="fail on any difference")
    ap.add_argument("--allow", "--allow-removed", action="append", default=[], metavar="KIND:KEY", dest="allow")
    ap.add_argument("--allow-new", action="store_true", help="exit 0 if the baseline has no such board")
    ap.add_argument("--json", help="write the full result as JSON here")
    args = ap.parse_args()

    if args.against:
        if not os.path.exists(args.against):
            sys.exit("board_diff: baseline %s does not exist" % args.against)
        old_path, baseline = args.against, args.against
    else:
        old_path, baseline = load_rev(args.board, args.rev), "%s:%s" % (args.rev, args.board)
    if old_path is None:
        if args.allow_new:
            print("board_diff: %s is new (not in %s)" % (args.board, args.rev))
            return 0
        print("board_diff: FAIL %s not found at %s (pass --allow-new for a new board)" % (args.board, args.rev))
        return 2

    old = snapshot(pcbnew.LoadBoard(old_path))
    new = snapshot(pcbnew.LoadBoard(args.board))
    d = diff(old, new)
    bad = failures(d, args.mode, args.allow)
    text_diff = []
    if args.strict:
        bad = d["removed"] + d["added"] + d["changed"]
        text_diff = list(difflib.unified_diff(normalized_text(old_path), normalized_text(args.board),
                                              "baseline", "board", n=1, lineterm=""))

    def counts(s):
        c = {k: len(s[k]) for k in KINDS}
        c["field"] = sum(len(f["fields"]) for f in s["footprint"].values())
        return c

    ok = not bad and not text_diff
    result = {
        "board": args.board, "baseline": baseline, "mode": args.mode, "strict": args.strict,
        "allow": args.allow, "counts_before": counts(old), "counts_after": counts(new),
        "diff": d, "failures": bad, "normalized_text_diff": text_diff[:400], "ok": ok,
    }
    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2)

    print("board_diff: %s vs %s (mode %s%s)" % (args.board, baseline, args.mode, ", strict" if args.strict else ""))
    print("  before: %s" % result["counts_before"])
    print("  after:  %s" % result["counts_after"])
    for a, b in sorted(d["renamed_nets"].items()):
        print("  renamed net %s -> %s" % (a, b))
    fail_ids = {id(x) for x in bad}
    for label in ("removed", "added", "changed"):
        for item in d[label]:
            extra = ""
            if label == "changed":
                extra = " %s: %r -> %r%s" % (item["attr"], item["old"], item["new"], " (net rename)" if item.get("rename") else "")
            mark = "!" if id(item) in fail_ids else " "
            print(" %s%-7s %-9s %s%s" % (mark, label, item["kind"], item["key"], extra))
    if text_diff:
        print("  normalized text differs (%d diff lines), first lines:" % len(text_diff))
        for line in text_diff[:20]:
            print("    " + line)
    if not ok:
        print("board_diff: FAIL (%d failing differences%s)" % (len(bad), ", text differs" if text_diff else ""))
        return 1
    print("board_diff: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
