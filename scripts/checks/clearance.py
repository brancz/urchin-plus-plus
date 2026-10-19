#!/usr/bin/env python3
"""Placement clearance and keep-out report for a half (phase 3; rules 2 and 6).

    "$KICAD_PY" scripts/checks/clearance.py BOARD --half left|right [--json OUT] [--spots R]

A part's envelope on a side is its courtyard plus its copper pads on that side
(EasyEDA courtyards often stop inside the pads), each as its own polygon. Checked:
  - side: every assembled part (in BOM and position files) is on the bottom; on top
    only keys (their sockets are on the bottom), the battery outline and its pads
    (rule 2);
  - parts on the same side keep 0.25 mm between envelopes (JLC assembly spacing),
    except the mechanical parts whose overlaps the original already has;
  - each envelope keeps 0.3 mm from every hole edge (any side) and from the outline;
    for the parts meant to reach past the edge (USB-C shell, switch lever) only their
    copper pads must keep 0.3 mm inside;
  - bottom parts stay outside the tenting puck's courtyard (the puck must sit flat),
    and keys' socket pads count as obstacles;
  - the antenna keep-out (ANTENNA_KEEPOUT, drawn by place.py; its layers and forbid
    settings are checked too): no copper pad, track, via or zone fill (measured as
    intersection area after a fresh fill) of any net on any layer, no part but U1 and
    no key reaching into it, and the battery at least 3 mm away; NPTH holes without
    copper are allowed;
  - a footprint's own non-plated holes keep 0.25 mm from its own copper (KiCad's DRC
    doesn't check that);
  - the battery's top envelope keeps 0.25 mm from every other top item and hole.
--spots R lists free bottom positions for a circle of radius R (feet, discs).
Exit 1 on any violation. Runs under KiCad's Python; Python 3.9.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
PART_GAP = 0.25
HOLE_GAP = 0.3
EDGE_GAP = 0.3
PAST_EDGE = {"J1", "SW35"}   # USB-C shell and slide-switch lever reach past the inner edge
TOP_OK = ("SW", "BT", "H")   # keys, the battery (pads BT1, outline BT2), puck and case holes (not assembled)
# Through-hole joints under the battery: J1's shell legs (1.01 mm) and SW35's pegs (0.55 mm) are
# shorter than the 1.6 mm board, so nothing protrudes; the cell sits on 1 mm foam tape over them.
UNDER_BATTERY = {"J1", "SW35"}
BATTERY_KEEPOUT_GAP = 3.0  # mm between the cell and the antenna keep-out
OWN_HOLE_GAP = 0.25        # mm, a footprint's copper to its own non-plated hole (JLC hole-to-copper)
MECHANICAL = ("SW", "H")     # the original's own parts: overlaps among them are inherited


def mm(v):
    return v / 1e6


def hull(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def poly_points(sps):
    out = []
    for i in range(sps.OutlineCount()):
        o = sps.Outline(i)
        for j in range(o.PointCount()):
            p = o.CPoint(j)
            out.append((mm(p.x), mm(p.y)))
    return out


def seg_dist(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def inside(p, poly):
    c = False
    for i in range(len(poly)):
        a, b = poly[i], poly[i - 1]
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]:
            c = not c
    return c


def _orient(a, b, c):
    v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)


def segs_cross(a, b, c, d):
    """Do segments a-b and c-d touch or cross?"""
    o1, o2, o3, o4 = _orient(a, b, c), _orient(a, b, d), _orient(c, d, a), _orient(c, d, b)
    if o1 != o2 and o3 != o4:
        return True
    on = lambda p, q, r: min(p[0], r[0]) - 1e-12 <= q[0] <= max(p[0], r[0]) + 1e-12 and \
        min(p[1], r[1]) - 1e-12 <= q[1] <= max(p[1], r[1]) + 1e-12
    return (o1 == 0 and on(a, c, b)) or (o2 == 0 and on(a, d, b)) or (o3 == 0 and on(c, a, d)) or (o4 == 0 and on(c, b, d))


def edges_of(P):
    """Edges of a polygon, or the single segment of a two-point path."""
    if len(P) == 2:
        return [(P[0], P[1])]
    return [(P[i - 1], P[i]) for i in range(len(P))]


def poly_dist(A, B):
    """Distance between two polygons (or a segment and a polygon); 0 if they touch or overlap."""
    if not A or not B:
        return float("inf")
    EA, EB = edges_of(A), edges_of(B)
    if any(segs_cross(a, b, c, d) for a, b in EA for c, d in EB):
        return 0.0
    if (len(B) > 2 and inside(A[0], B)) or (len(A) > 2 and inside(B[0], A)):
        return 0.0
    d = float("inf")
    for P, EQ in ((A, EB), (B, EA)):
        for p in P:
            for a, b in EQ:
                d = min(d, seg_dist(p, a, b))
    return d


def circle_poly(c, r, n=24):
    return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def outlines(sps):
    out = []
    for i in range(sps.OutlineCount()):
        o = sps.Outline(i)
        out.append([(mm(o.CPoint(j).x), mm(o.CPoint(j).y)) for j in range(o.PointCount())])
    return out


def envelope(fp, side):
    """List of polygons: the courtyard outlines and the copper pads on that side."""
    crt = pcbnew.B_CrtYd if side == "bottom" else pcbnew.F_CrtYd
    cu = pcbnew.B_Cu if side == "bottom" else pcbnew.F_Cu
    polys = [hull(o) for o in outlines(fp.GetCourtyard(crt)) if o]
    for p in fp.Pads():
        if p.IsOnLayer(cu) and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
            sps = pcbnew.SHAPE_POLY_SET()
            p.TransformShapeToPolygon(sps, cu, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
            polys += [o for o in outlines(sps) if o]
    return polys


def env_dist(A, B):
    return min((poly_dist(a, b) for a in A for b in B), default=float("inf"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--half", required=True, choices=("left", "right"))
    ap.add_argument("--json")
    ap.add_argument("--spots", type=float)
    args = ap.parse_args()
    board = pcbnew.LoadBoard(args.board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())  # check fresh fills, not whatever was saved
    problems, notes = [], []

    edge_segs = []
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline)
    edge_poly = poly_points(outline)
    for i in range(len(edge_poly)):
        edge_segs.append((edge_poly[i], edge_poly[i - 1]))

    holes = []  # (centre, radius, ref)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetDrillSize().x > 0:
                holes.append(((mm(p.GetPosition().x), mm(p.GetPosition().y)), mm(max(p.GetDrillSize().x, p.GetDrillSize().y)) / 2,
                              fp.GetReference()))

    keepout = next((z for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName() == "ANTENNA_KEEPOUT"), None)
    if keepout is None:
        problems.append("no ANTENNA_KEEPOUT rule area")
        ko = []
    else:
        ko = poly_points(keepout.Outline())
        layers = [l for l in (pcbnew.F_Cu, pcbnew.B_Cu) if keepout.GetLayerSet().Contains(l)]
        if len(layers) != 2 or not (keepout.GetDoNotAllowTracks() and keepout.GetDoNotAllowVias()
                                    and keepout.GetDoNotAllowCopperPour()):
            problems.append("ANTENNA_KEEPOUT must forbid tracks, vias and pour on F.Cu and B.Cu")

    env = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        side = "bottom" if fp.GetLayer() == pcbnew.B_Cu else "top"
        assembled = not (fp.IsExcludedFromBOM() or fp.IsExcludedFromPosFiles())
        if assembled and side != "bottom":
            problems.append("%s is assembled but on the top (rule 2)" % ref)
        if side == "top" and not ref.startswith(TOP_OK):
            problems.append("%s is on the top; only keys and the battery may be (rule 2)" % ref)
        for s in ("bottom", "top"):
            e = envelope(fp, s)
            if e:
                env[(ref, s)] = e

    def mech(r):
        return r.startswith(MECHANICAL) and r not in ("SW35", "SW36")  # the slide switch and reset are electronics

    items = sorted(env)
    min_gap = {}
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if a[1] != b[1] or a[0] == b[0]:
                continue
            if mech(a[0]) and mech(b[0]):
                continue
            if a[1] == "top" and {a[0], b[0]} & {"BT2"} and {a[0], b[0]} & UNDER_BATTERY:
                continue
            d = env_dist(env[a], env[b])
            min_gap[(a, b)] = d
            if d < PART_GAP:
                problems.append("%s and %s (%s): %.2f mm apart, need %.2f" % (a[0], b[0], a[1], d, PART_GAP))

    for (ref, side), e in env.items():
        if mech(ref):
            continue
        for c, r, href in holes:
            if href == ref or (ref == "BT2" and href in UNDER_BATTERY):
                continue
            d = env_dist(e, [circle_poly(c, r)])
            if d < HOLE_GAP:
                problems.append("%s (%s) is %.2f mm from a hole of %s at (%.2f, %.2f), need %.2f" % (ref, side, d, href, c[0], c[1], HOLE_GAP))
        edge_e = e
        if ref in PAST_EDGE:  # the body may reach past the edge; the copper may not
            fp = board.FindFootprintByReference(ref)
            cu = pcbnew.B_Cu if side == "bottom" else pcbnew.F_Cu
            edge_e = []
            for pad in fp.Pads():
                if pad.IsOnLayer(cu) and pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                    sps = pcbnew.SHAPE_POLY_SET()
                    pad.TransformShapeToPolygon(sps, cu, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
                    edge_e += [o for o in outlines(sps) if o]
        if edge_e:
            d = min(seg_dist(p, a, b) for poly in edge_e for p in poly for a, b in edge_segs)
            outside = any(not inside(p, edge_poly) for poly in edge_e for p in poly)
            if outside or d < EDGE_GAP:
                problems.append("%s (%s) is %s the board edge (%.2f mm), need %.2f inside" % (
                    ref, side, "past" if outside else "close to", d, EDGE_GAP))
        if ko and ref != "U1" and env_dist(e, [ko]) == 0:
            problems.append("%s (%s) is inside the antenna keep-out (rule 6)" % (ref, side))
        if ko and ref == "BT2" and env_dist(e, [ko]) < BATTERY_KEEPOUT_GAP:
            problems.append("the battery is %.2f mm from the antenna keep-out, need %.1f" % (env_dist(e, [ko]), BATTERY_KEEPOUT_GAP))

    # Keys (mechanical) may come near the keep-out but not into it.
    for (ref, side), e in env.items():
        if ko and mech(ref) and ref.startswith("SW") and env_dist(e, [ko]) == 0:
            problems.append("%s (%s) reaches into the antenna keep-out (rule 6)" % (ref, side))

    # A part's own copper against its own holes (KiCad's DRC skips these): hole-to-copper 0.25 mm.
    for fp in board.GetFootprints():
        own = [p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]
        for h in own:
            hc = (mm(h.GetPosition().x), mm(h.GetPosition().y))
            hr = mm(max(h.GetDrillSize().x, h.GetDrillSize().y)) / 2
            for p in fp.Pads():
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    continue
                for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                    if p.IsOnLayer(layer):
                        sps = pcbnew.SHAPE_POLY_SET()
                        p.TransformShapeToPolygon(sps, layer, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
                        d = min(poly_dist(o, circle_poly(hc, hr, 48)) for o in outlines(sps))
                        if d < OWN_HOLE_GAP:
                            problems.append("%s pad %s is %.3f mm from its own %.2f mm hole, need %.2f" % (
                                fp.GetReference(), p.GetNumber(), d, 2 * hr, OWN_HOLE_GAP))
                        break

    puck = board.FindFootprintByReference("H1")
    if puck is not None:
        pc = (mm(puck.GetPosition().x), mm(puck.GetPosition().y))
        pr = 20.55
        for (ref, side), e in env.items():
            if side == "bottom" and not mech(ref) and env_dist(e, [circle_poly(pc, pr, 72)]) == 0:
                problems.append("%s is under the tenting puck (courtyard radius %.2f mm)" % (ref, pr))

    if ko:
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    continue
                for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                    if p.IsOnLayer(layer):
                        sps = pcbnew.SHAPE_POLY_SET()
                        p.TransformShapeToPolygon(sps, layer, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
                        if any(poly_dist(o, ko) == 0 for o in outlines(sps)):
                            problems.append("pad %s.%s copper inside the antenna keep-out" % (fp.GetReference(), p.GetNumber()))
        for t in board.GetTracks():
            pts = [(mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))]
            if any(inside(p, ko) for p in pts) or poly_dist(pts, ko) < mm(t.GetWidth()) / 2:
                problems.append("%s on %s inside the antenna keep-out" % (t.GetClass(), t.GetNetname()))
        ko_sps = pcbnew.SHAPE_POLY_SET(keepout.Outline())
        for z in board.Zones():
            if z.GetIsRuleArea():
                continue
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if z.IsOnLayer(layer) and z.HasFilledPolysForLayer(layer):
                    inter = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(layer))
                    inter.BooleanIntersection(ko_sps)
                    area = inter.Area() / 1e12  # nm^2 -> mm^2
                    if area > 1e-4:
                        problems.append("zone %s fill on %s covers %.4f mm^2 of the antenna keep-out" % (
                            z.GetNetname(), board.GetLayerName(layer), area))

    spots = []
    if args.spots:
        r = args.spots
        obstacles = [e for (ref, side), e in env.items() if side == "bottom" and not ref.startswith("MK")]
        xs = [p[0] for p in edge_poly]
        ys = [p[1] for p in edge_poly]
        pc = (mm(puck.GetPosition().x), mm(puck.GetPosition().y)) if puck else None
        y = min(ys)
        while y < max(ys):
            x = min(xs)
            while x < max(xs):
                c = (x, y)
                if inside(c, edge_poly) and min(seg_dist(c, a, b) for a, b in edge_segs) >= r + 1.0 and \
                        (pc is None or math.hypot(c[0] - pc[0], c[1] - pc[1]) >= r + 20.55 + 0.5) and \
                        all(math.hypot(c[0] - h[0][0], c[1] - h[0][1]) >= r + h[1] + 0.5 for h in holes):
                    cp = [circle_poly(c, r + 0.5, 16)]
                    if all(env_dist(cp, o) > 0 for o in obstacles):
                        spots.append((round(x, 1), round(y, 1)))
                x += 1.0
            y += 1.0
        notes.append("%d free spots for r=%.1f" % (len(spots), r))

    result = {"board": args.board, "half": args.half, "problems": problems, "notes": notes,
              "spots": spots, "min_part_gap_mm": round(min(min_gap.values()), 3) if min_gap else None}
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
    print("clearance %s (%s): %d envelopes, smallest part gap %s mm" % (args.board, args.half, len(env), result["min_part_gap_mm"]))
    for n in notes:
        print("  " + n)
    for p in problems:
        print("FAIL " + p)
    print("clearance: %s" % ("OK" if not problems else "FAIL (%d)" % len(problems)))
    sys.stdout.flush()
    os._exit(1 if problems else 0)


if __name__ == "__main__":
    main()
