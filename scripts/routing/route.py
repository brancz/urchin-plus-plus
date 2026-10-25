#!/usr/bin/env python3
"""Route a board (a half, or the dock): rip up, Freerouting, import, ground pour on both layers (phase 4).

    "$KICAD_PY" scripts/routing/route.py BOARD WORK_DIR [--passes 100] [--attempts 4 | --variants N...] [--jobs 6] [--threads 2]
    "$KICAD_PY" scripts/routing/route.py BOARD --ripup      # only remove tracks, vias, pours
    "$KICAD_PY" scripts/routing/route.py BOARD --ripup-nets NET...   # only those nets' tracks and vias
    "$KICAD_PY" scripts/routing/route.py BOARD --ripup-drc   # only the tracks and vias in a DRC error
    "$KICAD_PY" scripts/routing/route.py BOARD --restitch    # add the GND stitching vias that now fit
    "$KICAD_PY" scripts/routing/route.py BOARD WORK_DIR --complete-only --widths 0.175 0.3 [--clearance 0.17]
                                                            # completion passes on a routed BOARD

  1. Remove every track, via and GND pour; on a half, add the scripted critical routes
     (scripts/routing/preroutes.py: the USB-C receptacle's paired pins), locked so the
     router keeps them; save that as WORK_DIR/ripped.kicad_pcb.
  2. Export a Specctra DSN (net classes and the keep-out rule areas come along from the
     board and its .kicad_pro), with the routing boundary inset by 0.7 mm: the router
     keeps only track and via centres inside its boundary and ignores copper-to-edge
     clearance (0.3 mm + a 0.35 mm via radius).
  3. Run Freerouting 2.5.0 headless ($FREEROUTING_JAR, java 25+ on PATH), --jobs at a time,
     on --attempts variants of the DSN. Freerouting is deterministic, and its result is
     sensitive to track widths and clearance, so the variants differ in those: signal/power
     widths in eight combinations of 0.127-0.2 / 0.25-0.3 mm, each with a routing clearance
     of 0.17, then 0.175, then 0.18 mm (24 variants; all within the design rules: the rule is
     0.15 mm, and Freerouting undershoots near pads by up to ~0.025 mm). Attempt N routes
     VARIANTS[N]. Logs: WORK_DIR/attempt-N/.
  4. Finish every attempt on its own copy of the ripped board (one process each, KiCad 9's
     SWIG can't load many boards in one process): import the session and put every
     footprint back at its exact position (the session rounds them to 0.1 um; rule 1); drop the
     router's segments shorter than 1 um; widen its neck-downs at pads to JLC's 2-layer minimum,
     0.127 mm (more would eat the clearance);
     pour GND on F.Cu and B.Cu over the whole outline (0.3 mm clearance, 0.25 mm minimum
     width, thermal reliefs, islands removed; the keep-out rule areas forbid pour inside
     them), with a solid-connection GND zone under the module (its GND pads join the
     pour without thermal spokes); stitch the pours with GND vias (a 5 mm grid, a fence
     along the antenna keep-out's edge, a ring around the module, and a 1.6 mm grid under
     and within 3 mm of the module), each only where it sits wholly inside GND copper on
     both layers, outside the via-forbidding rule areas and part bodies (the module's
     body excepted: its datasheet wants grounded copper under it), and 0.5 mm
     hole-to-hole from every other hole; drop GND stubs closer than
     0.3 mm to the edge (to the edge-mounted USB-C and switch shells) if the pour keeps
     everything connected.
  5. Count each finished board's unconnected items with KiCad's own connectivity (the
     router's "0 unrouted" isn't reliable: its session can miss whole nets) and keep the
     best (fewest unconnected, then fewest vias).
  6. If that still has unconnected items, completion passes: export the best board with
     its tracks (pours removed) as a DSN, let Freerouting finish the rest, finish and
     count again; keep it if it is better. Up to --completions passes.
  7. Save the best as BOARD, and widen its tracks to 0.15 mm wherever KiCad's DRC allows
     (scripts/routing/widen.py).
GND is routed as a net too, wherever Freerouting gets it to; the pour completes it (on the
dock, the right half's GND pins hang on the pour alone). Connectivity is always counted with
the zones filled.
Prints a JSON summary. Runs under KiCad's Python; Python 3.9.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preroutes  # noqa: E402

POUR_LAYERS = {"GND_TOP": pcbnew.F_Cu, "GND_BOTTOM": pcbnew.B_Cu}  # whole-outline pours
POURS = set(POUR_LAYERS) | {"GND_MODULE"}                            # every zone route.py owns
EDGE_INSET = 0.7         # mm: 0.3 mm copper-to-edge + 0.35 mm via radius + margin
MIN_WIDTH = 0.127        # mm, JLC 2-layer minimum
ROUTE_CLEARANCE = 0.17   # mm: Freerouting undershoots its clearance by up to ~0.025 mm near pads
WIDTHS = [(0.2, 0.3), (0.15, 0.25), (0.175, 0.3), (0.15, 0.3),       # mm: signal (Default, USB), Power
          (0.127, 0.25), (0.127, 0.3), (0.175, 0.25), (0.2, 0.25)]
CLEARANCES = (ROUTE_CLEARANCE, 0.175, 0.18)                          # mm, routing clearance
VARIANTS = [(sig, pwr, cl) for cl in CLEARANCES for sig, pwr in WIDTHS]  # attempt N routes with VARIANTS[N]


def nm(v):
    return int(round(v * 1e6))


def inset_points(board, inset):
    """The outline inset by `inset` mm, as DSN coordinates (um, y up). Call it before any
    save or export: KiCad 9's SWIG hands back untyped objects afterwards."""
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline)
    outline.Inflate(-nm(inset), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, nm(0.005))
    if outline.OutlineCount() != 1:
        sys.exit("inset outline has %d parts" % outline.OutlineCount())
    o = outline.Outline(0)
    pts = ["%.1f %.1f" % (o.CPoint(i).x / 1000.0, -o.CPoint(i).y / 1000.0) for i in range(o.PointCount())]
    return pts + pts[:1]


