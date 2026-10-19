# Phase 4 — routing

Date: 2026-10-18. Re-routed after the first phases 4–6 review, and repaired after the second one (`reports/phase5/review.md`).

## Exit criteria

| Criterion (docs/PLAN.md) | Result | Evidence |
|---|---|---|
| Fully routed boards | 0 unconnected items on both halves (KiCad connectivity) | `drc-{left,right}.json` (`unconnected: 0`) |
| DRC clean | Both halves: 0 errors against JLC's rules. 7 excused per half, all inherited from the original (`hardware/drc_allow.json`): the puck courtyard overlapping socket courtyards, and socket pads overhanging the outline. Warnings are listed below. | `drc-{left,right}.md` |
| Board-diff check clean | After routing, `scripts/ato_build.sh hardware` passes board_diff for both halves, and `ato build --frozen` changes nothing. atopile keeps every track, via and pour. | `scripts/checks/hardware_all.sh --frozen` (CI) |
| Re-checked on the routed boards | Connectivity (datasheet netlist, LCSC number per designator); clearance and antenna keep-out with the pours filled; every rule area's settings; rule 1 zero deviation. All OK. | `connectivity-*.json`, `clearance-*.json`, `geometry-*.json` |

## How the boards were routed (`scripts/routing/route.py`)

**Critical routes first** (`scripts/routing/preroutes.py`). The USB-C receptacle's D+ (A6/B6), D− (A7/B7) and VBUS pads interleave. A script joins them in the connector's own frame, fixed before routing:

- D− runs as a U under the receptacle body on the bottom layer;
- D+ and VBUS go through vias, with a top-layer link just behind the pads.

**Freerouting 2.5.0 for everything else**, GND included:

