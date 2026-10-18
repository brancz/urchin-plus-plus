# Phase 1 — geometry

Date: 2026-10-18.

## Exit criteria

| Criterion (docs/PLAN.md) | Result | Evidence |
|---|---|---|
| Geometry file as the single source for placement | `hardware/geometry/urchin.json`, written by `scripts/geometry/extract.py` from `reference/urchin/main.kicad_pcb` (source commit and SHA-256 recorded in the file) | `hardware/geometry/urchin.json` |
| A script that overlays the extracted geometry on the original and reports zero deviation | `scripts/checks/geometry.py` derives everything from the **original board** (outline and tab closures included) and only checks that the geometry file agrees. Per half, the preview boards built from the geometry file and the generated parts (`preview/`) show zero deviation: 17 switches, the puck, 7 case holes, 129 pads, and 29 edge primitives, to the nanometre. It catches a 1 µm move and every mutation the reviewer tried (extra or duplicate footprints, pads moved to the other side or reshaped or rotated, extra or tampered Edge.Cuts). `scripts/checks/geometry_all.sh` runs in CI: it fetches duckyb/urchin at the recorded commit, verifies the SHA-256, regenerates the geometry file and the parts byte for byte, and checks the boards. | `geometry-left.json`, `geometry-right.json`, `preview/` |
| Renders of both halves | top and bottom of each half | `render-{left,right}-{top,bottom}.png` |

## What is extracted, per half

- **Switches:** 17 Choc footprint positions and rotations (the footprint origin is the switch centre), named `rNcM` (row 0 = top; column 0 = pinky … 4 = inner index) and `t0`/`t1` (thumbs, t0 nearer the main block).
  - The original's half at x > 128.4 is the left hand (its silkscreen says LEFT), with SW1–SW17.
  - The half at x < 128.4 is the right hand, with SW18–SW34.
- **Outline:** every Edge.Cuts line and arc of the half as drawn (27 per half).
  - The original is a two-half panel joined by two mouse-bite tabs. Its tab stubs and slot ends (12 primitives) are dropped.
  - Each half's edge is closed across the two tab openings with straight segments collinear with that edge (x = 129.667 left, x = 127.127 right). These closures are the only derived geometry, and they are listed separately in the file.
- **Tenting-puck mount:** `Tenting_Puck2_no_pads`, three plated 2.2 mm holes on a 19.05 mm radius, at (183.261, 51.562) rotated −3° (left) and at (73.787, 51.562) rotated −177° (right).
- **Case holes:** the M2 holes, kept for compatibility with existing cases and the MCU cover. Per half, 7 of the 9 are kept and made non-plated (same drill). Two are dropped because their drills overlap: one overlaps a tenting-puck hole, the other overlaps a larger case hole. Overlapping drills are a fabrication risk, and the puck is rule-1 geometry. `case_holes_dropped` in the geometry file records which ones and why.
- **Old controller area:** the nice!nano, nice!view, power switch, reset and battery pads, with positions and bounding boxes, as placement hints. The nano's USB end is at the notch in the top edge.

## Parts generated from the original footprints (`scripts/geometry/mechanical_parts.py`)

atopile deletes every footprint it didn't create (reports/phase0/), so these are atopile parts with the original footprints:

- `KEY_CHOC`: switch holes, plus the Kailh Choc hotswap socket's two pads on B.Cu.
  - The socket is sold out at JLC and LCSC, so it is hand-soldered (ARCHITECTURE.md decision log).
  - The footprint is excluded from the BOM and position files.
  - The socket pads carry no paste, so JLC's bottom stencil prints none there.
- `PUCK`: the tenting-puck mount.
- `HOLE_M2_4_2`, `HOLE_M2_3_5`: the case holes, non-plated. The swoop and chocolad variants have identical pads.

Cosmetic changes, made so that atopile can't mangle these parts:

- Of two items with identical geometry on different layers, only one is kept: courtyard over fab, and for the puck its bottom silkscreen (the puck mounts underneath).
- `${REFERENCE}` texts are dropped, because atopile strips them anyway.

Holes and pads are untouched, as the zero-deviation check shows. The only exception is the documented one: case holes are non-plated. Generation is deterministic, with UUIDs derived from the part name and item index.

## Inherited from the original (DRC exclusions to record in phase 5)

- **Socket pads overhanging the outline:** up to 0.4 mm on left SW5 and SW17, and right SW22, SW27 and SW32. The router trims them, leaving about 85% of the pad.
- **Puck courtyard:** the tenting puck's bottom courtyard overlaps the socket courtyards.

## Reproduce

```bash
"$KICAD_PY" scripts/geometry/extract.py
"$KICAD_PY" scripts/geometry/mechanical_parts.py
"$KICAD_PY" scripts/geometry/preview.py reports/phase1/preview
"$KICAD_PY" scripts/checks/geometry.py reports/phase1/preview/left.kicad_pcb --half left
scripts/render.sh reports/phase1/preview/left.kicad_pcb reports/phase1/render-left
scripts/checks/geometry_all.sh      # what CI runs
```

## Review

See `review.md`.
