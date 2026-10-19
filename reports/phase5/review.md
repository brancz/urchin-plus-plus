# Phases 4–6 reviews: findings and dispositions

Three reviewer passes. Each checked the previous one's dispositions against the artifacts and added its own findings.

## First review

The reviewer subagent reviewed the phase 4–6 working tree on 2026-10-18 (worktree `urchin++-p4`, before the fixes below), using artifacts and datasheets only. It:

- rebuilt the JLC bundle from a scratch copy: BOM and CPL byte-identical, Gerbers pixel-identical;
- re-ran the geometry, connectivity, clearance and DRC checks on copies;
- wrote its own checks: net extraction, via-to-pad distances, GND islands and layer bridges, copper under J1/U1/SW35, a Gerber rasterisation of the keep-out, and the panel outline against the halves.

Scratch material is in `scratch/review4/` of that worktree.

It confirmed, with no findings:

- **Every pin against the datasheets** on both routed boards: U1 (all 43, including the bottom-view chirality), U2, U3, J1, D1–D5, LED1/LED2, SW35, SW36 and the passives. This covers the power path, the charger configuration, the USB pair and ESD, module power, reset and SWD. No shorts, and the scripted USB-C joins connect the right pins.
- **Rule 6:** no copper inside the antenna keep-out on either layer of either half, in the Gerbers actually uploaded.
- **Rules 1 and 2:** zero deviation on both halves; all 60 placements on the bottom; paste only on assembled pads.
- **JLC 2-layer limits:** tracks, clearance, vias (tented, no via-in-pad), holes, copper-to-edge apart from the 5 inherited socket pads, and plating.
- **BOM/CPL** consistency. The CPL rotation convention, (180° − KiCad angle) with Y negated, matches KiKit's `MirrorBottom` and EasyEDA's bottom-side flip. It traced pin 1 of U1, U2, U3, the diodes, J1 and SW35 through it.

No high-severity findings.

| # | Finding | Disposition |
|---|---|---|
| M1 | The module's ground was weak. The top pour joined the bottom one through 5 vias, the nearest 39 mm from U1. The module's GND pads had thermal spokes. Signal tracks ran on the module side under the module, and a key trace crossed the module's RF end 1.1 mm from the antenna section. | **Partly fixed, rest accepted.** This disposition was corrected after the second review (its M1 and M2); see "M1 in numbers" below.<br>**Fixed:**<br>– a solid-connection GND zone on B.Cu under U1;<br>– GND stitching under and around the module, so 5–6 vias sit under its body on each half.<br>**Accepted:**<br>– slow-signal tracks under the module on its side;<br>– on the left, the USB pair crossing under the module on the far layer;<br>– on the right, LED_B on the module side under the RF end;<br>– on the left, KEY_R0C4 on the far layer under the RF end.<br>A rule area keeping that region clear was tried and could not be routed. |
| M2 | J1 and SW35 reach about 1 mm past the panel's short edges, which had no rail. | **Fixed.** The panel has a 5 mm frame on all four sides (`hardware/panel.json`). Each half has seven tabs (`scripts/fab/panel_layout.py`): two to the top frame, two to the bottom, the original two across the gap, and one to the side frame beside the antenna, where the keep-out keeps copper away from the mouse bites. |
| M3 | J1's four through-hole shell legs had no solder paste, so reflow wouldn't solder them. | **Fixed.** The legs have bottom paste apertures (pin-in-paste; `paste_pads` in `hardware/parts.json`), checked in the paste Gerber. |
| M4 | The JLC checklist was wrong in places (1 design; "a uniform 180°" correction; tooling-hole and fiducial counts) and missed DFM answers, "Confirm parts placement", the LED pin-1 positions and the solder-mask colour. | **Fixed.** The checklist in `reports/phase6/README.md` is rewritten with each of these. |
| L1 | Tracks and vias ran under J1's grounded shell on the component layer. | **Fixed for vias.** The rule area `J1_SHELL` (J1's courtyard, both layers) forbids vias. Tracks may still pass under the shell, insulated by solder mask; they carry slow signals. |
| L2 | The panel outline wasn't exactly the original: mill radius 1 mm against 0.5/0.75 mm corners, arc polygonisation up to 0.026 mm, and mouse-bite nubs. Nothing checked the panel's outline. | **Fixed.** Mill radius is 0.5 mm, the original's smallest inside corner. KiKit's arc approximation is replaced by one within 0.5 µm, and arc reconstruction, which re-fit arcs up to 0.012 mm off, is off. Mouse bites sit 0.1 mm inside the edge. The new `scripts/checks/panel_outline.py` (run by `scripts/fab/build.sh`) samples every half's outline every 0.1 mm against the panel's: worst 1.5 µm, outside the tab zones. |
| L3 | Silkscreen text was 0.8 mm / 0.12 mm against JLC's 1.0 / 0.15 mm guidance. 30 silk lines were 0.06 mm. The right half's BT2 designator was off the board. | **Fixed / accepted.** Designators and custom-part labels are 1.0 mm with a 0.15 mm stroke. The custom parts' outlines are 0.15 mm. The BT designators are hidden. **Accepted:** the 0.06 mm items are dots of r = 0.03 mm, EasyEDA markers inside JLC's own footprints; JLC drops what it can't print. The original key and puck footprints keep their 0.12 mm lines (the original was built at JLC with them). |
| L4 | PLAN status out of date; the decision log said four width variants; the phase 4 README implied ground under the whole module side; bring-up expected "3V3"; BAT toggles without a battery. | **Fixed.** PLAN status and bring-up step 2 are updated. The decision log has a phases 4–6 entry: 24 routing variants (8 widths × 3 clearances), track widening, module ground, `J1_SHELL`, pin-in-paste, panel and silkscreen. The phase 4 README is rewritten. |