def shrink_boundary(dsn, pts):
    """Replace the DSN's routing boundary with the given points (inset_points)."""
    text = open(dsn).read()
    new, n = re.subn(r"\(boundary\s*\(path pcb 0[^)]*\)\s*\)", "(boundary\n      (path pcb 0  %s)\n    )" % "  ".join(pts),
                     text, count=1)
    if n != 1:
        sys.exit("no boundary in %s" % dsn)
    open(dsn, "w").write(new)


def with_widths(dsn_text, signal, power, clearance=ROUTE_CLEARANCE):
    """Set the routing width of each net class in a DSN, and the routing clearance."""
    def fix(m):
        width = power if m.group(1) == "Power" else signal
        out = re.sub(r"\(width [0-9.]+\)", "(width %d)" % round(width * 1000), m.group(0), count=1)
        return re.sub(r"\(clearance [0-9.]+\)", "(clearance %d)" % round(clearance * 1000), out, count=1)
    out, n = re.subn(r"\(class (\S+) .*?\(rule.*?\)\s*\)", fix, dsn_text, flags=re.S)
    if n < 2:  # Default and Power; USB too on a half (the dock has no data pair)
        sys.exit("expected at least 2 net classes in the DSN, found %d" % n)
    return out


def prepare(board_path, work):
    """Rip up, save WORK/ripped.kicad_pcb and the routing DSN."""
    board = pcbnew.LoadBoard(board_path)
    boundary = inset_points(board, EDGE_INSET)
    tracks = list(board.GetTracks())  # take every wrapper before the first edit (KiCad 9 SWIG)
    pours = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetZoneName() in POURS]
    for item in tracks + pours:
        board.Remove(item)
    if preroutes.applies(board):
        preroutes.add(board)
    ripped = os.path.join(work, "ripped.kicad_pcb")
    board.Save(ripped)
    for ext in (".kicad_pro", ".kicad_dru"):
        src = os.path.splitext(board_path)[0] + ext
        if os.path.exists(src):
            shutil.copy(src, os.path.join(work, "ripped" + ext))
    dsn = os.path.join(work, "board.dsn")
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        sys.exit("DSN export failed")
    shrink_boundary(dsn, boundary)
    return dsn


STITCH_GRID = 5.0   # mm
FENCE_STEP = 1.6    # mm between fence vias (0.7 mm vias, 0.5 mm hole-to-hole needs >= 0.8)
RIPUP_DRC_TYPES = {"clearance", "items_not_allowed", "hole_clearance", "tracks_crossing", "shorting_items"}
MODULE_GRID = 1.6   # mm, candidate grid under and around the module (its courtyard grown by MODULE_MARGIN)
MODULE_MARGIN = 3.0 # mm
VIA = (0.7, 0.3)    # mm


