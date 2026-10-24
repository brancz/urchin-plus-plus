"""Fit checks for the dock: the tray, the dock PCB (kicad-cli's STEP export of the routed
board, every 3D model) and both halves in their cases, seated in the pockets. The pogo pins
are modelled compressed, as they stand under a seated half. Their landing on the half's pads,
their place in the case's window, their compression and the feet's room in the tray are
worked out from the tolerances in params.py; how far a case moves and turns in its pocket, and
a board in its case, from their outlines (play.Play)."""

import json
import math
from pathlib import Path

from build123d import Compound, Kind, Pos, Vector, import_step, offset

from . import params as P
from .board import Board, xy
from .case import box, case, cover, cover_holes, cyl, dock_window
from .checks import MIN_GAP, STEP_UNDERSIDE, board_parts, fit, keycaps, switches
from .play import AXES, Play
from .tray import PLACEMENT, Dock

PLUG_LEN = 20.0         # mm of a USB-C plug's overmold modelled in front of the receptacle


def seated(shape, dx):
    """A half's part (case frame) seated in its pocket (dock frame)."""
    return Pos(dx, 0, P.Z_DOCK) * shape


def dock_refs(dock: Dock):
    """{ref: (x, y)} of every dock PCB footprint in the dock frame."""
    refs = {f"P{i + 1}": (x, y) for i, (x, y, _, _) in enumerate(dock.pins)}
    refs["J1"] = dock.usb
    refs.update({f"H{i + 1}": s for i, s in enumerate(dock.screws)})
    for ref, r in json.loads(PLACEMENT.read_text())["parts"].items():
        refs[ref] = dock.from_kicad(r["x"], r["y"])
    return refs


def pin(x, y):
    """A pogo pin compressed under a seated half: flange, barrel, and the plunger up to the
    half's pad."""
    z = P.Z_DOCK
    return (cyl(x, y, P.PIN_FLANGE[0], z, z + P.PIN_FLANGE[1]) + cyl(x, y, P.PIN_BARREL[0], z, z + P.PIN_BARREL[1])
            + cyl(x, y, P.PIN_TIP_D, z + P.PIN_BARREL[1], z + P.Z_PCB_BOTTOM))


def dock_parts(dock: Dock, step_path):
    """[(name, shape)] of the dock PCB and its parts in the dock frame, its top at Z_DOCK; the
    pins' models swapped for compressed pins. Also the free pins' height from their models."""
    ox, oy = P.DOCK_PCB_ORIGIN
    step = list(import_step(str(step_path)))
    body = max(step, key=lambda c: c.bounding_box().size.X * c.bounding_box().size.Y)
    # The STEP is in KiCad x and -y. kicad-cli seats top parts as far above the board body as
    # bottom parts below it: on the board's top surface, which goes at Z_DOCK.
    place = Pos(dock.x_c - ox, dock.pins[0][1] + oy, P.Z_DOCK - (body.bounding_box().max.Z - STEP_UNDERSIDE))
    refs = dock_refs(dock)
    parts, free = [("dock pcb", place * body)], []
    for c in step:
        if c is body:
            continue
        c = place * c
        cc = c.bounding_box().center()
        ref = min(refs, key=lambda r: math.hypot(refs[r][0] - cc.X, refs[r][1] - cc.Y))
        if ref.startswith("P"):
            free.append(round(c.bounding_box().max.Z - P.Z_DOCK, 3))
            continue
        parts.append((f"dock {ref} 3D model", c))
    parts += [(f"dock P{i + 1} pin, compressed", pin(x, y)) for i, (x, y, _, _) in enumerate(dock.pins)]
    for i, (x, y) in enumerate(dock.screws):
        parts.append((f"dock H{i + 1} screw head", cyl(x, y, P.DOCK_SCREW_HEAD[0], P.Z_DOCK, P.Z_DOCK + P.DOCK_SCREW_HEAD[1])))
    return parts, free