## M1 in numbers (final boards)

| | Left | Right |
|---|---|---|
| GND vias in total | 185 | 180 |
| GND vias under U1's body / within 3 mm of it / under its RF end | 5 / 6 / 1 | 6 / 1 / 1 |
| Module GND pads | solid connection (`GND_MODULE` zone) | solid connection |
| GND copper on the module side under U1, outside the keep-out | 52% | 53% |
| Module-side (B.Cu) track under U1 | 34 mm: keys, one LED line | 48 mm: LEDs (LED_B 17 mm, round the RF end 0.43 mm from the antenna section), keys, reset, charge sense |
| Far-layer (F.Cu) track under U1 | USB_DN 15.5 mm, USB_DP 14.9 mm, keys, LED_G, PGOOD_SENSE | SWDCLK 17.1, SWDIO 16.9 mm, LEDs, charge sense, reset |
| Closest signal copper to the antenna keep-out | 0.52 mm (KEY_R0C4 via) | 0.19 mm (KEY_R0C4 leaving pin 1 sideways) |

**Why the rest is accepted.**

- The E73 datasheet (p.8) asks high-frequency and power traces to avoid the area under the module. If they must pass, they go on the far layer near the module's digital part, with the module side fully poured and well grounded.
- The only high-frequency signal under a module is the left half's full-speed USB pair, on the far layer. Its nanosecond edges carry a few hundred MHz of spectrum, against the radio's 2.4 GHz.
- The module side is about half ground, not full: the module's own pads take part of it, and slow-signal tracks with their clearances the rest.
- The lines under the RF end (LED_B, KEY_R0C3/4) are static or change at keyboard rates.
- Clearing that region was tried twice:
  - a rule area on both layers, and on the module side only;
  - Freerouting's completion passes and a hand route.

  Those nets have no other way out: the inner pad column and the neighbouring escapes block it. So the remaining risk is reduced range, not a board that doesn't work.

Details and evidence are in `reports/phase4/README.md`.

## Second review

The reviewer subagent re-reviewed the fixed tree on 2026-10-18 from artifacts and datasheets only. It:

