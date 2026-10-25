"""Fit checks for the dock: the tray, its cover, the dock PCB (kicad-cli's STEP export of the
routed board, every 3D model) and both halves in their cases, seated in the pockets, with the
pogo pins soldered on the halves modelled compressed on the dock's contacts. The pins' landing
on the contacts, their place in the case's window, their compression, how the pockets guide a
half onto them and the feet's room in the tray are worked out from the tolerances in
params.py; how far a case moves and turns in its pocket, and a board in its case, from their
outlines (play.Play). Also the soldering jig on each half's board."""

import json
import math
from pathlib import Path

from build123d import Circle, Compound, Kind, Pos, Vector, import_step, offset

from . import params as P
from . import pins as PN
from .board import Board, xy
from .case import board_pins, box, case, cyl, dock_window, outer_edge, shell
from .checks import MIN_GAP, STEP_UNDERSIDE, board_parts, fit, keycaps, switches
from .play import AXES, Play
from .tray import PLACEMENT, Dock, rect

PLUG_LEN = 20.0         # mm of a USB-C plug's overmold modelled behind the receptacle


def seated(shape, dx):
    """A half's part (case frame) seated in its pocket (dock frame)."""
    return Pos(dx, 0, P.Z_DOCK) * shape


def dock_refs(dock: Dock):
    """{ref: (x, y)} of every dock PCB footprint with a 3D model, in the dock frame."""
    refs = {"J1": dock.usb}
    for ref, r in json.loads(PLACEMENT.read_text())["parts"].items():
        refs[ref] = dock.from_kicad(r["x"], r["y"])
    return refs


def dock_parts(dock: Dock, step_path):
    """[(name, shape)] of the dock PCB ("dock pcb") and its parts' models ("dock REF 3D model")
    in the dock frame, its top at Z_DOCK."""
    ox, oy = P.DOCK_PCB_ORIGIN
    step = list(import_step(str(step_path)))
    body = max(step, key=lambda c: c.bounding_box().size.X * c.bounding_box().size.Y)
    # The STEP is in KiCad x and -y. kicad-cli seats top parts as far above the board body as
    # bottom parts below it: on the board's top surface, which goes at Z_DOCK.
    place = Pos(dock.x_c - ox, dock.contacts[0][1] + oy, P.Z_DOCK - (body.bounding_box().max.Z - STEP_UNDERSIDE))
    refs = dock_refs(dock)
    parts = [("dock pcb", place * body)]
    for c in step:
        if c is body:
            continue
        c = place * c
        cc = c.bounding_box().center()
        ref = min(refs, key=lambda r: math.hypot(refs[r][0] - cc.X, refs[r][1] - cc.Y))
        parts.append((f"dock {ref} 3D model", c))
    return parts


def feet(dock: Dock):
    """The cases' rubber feet, below their undersides."""
    out = []
    for b, dx in dock.halves():
        for f in b["feet"]:
            x, y = dock.at(b, dx, (f["x"], f["y"]))
            out.append((f"{b.side} {f['ref']} foot", cyl(x, y, f["d"], P.Z_DOCK - (P.FOOT_H - P.FOOT_RECESS), P.Z_DOCK)))
    return out


def plug(dock: Dock):
    """A USB-C plug's overmold in the receptacle, against the tray's back face."""
    ux, _ = dock.usb
    zc = P.Z_DOCK + P.DOCK_USB_AXIS
    w, h = P.USB_PLUG
    y0 = (dock.outline & rect(ux - w / 2, ux + w / 2, dock.y_back - 5, dock.y_back + 5)).bounding_box().max.Y
    return ("USB-C plug", box(ux - w / 2, ux + w / 2, y0, y0 + PLUG_LEN, zc - h / 2, zc + h / 2))


def case_face(b: Board):
    return offset(b.outline(), P.FIT + P.WALL, kind=Kind.ARC).faces()[0]


