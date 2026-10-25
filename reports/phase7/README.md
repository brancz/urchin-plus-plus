# Phase 7: cases and dock

Status: **done (2026-10-24).** Cases, battery covers (since replaced by top shells), dock tray and dock PCB; two reviewer passes, every finding fixed or dispositioned in `review.md`; CI run 40118268118 green, with the artifacts `dock-jlc-bundle` and `printed-parts`. Design decisions are in `docs/ARCHITECTURE.md` ("Case", "Dock", and the decision log of 2026-10-24). The parts and the hardware to buy are listed in `mech/README.md`. After the phase closed, the hardware was changed to parts sold in Germany (ARCHITECTURE.md, "Hardware bought in Germany"): the cover's posts and nylon nuts replace the standoffs, M5 washers replace the steel discs, and the checks model the largest 401730 cell sold. That change had its own reviewer pass (`review.md`, "Hardware change"); the phase's CI run above predates it. On 2026-10-25 the battery cover gave way to a top shell over each half (below); the case rows below are from that rebuild, and its reviewer pass is still to come.

## Cases and top shells

The battery cover was replaced by a top shell over each half on 2026-10-25 (the owner wanted a less DIY look; ARCHITECTURE.md, "Top shell over each half"). The rows below are from that rebuild. Its reviewer pass runs together with the dock redesign that follows it.

Built by `scripts/mech/build.sh OUT` (2026-10-25):

1. kicad-cli exports each routed half as STEP.
2. `scripts/mech/board_data.py --check` confirms `mech/data/*.json` matches the boards.
3. `mech build` makes the parts, exports STEP and STL, runs every check, and renders.
4. `scripts/mech/slice.py` slices each part with Bambu Studio 02.07.01.62 for the A1 mini.

CI runs steps 1 to 3 without renders (job `mech`, artifact `printed-parts`). Since the dock was added, the same build also makes the tray and checks it (below); `checks.json` holds the case and dock rows together.

| Check | Result | Evidence |
|---|---|---|
| Fit: each printed part and each piece of hardware against the routed half's STEP, the switches and the keycaps | 104 checks (of the 141 in `checks.json`; the rest are the dock's), 0 failed. There is no overlap anywhere. Every gap is at least 0.25 mm, except where parts are meant to touch: the PCB on the case's standoffs and under the shell, the switches in the shell's plate, the screws in their holes, the shell 0.2 mm above the case's wall, and the tenting puck's screw heads on the PCB (0.11 mm from SW10's housing on the left, 0.13 mm from SW4's). (The PCB counts as touching everywhere, so the lips over it are checked in `hardware` instead.) Closest: the shell, moved by its 0.1 mm play on the switches, to the keycaps beside the lid 0.26 mm (nominally 0.36 mm); the shell to the battery 0.28 mm; the case to the module's 3D model 0.289 mm; the puck's screw heads to their pockets in the shell 0.3 mm. Every other keycap keeps 0.8 mm from its well. | `checks.json` → `fit` |
| Bed: every STL fits the A1 mini (180 × 180 × 180 mm) | 4 of 4 (6 of 6 with the tray). Case 114.3 × 94.4 × 7.8 mm, shell 114.3 × 94.4 × 7.2 mm | `checks.json` → `bed` |
| Hardware: thread engagement and screw tips | Two steel M2 × 8 per half, from below through the case's standoff and the PCB into a 1.7 mm pilot in the shell: 2.84 mm of thread with a board 0.16 mm thick, the tip 0.44 mm above the pilot's end with a board 0.16 mm thin, the head 0.2 mm inside the case's underside. At least 1.15 mm of plastic round each pilot (1.0 mm required). The printed pins at the antenna end go 0.84 mm into the shell with a thick board and stop 0.24 mm short of their bores' ends with a thin one | `checks.json` → `hardware` |
| Lips over the board's outer edge | Underside at 7.0 mm, on a layer boundary, 0.2 mm over the PCB and 0.04 mm over one 0.16 mm too thick. A board goes in tilted up to 11° (2° if 0.16 mm thick), pushed against the outer wall. Each lip stays at least 0.38 mm over the edge by RSS (0.23 mm worst case) with the board's play in its case (up to 0.37 mm inward, solved) and JLC's ±0.2 mm outline. The shell pockets each lip with 0.3 mm round it | `checks.json` → `hardware` (rows `lip*`) |
| No metal in the antenna keep-out | The nearest metal is a tenting puck screw, 18.6 mm away (only with the puck). The shell's screws are 34.9 mm away, the steel washers 47.3 mm | `checks.json` → `hardware` |
| The largest cell on the board | Centred on BT2's outline, its end on the outline's antenna-side end: 3.75 mm from the antenna keep-out (3 mm required). It reaches 0.4 mm over the ends of the wire pads (BT1), riding on its 1 mm foam 0.2 mm above a 28 AWG wire's solder joint, and over 21 % of each LED's light hole (at most half allowed). The lid's wall between the cell and the keys is at least 0.5 mm thick everywhere (0.5 mm required) | `checks.json` → `hardware` |
| USB-C window | J1's 3D model puts the receptacle's axis 4.0 mm above the case's underside, where the case's and shell's window assume it; the shell's wall ends 0.35 mm above a 6.5 mm plug overmold | `checks.json` → `hardware` |
| Insertion: the board can drop into its case | J1 (USB-C) and SW35 (power switch) reach past the cavity, and both drop through full-height openings in the wall | `checks.json` → `insertion` |
| Slicing (0.20 mm Standard, Bambu PLA Basic, no supports) | Each case: 27 min, 18.0 g. Each shell: 54 min, 15.4 g, with ironing on its top surfaces. The shells print without warnings. The cases get one, `not_support_traditional_timelapse` (from the pins on their standoffs): Bambu Studio's "traditional timelapse may cause surface imperfections", which matters only with timelapse recording on in traditional mode (print them without it, or in smooth mode). | `slice.json` |

