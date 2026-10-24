"""Place the dock board's footprints and draw its outline (phase 7).

    "$KICAD_PY" scripts/dock/place.py [BOARD] [--check]      default dock-pcb/layouts/dock/dock.kicad_pcb

  - Edge.Cuts: the outline and the magnet cutouts from dock-pcb/geometry.json, which the
    tray CAD writes (`mech dock-geometry`): the board follows the tray. Board drawings on
    Edge.Cuts are replaced.
  - The pogo pins P1-P6 on the halves' pad centres (geometry "pins", in order: left half
    pads 1-3, right half pads 1-3), J1 with its front face on the board's front edge, and
    the screw holes H1/H2: exactly where geometry.json puts them.
  - Everything else from dock-pcb/placement.json. Every part except the pins must lie inside
    geometry.json's parts area (on the board, PARTS_CLEAR away from the pockets): a case
    rests on the board everywhere else.
  - Designators: only those in placement.json's "labels" show (the connector and the LED),
    centred where it puts them, as 1.0 mm text with a 0.15 mm stroke (JLC's legible minimum);
    the rest would only crowd the tab.
  - Under J1's body, a rule area J1_SHELL on both layers forbidding vias (its shell sits on
    the solder mask, as on the keyboard), and J1_FRONT on F.Cu forbidding tracks too, from
    just in front of its pad row to its front: no track runs under the grounded shell.
The dock is assembled on its top side: every footprint must be a top-side one.
--check changes nothing and fails if anything differs. Runs under KiCad's Python; 3.9.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
SHELL_NAME, FRONT_NAME = "J1_SHELL", "J1_FRONT"
FRONT_GAP = 0.2  # mm from J1's pad row to J1_FRONT
LABEL_SIZE, LABEL_STROKE = 1.0, 0.15


def nm(v):
    return int(round(v * 1e6))


def at(x, y):
    return pcbnew.VECTOR2I(nm(x), nm(y))


def inside(poly, x, y):
    """Point in polygon (even-odd)."""
    n, hit = len(poly), False
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def courtyard_corners(fp, inset=0.0):
    """The corners of the footprint's courtyard box (its lines' centres), mm; `inset` pulls
    them in, so a courtyard drawn on the board's edge (J1's front) counts as inside."""
    fp.BuildCourtyardCaches()
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    x0, y0, x1, y1 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6
    w = 0.05 + inset  # KiCad's courtyard box includes half the 0.1 mm line
    return [(x0 + w, y0 + w), (x1 - w, y0 + w), (x1 - w, y1 - w), (x0 + w, y1 - w)]


def head_points(x, y, d, n=16):
    return [(x + d / 2 * math.cos(2 * math.pi * i / n), y + d / 2 * math.sin(2 * math.pi * i / n)) for i in range(n)]


def shell_polygon(fp):
    return [(nm(x), nm(y)) for x, y in courtyard_corners(fp)]


def front_polygon(fp):
    """J1's courtyard in front of its pad row (larger y: the board's front edge)."""
    (x0, y0), (x1, _), _, (_, y1) = courtyard_corners(fp)
    row = max(p.GetBoundingBox().GetBottom() for p in fp.Pads() if p.GetNumber() != "7") / 1e6
    y0 = row + FRONT_GAP
    return [(nm(x0), nm(y0)), (nm(x1), nm(y0)), (nm(x1), nm(y1)), (nm(x0), nm(y1))]


def rule_area(board, name, layers, poly, tracks):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowCopperPour(False)
    z.SetDoNotAllowFootprints(False)
    z.Outline().NewOutline()
    for x, y in poly:
        z.Outline().Append(x, y)
    board.Add(z)


def zone_points(z):
    o = z.Outline().COutline(0)
    return sorted((o.CPoint(i).x, o.CPoint(i).y) for i in range(o.PointCount()))


def edge_items(geo):
    """[(kind, data)] of what Edge.Cuts must hold, in a comparable form."""
    out = []
    pts = geo["outline"]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        out.append(("segment", tuple(sorted([(nm(a[0]), nm(a[1])), (nm(b[0]), nm(b[1]))]))))
    for c in geo["cutouts"]:
        out.append(("circle", ((nm(c["x"]), nm(c["y"])), nm(c["d"] / 2))))
    return sorted(out)


def board_edges(board):
    out = []
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
            s, e = d.GetStart(), d.GetEnd()
            out.append(("segment", tuple(sorted([(s.x, s.y), (e.x, e.y)]))))
        elif d.GetShape() == pcbnew.SHAPE_T_CIRCLE:
            c = d.GetCenter()
            out.append(("circle", ((c.x, c.y), d.GetRadius())))
        else:
            out.append(("other", d.GetShape()))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board", nargs="?", default=str(ROOT / "dock-pcb/layouts/dock/dock.kicad_pcb"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    geo = json.loads((ROOT / "dock-pcb/geometry.json").read_text())
    placement_file = json.loads((ROOT / "dock-pcb/placement.json").read_text())
    placement, labels = placement_file["parts"], placement_file["labels"]
    targets = {}
    for i, p in enumerate(geo["pins"]):
        targets["P%d" % (i + 1)] = dict(x=p["x"], y=p["y"], rot=0.0, net=p["net"])
    targets["J1"] = dict(x=geo["usb"]["x"], y=geo["usb"]["y"], rot=geo["usb"]["rot"])
    for i, s in enumerate(geo["screws"]):
        targets["H%d" % (i + 1)] = dict(x=s["x"], y=s["y"], rot=0.0)
    for ref, r in placement.items():
        if ref in targets:
            sys.exit("placement.json places %s, which comes from geometry.json" % ref)
        targets[ref] = r

    board = pcbnew.LoadBoard(args.board)
    footprints = list(board.GetFootprints())
    zones = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName() in (SHELL_NAME, FRONT_NAME)]
    edges = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    problems = []
    seen = set()
    for fp in footprints:
        ref = fp.GetReference()
        t = targets.get(ref)
        if t is None:
            problems.append("%s: no placement" % ref)
            continue
        seen.add(ref)
        if fp.GetLayer() != pcbnew.F_Cu:
            problems.append("%s: not a top-side footprint (the dock is assembled on its top)" % ref)
            continue
        if "net" in t:
            nets = {p.GetNetname() for p in fp.Pads()}
            if nets != {t["net"]}:
                problems.append("%s is on %s, the half's pad there is %s" % (ref, sorted(nets), t["net"]))
        if args.check:
            dr = (fp.GetOrientationDegrees() - t["rot"]) % 360
            if fp.GetPosition() != at(t["x"], t["y"]) or min(dr, 360 - dr) > 1e-6:
                problems.append("%s at (%.4f, %.4f) %.3f deg, placement says (%.4f, %.4f) %.3f deg" % (
                    ref, fp.GetPosition().x / 1e6, fp.GetPosition().y / 1e6, fp.GetOrientationDegrees(),
                    t["x"], t["y"], t["rot"]))
        else:
            fp.SetPosition(at(t["x"], t["y"]))
            fp.SetOrientationDegrees(t["rot"])
        f, lab = fp.Reference(), labels.get(ref)
        want = (True, at(lab["x"], lab["y"]), float(lab["rot"]), nm(LABEL_SIZE), nm(LABEL_STROKE),
                pcbnew.GR_TEXT_H_ALIGN_CENTER, pcbnew.GR_TEXT_V_ALIGN_CENTER) if lab else (False,)
        state = (f.IsVisible(), f.GetPosition(), f.GetTextAngleDegrees(), f.GetTextSize().x, f.GetTextThickness(),
                 f.GetHorizJustify(), f.GetVertJustify())
        if args.check:
            if state[:len(want)] != want:
                problems.append("%s designator: %s, labels say %s" % (ref, state[:len(want)], want))
        else:
            f.SetVisible(bool(lab))
            if lab:
                f.SetPosition(at(lab["x"], lab["y"]))
                f.SetTextAngleDegrees(lab["rot"])
                f.SetTextSize(pcbnew.VECTOR2I(nm(LABEL_SIZE), nm(LABEL_SIZE)))
                f.SetTextThickness(nm(LABEL_STROKE))
                f.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
                f.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    for ref in sorted(set(labels) - seen):
        problems.append("%s: labelled but not on the board" % ref)
    for ref in sorted(set(targets) - seen):
        problems.append("%s: placed but not on the board" % ref)

    heads = {"H%d" % (i + 1): s for i, s in enumerate(geo["screws"])}
    for fp in footprints:
        ref = fp.GetReference()
        if ref.startswith("P") or ref not in targets:
            continue
        if ref in heads:  # a screw head on the board's top
            corners = head_points(targets[ref]["x"], targets[ref]["y"], heads[ref]["head_d"])
        else:
            corners = courtyard_corners(fp, inset=0.01)
        outside = [c for c in corners if not inside(geo["parts_area"], *c)]
        if outside:
            problems.append("%s: courtyard corner %s outside the parts area (a case rests there)" % (
                ref, ", ".join("(%.2f, %.2f)" % c for c in outside)))

    if args.check:
        if board_edges(board) != edge_items(geo):
            problems.append("Edge.Cuts differs from geometry.json")
        j1 = next(fp for fp in footprints if fp.GetReference() == "J1")
        want = {SHELL_NAME: (False, {pcbnew.F_Cu, pcbnew.B_Cu}, shell_polygon(j1)),
                FRONT_NAME: (True, {pcbnew.F_Cu}, front_polygon(j1))}
        for name, (tracks, layers, poly) in want.items():
            found = [z for z in zones if z.GetZoneName() == name]
            if len(found) != 1:
                problems.append("%s rule area missing" % name)
                continue
            z = found[0]
            if not z.GetDoNotAllowVias() or z.GetDoNotAllowTracks() != tracks or set(z.GetLayerSet().Seq()) != layers:
                problems.append("%s rule area's settings changed" % name)
            elif zone_points(z) != sorted(poly):
                problems.append("%s outline differs from J1's" % name)
        for p in problems:
            print("FAIL", p)
        print("dock placement: %s" % ("OK" if not problems else "%d problems" % len(problems)))
        sys.stdout.flush()
        os._exit(1 if problems else 0)

    if problems:
        for p in problems:
            print("FAIL", p)
        sys.stdout.flush()
        os._exit(1)
    for item in zones + edges:
        board.Remove(item)
    pts = geo["outline"]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(at(*a))
        s.SetEnd(at(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(nm(0.1))
        board.Add(s)
    for c in geo["cutouts"]:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_CIRCLE)
        s.SetCenter(at(c["x"], c["y"]))
        s.SetEnd(at(c["x"] + c["d"] / 2, c["y"]))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(nm(0.1))
        board.Add(s)
    j1 = next(fp for fp in footprints if fp.GetReference() == "J1")
    rule_area(board, SHELL_NAME, (pcbnew.F_Cu, pcbnew.B_Cu), shell_polygon(j1), tracks=False)
    rule_area(board, FRONT_NAME, (pcbnew.F_Cu,), front_polygon(j1), tracks=True)
    board.Save(args.board)
    print("placed %d footprints on %s; outline %d segments, %d cutouts; rule areas %s, %s" % (
        len(seen), args.board, len(pts), len(geo["cutouts"]), SHELL_NAME, FRONT_NAME))
    sys.stdout.flush()
    os._exit(0)  # KiCad 9's SWIG objects segfault in destructors at exit


if __name__ == "__main__":
    main()
