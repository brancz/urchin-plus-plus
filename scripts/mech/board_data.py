#!/usr/bin/env python3
"""Mechanical data of both halves for the case and the dock tray (phase 7).

    "$KICAD_PY" scripts/mech/board_data.py           # writes mech/data/{left,right}.json
    "$KICAD_PY" scripts/mech/board_data.py --check   # fails if those files are stale

Everything the CAD in mech/ needs comes from the routed boards, never from hand-typed
numbers: the board outline, the case holes, the tenting puck, the charging pads, the steel
disc and rubber foot positions, the parts that need openings (USB-C, power switch, reset
button), the antenna keep-out, the battery's outline and courtyard, its wire pads and the key
positions.
Features are found by footprint name, because the two halves use different references.

Coordinates are KiCad's: millimetres, y pointing down, in each board's own frame.
Needs KiCad 9's Python (pcbnew); stays Python 3.9-compatible.
"""

import argparse
import json
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "mech" / "data"
SIDES = ("left", "right")
mm = pcbnew.ToMM


def r(v):
    return round(v, 4)


def pt(p):
    return [r(mm(p.x)), r(mm(p.y))]


def bbox(box):
    return [r(mm(box.GetLeft())), r(mm(box.GetTop())), r(mm(box.GetRight())), r(mm(box.GetBottom()))]


def courtyard(fp):
    layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    poly = fp.GetCourtyard(layer)
    return bbox(poly.BBox()) if poly.OutlineCount() else None


def lib_name(fp):
    return fp.GetFPID().GetLibItemName().wx_str()


def footprint(fp, **extra):
    d = {"ref": fp.GetReference(), "x": pt(fp.GetPosition())[0], "y": pt(fp.GetPosition())[1],
         "rot": r(fp.GetOrientationDegrees()), "side": "bottom" if fp.IsFlipped() else "top",
         "courtyard": courtyard(fp)}
    d.update(extra)
    return d


def body_diameter(fp):
    """The diameter of a marker footprint's smallest circle: the part's body (the larger one
    is its courtyard)."""
    radii = [mm(g.GetRadius()) for g in fp.GraphicalItems() if g.GetShape() == pcbnew.SHAPE_T_CIRCLE]
    return r(2 * min(radii))


def silk_bbox(fp):
    """(x0, y0, x1, y1) of the line centres on a footprint's silkscreen: a part's outline."""
    layer = pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS
    pts = [pt(q) for g in fp.GraphicalItems() if isinstance(g, pcbnew.PCB_SHAPE) and g.GetLayer() == layer
           and g.GetShape() == pcbnew.SHAPE_T_SEGMENT
           for q in (g.GetStart(), g.GetEnd())]
    return [min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)]


def holes(fp):
    return [{"x": pt(p.GetPosition())[0], "y": pt(p.GetPosition())[1], "d": r(mm(p.GetDrillSize().x))}
            for p in fp.Pads() if p.GetDrillSize().x > 0]