The modelled parts are what the STEP lacks:

| Part | Model |
|---|---|
| Hotswap sockets | B.CrtYd outline, 1.85 mm tall |
| Battery | 17.5 × 32.5 mm, centred on BT2's outline from its antenna-side end, 5.5 mm tall (a 4.5 mm cell on 1 mm foam) |
| Switches | Kailh's Choc v1 drawing (`docs/datasheets/Kailh_CPG135001D02_Choc-v1.pdf`): a 13.8 mm housing, 14.5 mm across the clips up to 1.0 mm above the PCB, a 15.0 × 0.8 mm flange whose underside is 2.2 mm above the PCB, and the housing up to 5.0 mm |
| Keycaps | 17.5 × 16.5 mm, from 2.5 to 9.5 mm above the PCB |
| Shell screws | A 4.0 × 1.6 mm pan head and a 1.6 mm shank, 8 mm long |
| Tenting puck screws | ISO 7380 button heads, 3.5 × 1.3 mm, on the PCB |

The keycap model is deliberately conservative. A Choc keycap pressed fully down stays well above 2.5 mm: it rests on the switch's stem, which travels 3 mm from 8 mm. A keycap that reached below 2.2 mm would hit every Choc plate. The top, 9.5 mm, is a 4 mm-tall MBK keycap at rest.

Found and fixed while checking:

- **Screws in the 3.8 mm holes between keys collided with the switches.** These holes sit 2.1 mm from a switch body, under a keycap's edge. No head or washer that could bear on a 3.8 mm hole fits there.
  - Now only the holes at least 2.5 mm from every keycap take a screw.
  - Two lips on the outer wall hold that edge down.
- **The cover's top screw was too long.** An M2 × 4 would have met the M2 × 8 inside the 6 mm standoff. It became an M2 × 3, and the stack check would catch this. (Since replaced twice: by an M2 × 16 through the cover's post into a nut, then by the top shell.)
- **The board couldn't drop into the case.** The power switch's actuator reaches past the board's edge, and the wall above its slot blocked it. The slot is now open to the top of the wall, and the insertion check covers this.
- **The shell's walls round its screws were too thin.** Square-cornered wells left 0.97 mm of plastic round a pilot; the wells now have round corners, and the rim stays round each screw (1.15 mm).
- **The tenting puck's pan heads hit two switches.** With the switches modelled from their drawing, a 4 mm M2 pan head under the shell overlapped SW4 and SW10. That was also true before the shell. The puck now takes 3.5 mm button heads.

None of these needed a change to the keyboard PCB.

Renders (`render/`):

- `{left,right}-assembly-{iso,top}.png`: the case, shell, switches, PCB and parts.
- `{left,right}-{inner,outer}-edge.png`: the USB-C and power-switch openings, and the seam.
- `case_*-{iso,under}.png` and `shell_*-{iso,under}.png`: the parts alone.

## Dock

Two parts: the dock PCB (`dock-pcb/`, one JLC order, assembled on its top) and the tray (`mech/src/mech/tray.py`, two printed pieces). The board follows the tray: `mech dock-geometry` writes its outline, magnet cutouts, and the positions of the pins, the USB-C receptacle and the screws to `dock-pcb/geometry.json`, and `scripts/mech/build.sh` fails if that file is stale.

### Dock PCB

Parts research: `dock-parts.md`. Circuit: `dock-pcb/dock.ato` (USB-C, power only → 0.5 A polyfuse → 5 V to the pins; SMF6.0A TVS after the fuse; 5.1 kΩ on each CC pin; green LED at about 1 mA).

