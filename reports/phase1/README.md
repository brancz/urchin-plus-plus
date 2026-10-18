# Phase 1 — geometry

Date: 2026-10-18.

## Exit criteria

| Criterion (docs/PLAN.md) | Result | Evidence |
|---|---|---|
| Geometry file as the single source for placement | `hardware/geometry/urchin.json`, written by `scripts/geometry/extract.py` from `reference/urchin/main.kicad_pcb` (source commit and SHA-256 recorded in the file) | `hardware/geometry/urchin.json` |
| A script that overlays the extracted geometry on the original and reports zero deviation | `scripts/checks/geometry.py` compares a board with the **original board** (not with the geometry file). The preview boards built from the geometry file and the generated parts show zero deviation: 27 footprints, 131 holes and pads, 29 edge primitives per half, to the nanometre. A 1 µm move of one switch is caught. | `geometry-left.json`, `geometry-right.json` |
| Renders of both halves | top and bottom of each half | `render-{left,right}-{top,bottom}.png` |

## What is extracted, per half

- **Switches:** 17 Choc footprint positions and rotations (the footprint origin is the switch centre), named `rNcM` (row 0 = top; column 0 = pinky … 4 = inner index) and `t0`/`t1` (thumbs, t0 nearer the main block).
  - The original's half at x > 128.4 is the left hand (its silkscreen says LEFT), with SW1–SW17.
  - The half at x < 128.4 is the right hand, with SW18–SW34.
- **Outline:** every Edge.Cuts line and arc of the half as drawn (27 per half).
  - The original is a two-half panel joined by two mouse-bite tabs. Its tab stubs and slot ends (12 primitives) are dropped.
  - Each half's edge is closed across the two tab openings with straight segments collinear with that edge (x = 129.667 left, x = 127.127 right). These closures are the only derived geometry, and they are listed separately in the file.
- **Tenting-puck mount:** `Tenting_Puck2_no_pads`, three plated 2.2 mm holes on a 19.05 mm radius, at (183.261, 51.562) rotated −3° (left) and at (73.787, 51.562) rotated −177° (right).
- **Case holes:** all 9 M2 holes per half, kept for compatibility with existing cases and the MCU cover. Two of them overlap in the original; that is kept as is.
- **Old controller area:** the nice!nano, nice!view, power switch, reset and battery pads, with positions and bounding boxes, as placement hints. The nano's USB end is at the notch in the top edge.

## Parts generated from the original footprints (`scripts/geometry/mechanical_parts.py`)

atopile deletes every footprint it didn't create (reports/phase0/), so these are atopile parts with the original footprints:

- `KEY_CHOC`: switch holes, plus the Kailh Choc hotswap socket's two pads on B.Cu. The socket is hand-soldered (see phase 2), so this footprint is excluded from the BOM and position files.
- `PUCK`: the tenting-puck mount.
- `HOLE_M2_4_2`, `HOLE_M2_3_5`: the case holes. The swoop and chocolad variants have identical pads.

Cosmetic changes, made so that atopile can't mangle these parts:

- Of two items with identical geometry on different layers, only one is kept: courtyard over fab, and for the puck its bottom silkscreen (the puck mounts underneath).
- `${REFERENCE}` texts are dropped, because atopile strips them anyway.

Holes and pads are untouched, as the zero-deviation check shows.

## Reproduce

```bash
"$KICAD_PY" scripts/geometry/extract.py
"$KICAD_PY" scripts/geometry/mechanical_parts.py
"$KICAD_PY" scripts/geometry/preview.py scratch/preview
"$KICAD_PY" scripts/checks/geometry.py scratch/preview/left.kicad_pcb --half left
scripts/render.sh scratch/preview/left.kicad_pcb reports/phase1/render-left
```