def stitch(board, gnd, rule_areas):
    """Add GND stitching vias; returns how many. Candidates are tested against the GND pours
    filled without island removal: a pour island (under the module, between the far layer's
    tracks) is exactly what a stitching via connects, and the caller's refill, with islands
    removed again, keeps the islands that got one."""
    pours = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND"]
    modes = [z.GetIslandRemovalMode() for z in pours]
    for z in pours:
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
    pcbnew.ZONE_FILLER(board).Fill(pours)
    fills = {}
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        u = pcbnew.SHAPE_POLY_SET()
        for z in pours:
            if z.IsOnLayer(layer) and z.HasFilledPolysForLayer(layer):
                u.BooleanAdd(pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(layer)))
        u.Inflate(-nm(VIA[0] / 2 + 0.05), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, nm(0.005))
        fills[layer] = u
    for z, mode in zip(pours, modes):
        z.SetIslandRemovalMode(mode)
    forbid = []
    for z in rule_areas:
        if z.GetDoNotAllowVias():
            forbid.append(pcbnew.SHAPE_POLY_SET(z.Outline()))
    bodies = []
    for fp in board.GetFootprints():
        if fp.GetReference().startswith(("H1", "MK")):
            continue  # under the puck and the feet a tented via is harmless
        if fp.GetReference() == "U1":
            continue  # under the module, grounded copper on its side is what its datasheet (p.8) asks for
        fp.BuildCourtyardCaches()
        for layer in (pcbnew.B_CrtYd,):
            c = fp.GetCourtyard(layer)
            if c.OutlineCount():
                bodies.append(pcbnew.SHAPE_POLY_SET(c))
    holes = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetDrillSize().x > 0:
                holes.append((p.GetPosition().x, p.GetPosition().y, max(p.GetDrillSize().x, p.GetDrillSize().y) / 2))
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":  # a via fresh from a session has no drill of its own: the default's
            holes.append((t.GetPosition().x, t.GetPosition().y, t.GetDrillValue() / 2))

    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline)
    bb = outline.BBox()
    candidates = []
    y = bb.GetTop()
    while y < bb.GetBottom():
        x = bb.GetLeft()
        while x < bb.GetRight():
            candidates.append((x, y))
            x += nm(STITCH_GRID)
        y += nm(STITCH_GRID)
    ko = next((z for z in rule_areas if z.GetZoneName() == "ANTENNA_KEEPOUT"), None)
    if ko is not None:  # fence just outside the keep-out's inner edge
        kb = ko.Outline().BBox()
        x = kb.GetLeft()
        while x <= kb.GetRight():
            candidates.append((x, kb.GetBottom() + nm(0.9)))
            x += nm(FENCE_STEP)
    u1 = board.FindFootprintByReference("U1")
    if u1 is not None:  # ring around the module, outside its edge pads
        u1.BuildCourtyardCaches()
        cb = u1.GetCourtyard(pcbnew.B_CrtYd).BBox()
        ring = nm(1.9)
        x0, x1, y1 = cb.GetLeft() - ring, cb.GetRight() + ring, cb.GetBottom() + ring
        y0 = ko.Outline().BBox().GetBottom() + nm(0.9) if ko is not None else cb.GetTop()
        y = y0
        while y <= y1:
            candidates += [(x0, y), (x1, y)]
            y += nm(FENCE_STEP)
        x = x0
        while x <= x1:
            candidates.append((x, y1))
            x += nm(FENCE_STEP)
        # a denser grid under and around the module; the checks below keep what fits
        m = nm(MODULE_MARGIN)
        y = cb.GetTop() - m
        while y <= cb.GetBottom() + m:
            x = cb.GetLeft() - m
            while x <= cb.GetRight() + m:
                candidates.append((x, y))
                x += nm(MODULE_GRID)
            y += nm(MODULE_GRID)

    r_hole = nm(VIA[1]) / 2
    added = 0
    for x, y in candidates:
        x, y = int(x), int(y)
        pt = pcbnew.VECTOR2I(x, y)
        if not all(fills[l].Contains(pt) for l in fills):
            continue
        if any(f.Contains(pt) for f in forbid) or any(b.Contains(pt) for b in bodies):
            continue
        if any(((x - hx) ** 2 + (y - hy) ** 2) ** 0.5 < r_hole + hr + nm(0.5) for hx, hy, hr in holes):
            continue
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pt)
        v.SetWidth(nm(VIA[0]))
        v.SetDrill(nm(VIA[1]))
        v.SetNet(gnd)
        board.Add(v)
        holes.append((x, y, r_hole))
        added += 1
    return added


