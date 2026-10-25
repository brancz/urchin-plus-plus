"""A 3D preview of the finished keyboard as one HTML page: both halves in their cases and
shells with switches, keycaps, battery and hardware, and the dock. The printed parts, the boards' STEP
exports and the hardware positions are the ones the build checks; the switches and keycaps
are simplified (no 3D models for them are installed). The page (`preview.html` next to this
file, three.js from a CDN) gets the meshes inlined: quantized to 16 bits per coordinate in
each mesh's bounding box, gzipped, base64.

    uv run mech preview --boards DIR --out FILE.html
"""

import base64
import gzip
import json
import math
from pathlib import Path

import numpy as np
from build123d import Align, Axis, Box, Plane, Pos, Rectangle, RectangleRounded, Sphere, fillet, loft

from . import checks, dock_checks, pins
from . import params as P
from .board import Board, rect_face, xy
from .checks import STEP_UNDERSIDE
from .case import box, case, cell_box, cyl, prism, screw_holes, shell
from .tray import Dock

TEMPLATE = Path(__file__).with_name("preview.html")
LOW = (Align.CENTER, Align.CENTER, Align.MIN)

KEYCAP_Z = P.KEYCAP_REST  # a Choc keycap's lowest point above the PCB at rest (params)
KEYCAP_H = P.KEYCAP_TOP - P.KEYCAP_REST
CELL_T = 4.3        # the EEMB 401730 (mech/README.md), on its foam

# Board parts by reference prefix: (kind, label, what it is).
PART_KINDS = {
    "U1": ("ic", "E73 module", "nRF52840 with its antenna, on the bottom"),
    "U2": ("ic", "BQ24073 charger", "charges the cell from USB-C or the dock"),
    "U3": ("ic", "USBLC6 ESD protection", "on the USB-C data lines"),
    "J": ("metal", "USB-C receptacle", "charging and firmware updates"),
    "SW35": ("metal", "Power switch", "slide switch, through the inner wall"),
    "SW36": ("metal", "Reset button", "pressed with a pin through the case floor"),
    "LED1": ("led", "Status LED", "RGB, shines up through the PCB"),
    "LED2": ("led", "Charge LED", "amber while charging, green when full"),
    "D": ("ic", "Diode", ""),
    "R": ("ic", "Resistor", ""),
    "C": ("cap", "Capacitor", ""),
    "F": ("ic", "Polyfuse", "0.5 A, resets once cool"),
}


def part_kind(ref):
    for prefix in sorted(PART_KINDS, key=len, reverse=True):
        if ref.startswith(prefix):
            return PART_KINDS[prefix]
    return ("ic", ref, "")


def switch():
    """A Kailh Choc v1, simplified: bottom housing, flange, top housing, stem."""
    s = Box(13.8, 13.8, 2.2, align=LOW)
    s += Pos(0, 0, 2.2) * Box(15.0, 15.0, 0.8, align=LOW)
    s += loft([Plane.XY.offset(3.0) * Rectangle(13.8, 13.8), Plane.XY.offset(4.4) * Rectangle(11.5, 10.5)])
    s += Pos(0, 0, 4.4) * Box(5.4, 3.0, KEYCAP_Z + 0.5 - 4.4, align=LOW)  # the stem, up into the keycap
    return s


def keycap():
    """A low-profile Choc keycap (MBK-like): 17.5 x 16.5 mm, tapered, with a shallow dish."""
    w, h = P.KEYCAP
    cap = loft([RectangleRounded(w, h, 1.6), Plane.XY.offset(KEYCAP_H) * RectangleRounded(w - 1.2, h - 1.2, 1.2)])
    cap = fillet(cap.edges().group_by(Axis.Z)[-1], 0.5)
    sag, r = 0.35, 70.0
    return cap - Pos(0, 0, KEYCAP_H - sag + r) * Sphere(r)