def feet(dock: Dock):
    """The cases' rubber feet, below their undersides."""
    out = []
    for b, dx in dock.halves():
        for f in b["feet"]:
            x, y = dock.at(b, dx, (f["x"], f["y"]))
            out.append((f"{b.side} {f['ref']} foot", cyl(x, y, f["d"], P.Z_DOCK - (P.FOOT_H - P.FOOT_RECESS), P.Z_DOCK)))
    return out


def plug(dock: Dock):
    """A USB-C plug's overmold in the receptacle, out through the tray's front wall."""
    ux, _ = dock.usb
    zc = P.Z_DOCK + P.USB_AXIS
    w, h = P.USB_PLUG
    return ("USB-C plug", box(ux - w / 2, ux + w / 2, dock.y_front - PLUG_LEN, dock.y_front, zc - h / 2, zc + h / 2))


def case_face(b: Board):
    return offset(b.outline(), P.FIT + P.WALL, kind=Kind.ARC).faces()[0]


def checks(dock: Dock, tray, pieces, boards_dir):
    """Every dock check; returns (report rows by kind, shapes for the renders)."""
    rows = {"fit": [], "pins": [], "hardware": []}
    dparts, free = dock_parts(dock, Path(boards_dir) / "dock.step")
    dpcb = dparts[0][1]
    cases, halves, above = [], [], []
    for b, dx in dock.halves():
        c = seated(case(b), dx)
        cases.append((f"case_{b.side}", c))
        halves += [(f"{b.side} {n}", seated(s, dx)) for n, s in board_parts(b, Path(boards_dir) / f"{b.side}.step")]
        above += [(f"{b.side} switches", seated(Compound([s for _, s in switches(b)]), dx)),
                  (f"{b.side} keycaps", seated(Compound([s for _, s in keycaps(b)]), dx)),
                  (f"cover_{b.side}", seated(cover(b), dx))]
    case_names = tuple(n for n, _ in cases)

    # The tray: the cases rest on its floor and the dock PCB in its recess; everything else,
    # the switches, keycaps and battery covers over its walls included, keeps MIN_GAP. Its walls
    # above the floor keep POCKET_CLEAR from the cases.
    for name, piece in zip(("tray_left", "tray_right"), pieces):
        rows["fit"] += fit(name, piece, cases + above + [("dock pcb", dpcb)] + dparts[1:] + feet(dock) + [plug(dock)],
                           touching=case_names + ("dock pcb",))
        bb = piece.bounding_box()
        walls = piece & box(bb.min.X - 1, bb.max.X + 1, bb.min.Y - 1, bb.max.Y + 1, P.Z_DOCK + 0.05, bb.max.Z + 1)
        rows["fit"] += fit(f"{name} walls", walls, cases)
    rows["fit"] += fit("tray_left", pieces[0], [("tray_right", pieces[1])], touching=("tray_right",))

    # The dock's parts, its screw heads and the plug against the seated cases; the pins against
    # the halves' parts too (they touch the half's PCB, at its pads).
    half_pcbs = tuple(n for n, _ in halves if n.endswith(" pcb"))
    for name, shape in dparts[1:] + [plug(dock)]:
        if " pin" in name:
            rows["fit"] += fit(name, shape, cases + halves, touching=half_pcbs)
        else:
            rows["fit"] += fit(name, shape, cases)
    rows["fit"] += fit("dock pcb", dpcb, cases, touching=case_names)

    rows["pins"] = pin_rows(dock, free)
    rows["hardware"] = hardware_rows(dock, tray)
    return rows, {"cases": cases, "halves": halves, "dock": dparts}


def stack(terms):
    """(linear, root sum of squares) of a dict of tolerances."""
    v = list(terms.values())
    return sum(v), math.sqrt(sum(t * t for t in v))


def r2(v):
    return round(v, 2)