def finish(ripped, ses, out):
    """Import a session into a copy of the ripped board, fix up, pour, save to OUT."""
    board = pcbnew.LoadBoard(ripped)
    rule_areas = [z for z in board.Zones() if z.GetIsRuleArea()]  # wrappers taken before any edit
    # The session re-places footprints at its 0.1 um resolution; rule 1 wants the exact
    # original positions back (tracks end within 0.05 um of pad centres, still on the pads).
    exact = {fp.GetReference(): (pcbnew.VECTOR2I(fp.GetPosition()), fp.GetOrientationDegrees())
             for fp in board.GetFootprints()}
    if not pcbnew.ImportSpecctraSES(board, ses):
        sys.exit("SES import failed")
    for fp in board.GetFootprints():
        pos, rot = exact[fp.GetReference()]
        fp.SetPosition(pos)
        fp.SetOrientationDegrees(rot)
    # Its stubs onto a pad it saw 0.1 um off (a locked pre-route already ends there).
    for t in [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetLength() < nm(0.001)]:
        board.Remove(t)
    widened = 0
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < nm(MIN_WIDTH):
            t.SetWidth(nm(MIN_WIDTH))
            widened += 1

    gnd = board.FindNet("GND")
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline)
    for name, layer in POUR_LAYERS.items():
        z = pcbnew.ZONE(board)
        z.SetZoneName(name)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetLocalClearance(nm(0.3))
        z.SetMinThickness(nm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(nm(0.3))
        z.SetThermalReliefSpokeWidth(nm(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetAssignedPriority(0)
        o = outline.Outline(0)
        z.Outline().NewOutline()
        for i in range(o.PointCount()):
            p = o.CPoint(i)
            z.Outline().Append(p.x, p.y)
        board.Add(z)
    u1 = board.FindFootprintByReference("U1")
    if u1 is not None:  # module GND pads straight into the pour (E73 p.8: solid ground on the module side)
        u1.BuildCourtyardCaches()
        cb = u1.GetCourtyard(pcbnew.B_CrtYd).BBox()
        m = pcbnew.ZONE(board)
        m.SetZoneName("GND_MODULE")
        m.SetLayer(pcbnew.B_Cu)
        m.SetNet(gnd)
        m.SetLocalClearance(nm(0.3))
        m.SetMinThickness(nm(0.25))
        m.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        m.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        m.SetAssignedPriority(1)
        grow = nm(1.2)
        m.Outline().NewOutline()
        for x, y in ((cb.GetLeft() - grow, cb.GetTop()), (cb.GetRight() + grow, cb.GetTop()),
                     (cb.GetRight() + grow, cb.GetBottom() + grow), (cb.GetLeft() - grow, cb.GetBottom() + grow)):
            m.Outline().Append(int(x), int(y))
        board.Add(m)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    stitched = stitch(board, gnd, rule_areas)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    board.BuildConnectivity()
    before = board.GetConnectivity().GetUnconnectedCount(False)
    edge = outline.Outline(0)
    segs = [edge.CSegment(i) for i in range(edge.SegmentCount())]
    stubs = []
    for t in list(board.GetTracks()):
        if t.GetClass() == "PCB_TRACK" and t.GetNetname() == "GND":
            d = min(pcbnew.SEG(t.GetStart(), t.GetEnd()).Distance(s) for s in segs)  # to the edges
            if d - t.GetWidth() / 2 < nm(0.3):
                stubs.append(t)
    for t in stubs:
        board.Remove(t)
    if stubs:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        board.BuildConnectivity()
        if board.GetConnectivity().GetUnconnectedCount(False) > before:
            sys.exit("dropping %d GND stubs at the edge disconnected something" % len(stubs))

    routed = list(board.GetTracks())
    for t in routed:
        t.SetLocked(False)  # atopile drops locks
    board.BuildConnectivity()
    result = {"unrouted": board.GetConnectivity().GetUnconnectedCount(False),
              "tracks": sum(1 for t in routed if t.GetClass() == "PCB_TRACK"),
              "vias": sum(1 for t in routed if t.GetClass() == "PCB_VIA"),
              "widened": widened, "edge_gnd_stubs_dropped": len(stubs), "stitching_vias": stitched}
    board.Save(out)
    return result


def complete(best, work, passes, project):
    """Let Freerouting finish a routed board: tracks stay as wiring, pours go."""
    os.makedirs(work, exist_ok=True)
    start = os.path.join(work, "start.kicad_pcb")
    # KiCad 9 keeps net classes in the project file; every board copy needs one beside it
    for board in (best["board"], start, os.path.join(work, "ripped.kicad_pcb")):
        shutil.copy(project, os.path.splitext(board)[0] + ".kicad_pro")
    child = subprocess.run([sys.executable, __file__, best["board"], work, "--strip-pours", start],
                           capture_output=True, text=True)
    if child.returncode != 0:
        return None
    dsn = os.path.join(work, "board.dsn")
    text = open(os.path.join(work, "start.dsn")).read()
    open(dsn, "w").write(with_widths(text, *best["widths"]))
    ses = os.path.join(work, "board.ses")
    with open(os.path.join(work, "freerouting.log"), "w") as log:
        subprocess.run(["java", "-jar", os.environ["FREEROUTING_JAR"], "-de", dsn, "-do", ses, "-mp", str(passes),
                        "-mt", "2"], stdout=log, stderr=subprocess.STDOUT)
    if not os.path.exists(ses):
        return None
    ripped = os.path.join(work, "ripped.kicad_pcb")
    out = os.path.join(work, "finished.kicad_pcb")
    child = subprocess.run([sys.executable, __file__, ripped, work, "--finish", ses, out], capture_output=True, text=True)
    line = [l for l in child.stdout.splitlines() if l.startswith("{")]
    if child.returncode != 0 or not line:
        return None
    r = json.loads(line[-1])
    r["board"] = out
    return r


def strip_pours(board_path, out):
    """For a completion pass: keep the tracks, drop the pours, write the board, a ripped copy
    (the session from Freerouting contains every track, old and new) and the DSN."""
    board = pcbnew.LoadBoard(board_path)
    boundary = inset_points(board, EDGE_INSET)
    tracks = list(board.GetTracks())
    for z in [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetZoneName() in POURS]:
        board.Remove(z)
    board.Save(out)
    work = os.path.dirname(out)
    dsn = os.path.join(work, "start.dsn")
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        sys.exit("DSN export failed")
    shrink_boundary(dsn, boundary)
    for t in tracks:
        board.Remove(t)
    board.Save(os.path.join(work, "ripped.kicad_pcb"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("work", nargs="?")
    ap.add_argument("--ripup", action="store_true", help="remove all tracks, vias and GND pours from BOARD, then stop")
    ap.add_argument("--ripup-nets", nargs="+", metavar="NET", help="remove these nets' tracks and vias from BOARD, then stop")
    ap.add_argument("--ripup-drc", action="store_true",
                    help="remove the tracks and vias that take part in a DRC error (after a rule or footprint change), then stop")
    ap.add_argument("--remove-uuids", metavar="JSON", help=argparse.SUPPRESS)
    ap.add_argument("--restitch", action="store_true", help="add GND stitching vias to a routed BOARD where they fit, then stop")
    ap.add_argument("--passes", type=int, default=100)
    ap.add_argument("--attempts", type=int, default=4, help="route VARIANTS[0:N] (at most %d)" % len(VARIANTS))
    ap.add_argument("--variants", type=int, nargs="+", help="route only these VARIANTS indices (instead of --attempts)")
    ap.add_argument("--jobs", type=int, default=6, help="Freerouting runs at a time (each takes ~2 GB)")
    ap.add_argument("--threads", type=int, default=2, help="Freerouting optimizer threads (-mt)")
    ap.add_argument("--completions", type=int, default=3)
    ap.add_argument("--finish", nargs=2, metavar=("SES", "OUT"), help=argparse.SUPPRESS)
    ap.add_argument("--strip-pours", metavar="OUT", help=argparse.SUPPRESS)
    ap.add_argument("--complete-only", action="store_true", help="only run completion passes on a routed BOARD")
    ap.add_argument("--widths", nargs=2, type=float, default=list(WIDTHS[0]), help="signal and power width for --complete-only")
    ap.add_argument("--clearance", type=float, default=ROUTE_CLEARANCE, help="routing clearance for --complete-only")
    ap.add_argument("--count", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.ripup:  # before a rebuild that moves nets: copper on old nets would fail board_diff
        board = pcbnew.LoadBoard(args.board)
        items = list(board.GetTracks()) + [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetZoneName() in POURS]
        for item in items:
            board.Remove(item)
        board.Save(args.board)
        print("ripped up %d items on %s" % (len(items), args.board))
        sys.stdout.flush()
        os._exit(0)
    if args.ripup_nets:  # before completion passes that re-route only these nets
        board = pcbnew.LoadBoard(args.board)
        items = [t for t in board.GetTracks() if t.GetNetname() in args.ripup_nets]
        for item in items:
            board.Remove(item)
        board.Save(args.board)
        print("ripped up %d tracks and vias of %s on %s" % (len(items), ", ".join(args.ripup_nets), args.board))
        sys.stdout.flush()
        os._exit(0)
    if args.restitch:  # after the stitching rules changed, on a routed board
        board = pcbnew.LoadBoard(args.board)
        zones = list(board.Zones())
        rule_areas = [z for z in zones if z.GetIsRuleArea()]
        pcbnew.ZONE_FILLER(board).Fill(zones)
        added = stitch(board, board.FindNet("GND"), rule_areas)
        pcbnew.ZONE_FILLER(board).Fill(zones)
        board.Save(args.board)
        print(json.dumps({"board": args.board, "stitching_vias_added": added}))
        sys.stdout.flush()
        os._exit(0)
    if args.remove_uuids:  # child process for --ripup-drc
        uuids = set(json.load(open(args.remove_uuids)))
        board = pcbnew.LoadBoard(args.board)
        items = [t for t in board.GetTracks() if t.m_Uuid.AsString() in uuids]
        for item in items:
            board.Remove(item)
        board.Save(args.board)
        print("ripped up %d tracks and vias in DRC errors on %s" % (len(items), args.board))
        sys.stdout.flush()
        os._exit(0)
    if args.ripup_drc:  # the copper a rule or footprint change broke, for completion passes to redo
        import tempfile
        import widen
        work = tempfile.mkdtemp()
        filled = os.path.join(work, "filled.kicad_pcb")
        json.dump({}, open(os.path.join(work, "none.json"), "w"))
        me = os.path.dirname(os.path.abspath(__file__))
        subprocess.run([sys.executable, os.path.join(me, "widen.py"), args.board, "--apply",
                        os.path.join(work, "none.json"), filled], check=True, capture_output=True)
        errors = widen.drc_errors(filled, os.path.splitext(args.board)[0] + ".kicad_pro")
        uuids = sorted({u for kind, items in errors if kind in RIPUP_DRC_TYPES for u in items if u})
        json.dump(uuids, open(os.path.join(work, "uuids.json"), "w"))
        child = subprocess.run([sys.executable, __file__, args.board, "--remove-uuids", os.path.join(work, "uuids.json")],
                               capture_output=True, text=True)
        print(child.stdout.strip())
        shutil.rmtree(work)
        sys.exit(child.returncode)
    if args.strip_pours:  # child process for a completion pass
        strip_pours(args.board, args.strip_pours)
        sys.stdout.flush()
        os._exit(0)
    if args.finish:  # child process: BOARD is the ripped board
        print(json.dumps(finish(args.board, *args.finish)))
        sys.stdout.flush()
        os._exit(0)

    if args.count:  # child process: unconnected items and vias of BOARD
        board = pcbnew.LoadBoard(args.board)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        board.BuildConnectivity()
        print(json.dumps({"unrouted": board.GetConnectivity().GetUnconnectedCount(False),
                          "vias": sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA")}))
        sys.stdout.flush()
        os._exit(0)

    os.makedirs(args.work, exist_ok=True)
    if args.complete_only:
        project = os.path.join(args.work, "ripped.kicad_pro")
        shutil.copy(os.path.splitext(args.board)[0] + ".kicad_pro", project)
        start = os.path.join(args.work, "routed.kicad_pcb")
        shutil.copy(args.board, start)
        shutil.copy(project, os.path.join(args.work, "routed.kicad_pro"))
        child = subprocess.run([sys.executable, __file__, start, "--count"], capture_output=True, text=True)
        best = json.loads([l for l in child.stdout.splitlines() if l.startswith("{")][-1])
        best.update(board=start, widths=tuple(args.widths) + (args.clearance,), attempt="routed")
        first = dict(best)
        for n in range(args.completions):
            if best["unrouted"] == 0:
                break
            r = complete(best, os.path.join(args.work, "complete-%d" % n), args.passes, project)
            if r is not None and (r["unrouted"], r["vias"]) < (best["unrouted"], best["vias"]):
                r.update(widths=best["widths"], attempt="complete-%d" % n)
                best = r
        if best is not first:
            shutil.copy(best["board"], args.board)
            widen = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "widen.py"),
                                    args.board], capture_output=True, text=True)
            if widen.returncode != 0:
                sys.exit("widen.py failed on %s:\n%s" % (args.board, widen.stderr[-2000:]))
        print(json.dumps({"board": args.board, "before": first["unrouted"], "unrouted": best["unrouted"],
                          "vias": best["vias"], "stitching_vias": best.get("stitching_vias"), "chosen": best["attempt"]}))
        sys.stdout.flush()
        os._exit(0)
    dsn = prepare(args.board, args.work)
    base = open(dsn).read()
    chosen = args.variants if args.variants else range(min(args.attempts, len(VARIANTS)))
    pending, running, runs = [(i, VARIANTS[i]) for i in chosen], [], []
    while pending or running:  # Freerouting is deterministic: the variants are what differ
        while pending and len(running) < args.jobs:
            i, (sig, pwr, cl) = pending.pop(0)
            work = os.path.join(args.work, "attempt-%d" % i)
            os.makedirs(work, exist_ok=True)
            variant = os.path.join(work, "board.dsn")
            open(variant, "w").write(with_widths(base, sig, pwr, cl))
            log = open(os.path.join(work, "freerouting.log"), "w")
            cmd = ["java", "-jar", os.environ["FREEROUTING_JAR"], "-de", variant, "-do", os.path.join(work, "board.ses"),
                   "-mp", str(args.passes), "-mt", str(args.threads)]
            running.append((i, work, (sig, pwr, cl), log, subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)))
        for run in [r for r in running if r[4].poll() is not None]:
            run[3].close()
            running.remove(run)
            runs.append(run)
        time.sleep(1)

    results = []
    ripped = os.path.join(args.work, "ripped.kicad_pcb")
    for _i, work, widths, _log, proc in sorted(runs, key=lambda r: r[0]):
        ses = os.path.join(work, "board.ses")
        if proc.returncode != 0 or not os.path.exists(ses):
            continue
        out = os.path.join(work, "finished.kicad_pcb")
        child = subprocess.run([sys.executable, __file__, ripped, work, "--finish", ses, out],
                               capture_output=True, text=True)
        line = [l for l in child.stdout.splitlines() if l.startswith("{")]
        if child.returncode == 0 and line:
            r = json.loads(line[-1])
            r.update(attempt=os.path.basename(work), widths=widths, board=out)
            results.append(r)
    if not results:
        sys.exit("no Freerouting attempt produced a usable board (see %s/attempt-*/)" % args.work)
    best = min(results, key=lambda r: (r["unrouted"], r["vias"]))
    for n in range(args.completions):
        if best["unrouted"] == 0:
            break
        work = os.path.join(args.work, "complete-%d" % n)
        os.makedirs(work, exist_ok=True)
        r = complete(best, work, args.passes, os.path.join(args.work, "ripped.kicad_pro"))
        if r is not None and (r["unrouted"], r["vias"]) < (best["unrouted"], best["vias"]):
            r.update(attempt="%s+complete-%d" % (best["attempt"], n), widths=best["widths"])
            results.append(r)
            best = r
    shutil.copy(best["board"], args.board)
    child = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "widen.py"), args.board],
                           capture_output=True, text=True)
    line = [l for l in child.stdout.splitlines() if l.startswith("{")]
    if child.returncode != 0 or not line:
        sys.exit("widen.py failed on %s:\n%s" % (args.board, child.stderr[-2000:]))
    print(json.dumps({"board": args.board, "chosen": best["attempt"], "widths": best["widths"], "threads": args.threads,
                      "widened_to_0.15": json.loads(line[-1])["widened"],
                      "unrouted": best["unrouted"], "tracks": best["tracks"], "vias": best["vias"],
                      "widened": best["widened"], "edge_gnd_stubs_dropped": best["edge_gnd_stubs_dropped"],
                      "attempts": sorted((r["unrouted"], r["vias"], r["attempt"]) for r in results)}))
    sys.stdout.flush()
    os._exit(0)  # KiCad 9's SWIG objects segfault in destructors at exit


if __name__ == "__main__":
    main()