class Meshes:
    """Meshes for the page: each one tessellated once, quantized, and placed once or many times."""

    def __init__(self):
        self.meta, self.chunks, self.offset = [], [], 0

    def _push(self, arr):
        data = arr.tobytes()
        data += b"\0" * (-len(data) % 4)
        at = self.offset
        self.chunks.append(data)
        self.offset += len(data)
        return at

    def add(self, shape, label, kind, group, layer, info="", inst=None, tol=0.05, ang=0.35):
        verts, tris = shape.tessellate(tol, ang)
        if not tris:
            return
        v = np.array([(p.X, p.Y, p.Z) for p in verts], dtype=np.float64)
        lo, hi = v.min(axis=0), v.max(axis=0)
        q = np.round((v - lo) / np.maximum(hi - lo, 1e-9) * 65535).astype("<u2")
        wide = len(v) > 65535
        t = np.array(tris, dtype="<u4" if wide else "<u2")
        self.meta.append({
            "label": label, "info": info, "kind": kind, "group": group, "layer": layer,
            "nv": len(v), "ni": len(t), "i32": wide,
            "lo": [round(float(x), 4) for x in lo], "hi": [round(float(x), 4) for x in hi],
            "vo": self._push(q), "io": self._push(t), "inst": inst,
        })

    def blob(self):
        return base64.b64encode(gzip.compress(b"".join(self.chunks), 9)).decode()


def half(m: Meshes, board: Board, step_path):
    g = board.side
    m.add(case(board), "Case", "print", g, "case", "printed in PLA, floor down, no supports")
    m.add(shell(board), "Top shell", "print", g, "shell",
          "printed upright; the switches clip into its plate, two screws from below hold it")

    for name, shape in checks.board_parts(board, step_path):
        if name == "pcb":
            m.add(shape, "PCB", "pcb", g, "pcb", "1.6 mm, ENIG; every assembled part is on the bottom", tol=0.03)
        elif name.endswith("3D model"):
            kind, label, info = part_kind(name.split()[0])
            m.add(shape, label, kind, g, "pcb", info, tol=0.03, ang=0.6)
        elif name.endswith("socket"):
            m.add(shape, "Hot-swap socket", "socket", g, "pcb", "Kailh Choc, under each switch")

    for _, shape in pins.pins(board):
        m.add(shape, "Pogo pin", "gold", g, "pcb", "spring-loaded, soldered on the charging pad; "
              "presses on the dock's gold contact")

    keys = [[*xy((k["x"], k["y"])), 0.0, k["rot"]] for k in board["keys"]]
    m.add(switch(), "Kailh Choc v1 switch", "switch", g, "switch", "3 mm travel, in a hot-swap socket",
          inst=[[x, y, P.Z_PCB_TOP, r] for x, y, _, r in keys])
    m.add(keycap(), "Choc keycap", "keycap", g, "keycap", "17.5 x 16.5 mm low profile",
          inst=[[x, y, P.Z_PCB_TOP + KEYCAP_Z, r] for x, y, _, r in keys])

    x0, y0, x1, y1 = board["battery"]["outline"]
    m.add(prism(rect_face((x0, y0, x1, y1)), P.Z_PCB_TOP, P.Z_PCB_TOP + P.FOAM_T), "Foam tape", "foam", g, "cell",
          "1 mm, cut to the outline")
    cx0, cy0, cx1, cy1 = cell_box(board)
    cx, cy = xy(((cx0 + cx1) / 2, (cy0 + cy1) / 2))
    cell = fillet(Box(cx1 - cx0, cy1 - cy0, CELL_T, align=LOW).edges().filter_by(Axis.Z), 1.0)
    m.add(Pos(cx, cy, P.Z_PCB_TOP + P.FOAM_T) * cell, "401730 LiPo cell", "cell", g, "cell",
          "150 mAh, wires soldered to the pads")

    hd, hh = P.SHELL_SCREW_HEAD
    for h in screw_holes(board):
        x, y = xy((h["x"], h["y"]))
        m.add(cyl(x, y, hd, P.HEAD_DEPTH - hh, P.HEAD_DEPTH), f"M2 x {P.SHELL_SCREW_L:g} screw", "steel", g, "under",
              "from the underside, through the PCB into the shell")
    for d in board["steel_discs"]:
        x, y = xy((d["x"], d["y"]))
        m.add(cyl(x, y, 10.0, P.DISC_T - 1.0, P.DISC_T) - cyl(x, y, 5.3, P.DISC_T - 1.1, P.DISC_T + 0.1),
              "M5 steel washer", "zinc", g, "under", "the dock's magnets pull on it")
    for f in board["feet"]:
        x, y = xy((f["x"], f["y"]))
        m.add(cyl(x, y, f["d"], -(P.FOOT_H - P.FOOT_RECESS), P.FOOT_RECESS), "Rubber foot", "rubber", g, "under",
              f"6 x {P.FOOT_H:g} mm bumper")
    for led in board["leds"]:
        kind = "glow-charge" if led["ref"] == "LED2" else "glow-status"
        for h in led["holes"]:
            x, y = xy((h["x"], h["y"]))
            m.add(cyl(x, y, P.LED_WINDOW_D - 0.3, P.Z_LID_TOP - 0.6, P.Z_LID_TOP - 0.5), PART_KINDS[led["ref"]][1],
                  kind, g, "shell", PART_KINDS[led["ref"]][2])