def checks(dock: Dock, tray, pieces, cover, dparts, boards_dir):
    """Every dock check; returns (report rows by kind, shapes for the renders)."""
    rows = {"fit": [], "pins": [], "hardware": []}
    dpcb = dparts[0][1]
    cases, shells, halves, above, docked = [], [], [], [], []
    for b, dx in dock.halves():
        cases.append((f"case_{b.side}", seated(case(b), dx)))
        shells.append((f"shell_{b.side}", seated(shell(b), dx)))
        halves += [(f"{b.side} {n}", seated(s, dx)) for n, s in board_parts(b, Path(boards_dir) / f"{b.side}.step")]
        above += [(f"{b.side} switches", seated(Compound([s for _, s in switches(b)]), dx)),
                  (f"{b.side} keycaps", seated(Compound([s for _, s in keycaps(b)]), dx))]
        # Docked, each pin is pressed up until its tip is on the contact, level with the case's underside.
        docked += [(f"{n}, compressed", seated(s, dx)) for n, s in PN.pins(b, tip_z=0.0)]
    case_names = tuple(n for n, _ in cases)
    printed = [("tray_left", pieces[0]), ("tray_right", pieces[1]), ("dock_cover", cover)]

    # The tray: the cases rest on its floor, the dock PCB and the cover lie in its recess, the
    # plug's overmold butts on its back face; everything else keeps MIN_GAP. Its walls above
    # the floor keep MIN_GAP from the cases and shells.
    for name, piece in printed[:2]:
        rows["fit"] += fit(name, piece, cases + shells + above + docked + [("dock pcb", dpcb)] + dparts[1:] + feet(dock)
                           + [plug(dock), ("dock_cover", cover)],
                           touching=case_names + ("dock pcb", "dock_cover", "USB-C plug"))
        bb = piece.bounding_box()
        walls = piece & box(bb.min.X - 1, bb.max.X + 1, bb.min.Y - 1, bb.max.Y + 1, P.Z_DOCK + 0.05, bb.max.Z + 1)
        rows["fit"] += fit(f"{name} walls", walls, cases + shells)
    rows["fit"] += fit("tray_left", pieces[0], [("tray_right", pieces[1])], touching=("tray_right",))
    # The cover rests on the PCB; its walls are pocket walls where it crosses them.
    rows["fit"] += fit("dock_cover", cover, cases + shells + above + [("dock pcb", dpcb)] + dparts[1:] + [plug(dock)],
                       touching=("dock pcb", "USB-C plug"))

    # The dock's parts and the plug against the seated cases; the dock PCB under them.
    for name, shape in dparts[1:] + [plug(dock)]:
        rows["fit"] += fit(name, shape, cases)
    rows["fit"] += fit("dock pcb", dpcb, cases, touching=case_names)
    # The receptacle sits on the board, its legs in their slots and its body in the notch.
    j1 = next(s for n, s in dparts if n == "dock J1 3D model")
    rows["fit"] += fit("dock J1 3D model", j1, [("dock pcb", dpcb)], touching=("dock pcb",))
    # The pins, compressed: through the case's window, on the dock's contacts, soldered on the
    # half's pads.
    half_pcbs = tuple(n for n, _ in halves if n.endswith(" pcb"))
    for name, shape in docked:
        rows["fit"] += fit(name, shape, cases + halves + [("dock pcb", dpcb)], touching=half_pcbs + ("dock pcb",))

    rows["pins"] = pin_rows(dock)
    rows["hardware"] = hardware_rows(dock, tray, cover, dparts)
    return rows, {"cases": cases, "shells": shells, "halves": halves, "dock": dparts, "pins": docked}