| Check | Result | Evidence |
|---|---|---|
| Stock (live JLC, 2026-10-24T16:12:04Z, for 5 boards) | 7 of 7 lines in stock; each has its datasheet in `docs/datasheets/` | `dock-bom.md`, `dock-bom.json` |
| Build | `scripts/ato_build.sh dock-pcb --frozen` changes nothing | CI |
| Placement | The pins sit on the halves' pad centres from `geometry.json`, and J1 and the screw holes where it puts them. Every part's courtyard and both screw heads are inside the parts area (0.8 mm from the pockets, where no case rests). No vias under J1's shell, and no F.Cu tracks in front of its pad row (rule areas J1_SHELL and J1_FRONT, checked here and by DRC) | `dock/placement.txt` |
| Connectivity, against a netlist written from the datasheets | 28 numbered pads on their nets, LCSC number per designator, no other nets | `dock/connectivity.json` |
| Routing | All connections routed: the 5 V trunk scripted (0.5 mm, F.Cu, along the strip below the magnet cutouts), the rest Freerouting; VBUS joins A9 and B9 behind J1's pads; GND pour on both layers | `dock/routing.json`, `dock/copper-*.png` |
| DRC (JLC rules, zones refilled) | 0 errors, 0 unconnected. 11 warnings, dispositioned below | `dock/drc.md`, `dock/drc.json` |
| Assembly files | 13 placements, 7 BOM lines, all on the top | `dock/bom.csv`, `dock/positions.csv` |

DRC warnings:

- `missing_courtyard` (2): H1 and H2 are bare screw holes; the screw heads are checked as circles instead (placement, and the fit checks below).
- `silk_edge_clearance` (4): the EasyEDA outline of J1 runs to the board edge at the receptacle's mouth; JLC clips silkscreen at the edge.
- `silk_over_copper` (5): EasyEDA pin-1 dots and outlines touching their own pads (R1, R2, R3, F1, LED1); JLC clips silkscreen off pads.

The JLC bundle is `scripts/dock/fab.sh OUT` (also the CI artifact `dock-jlc-bundle`): Gerbers, BOM and CPL, with renders (`dock/dock-{top,bottom}.png`).

### JLC upload checklist: dock PCB (done by the human)

The bundle is `scripts/dock/fab.sh OUT` (or the CI artifact `dock-jlc-bundle`): `OUT/jlc/urchin-dock-gerbers.zip`, `OUT/jlc/bom.csv`, `OUT/jlc/positions.csv`. One dock serves both halves.

**PCB:**