def dock(m: Meshes, d: Dock, step_path):
    for piece in d.pieces(d.tray()):
        m.add(piece, "Dock tray", "print", "dock", "dock", "two printed pieces, joined by the dock PCB and the cover")
    parts = dock_checks.dock_parts(d, step_path)
    cover = d.cover([(n.split()[1], s) for n, s in parts[1:]])
    m.add(cover, "Dock cover", "print", "dock", "dock", "printed, glued over the dock PCB's parts; "
          "a pinhole over the power LED")
    for plate in d.floor_plates():
        m.add(plate, "Dock floor plate", "print", "dock", "dock", "printed, 0.4 mm, glued over the pocket's floor and "
              "the dock PCB; a slot over the gold contacts")
    for name, shape in parts:
        if name == "dock pcb":
            m.add(shape, "Dock PCB", "pcb-black", "dock", "dock", "black mask, USB-C in at the back, 5 V out to the "
                  "gold contacts", tol=0.03)
        else:
            ref = name.split()[1]
            kind, label, info = part_kind(ref)
            if ref == "LED1":
                label, info = "Power LED", "green while the dock has power"
            elif ref.startswith("J"):
                info = "power only, at the back: any 5 V USB-C charger"
            m.add(shape, label, kind, "dock", "dock", info, tol=0.03, ang=0.6)
    w, h = P.DOCK_CONTACT
    for x, y, net, _ in d.contacts:
        m.add(box(x - w / 2, x + w / 2, y - h / 2, y + h / 2, P.Z_DOCK + STEP_UNDERSIDE, P.Z_DOCK), "Dock contact", "gold", "dock",
              "dock", f"flat gold (ENIG) pad, {'5 V' if net == 'DOCK_5V' else 'GND'}: a half's pogo pin lands on it")
    x, y = d.placed("LED1")
    top = d.top
    m.add(cyl(x, y, P.LED_HOLE_D - 0.1, top - 0.3, top - 0.25), "Power LED", "glow-power", "dock", "dock",
          "green while the dock has power")


def build(boards_dir, out):
    boards_dir = Path(boards_dir)
    m = Meshes()
    d = Dock.load()
    boxes = {}
    for board in (d.left, d.right):
        half(m, board, boards_dir / f"{board.side}.step")
        bb = case(board).bounding_box()
        boxes[board.side] = [round(v, 2) for v in (bb.min.X, bb.min.Y, bb.max.X, bb.max.Y)]
    dock(m, d, boards_dir / "dock.step")
    tb = d.tray().bounding_box()
    boxes["dock"] = [round(v, 2) for v in (tb.min.X, tb.min.Y, tb.max.X, tb.max.Y)]

    left = boxes["left"]
    meta = {
        "meshes": m.meta,
        "boxes": boxes,
        "dx": round(d.dx, 3),
        "z_dock": P.Z_POCKET,
        "z_desk": P.FOOT_H - P.FOOT_RECESS,
        "spec": {
            "keys": sum(len(b["keys"]) for b in (d.left, d.right)),
            "half_mm": [round(left[2] - left[0]), round(left[3] - left[1])],
            "height_mm": round(P.FOOT_H - P.FOOT_RECESS + P.Z_PCB_TOP + KEYCAP_Z + KEYCAP_H, 1),
            "dock_mm": [round(tb.size.X), round(tb.size.Y)],
        },
    }
    html = TEMPLATE.read_text()
    html = html.replace("__MESH_META__", json.dumps(meta, separators=(",", ":")))
    html = html.replace("__MESH_DATA__", m.blob())
    Path(out).write_text(html)
    tris = sum(x["ni"] * (len(x["inst"]) if x["inst"] else 1) for x in m.meta)
    print(f"mech preview: {len(m.meta)} meshes, {tris} triangles drawn, {len(html) / 1e6:.1f} MB; wrote {out}")
    return 0