def jig_checks(board: Board, jig, parts):
    """The soldering jig on the half's board (case frame): clear of its parts, its feet on the
    board, each plunger held in its bore and each barrel clear of the plate. `parts` are
    board_parts()."""
    free = PN.pins(board)
    rows = fit(f"pin_jig_{board.side}", jig, parts + free, touching=("pcb",) + tuple(n for n, _ in free))
    outline = board.outline()
    hw = []
    feet = ([("leg", x, y, P.JIG_LEG_D) for x, y, _ in PN.jig_holes(board)]
            + [("foot", x, y, P.JIG_FOOT_D) for x, y in PN.jig_feet(board)])
    for what, x, y, d in feet:
        v = Vector(x, y, 0)
        edge = min(e.distance_to(v) for e in outline.edges())
        inside = (edge if outline.is_inside(v) else -edge) - d / 2
        hw.append({"stack": f"jig {what} at ({x:.1f}, {y:.1f}) on the board", "inside_edge_mm": r2(inside),
                   "ok": inside >= MIN_GAP})
    z0, z1 = PN.jig_z()
    tip = PN.free_tip_z()
    held = min(P.JIG_PLATE_T, z1 - tip)
    barrel = P.Z_PCB_BOTTOM - P.PIN_SOLDER - P.PIN_BARREL[1] - z1
    tall, _ = stack(P.PIN_HEIGHT_TOL)
    hw.append({"stack": "jig plate on the plungers", "plunger_held_mm": r2(held), "barrel_above_plate_mm": r2(barrel),
               "tip_inside_plate_mm": r2(tip - z0), "pin_height_tol_mm": r2(tall),
               "ok": held >= 1.0 and barrel - tall >= MIN_GAP and r2(tip - tall - z0) >= P.JIG_TIP_INSET})
    # The iron goes on each pad's ends, past the pin's flange: in view from above, past the plate.
    shadow = offset(PN.jig_plate(board), MIN_GAP, kind=Kind.ARC)
    for p in board["dock_pads"]["pads"]:
        x, y = xy((p["x"], p["y"]))
        beyond = rect(x - p["w"] / 2, x + p["w"] / 2, y - p["h"] / 2, y + p["h"] / 2) - Pos(x, y) * Circle(P.PIN_FLANGE[0] / 2)
        for end, (y0, y1) in (("+y", (y, y + p["h"])), ("-y", (y - p["h"], y))):
            area = beyond & rect(x - p["w"], x + p["w"], y0, y1)
            seen = area - shadow
            view = sum(f.area for f in seen.faces()) if seen is not None else 0.0
            hw.append({"stack": f"jig: pad {p['number']}'s {end} end in view for the iron", "pad_end_mm2": r2(area.area),
                       "in_view_mm2": r2(view), "ok": view >= P.JIG_PAD_VIEW})
    return rows, [dict(r, side=board.side) for r in hw]


def stack(terms):
    """(linear, root sum of squares) of a dict of tolerances."""
    v = list(terms.values())
    return sum(v), math.sqrt(sum(t * t for t in v))


def r2(v):
    return round(v, 2)