def extract(side):
    path = ROOT / "hardware" / "layouts" / side / ("%s.kicad_pcb" % side)
    board = pcbnew.LoadBoard(str(path))

    outlines = pcbnew.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(outlines):
        sys.exit("board_data: %s: the board outline isn't closed" % path)
    if outlines.OutlineCount() != 1:
        sys.exit("board_data: %s: expected one outline, got %d" % (path, outlines.OutlineCount()))
    outer = outlines.Outline(0)
    outline = [pt(outer.CPoint(i)) for i in range(outer.PointCount())]
    cutouts = [[pt(outlines.Hole(0, h).CPoint(i)) for i in range(outlines.Hole(0, h).PointCount())]
               for h in range(outlines.HoleCount(0))]

    data = {
        "side": side,
        "source": str(path.relative_to(ROOT)),
        "thickness": r(mm(board.GetDesignSettings().GetBoardThickness())),
        "bbox": bbox(board.GetBoardEdgesBoundingBox()),
        "outline": outline,
        "cutouts": cutouts,
        "case_holes": [], "puck": None, "dock_pads": None, "steel_discs": [], "feet": [],
        "usb": None, "power_switch": None, "reset": None, "battery": None, "battery_pads": None,
        "leds": [], "keys": [],
        "rule_areas": {},
        # Every physical part on the bottom (markers excluded): what the case's standoffs and
        # floor must stay clear of.
        "bottom_courtyards": [],
    }
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        name = lib_name(fp)
        if fp.IsFlipped() and name not in ("STEEL_DISC", "RUBBER_FOOT"):
            poly = fp.GetCourtyard(pcbnew.B_CrtYd)
            if poly.OutlineCount():
                data["bottom_courtyards"].append({"ref": fp.GetReference(), "polygon": [
                    pt(poly.Outline(0).CPoint(i)) for i in range(poly.Outline(0).PointCount())]})
        if name.startswith("M2_hole_"):
            h = holes(fp)[0]
            # 3.5 mm footprints have a 2.2 mm drill (screw clearance), 4.2 mm ones a 3.8 mm drill.
            data["case_holes"].append(dict(footprint(fp), x=h["x"], y=h["y"], d=h["d"], kind=name))
        elif name.startswith("Tenting_Puck"):
            # The puck's outline is the circle on B.SilkS through its arc ends.
            radius = 0.0
            for g in fp.GraphicalItems():
                if g.GetLayer() == pcbnew.B_SilkS and g.GetShape() in (pcbnew.SHAPE_T_ARC, pcbnew.SHAPE_T_SEGMENT):
                    for q in (g.GetStart(), g.GetEnd()):
                        radius = max(radius, ((mm(q.x) - mm(fp.GetPosition().x)) ** 2
                                              + (mm(q.y) - mm(fp.GetPosition().y)) ** 2) ** 0.5)
            data["puck"] = footprint(fp, radius=r(radius), holes=holes(fp))
        elif name == "DOCK_PADS":
            pads = [{"number": p.GetNumber(), "x": pt(p.GetPosition())[0], "y": pt(p.GetPosition())[1],
                     "w": r(mm(p.GetSize().x)), "h": r(mm(p.GetSize().y)), "net": p.GetNetname()}
                    for p in sorted(fp.Pads(), key=lambda p: p.GetNumber())]
            data["dock_pads"] = footprint(fp, pads=pads)
        elif name == "STEEL_DISC":
            data["steel_discs"].append(footprint(fp, d=body_diameter(fp)))
        elif name == "RUBBER_FOOT":
            data["feet"].append(footprint(fp, d=body_diameter(fp)))
        elif name.startswith("USB-C"):
            data["usb"] = footprint(fp)
        elif name == "SW-TH_MSK12C02":
            data["power_switch"] = footprint(fp)
        elif name.startswith("SW-SMD_L3.9"):
            data["reset"] = footprint(fp)
        elif name.startswith("BATTERY_"):
            data["battery"] = footprint(fp, outline=silk_bbox(fp))
        elif name == "BAT_PADS":
            # The cell's wire pads, beside the end of its outline.
            data["battery_pads"] = footprint(fp, pads=[
                {"number": p.GetNumber(), "x": pt(p.GetPosition())[0], "y": pt(p.GetPosition())[1],
                 "w": r(mm(p.GetSize().x)), "h": r(mm(p.GetSize().y))}
                for p in sorted(fp.Pads(), key=lambda p: p.GetNumber())])
        elif name.startswith("LED-ARRAY"):
            data["leds"].append(footprint(fp, holes=holes(fp)))
        elif "Choc" in name:
            # The hotswap socket under the key: its courtyard on B.CrtYd. The footprint's 3D
            # model isn't installed, so the board STEP lacks the sockets and the case checks
            # use this outline (1.85 mm tall, docs/ARCHITECTURE.md).
            poly = fp.GetCourtyard(pcbnew.B_CrtYd)
            socket = [pt(poly.Outline(0).CPoint(i)) for i in range(poly.Outline(0).PointCount())]
            data["keys"].append(footprint(fp, socket=socket))
    for z in board.Zones():
        if z.GetIsRuleArea():
            o = z.Outline().Outline(0)
            data["rule_areas"][z.GetZoneName()] = [pt(o.CPoint(i)) for i in range(o.PointCount())]

    missing = [k for k in ("puck", "dock_pads", "usb", "power_switch", "reset", "battery", "battery_pads")
               if not data[k]]
    if missing or len(data["keys"]) != 17 or len(data["steel_discs"]) != 2 or len(data["feet"]) != 4 \
            or len(data["case_holes"]) != 7 or "ANTENNA_KEEPOUT" not in data["rule_areas"]:
        sys.exit("board_data: %s: missing features %s, or wrong counts (keys %d, discs %d, feet %d, holes %d)"
                 % (side, missing, len(data["keys"]), len(data["steel_discs"]), len(data["feet"]),
                    len(data["case_holes"])))
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if mech/data is stale")
    args = ap.parse_args()
    stale = []
    for side in SIDES:
        text = json.dumps(extract(side), indent=1) + "\n"
        out = OUT / ("%s.json" % side)
        if args.check:
            if not out.exists() or out.read_text() != text:
                stale.append(str(out.relative_to(ROOT)))
        else:
            OUT.mkdir(parents=True, exist_ok=True)
            out.write_text(text)
            print("wrote %s" % out.relative_to(ROOT))
    if stale:
        sys.exit("board_data: stale, rerun scripts/mech/board_data.py: %s" % ", ".join(stale))


if __name__ == "__main__":
    main()