- rebuilt the bundle and found BOM/CPL byte-identical and Gerbers pixel-identical;
- re-ran all checks;
- checked each first-review disposition;
- re-checked every pin against the datasheets.

It found no high-severity issues. Scratch material is in `scratch/review5/` of that worktree.

| # | Finding | Disposition |
|---|---|---|
| M1 | The stitching fence and ring claimed for the first review's M1 weren't on either board: every candidate was rejected, leaving no GND via within 3 mm of the module, and nothing reported the count. | **Fixed.** `stitch()` now allows GND vias under the module's body (what its datasheet wants there) and adds a 1.6 mm grid under and around it. It also tests candidates against the pours filled without island removal: under the module the top pour is islands between far-layer tracks, which a via connects. The boards were restitched (`route.py --restitch`); the counts are in the table above and in `routing-*.json`. |
| M2 | The M1 acceptance rested on a wrong fact (USB does run under the left module, on the far layer), the datasheet's fallback (module side fully poured) isn't met, and LED_B loops on the module side under the right module's RF end, 0.43 mm from the antenna section. | **Corrected and accepted.** The table and the acceptance above now state these facts. Re-routing LED_B and KEY_R0C3/4 away from the RF end was tried and failed (see above). |
| M3 | The LED lens (1.4 × 1.25 mm, diagonal 1.88 mm) doesn't fit the 1.8 mm hole. | **Fixed.** The hole is the datasheet's 2.1 mm. The pads moved 0.15 mm outward (centres x ±1.70), keeping 0.265 mm hole-to-copper and 0.3 mm of overlap with the LED's end terminals (`hardware/parts.json`). The three tracks that ended up too close were repaired (`route.py --ripup-drc`, `scripts/routing/joins.py` with `hardware/routing_joins.json`). The drill file has four 2.1 mm holes. |
| M4 | KiKit's zone refill dropped a 21 mm² piece of the right half's top pour beside the antenna end: the side tab's mouse bites cut its only link. DRC can't see it. | **Fixed.** The side tab moved into the antenna keep-out's stretch of edge and narrowed to 3 mm, so its mouse bites stay 0.5 mm from any copper. The new `scripts/checks/panel_fills.py`, run by `fab/build.sh`, compares the panel's GND pours with the halves'. It now finds 0.001 mm² missing per layer, away from the mouse bites; before the fix it found 20.95 mm². |
| L1 | J1's pin-in-paste apertures equal the pads, so the legs get only about 10% barrel fill. | **Accepted, mitigated.** Overprinting isn't safe: the leg pads are 0.23 mm from the receptacle's SMD pins. The checklist adds a step after delivery: solder J1's four legs by hand, alongside the hotswap sockets. |
| L2 | U2's exposed pad gets 100% paste. | **Fixed.** A new `paste_margin` fixup shrinks it 0.15 mm per side, to 68% coverage, as in TI's example stencil (BQ24073 datasheet p.41). |
| L3 | VDD has only C1 (100 nF), and the module's own VDD capacitor can't be confirmed from the datasheet. | **Fixed.** C1 is 4.7 µF (C23733, 0402, basic part, 2.1 M in stock) in the same footprint. Datasheet: `docs/datasheets/C23733_C0402_4u7_10V.pdf`. |
| L4 | The battery reads full while charging (VDDH sits at the charger's regulated 4.4 V output). | **Accepted, for phase 8.** The firmware should treat readings while PGOOD is low (input present) as "charging", not as the cell's voltage. |
| L5 | The 0.127 mm segments are longer than "at pads" (29 mm on the right half). | **Fixed in the report.** The phase 4 README gives the true figure. 0.127 mm is JLC's 2-layer minimum. |
| L6 | The side tab sits about 1.5 mm from U1's corner pads. | **Accepted, noted.** The tab moved up into the keep-out stretch (M4), and the nearest pads are unconnected. The checklist asks for care when snapping the side tabs. |
| L7 | Checklist and doc inaccuracies: panel size including the outline stroke; "14 tabs" shows as 12 bridges; suffixed designators on the silkscreen; this file promised a second review; ARCHITECTURE open items still listed the phase 6 items; the left half was routed with 8 variants, not 24; no 3D models in the panel renders. | **Fixed.** Each is corrected in `reports/phase6/README.md`, ARCHITECTURE.md (open items) or the phase 4 README. The panel renders are of bare boards; the halves' renders in `reports/phase4/` show the parts. |

## Third review

The reviewer subagent re-reviewed the tree after the second-review fixes on 2026-10-18, using artifacts and datasheets only. It:

- ran `hardware_all.sh --frozen` and `geometry_all.sh`, both passing;
- rebuilt the bundle: BOM/CPL byte-identical, Gerbers raster-identical apart from a 0.09 mm² refill sliver;
- checked the joins, vias, tenting, keep-out and pours with its own scripts;
- re-checked U1, U2, the LEDs, C1 and U3 against their datasheets.

It confirmed every second-review disposition and agreed with the M1/M2 acceptance. It found no high-severity issues and judged the bundle ready for fabrication and assembly once M1 below was dealt with. Scratch material is in `scratch/review6/` of that worktree.

| # | Finding | Disposition |
|---|---|---|
| M1 | The side tab's top mouse bite left 0.59 mm of board to the 2.2 mm case hole in the ear (H8 left, H2 right), so snapping could crack the ear. Nothing checked it. | **Fixed.** The side tab is 2 mm wide at y 40.9, so its bites run from y 39.4 to 42.4 and leave 0.95 mm to the hole. `panel_outline.py` now fails if any mouse bite leaves less than 0.8 mm of board to any hole. The checklist also says to snap that tab gently or cut it. |
| L1 | Committing: untracked files the build needs, the `reference` symlink not covered by `.gitignore`, and the board-history trap if staged and unstaged changes go in separate commits. | **Fixed.** `.gitignore` also ignores `/reference`. Everything goes in one commit with all new files. |
| L2 | The left half's connection_width warning was misexplained. | **Fixed.** The phase 4 README now names the VSYS track at SW35 pad 1. |
| L3 | The documented repair steps listed `--ripup-drc` before `joins.py`, which can't be replayed. | **Fixed.** `routing-*.json`, the phase 4 README and the decision log now say the final boards got only the joins; `--ripup-drc` was used for the completion attempts. |
| L4 | ARCHITECTURE said J1 needs no hand soldering, contradicting the checklist. | **Fixed.** The second-review entry supersedes it. |
| L5 | After the LED pad move, silkscreen and the EasyEDA courtyard (±1.6 × ±0.63 mm) no longer match the pads (to ±2.1 mm). | **Accepted.** Cosmetic: JLC clips silkscreen at pads, the clearance checks use the pads themselves, and the checklist gives LED pin 1 by coordinates. |
| L6 | JLC's preview will overlay its C409782 footprint (pads ±1.45 mm, no hole) on our pads at ±1.70 mm; EasyEDA calls the part MHT150RGBCT. | **Fixed in the checklist.** It says the offset is intended and to confirm the MPN MHT151RGBCT on JLC's part page. |
| L7 | The lens has 0.11 mm of radial margin in the 2.1 mm hole. | **Accepted.** It is the datasheet's own hole, and larger pads-to-hole spacing would cost terminal overlap. |
| L8 | C1's effective capacitance at 3 V is below 4.7 µF (0402 X5R DC bias). | **Accepted.** Still an order of magnitude above the 100 nF it replaced. |
| L9 | `panel_fills.py` only checked for missing copper. | **Fixed.** It also fails on more than 1 mm² of extra GND copper per layer, or any inside the antenna keep-out. Measured: 0.37 mm² extra per layer (edge slivers), none in the keep-out. |
| L10 | Stale numbers: the RF-end via is 0.90 mm from the keep-out; the corner pads are now about 1.8 mm from the side tab; leftover `fp-lib-table` entries. | **Fixed** in the README and checklist. The `fp-lib-table` entries are atopile's and harmless. |