def pin_rows(dock: Dock):
    """The pins: compression, the pockets' guidance, the desk under a half on its feet, the tilt
    into the case, and per pin, where its tip lands on the contact and where it stands in the
    case's window."""
    rows = []
    protrusion = P.PIN_SOLDER + P.PIN_FREE - P.Z_PCB_BOTTOM  # a free tip below the case's underside
    half_tol = {**P.PIN_HEIGHT_TOL, **P.CASE_HEIGHT_TOL}
    every = {**half_tol, **P.DOCK_HEIGHT_TOL}
    lin, rss = stack(every)
    stroke = P.PIN_FREE - P.PIN_BOTTOM
    rows.append({"check": "pin compression", "nominal_mm": r2(protrusion), "rss_mm": [r2(protrusion - rss), r2(protrusion + rss)],
                 "worst_case_mm": [r2(protrusion - lin), r2(protrusion + lin)], "limits_mm": [P.MIN_COMPRESSION, r2(stroke)],
                 "terms_mm": every, "ok": protrusion - rss >= P.MIN_COMPRESSION and protrusion + rss <= stroke})
    # A half must be in the pocket's straight walls (its full outline, above its bottom chamfer)
    # before its pins' tips come down onto the contacts.
    straight = P.POCKET_DEPTH - P.FUNNEL
    rows.append({"check": "the pocket guides a half before its pins meet the contacts", "straight_wall_mm": r2(straight),
                 "case_bottom_chamfer_mm": P.EDGE_BOTTOM, "tips_meet_contacts_at_mm": r2(protrusion + lin),
                 "ok": straight - P.EDGE_BOTTOM >= protrusion + lin})
    # Off the dock, a half stands on its feet (the shortest allowed, pressed in) and its pins
    # stay off the desk.
    feet = P.FOOT_H - P.FOOT_RECESS - P.FOOT_SQUASH
    tips = protrusion + stack(half_tol)[0]
    rows.append({"check": "the pins clear the desk under a half on its feet", "feet_below_case_mm": r2(feet),
                 "foot_squash_mm": P.FOOT_SQUASH, "tips_below_case_mm": r2(tips), "ok": feet - tips >= MIN_GAP})

    pin_lin, _ = stack(P.PIN_TOL)
    r = P.PIN_BARREL[0] / 2  # the barrel reaches into the floor's window; the flange stays above the floor
    for b, dx in dock.halves():
        in_pocket = Play(case_face(b), P.POCKET_PLAY)
        in_case = Play(b.outline(), P.BOARD_WALL_PLAY, pins=board_pins(b))
        win = dock_window(b).bounding_box()
        rows += tilt_rows(b, in_case, win, pin_lin)
        half = {"x": P.DOCK_CONTACT[0] / 2, "y": P.DOCK_CONTACT[1] / 2}
        for p in b["dock_pads"]["pads"]:
            q = xy((p["x"], p["y"]))
            to_window = {"x": min(q[0] - win.min.X, win.max.X - q[0]) - r, "y": min(q[1] - win.min.Y, win.max.Y - q[1]) - r}
            row = {"check": f"{b.side} pin on pad {p['number']} ({p['net']})", "contact_mm": list(P.DOCK_CONTACT),
                   "terms_mm": {}}
            ok = True
            for axis in AXES:
                case_play, board_play = in_pocket.along(q, axis), in_case.along(q, axis)
                terms = {"case in its pocket (moves and turns)": case_play,
                         "board in its case (moves and turns)": board_play, **P.PIN_TOL, **P.DOCK_TOL}
                for k, v in terms.items():
                    row["terms_mm"].setdefault(k, []).append(r2(v))
                lin, rss = stack(terms)
                room = half[axis] - P.PIN_PAD_MARGIN
                # The pin is on the board: the board's play in its case and the pin's own error
                # move it in the case's window.
                window_need = board_play + pin_lin + MIN_GAP
                row.setdefault("landing_rss_mm", []).append(r2(rss))
                row.setdefault("landing_worst_case_mm", []).append(r2(lin))
                row.setdefault("tip_room_on_contact_mm", []).append(r2(room))
                row.setdefault("worst_case_on_contact", []).append(lin <= half[axis])
                row.setdefault("pin_to_window_mm", []).append(r2(to_window[axis]))
                row.setdefault("window_needs_mm", []).append(r2(window_need))
                ok &= rss <= room and window_need <= to_window[axis]
            row["ok"] = bool(ok)
            rows.append(row)
    return rows


def tilt_rows(b: Board, in_case, win, pin_lin):
    """The board goes into its case tilted, its outer edge under the lips, and turns down about
    its outer bottom edge (checks.lip_rows). Each pin's barrel end and tip come down to the
    floor's top while the board is still tilted, and so inward of their place: there they must
    be inside the window, with the board's play in its case, the pin's own error and MIN_GAP.
    Lower, the board is flatter and they are nearer their place."""
    a, _, n = outer_edge(b)
    u = Vector(-n.X, -n.Y)                  # inward
    drop = P.Z_PCB_BOTTOM - P.FLOOR         # the pivot above the floor's top
    rows = []
    for i, (x, y) in enumerate(PN.pad_centres(b)):
        q = Vector(x, y)
        d = (q - a).dot(u)                  # the pad, inward of the pivot
        play = in_case.reach((x, y), (u.X, u.Y))
        row = {"check": f"{b.side} pin on pad {i + 1}: the board tilts into its case", "pad_from_outer_edge_mm": r2(d),
               "parts": {}}
        ok = True
        for what, hang, rad in (("barrel end", P.PIN_SOLDER + P.PIN_BARREL[1], P.PIN_BARREL[0] / 2),
                                ("tip", P.PIN_SOLDER + P.PIN_FREE, P.PIN_TIP_D / 2)):
            # d sin(t) - hang cos(t) = -drop: the point at the floor's top
            t = math.atan2(hang, d) - math.asin(drop / math.hypot(d, hang))
            shift = d * math.cos(t) + hang * math.sin(t) - d
            # The window's edge inward of the pin (the outer edge's normal is within 20 degrees of x).
            room = ((win.max.X - x) if u.X > 0 else (x - win.min.X)) - rad
            need = abs(u.X) * shift + play + pin_lin + MIN_GAP
            row["parts"][what] = {"tilt_deg": round(math.degrees(t), 1), "moved_inward_mm": r2(shift),
                                  "room_to_window_mm": r2(room), "needs_mm": r2(need)}
            ok &= need <= room
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