- [ ] Upload `urchin-dock-gerbers.zip`. JLC's viewer should show one 2-layer board, 144.1 × 30.8 mm: a long bar with two 12.1 mm round cutouts and three round pads at each end, and a tab in the middle with the USB-C footprint on its front edge.
- [ ] **Base material** FR-4, **2 layers**, **1.6 mm**, 1 oz copper.
- [ ] **Surface finish:** lead-free HASL is fine; ENIG is optional. The pads carry soldered pins, not contacts.
- [ ] **Solder mask green**, JLC's default.
- [ ] **Different Design: 1** (JLC's default): one board. **Delivery format: single PCB**, no panel. **Quantity 5**, JLC's minimum.
- [ ] **Remove mark / order number:** JLC's default placement is fine.

**If JLC's DFM check or an engineer asks about these, they are intended:**

- **The two 12.1 mm round cutouts:** the tray's magnet bosses pass through them.
- **Parts at the board edge:** the USB-C receptacle's mouth (J1) is flush with the tab's front edge.
- **Plated slots with paste (J1's four shell legs):** intended pin-in-paste, so reflow solders the legs.
- **Silkscreen on pads or at the edge:** EasyEDA's outlines of J1 at the edge, and pin-1 marks touching pads on R1–R3, F1 and LED1. JLC clips both.

**Assembly:**

- [ ] PCB Assembly on, **assembly side: Top**. Quantity 2, JLC's minimum.
- [ ] Upload `bom.csv` and `positions.csv`: 7 BOM lines, 13 placements. The LCSC numbers must match `dock-bom.md`, with nothing "not matched".
- [ ] Choose **"Confirm parts placement"**, so JLC sends its placement for approval before production.
- [ ] In JLC's placement preview, check each part against its own pads. Positions are given in KiCad's top view, with the USB-C at the bottom:
  - **D1 (SMF6.0A, TVS, just above the fuse):** the cathode band is on the **left** pad, the one the wide 5 V track joins. Reversed, it shorts 5 V to ground: the fuse trips and the dock is dead.
  - **LED1 (green 0805, right of the fuse):** the anode (pad 1, "+" in its datasheet) is the pad **farther from the USB-C**. Reversed, it stays dark.
  - **J1 (USB-C):** the opening faces out of the tab's front edge; the four legs go into the plated slots.
  - **P1–P6 (pogo pins):** each centred on its round pad.
  - F1 and R1–R3 have no polarity.
- [ ] Confirm the stock of C5221284 (the pogo pins, 6 per board) at order time.

**After delivery (by hand):**

- [ ] J1: add solder to its four shell legs with an iron, as on the keyboard. The legs take the cable's forces.
- [ ] Then assemble the dock as in `mech/README.md` ("The dock"), including the check of the pins' height.

### Tray

| Check | Result | Evidence |
|---|---|---|
| Fit, with both cased halves seated and the dock PCB (kicad-cli STEP, every 3D model) in its recess | 37 checks, 0 failed. Each case rests on the floor and the PCB; the pocket walls keep 0.4 mm from it and 0.54 mm from the top shell; the switches clear the walls by 4.4 mm, and the keycaps pass above them; the two tray pieces meet 0.2 mm apart. Every dock part, screw head and the USB-C plug's overmold keeps at least 0.25 mm from the tray and the cases (nearest: LED1 to the right case, 2.75 mm). The compressed pins touch only the halves' PCBs, 1.75 mm from the case window when centred | `checks.json` → `fit` (rows `tray_*`, `dock *`) |
| Pin model | The pogo pin's EasyEDA 3D model stands 6.0 mm, as its datasheet and `params.py` say | `checks.json` → `dock_pins` |
| Guidance | The pockets are 8.2 mm deep; their straight walls reach 7.0 mm, above the tallest free pin tip (6.46 mm worst case) plus the case's 0.4 mm bottom chamfer, so a half is in them before it meets the pins | `checks.json` → `dock_pins` |
| Pin compression | 0.8 mm nominal. 0.51 to 1.09 mm by RSS of the pin's ±0.15 mm, its solder joint (0.05), the PCB's thickness (±0.16), the recess depth (0.1) and the case's standoffs (0.15): inside 0.2 mm to the 1.4 mm stroke. Worst case 0.19 to 1.41 mm | `checks.json` → `dock_pins` |
| Pin landing, per pad and axis | The case's and the board's play (moving and turning) solved from their outlines: 0.69 / 0.61 mm (x / y) for the case in its pocket, 0.4 / 0.51 mm for the board in its case. With the dock PCB on its bosses (0.25), pocket to boss (0.1), the pin on its land (0.15) and its tilt (0.1): 0.86 mm by RSS across the pad, against 1.1 mm of room (the 2.5 mm pad less 0.15 mm at each edge). Worst case 1.69 mm, off the pad's 1.25 mm half-width if every term lines up; along the pad (1.85 mm of room) it stays on. In the worst case the case's window still clears the pins' flanges (1.54 mm needed, 1.75 mm there) | `checks.json` → `dock_pins` |
| Hardware | M2 × 5 through the dock PCB into an M2 × 3 insert: 3.0 mm of thread, tip 0.6 mm above the hole's bottom; 1.72 mm of printed wall round each insert. 0.8 mm wall round each magnet inside the PCB's hole; magnet pockets 6.4 mm deep under a 0.6 mm skin. Feet: through-holes, so any foot up to 7.4 mm tall docks; each foot moves at most 1.4 mm (the case's play plus 0.2 mm in its seat) against 2.0 mm of room | `checks.json` → `hardware` (side `dock`) |
| Bed | Each piece 119.6 × 101.2 × 15.2 mm | `checks.json` → `bed` |
| Slicing (0.20 mm Standard, Bambu PLA Basic, no supports) | Each piece: 56 min, 39.4 g. No slicer warnings | `slice.json` |

The play of a case in its pocket and of a board in its case is a linear program over a move and a small turn (`dock_checks.Play`): every short stretch of the outline may move outward by at most the clearance, and each locating screw by its play. On a rectangle it gives the clearance at every point, as it should.

Renders (`render/`): `tray-{iso,top,under}.png` (the tray with the dock PCB), `dock-iso.png` (with both cased halves and their shells), `dock-pin-section.png` (a cut through the left half's pins: tray, dock PCB, compressed pins, the case's floor and window, the half's PCB).

None of this needed a change to the keyboard PCB.

What only a print can tell: the magnets' pull through the 0.6 mm skin on the case's M5 washers (two N52 10 × 3 mm per half against the pins' 3 to 3.5 N; dock step 6 checks it), how hard a half is to lift out by the finger notches, and the pins' real free height (measure it, `mech/README.md`).
