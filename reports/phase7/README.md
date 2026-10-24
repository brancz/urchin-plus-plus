# Phase 7: cases and dock

Status: **cases and battery covers done; dock tray and dock PCB in progress.** Design decisions are in `docs/ARCHITECTURE.md` ("Case", "Dock", and the decision log of 2026-10-24). The parts and the hardware to buy are listed in `mech/README.md`.

## Cases and battery covers

Built by `scripts/mech/build.sh OUT` (2026-10-24):

1. kicad-cli exports each routed half as STEP.
2. `scripts/mech/board_data.py --check` confirms `mech/data/*.json` matches the boards.
3. `mech build` makes the parts, exports STEP and STL, runs every check, and renders.
4. `scripts/mech/slice.py` slices each part with Bambu Studio 02.07.01.62 for the A1 mini.

CI runs steps 1 to 3 without renders (job `mech`, artifact `printed-parts`).

| Check | Result | Evidence |
|---|---|---|
| Fit: each printed part and each piece of hardware against the routed half's STEP | 46 checks, 0 failed. There is no overlap anywhere. Every gap is at least 0.25 mm, except where parts are meant to touch: the PCB on its standoffs, and the cover on the case and on its standoffs. Closest: case to the module's 3D model 0.289 mm; cover to the SW17 keycap 0.8 mm; the thumb screw's washer and head to the SW17 keycap 1.24 mm. | `checks.json` → `fit` |
| Bed: every STL fits the A1 mini (180 × 180 × 180 mm) | 4 of 4 | `checks.json` → `bed` |
| Hardware: thread engagement and screw tips | M2 × 5 in the heat-set insert: 3.0 mm thread engaged, tip 0.9 mm above the hole's bottom. Nylon M2 × 8 and M2 × 3 in the 6 mm standoff: 3.0 and 2.2 mm of thread, 0.8 mm between the tips. The lower screw head sits 0.2 mm inside the case's underside. | `checks.json` → `hardware` |
| No metal in the antenna keep-out | The nearest metal is the thumb screw, washer and insert, 34.4 mm away. The steel discs are 47.3 mm away. | `checks.json` → `hardware` |
| Insertion: the board can drop into its case | J1 (USB-C) and SW35 (power switch) reach past the cavity, and both drop through full-height openings in the wall | `checks.json` → `insertion` |
| Slicing (0.20 mm Standard, Bambu PLA Basic, no supports) | Each case: 27 min, 18.3 g. Each cover: 8 min, 3.2 g. The slicer gave no warnings. | `slice.json` |

The modelled parts are what the STEP lacks:

| Part | Model |
|---|---|
| Hotswap sockets | B.CrtYd outline, 1.85 mm tall |
| Battery | courtyard, 5 mm tall |
| Switch bodies | 15 × 15 mm, 5 mm tall |
| Keycaps | 17.5 × 16.5 mm, from 2 to 8 mm above the PCB |

The keycap model is deliberately conservative: a Choc keycap pressed fully down stays well above 2 mm.

Found and fixed while checking:

- **Screws in the 3.8 mm holes between keys collided with the switches.** These holes sit 2.1 mm from a switch body, under a keycap's edge. No head or washer that could bear on a 3.8 mm hole fits there.
  - Now only the hole whose washer clears every keycap takes a screw: the one by the thumb keys.
  - Two lips on the outer wall hold that edge down.
- **The cover's top screw was too long.** An M2 × 4 would have met the M2 × 8 inside the 6 mm standoff. It is now an M2 × 3, and the stack check would catch this.
- **The board couldn't drop into the case.** The power switch's actuator reaches past the board's edge, and the wall above its slot blocked it. The slot is now open to the top of the wall, and the insertion check covers this.

None of these needed a change to the keyboard PCB.

Renders (`render/`):

- `{left,right}-assembly-{iso,top}.png`: the case, cover, PCB and parts.
- `{left,right}-{inner,outer}-edge.png`: the USB-C and power-switch openings, and the lips.
- `case_*-{iso,under}.png` and `cover_*-iso.png`: the parts alone.

## Dock

Not done yet: the tray, the dock PCB, the fit check of the cased halves on the pins, and the review.
