# Phase 3 review: findings and dispositions

The reviewer subagent checked commit 9f1a638 on 2026-10-18, using artifacts and datasheets only. It ran the CI checks on a copy, 22 mutation tests against `place.py --check`, `clearance.py` and `drc.py`, and an independent spacing check with shapely. Scratch material is in `scratch/review3/` of that worktree.

It confirmed against the datasheets:

- the module footprint (every p.5 dimension within 0.01 mm), its orientation and antenna end on both halves
- the keep-out position
- the USB-C and slide-switch orientation and pin order
- the LED land pattern and pin order
- the U2/U3 pin order
- rules 1 and 2 on both halves
- the mechanical clearances: puck, feet, discs, reset and SWD access

The fixes are in the commits after 9f1a638 ("Address phase 2 review …" and "Phase 4 …").

| # | Finding | Disposition |
|---|---|---|
| H1 | The rule-6 check could be bypassed. The keep-out's settings were never checked. Tracks crossing the zone without an endpoint inside passed. The overlap test missed crossing shapes. A compliant ground pour would be flagged. Fills weren't refreshed. | **Fixed.** `place.py --check` asserts each rule area's layers and forbid settings. `clearance.py` asserts them again. It tests overlap by edge intersection (crossing bars and a track through a zone now measure 0). It measures each pour's fill inside the keep-out by intersection area, after a fresh fill. `drc.py` refills zones on its copy before running KiCad's DRC. Re-run: a GND track through the zone fails, and a compliant GND pour next to it passes. |
| M1 | The LED holes were 0.117 mm from the LED pads, against the 0.25 mm hole-to-copper rule, and no check covered a footprint's own hole. | **Fixed.** The hole is 1.8 mm (0.25 mm to the pads; the 1.4 mm lens still clears it by 0.2 mm per side), recorded with its reason in `hardware/parts.json`. `clearance.py` now checks every footprint's own non-plated holes against its own copper. |
| M2 | The edge-clearance allow-list (`SW*`) also excused SW35/SW36. Keys shared pad UUIDs, so KiCad's DRC named the wrong key. | **Fixed.** The allow-list names the overhanging sockets per half (left SW5, SW17; right SW22, SW27, SW32). The puck rule requires H1 to be involved. The libraries carry no item UUIDs any more. `scripts/placement/unique_uuids.py` repaired the boards (743 duplicates per half), and the guardrail rejects duplicate UUIDs. For J1 and SW35, `clearance.py` lets only the body pass the edge; their copper pads must stay 0.3 mm inside. |
| M3 | The 3D models of U1, J1 and SW35 were offset, and the LED model was normal-mount. | **Fixed.** Model offsets and rotation are in `hardware/parts.json` (`model`) and applied by the import. Checked by exporting STEP: U1 body y 39.85–57.85, J1 front face on its courtyard front, SW35 lever tip on the courtyard end, LED body below the board with the lens up. |
| M4 | 3.5 mm feet don't clear a plugged-in USB-C overmold. | **Accepted, documented.** USB is for flashing and charging; with a cable in, the half may rest on the plug. For wired typing, use feet at least 5 mm tall (phase 6 checklist). |
| M5 | Routing around the module will be hard: the left USB pair, inner pads, and the channel next to the keys. | **Addressed in phase 4.** Both halves route completely. A rule area keeps tracks and vias out of B.Cu under the module's core (datasheet p.8). Inner pads escape through tented vias just inside the pad ring. |
| M6 | PLAN.md marked phase 3 done and gate 2 passed before this review existed. | **Fixed.** PLAN.md is updated only after this file. |
| L1 | Doc numbers: the lever protrudes 1.0 mm, not 1.4. J1's front face is 1.01 mm past the edge, while the drawing implies 0.48. The keep-out stops 0.12 mm short of the pad copper. | **Fixed** in the README. J1 stays where it is: the extra 0.5 mm overhang is harmless (front slots keep 0.71 mm copper-to-edge). Moving it inward would crowd C5/R11. |
| L2 | The 1.0 mm lever on the bottom face is hard to reach in an enclosure. | **Accepted, documented.** Caseless use. A case (out of scope) needs a lever slot. |
| L3 | Metal near the antenna: the battery at 3.48 mm (opposite face), keys at 1.6 mm, case screws in the keep-out. | **Fixed/accepted.** `clearance.py` requires 3 mm between battery and keep-out, and no key may reach into it. The keys' switch housings are plastic; the 1.6 mm figure is the socket area. Nylon screws for the ear holes are in the README and go into the phase 6 checklist. |
| L4 | SW35's footprint was typed through-hole although all its pads are SMD. | **Fixed.** The import marks a footprint without plated through-hole pads as SMD. |
| L5 | Mirroring with rot' = −rot reverses the pin order of two-terminal parts on the right half. | **Fixed.** The default is rot' = 180 − rot, which mirrors pin order. The module, USB-C, switch, pads and markers override it (`rot_right`). |
| L6 | The right half's outline sits 0.032 mm off an exact mirror. | **Accepted.** That is the original's geometry (rule 1). |
| L7 | The battery outline was 0.32 mm from the inner edge, inside cell tolerance. | **Fixed.** The outline moved 0.4 mm inward (0.75 mm clear). |