def hardware_rows(dock: Dock, tray, cover, dparts):
    """The magnets' pockets and walls, the cases' feet in the tray's holes, the cover over the
    dock PCB's parts, and the USB-C receptacle at the back."""
    rows = []
    wall = (dock.magnet_hole_d - 2 * P.BOSS_CLEAR - (P.MAGNET[0] + P.MAGNET_FIT)) / 2
    rows.append({"stack": "magnet pocket wall inside the dock PCB's hole", "wall_mm": r2(wall),
                 "ok": wall >= P.MAGNET_WALL - 1e-9})
    depth = P.Z_DOCK - P.MAGNET_SKIN
    rows.append({"stack": f"magnet pocket depth (a {P.MAGNET[0]:g} x {P.MAGNET[1]:g} mm magnet and its glue)",
                 "depth_mm": r2(depth), "skin_mm": P.MAGNET_SKIN, "ok": depth >= P.MAGNET_POCKET_H})
    under = {(m[0], m[1]) for m in dock.pcb_magnets}
    for x, y, ref, side in dock.magnets:
        if (x, y) in under:
            continue
        w = wall_around(tray, x, y, P.MAGNET[0] + P.MAGNET_FIT, P.Z_DOCK - P.DOCK_PCB_T, P.Z_DOCK - P.MAGNET_SKIN,
                        P.MAGNET_WALL)
        rows.append({"stack": f"{side} {ref} magnet pocket: wall to the dock PCB's recess", "wall_mm": r2(w),
                     "min_mm": P.MAGNET_WALL, "ok": w >= P.MAGNET_WALL})
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
    # The cover: a printable skin over every part under it. The receptacle's pocket opens
    # through the back face round its mouth; its top stays under the tray's flat top (it cuts
    # into the face's top chamfer, behind the dock).
    top = P.Z_DOCK + P.POCKET_DEPTH
    for name, shape in dparts[1:]:
        roof = shape.bounding_box().max.Z + P.COVER_PART_CLEAR
        row = {"stack": f"cover over {name.split()[1]}", "skin_mm": r2(top - roof), "min_mm": P.COVER_MIN_SKIN,
               "ok": top - roof >= P.COVER_MIN_SKIN}
        if name == "dock J1 3D model":
            row["opening_into_back_chamfer_mm"] = r2(max(0.0, roof - (top - P.TRAY_EDGE_TOP)))
        rows.append(row)
    led = next(s for n, s in dparts if n == "dock LED1 3D model").bounding_box().center()
    hole = cover & cyl(led.X, led.Y, P.LED_HOLE_D - 0.05, P.Z_DOCK, top + 1)
    rows.append({"stack": "cover's pinhole over the power LED", "blocked_mm3": r2(hole.volume if hole else 0.0),
                 "ok": hole is None or hole.volume < 1e-3})
    # The receptacle: its mouth on the back face, its plug above the desk, its axis where
    # params say.
    j1 = next(s for n, s in dparts if n == "dock J1 3D model").bounding_box()
    zc = P.Z_DOCK + P.DOCK_USB_AXIS
    rows.append({"stack": "USB-C mouth on the tray's back face", "mouth_y_mm": r2(j1.max.Y), "back_face_y_mm": r2(dock.y_back),
                 "ok": abs(j1.max.Y - dock.y_back) <= 0.1})
    rows.append({"stack": "USB-C axis (3D model) where params put it", "model_mm": r2((j1.min.Z + j1.max.Z) / 2),
                 "params_mm": r2(zc), "ok": abs((j1.min.Z + j1.max.Z) / 2 - zc) <= 0.05})
    rows.append({"stack": "USB-C plug's overmold above the desk", "bottom_mm": r2(zc - P.USB_PLUG[1] / 2),
                 "ok": zc - P.USB_PLUG[1] / 2 >= 0.2})
    return rows