- Up to 24 variants per half: 8 signal/power width pairs × routing clearance 0.17, 0.175 or 0.18 mm. Freerouting gives the same result for the same input, so only different inputs give different routes. The design rule is 0.15 mm, and Freerouting undershoots near pads.
- The left half's routing came from a run of the first 8 variants; the right half needed variant 13.
- The routing boundary is inset 0.7 mm, for copper-to-edge clearance.
- Vias are 0.7/0.3 mm, so via holes stay 0.5 mm apart (JLC's hole-to-hole minimum).

**Every attempt is imported and counted with KiCad's own connectivity.** Freerouting's own "0 unrouted" was wrong more than once: its session can miss whole nets. The best attempt is kept (`routing-{left,right}.json`):

- **left:** 0.175/0.3 mm signal/power at 0.17 mm clearance;
- **right:** 0.127/0.3 mm at 0.175 mm, with a single-threaded optimizer. No variant at 0.17 mm routed the right half completely.

Finally, every track narrower than 0.15 mm is widened to 0.15 mm wherever KiCad's DRC allows it (`scripts/routing/widen.py`, the last step of `route.py`). On the right half that is 413 of 429 thin segments. 16 segments stay at 0.127 mm, 29 mm in total, mostly on B.Cu under the module where the clearance doesn't allow more. 0.127 mm is JLC's 2-layer minimum.

**Repairs after the second review.** The LED pads moved 0.15 mm outward for the 2.1 mm lens hole. That brought three tracks too close to them: RESET_N on the left, VDD and LED_R_K on the right.

- Freerouting's completion passes (after `route.py --ripup-drc` removed just the copper in DRC errors) couldn't close the gaps.
- So the final boards keep their routing, and `scripts/routing/joins.py` swaps exactly those segments for the replacements listed in `hardware/routing_joins.json`, each with its reason.
- `route.py --restitch` then added the stitching vias that the new rules allow under and around the module.

**After import:**

- every footprint goes back to its exact position (the session rounds to 0.1 µm, and rule 1 wants zero deviation);
- neck-downs at pads are widened to JLC's 0.127 mm minimum;
- GND is poured on both layers (0.3 mm clearance, thermal reliefs, islands removed);
- a solid-connection GND zone goes on the module side under U1;
- the pours are stitched (see below);
- ground stubs within 0.3 mm of the edge (to the edge-mounted USB-C and switch shells) are dropped where the pour keeps them connected.

**Rule areas the router respects** (`scripts/placement/place.py` draws them from U1's and J1's positions; `place.py --check` verifies their outlines and settings, and `clearance.py` the keep-out's again):

| Rule area | Layers | Forbids | Where |
|---|---|---|---|
| `ANTENNA_KEEPOUT` | both | tracks, vias, pour | the antenna section and the old notch's ears (rule 6) |
| `MODULE_CORE` | B.Cu (module side) | tracks, vias | inside the module's inner pad rows; inner pads escape through tented vias just inside the pad ring |
| `J1_SHELL` | both | vias | under the USB-C receptacle's grounded shell |

## Ground around the module (review M1)

The E73 datasheet (p.8) asks for well-grounded copper on the module side, and keeps high-frequency and power traces from under the module. What the boards have:

- **Solid ground under the module.** A GND zone on B.Cu (the module side) covers U1's courtyard grown by 1.2 mm. Its pads connect solidly, without thermal spokes, and it fills everywhere no track runs.
- **Stitching vias.** GND vias join the two pours. Candidates:
  - a 5 mm grid over the board;
  - a fence along the antenna keep-out's edge;
  - a ring around the module;
  - a 1.6 mm grid under and within 3 mm of the module.

  A via is placed only where it lies wholly inside GND copper on both layers. Islands count, because the via is what connects them. It must also be outside the via-forbidding rule areas and part bodies (the module's own body excepted) and 0.5 mm hole-to-hole from every other hole.

  | | Left | Right |
  |---|---|---|
  | GND vias in total | 185 | 180 |
  | Under the module's body | 5 | 6 |
  | Within 3 mm of it | 6 | 1 |
  | Under its RF end, centre 0.90 mm from the keep-out | 1 | 1 |

  Before the first review, the left half's top pour reached the bottom one through only 5 vias, the nearest 39 mm from the module. After it, the nearest were 3–9 mm away.
- **Nothing under the module's core** on its side (`MODULE_CORE`).
- **Nothing in the antenna keep-out** on either layer, pours included (`clearance.py`).
- **The closest signal copper to the keep-out** is a key line, KEY_R0C4. On the left, a via 0.52 mm away. On the right, the track 0.19 mm away, leaving module pin 1 sideways.

**What runs under the module, accepted** (`reports/phase5/review.md`):

- **Module side (B.Cu).** About half the area under U1 outside the keep-out is GND copper (52% left, 53% right). The rest is the module's own pads and slow-signal tracks with their clearances: keys, LEDs, SWD, reset, status sense.
- **LED_B on the right half** loops on B.Cu round the top of the inner pad column, under the module's RF end, 0.43 mm from the antenna section.
- **KEY_R0C3/KEY_R0C4 on the left half** escape inner pins 38/40 next to the RF end, and KEY_R0C4 runs on F.Cu across it about 0.8 mm from the antenna section.
- **Far layer (F.Cu).** On the left, the USB pair crosses the module, 15.5 / 14.9 mm under its body: the module's USB pins are on the column away from the receptacle. On the right, SWD crosses it.

The E73 datasheet (p.8) says high-frequency and power traces should avoid the area under the module. If they must pass, it wants them on the far layer near the module's digital part, with the module side fully poured and well grounded. The boards meet the far-layer part; the module side is half ground, not full.

A rule area keeping tracks off the module side under the RF end was tried, on both layers and on B.Cu only. Freerouting's full routes and completion passes then failed on exactly these nets, and a hand route had no room: the pad's other exits are blocked by the inner pad column and neighbouring escapes. So it was taken out.

USB here is full speed. Its edges are nanoseconds, a few hundred MHz of spectrum, and the radio is at 2.4 GHz. The other lines are static or change at keyboard rates.

| | Left | Right |
|---|---|---|
| Vias (0.7/0.3 mm), of which GND | 269, 185 | 252, 180 |
| Vias inside U1's courtyard (inner-pad escapes and stitching) | 18 | 11 |
| Module-side (B.Cu) track under U1 | 34 mm: KEY_R2C0 5.4, KEY_R1C0 4.4, GND 3.9, KEY_R1C3 3.9, KEY_T1 3.7, KEY_R0C4 2.0 mm | 48 mm: LED_B 17.1, KEY_R2C4 5.4, LED_R 5.4, KEY_R2C3 4.7, KEY_T1 3.9, GND 3.5 mm |
| Far-layer (F.Cu) track under U1, longest | USB_DN 15.5, USB_DP 14.9, KEY_T1 11.3, KEY_R2C1 8.4 mm | SWDCLK 17.1, SWDIO 16.9, LED_B 8.1, CHG_SENSE 6.0 mm |
| Track length F.Cu / B.Cu | 1236 / 958 mm | 1102 / 1166 mm |
| Track widths | 0.15 (widened neck-downs), 0.175 signal, 0.2 USB, 0.225–0.3 power and GND | 0.127 (16 at pads), 0.15 signal, 0.2 USB, 0.225–0.3 power and GND |
| USB D+ / D− length | 51.7 / 48.5 mm | 37.0 / 34.8 mm |

USB here is full speed: 12 Mb/s, 83 ns bits, rise times of several ns. Traces of about 50 mm and a few mm of length difference are far below anything that matters, so no impedance control is needed.

## Placement changes made for routing (also in the phase 3 review dispositions)

- The diodes are 1N5819WS (SOD-323) instead of B5819W (SOD-123).
- C6 (VDDH bulk) sits next to the switch's common pin, and C1 is turned so its VDD pad faces module pin 19.
- D4/D5 (sense diodes) sit next to R6/R7 by the charge LED. U3 and R11 moved 1 mm inward to make room for the USB-C vias.
- After the second review: the LED pads sit 0.15 mm further out for the 2.1 mm lens hole, C1 is 4.7 µF in the same 0402 footprint, and U2's exposed pad gets 68% paste.
- Right half only: R6/R7 swap rows (the 180°-turned LED has red and green the other way up), and module pins 1/2 carry keys (decision log).

## DRC warnings (not errors)

| Type | Left | Right | Disposition |
|---|---|---|---|
| silk_over_copper | 72 | 71 | EasyEDA footprints draw silkscreen over their own pads; JLC clips silkscreen at pads |
| silk_overlap | 50 | 59 | silkscreen outlines of neighbouring parts touching; cosmetic |
| missing_courtyard | 7 | 7 | the original case-hole footprints have none (rule 1) |
| silk_edge_clearance | 5 | 5 | the original key footprints' silkscreen near the outline (rule 1) |
| connection_width | 1 | 13 | below the 0.15 mm minimum connection width. Right: the 0.127 mm segments that couldn't be widened (JLC's 2-layer minimum is 0.127 mm). Left: the VSYS track meeting SW35 pad 1 at an angle (0.016 mm reported); the 0.3 mm segment from the pad centre carries the connection |
| starved_thermal | 1 | 0 | a GND pad with fewer than two thermal spokes; it also has a routed GND track |

The bottom designators are mirrored so they read correctly from below, and set to 1.0 mm text with a 0.15 mm stroke. The small passives' designators are hidden (`scripts/placement/silk.py`).

## Images

- `copper-{left,right}-{F_Cu,B_Cu,both}.png`: copper, top view.
- `render-{left,right}-{top,bottom}.png`: 3D renders.
