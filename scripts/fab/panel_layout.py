"""KiKit layout plugin: both halves in one panel, where the original Urchin panel had them.

Used by hardware/panel.json (`"layout": {"type": "plugin", "code":
"scripts/fab/panel_layout.py.HalvesLayout", "arg": "LEFT.kicad_pcb;RIGHT.kicad_pcb"}`,
`"tabs": {"type": "annotation"}`). KiKit's own layouts repeat one board; this one
appends the two different halves at their own coordinates (both boards keep the
original panel's coordinates, so their relative position is the original's: a 2.54 mm
gap at x = 128.397). Designators get a side suffix (U1 -> U1_L / U1_R) so the panel's
BOM and CPL have unique references; nets get an L-/R- prefix.

The panel has a full frame (hardware/panel.json): the USB-C receptacle and the slide
switch reach 1 mm past each half's inner edge, which becomes a short panel edge.

Tabs are placed here as KiKit tab annotations rather than by KiKit's even spacing,
because the original's hotswap socket pads overhang the outline in places (rule 1;
right half SW22, SW27, SW32 along the gap, left SW5 and SW17) and a tab there would put
mouse-bite holes into a pad. Positions are in the left half's coordinates and mirrored
for the right half; scripts/fab/build.sh checks the panel with DRC (mask bridges and hole
clearance would show a tab too close to copper).

KiKit turns arcs into 128 segments per full circle, which on the outline's large-radius arcs
leaves chords up to 0.025 mm inside the arc, and its arc reconstruction misses short ones.
Importing this module replaces KiKit's arc approximation with one whose chords stay within
0.5 um of the arc (rule 1; scripts/checks/panel_outline.py checks the panel's outline).
Runs inside KiKit (KiCad's Python); Python 3.9.
"""

import math

import kikit.substrate
import numpy as np
import pcbnew
from kikit.annotations import TabAnnotation
from kikit.common import findBoardBoundingBox
from kikit.panelize import Origin
from kikit.panelize_ui_impl import frameOffset
from kikit.plugin import LayoutPlugin
from shapely.geometry import LineString

SIDES = ("L", "R")
MIRROR_X = 128.397
TAB_WIDTH = 4.0      # mm
GAP_TABS_Y = (50.8, 68.33)       # between the halves: the original panel's two tabs, clear of the overhanging socket pads
TOP_TABS_X = (143.0, 195.0)       # left half; to the top rail
BOTTOM_TABS_X = (150.0, 200.0)    # left half; to the bottom rail
INNER_TABS_Y = (40.9,)            # to the side frame, beside the antenna, 2 mm wide: its mouse bites (y 39.4-42.4)
INNER_TAB_WIDTH = 2.0             # stay inside the keep-out (to y 43.25), clear of copper, and >= 0.9 mm from the ear's case hole
ARC_TOLERANCE = 0.0005            # mm, largest distance between an outline arc and its chords


def nm(v):
    return int(round(v * 1e6))


def approximate_arc(arc, endWith):
    """kikit.substrate.approximateArc with chords sized by ARC_TOLERANCE."""
    start = pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T)
    end = pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T)
    arc.CalcArcAngles(start, end)
    a0 = start.AsRadians()
    a1 = a0 + 2 * math.pi if arc.GetShape() == pcbnew.SHAPE_T_CIRCLE else end.AsRadians()
    r = arc.GetRadius()
    step = 2 * math.acos(1 - nm(ARC_TOLERANCE) / r) if r > nm(ARC_TOLERANCE) else math.pi / 6
    theta = np.linspace(a0, a1, max(12, int(math.ceil(abs(a1 - a0) / step)) + 1))
    outline = list(np.column_stack([arc.GetCenter()[0] + r * np.cos(theta), arc.GetCenter()[1] + r * np.sin(theta)]))
    target = np.array(endWith)
    if np.linalg.norm(target - outline[0]) < np.linalg.norm(target - outline[-1]):
        outline.reverse()
    return outline


kikit.substrate.approximateArc = approximate_arc


class HalvesLayout(LayoutPlugin):
    def buildLayout(self, panel, inputFile, sourceArea):
        paths = [p for p in self.userArg.split(";") if p]
        if len(paths) != 2:
            raise RuntimeError("HalvesLayout needs 'LEFT.kicad_pcb;RIGHT.kicad_pcb' as its argument")
        areas = []
        for side, path in zip(SIDES, paths):
            board = pcbnew.LoadBoard(path)
            area = findBoardBoundingBox(board)
            areas.append(area)
            panel.appendBoard(path, area.GetCenter(), sourceArea=area, origin=Origin.Center,
                              tolerance=pcbnew.FromMM(1), inheritDrc=False,
                              netRenamer=lambda n, name, s=side: "%s-%s" % (s, name),
                              refRenamer=lambda n, ref, s=side: "%s_%s" % (ref, s))
        top = min(a.GetTop() for a in areas) - nm(1)
        bottom = max(a.GetBottom() for a in areas) + nm(1)
        outer = (areas[0].GetRight() + nm(1), areas[1].GetLeft() - nm(1))  # beyond each half's inner edge
        for i, substrate in enumerate(panel.substrates):
            mirror = (lambda x: x) if i == 0 else (lambda x: 2 * MIRROR_X - x)
            toward_gap = -1 if i == 0 else 1  # the gap is to the left of the left half
            for y in GAP_TABS_Y:
                substrate.annotations.append(TabAnnotation(None, (nm(MIRROR_X), nm(y)), (-toward_gap, 0), nm(TAB_WIDTH)))
            for x in TOP_TABS_X:
                substrate.annotations.append(TabAnnotation(None, (nm(mirror(x)), top), (0, 1), nm(TAB_WIDTH)))
            for x in BOTTOM_TABS_X:
                substrate.annotations.append(TabAnnotation(None, (nm(mirror(x)), bottom), (0, -1), nm(TAB_WIDTH)))
            for y in INNER_TABS_Y:
                substrate.annotations.append(TabAnnotation(None, (outer[i], nm(y)), (toward_gap, 0), nm(INNER_TAB_WIDTH)))
        return panel.substrates

    def buildPartitionLine(self, panel, framingSubstrates):
        # A tab runs from the board out to the substrate's partition line. KiKit derives the
        # partition from bounding boxes and drops a half's side where its box ends a few tens
        # of µm inside the other half's (here the left half's top and the right half's bottom),
        # so no tab would be built there. Each half's partition is set explicitly instead: the
        # gap's midline, and the frame's inner edge on the other three sides.
        panel.buildPartitionLineFromBB(framingSubstrates)  # keeps KiKit's backbone line
        vspace, hspace = frameOffset(self.preset["framing"])
        boxes = [s.bounds() for s in panel.substrates]
        left = min(b[0] for b in boxes) - hspace
        top = min(b[1] for b in boxes) - vspace
        right = max(b[2] for b in boxes) + hspace
        bottom = max(b[3] for b in boxes) + vspace
        for i, substrate in enumerate(panel.substrates):
            x0, x1 = (nm(MIRROR_X), right) if i == 0 else (left, nm(MIRROR_X))
            substrate.partitionLine = LineString([(x0, top), (x1, top), (x1, bottom), (x0, bottom), (x0, top)])
