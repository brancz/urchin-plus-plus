# Phase 3 — placement

Date: 2026-10-18.

## Exit criteria

| Criterion (docs/PLAN.md) | Result | Evidence |
|---|---|---|
| Placement renders (top, bottom, 3D) | Both halves, 3D (with part models) and 2D (copper, silkscreen, courtyards, fab; bottom seen from below) | `render-{left,right}-{top,bottom}.png`, `placement-{left,right}-{top,bottom}.png` |
| Keep-out check | `scripts/checks/clearance.py` checks the antenna keep-out on both halves: no copper pad, track, via or zone fill, no part but U1, and no battery inside it. Both: OK. | `clearance-{left,right}.json` |
| Clearance report | `clearance.py`: part-to-part ≥ 0.25 mm on each side, ≥ 0.3 mm to holes and the outline, nothing under the tenting puck, rule 2 sides. Smallest gap 0.31 mm on both halves. KiCad DRC with JLC rules: 0 errors; the 7 (left) / 7 (right) excused errors are the two inherited ones in `hardware/drc_allow.json`. | `clearance-*.json`, `drc-*.json`, `drc-*.md` |
| Rule 1 on the real boards | Zero deviation: 17 switches, puck, 7 case holes, 129 pads, 29 edge primitives per half | `geometry-{left,right}.json` |
| Review | | `review.md` |

All of it runs in CI through `scripts/checks/hardware_all.sh` (`--frozen` build, placement check, connectivity, clearance, DRC) and `scripts/checks/geometry_all.sh`.

## How placement works

- `hardware/placement.json` places every electronic and mechanical-outline part of the **left** half, in the original board's coordinates. The right half is its mirror image: x' = 2 × 128.397 − x, rotation' = −rotation. Footprints are never flipped: every assembled part's library footprint is already bottom-side.
- Keys, the tenting puck and the case holes come from `hardware/geometry/urchin.json` (rule 1).
- `scripts/placement/place.py` writes the positions, the outline and the antenna keep-out rule area into each board. `--check` (in CI) fails if anything has drifted from the two source files.
- Positions survive `ato build`: a build after placement changes nothing (`board_diff` OK, `--frozen` OK).
- `scripts/placement/board_setup.py` writes the JLC design rules and net classes into each `.kicad_pro`.

## The controller area (left half, bottom; right half mirrored)

Coordinates are the left half's, in mm.

| Part | Where | Why |
|---|---|---|
| U1 E73 module | (229.81, 50.83), antenna end on the notch edge (y = 39.85) | Antenna at the board edge with nothing beyond it (ARCHITECTURE.md decision log) |
| SW35 slide switch | inner edge, y ≈ 62.6, lever 1.4 mm past the edge | Body 0.45 mm inside the edge so its shell tabs keep 0.3 mm copper-to-edge |
| J1 USB-C | inner edge, y ≈ 72.3, shell 1.0 mm past the edge | Per the HRO drawing's PCB-edge line. Shell legs are 1.01 mm long, shorter than the 1.6 mm board, so nothing pokes through under the battery |
| U2 charger + C2/C3/C4, R1/R4/R5 | below the module | Short power loops; OUT toward the switch, IN toward D1 |
| U3 ESD, D1, C5, R2/R3 | between U2 and J1 | ESD and CC resistors next to the connector |
| C1 (VDD), C6 (VDDH) | right under module pins 19 and 23 | Decoupling at the pins |
| D4/D5 (CHG/PGOOD sense) | under the module's bottom-left corner | |
| LED1 (status), LED2 (charge) | y = 80, below the battery, reverse-mounted under 2.1 mm holes | Visible from the top between the battery and the thumb keys |
| BT1 battery pads (top) | between the two LED holes | The cell's wires end here |
| SW36 reset | y = 83.6 | Pressed from below. The dock tray needs a relief there (phase 7) |
| TP2 SWD pads | left of the block, y = 74.4 | Reachable with pogo clips or by soldering wires |

**Antenna keep-out** (`ANTENNA_KEEPOUT`): the module's antenna end, from its edge to 0.06 mm short of the first pad row (module-local y −10.98 to −7.58), widened to ±9.4 mm (the notch's ears) and extended 5 mm past the board edge. It is a board-level rule area on both copper layers that forbids tracks, vias and copper pour. Pads are allowed only so that the two non-plated case holes in the ears pass. `clearance.py` rejects any copper pad, track, fill or part inside it.

## Top side

- Only keys and the battery are on top (rule 2, checked).
- The cell is a **401730** protected LiPo: 4.0 × 17 × 30 mm, about 180 mAh. Its outline (`BT2`) sits over the module body, below the keep-out (3.5 mm clear of it), and fills the old controller area from y = 46.75 to 77.25.
- Fix the cell with 1 mm double-sided foam tape. It covers J1's and SW35's through-hole joints, which don't protrude.

## Bottom space

- **Tenting puck:** no bottom part is inside its 20.55 mm courtyard (checked), so the puck sits flat.
- **Charging pads:** TP1 is at (178, 85), bottom centre, outside the puck. D2 and D3 sit next to it. Two 10 mm steel-disc positions (MK1, MK2) flank it for the dock magnets.
- **Sockets:** keys' socket pads and holes count as obstacles in every check.
- **Rubber feet:** four 6 mm positions (MK3–MK6) near the corners; a free-space search found nothing wider there. Feet must be at least 3.5 mm tall. The tallest bottom parts are the USB-C receptacle (3.26 mm, at the edge), the module (3.0 mm) and the sockets (1.85 mm).

## DRC warnings (not errors), to clean up in phase 4/5

- Silkscreen overlaps and silkscreen over copper (EasyEDA footprints, designators).
- Back-side text that isn't mirrored (designators that atopile places).
- Case holes without a courtyard (inherited).