def pin_rows(dock: Dock, free):
    """The pins: their height, the pockets' guidance, compression, and per pad, where the tip
    lands and where the pin stands in the case's window."""
    rows = []
    # The free height in the 3D model is the datasheet's (an independent reading).
    rows.append({"check": "pin model free height", "models_mm": sorted(set(free)), "params_mm": P.PIN_FREE,
                 "ok": len(free) == len(dock.pins) and all(abs(f - P.PIN_FREE) <= 0.05 for f in free)})
    # A half must be in the pocket's straight walls (its full outline, above its bottom chamfer)
    # before its underside comes down to the tallest pin tip.
    tip, _ = stack(P.PIN_HEIGHT_TOL)
    tip += P.PIN_FREE
    straight = P.POCKET_DEPTH - P.FUNNEL
    rows.append({"check": "the pocket guides a half before the pins meet it", "straight_wall_mm": r2(straight),
                 "tallest_tip_mm": r2(tip), "case_bottom_chamfer_mm": P.EDGE_BOTTOM,
                 "ok": straight - P.EDGE_BOTTOM >= tip})
    # Compression: the pins must stay pressed (contact force) and short of their bottom.
    nominal = P.PIN_FREE - P.Z_PCB_BOTTOM
    lin, rss = stack({**P.PIN_HEIGHT_TOL, **P.CASE_HEIGHT_TOL})
    stroke = P.PIN_FREE - P.PIN_BOTTOM
    rows.append({"check": "pin compression", "nominal_mm": r2(nominal), "rss_mm": [r2(nominal - rss), r2(nominal + rss)],
                 "worst_case_mm": [r2(nominal - lin), r2(nominal + lin)], "limits_mm": [P.MIN_COMPRESSION, r2(stroke)],
                 "terms_mm": {**P.PIN_HEIGHT_TOL, **P.CASE_HEIGHT_TOL},
                 "ok": nominal - rss >= P.MIN_COMPRESSION and nominal + rss <= stroke})

    dock_lin, _ = stack(P.DOCK_TOL)
    for b, dx in dock.halves():
        in_pocket = Play(case_face(b), P.POCKET_PLAY)
        in_case = Play(b.outline(), P.BOARD_WALL_PLAY,
                       pins=[(xy((h["x"], h["y"])), P.BOARD_SCREW_PLAY) for h in cover_holes(b)])
        win = dock_window(b).bounding_box()
        r = max(P.PIN_FLANGE[0], P.PIN_BARREL[0]) / 2
        for p in b["dock_pads"]["pads"]:
            q = xy((p["x"], p["y"]))
            half = {"x": p["w"] / 2, "y": p["h"] / 2}
            to_window = {"x": min(q[0] - win.min.X, win.max.X - q[0]) - r, "y": min(q[1] - win.min.Y, win.max.Y - q[1]) - r}
            row = {"check": f"{b.side} pad {p['number']} ({p['net']})", "pad_mm": [p["w"], p["h"]], "terms_mm": {}}
            ok = True
            for axis in AXES:
                case_play, board_play = in_pocket.along(q, axis), in_case.along(q, axis)
                terms = {"case in its pocket (moves and turns)": case_play,
                         "board in its case (moves and turns)": board_play, **P.DOCK_TOL}
                for k, v in terms.items():
                    row["terms_mm"].setdefault(k, []).append(r2(v))
                lin, rss = stack(terms)
                room = half[axis] - P.PIN_PAD_MARGIN
                # The window is in the case: the board's play doesn't move it.
                window_need = case_play + dock_lin + MIN_GAP
                row.setdefault("landing_rss_mm", []).append(r2(rss))
                row.setdefault("landing_worst_case_mm", []).append(r2(lin))
                row.setdefault("tip_room_on_pad_mm", []).append(r2(room))
                row.setdefault("worst_case_on_pad", []).append(lin <= half[axis])
                row.setdefault("pin_to_window_mm", []).append(r2(to_window[axis]))
                row.setdefault("window_needs_mm", []).append(r2(window_need))
                ok &= rss <= room and window_need <= to_window[axis]
            row["ok"] = bool(ok)
            rows.append(row)
    return rows


def wall_around(tray, x, y, d, z0, z1, need):
    """The thinnest printed wall around a vertical hole (d, z0..z1) in the tray, to 0.05 mm, up
    to need + 1."""
    local = tray & box(x - d / 2 - need - 2, x + d / 2 + need + 2, y - d / 2 - need - 2, y + d / 2 + need + 2, z0, z1)

    def solid(w):
        ring = cyl(x, y, d + 2 * w, z0 + 0.01, z1 - 0.01) - cyl(x, y, d, z0 - 1, z1 + 1)
        rest = ring - local
        return rest is None or rest.volume < 1e-3

    lo, hi = 0.0, need + 1.0
    if solid(hi):
        return hi
    while hi - lo > 0.05:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if solid(mid) else (lo, mid)
    return lo


def hardware_rows(dock: Dock, tray):
    """The dock PCB's M2 screws in the tray's heat-set inserts and the inserts' walls, the
    magnets' walls, and the cases' feet in the tray's holes."""
    under_head = P.Z_DOCK
    tip = under_head - P.DOCK_SCREW_L
    insert_top = P.Z_DOCK - P.DOCK_PCB_T
    engaged = insert_top - max(tip, insert_top - P.INSERT_L)
    to_bottom = tip - (insert_top - P.INSERT_DEPTH)
    rows = [{"stack": f"dock PCB: M2 x {P.DOCK_SCREW_L:g} through the PCB into an M2 x {P.INSERT_L:g} insert",
             "thread_mm": r2(engaged), "tip_to_hole_bottom_mm": r2(to_bottom),
             "ok": engaged >= P.MIN_THREAD and to_bottom >= P.MIN_TIP_GAP}]
    for i, (x, y) in enumerate(dock.screws):
        w = wall_around(tray, x, y, P.INSERT_D, insert_top - P.INSERT_DEPTH, insert_top, P.MIN_INSERT_WALL)
        rows.append({"stack": f"tray wall around the H{i + 1} insert", "wall_mm": r2(w),
                     "min_mm": P.MIN_INSERT_WALL, "ok": w >= P.MIN_INSERT_WALL})
    wall = (dock.magnet_hole_d - 2 * P.BOSS_CLEAR - (P.MAGNET[0] + P.MAGNET_FIT)) / 2
    rows.append({"stack": "magnet pocket wall inside the dock PCB's hole", "wall_mm": r2(wall),
                 "ok": wall >= P.MAGNET_WALL - 1e-9})
    depth = P.Z_DOCK - P.MAGNET_SKIN
    rows.append({"stack": f"magnet pocket depth (a {P.MAGNET[0]:g} x {P.MAGNET[1]:g} mm magnet; 10 x 5 fits too)",
                 "depth_mm": r2(depth), "skin_mm": P.MAGNET_SKIN, "ok": depth >= P.MAGNET_POCKET_H})
    # Feet: the tray's holes go through, so any foot shorter than this fits.
    tallest = P.Z_DOCK + P.FOOT_RECESS
    rows.append({"stack": "case feet: the tray's holes go through", "foot_h_mm": P.FOOT_H,
                 "tallest_foot_mm": r2(tallest), "ok": P.FOOT_H < tallest})
    # A foot moves with its case, and in its seat; it stays clear of its hole's wall and of the
    # dock PCB's edge.
    for b, dx in dock.halves():
        in_pocket = Play(case_face(b), P.POCKET_PLAY)
        for f in b["feet"]:
            moves = in_pocket.radial(xy((f["x"], f["y"]))) + P.FOOT_SEAT / 2
            x, y = dock.at(b, dx, (f["x"], f["y"]))
            room = min(P.FOOT_POCKET / 2, dock.pcb_outline.distance_to(Vector(x, y, 0)) - f["d"] / 2)
            rows.append({"stack": f"{b.side} {f['ref']} foot in its tray hole", "moves_mm": r2(moves),
                         "room_mm": r2(room), "ok": moves + MIN_GAP <= room})
    return rows
