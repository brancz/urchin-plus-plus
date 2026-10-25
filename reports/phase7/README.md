# Phase 7: cases and dock

Status: **done (2026-10-24).** Cases, battery covers (since replaced by top shells), dock tray and dock PCB; two reviewer passes, every finding fixed or dispositioned in `review.md`; CI run 40118268118 green, with the artifacts `dock-jlc-bundle` and `printed-parts`. Design decisions are in `docs/ARCHITECTURE.md` ("Case", "Dock", and the decision log of 2026-10-24). The parts and the hardware to buy are listed in `mech/README.md`. After the phase closed, the hardware was changed to parts sold in Germany (ARCHITECTURE.md, "Hardware bought in Germany"): the cover's posts and nylon nuts replace the standoffs, M5 washers replace the steel discs, and the checks model the largest 401730 cell sold. That change had its own reviewer pass (`review.md`, "Hardware change"); the phase's CI run above predates it. On 2026-10-25 the battery cover gave way to a top shell over each half, and the dock was redesigned before it was ordered (both below). The rows below are from those rebuilds. One reviewer pass covered both, and every finding is fixed or dispositioned in `review.md` ("Top shell and dock redesign").

## Cases and top shells

The battery cover was replaced by a top shell over each half on 2026-10-25 (the owner wanted a less DIY look; ARCHITECTURE.md, "Top shell over each half"). The rows below are from that rebuild. Its reviewer pass ran together with the dock redesign's (`review.md`, "Top shell and dock redesign").

Built by `scripts/mech/build.sh OUT` (2026-10-25):

1. kicad-cli exports each routed half as STEP.
2. `scripts/mech/board_data.py --check` confirms `mech/data/*.json` matches the boards.
3. `mech build` makes the parts, exports STEP and STL, runs every check, and renders.
4. `scripts/mech/slice.py` slices each part with Bambu Studio 02.07.01.62 for the A1 mini.

CI runs steps 1 to 3 without renders (job `mech`, artifact `printed-parts`). Since the dock was added, the same build also makes the tray and checks it (below); `checks.json` holds the case and dock rows together.

| Check | Result | Evidence |
|---|---|---|
| Fit: each printed part and each piece of hardware against the routed half's STEP, the switches and the keycaps | 104 checks (of the 155 in `checks.json`; the rest are the dock's and the jigs'), 0 failed. There is no overlap anywhere. Every gap is at least 0.25 mm, except where parts are meant to touch: the PCB on the case's standoffs and under the shell, the switches in the shell's plate, the screws in their holes, the shell 0.2 mm above the case's wall, and the tenting puck's screw heads on the PCB (0.11 mm from SW10's housing on the left, 0.13 mm from SW4's). (The PCB counts as touching everywhere, so the lips over it are checked in `hardware` instead.) Closest: the shell, moved by its 0.1 mm play on the switches, to the keycaps beside the lid 0.26 mm (nominally 0.36 mm); the shell to the battery 0.28 mm; the case to the module's 3D model 0.289 mm; the puck's screw heads to their pockets in the shell 0.3 mm. Every other keycap keeps 0.8 mm from its well. | `checks.json` → `fit` |
| Bed: every STL fits the A1 mini (180 × 180 × 180 mm) | 4 of 4 (9 of 9 with the dock and the jigs). Case 114.3 × 94.4 × 7.8 mm, shell 114.3 × 94.4 × 7.2 mm | `checks.json` → `bed` |
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

Redesigned on 2026-10-25, before it was ordered (ARCHITECTURE.md, decision log): the owner found a half hard to pick out of the deep pockets, and wants the cable to leave at the back, so the dock can sit at the far edge of a desk. The pogo pins moved onto the halves (soldered on their charging pads with a printed jig), the dock became a flat 6.6 mm slab with shallow pockets and gold contacts, and the USB-C moved to the middle of the back edge, under a printed cover. The rows below are from the redesign; the first design's are in git history (commit 64fd027).

Four parts: the dock PCB (`dock-pcb/`, one JLC order, assembled on its top), the tray (`mech/src/mech/tray.py`, two printed pieces), the cover over the PCB's parts, and a soldering jig per half (`mech/src/mech/pins.py`). The board follows the tray: `mech dock-geometry` writes its outline, magnet cutouts, and the positions of the contacts and the USB-C receptacle to `dock-pcb/geometry.json`, and `scripts/mech/build.sh` fails if that file is stale.

### Dock PCB

Parts research: `dock-parts.md` (its 2026-10-25 update covers the redesign). Circuit: `dock-pcb/dock.ato` (USB-C, power only → 0.5 A polyfuse → 5 V to the contacts; SMF6.0A TVS after the fuse; 5.1 kΩ on each CC pin; green LED at about 1 mA). The board is a U: under each half a bar with three flat ENIG contacts (3.2 × 6.0 mm, GND / 5 V / GND at the pins' 4 mm pitch) and a 12.1 mm hole for a magnet boss, an arm back along the half's inner wall, and a tab between the halves at the back with every part on it.

| Check | Result | Evidence |
|---|---|---|
| Stock (live JLC, 2026-10-25T13:57:41Z, for 5 boards) | 6 of 6 lines in stock; each has its datasheet in `docs/datasheets/`. The pogo pins are no longer on this BOM: the owner buys six loose (C5221284, 6,413 in stock at 2026-10-25T13:57:53Z) | `dock-bom.md`, `dock-bom.json` |
| Build | `scripts/ato_build.sh dock-pcb --frozen` changes nothing | CI |
| Placement | Each contact's pads sit under a half's pad centres from `geometry.json`, and J1 where it puts it, its mouth on the board's back edge. Every other part's courtyard is inside the parts area on the tab (0.8 mm from the pockets, where no case rests). No tracks or vias under J1's shell (rule area J1_SHELL, checked here and by DRC) | `dock/placement.txt` |
| Connectivity, against a netlist written from the datasheets | 28 numbered pads on their nets, LCSC number per designator, no other nets | `dock/connectivity.json` |
| Routing | All connections routed: the 5 V trunk scripted (0.5 mm: from the fuse across the tab and down each arm to the middle contact, with stubs to the TVS and the LED resistor), and the CC pull-downs' GND pads joined through a via to the bottom pour (J1's VBUS tracks box them in on the top); the rest Freerouting; GND pour on both layers; 28 tracks, 94 vias; no starved thermal | `dock/routing.json`, `dock/copper-*.svg` |
| DRC (JLC rules, zones refilled) | 0 errors, 0 unconnected. 13 warnings, dispositioned below | `dock/drc.md`, `dock/drc.json` |
| Assembly files | 7 placements, 6 BOM lines, all on the top | `dock/bom.csv`, `dock/positions.csv` |

DRC warnings:

- `silk_edge_clearance` (8): the EasyEDA outline of J1 runs to the board's edge at the notch, its two corner reliefs and the receptacle's mouth; JLC clips silkscreen at the edge.
- `silk_over_copper` (5): EasyEDA pin-1 dots and outlines touching their own pads (R1, R2, R3, F1, LED1); JLC clips silkscreen off pads.

The JLC bundle is `scripts/dock/fab.sh OUT` (also the CI artifact `dock-jlc-bundle`): Gerbers, BOM and CPL, with renders (`dock/dock-{top,bottom}.png`) and copper plots.

### JLC upload checklist: dock PCB (done by the human)

The bundle is `scripts/dock/fab.sh OUT` (or the CI artifact `dock-jlc-bundle`): `OUT/jlc/urchin-dock-gerbers.zip`, `OUT/jlc/bom.csv`, `OUT/jlc/positions.csv`. One dock serves both halves.

**PCB:**

- [ ] Upload `urchin-dock-gerbers.zip`. JLC's viewer should show one 2-layer board, 144.3 × 84.7 mm: a U, with a long bar at each lower corner carrying three gold pads and a 12.1 mm round cutout, an arm up from each bar's inner end, and a tab joining the arms at the top, with the USB-C footprint in a notch on its top edge.
- [ ] **Base material** FR-4, **2 layers**, **1.6 mm**, 1 oz copper.
- [ ] **Surface finish: ENIG.** Required: the pins press on the bare pads. (This changed with the redesign: HASL is no longer fine.)
- [ ] **Solder mask black**, as the board file's stackup says: the board shows in the pocket floors, and black disappears in a black tray. Any colour works; only the look changes.
- [ ] **Different Design: 1** (JLC's default): one board. **Delivery format: single PCB**, no panel. **Quantity 5**, JLC's minimum.
- [ ] **Remove mark / order number:** JLC's default placement is fine, as long as it isn't on the six gold pads.

**If JLC's DFM check or an engineer asks about these, they are intended:**

- **The two 12.1 mm round cutouts:** the tray's magnet bosses pass through them.
- **The notch in the tab's top edge, with a round relief behind each inner corner, and a part across it:** the USB-C receptacle (J1) is mid-mount; its body sits in the notch, its mouth flush with the board's edge. The reliefs keep the router's corner radius off the receptacle's body.
- **Plated slots with paste (J1's four shell legs):** intended pin-in-paste, so reflow solders the legs.
- **Large bare pads with no part on them (the six 3.2 × 6.0 mm contacts):** charging contacts; the halves' pogo pins press on them.
- **Silkscreen on pads or at the edge:** EasyEDA's outlines of J1 at the edge, and pin-1 marks touching pads on R1–R3, F1 and LED1. JLC clips both.

**Assembly:**

- [ ] PCB Assembly on, **assembly side: Top**. Quantity 2, JLC's minimum.
- [ ] Upload `bom.csv` and `positions.csv`: 6 BOM lines, 7 placements. The LCSC numbers must match `dock-bom.md`, with nothing "not matched".
- [ ] Choose **"Confirm parts placement"**, so JLC sends its placement for approval before production.
- [ ] In JLC's placement preview, check each part against its own pads. Positions are given in KiCad's top view, with the USB-C at the top:
  - **D1 (SMF6.0A, TVS, right of the fuse):** the cathode band is on the **left** pad, toward the fuse (5 V). Reversed, it shorts 5 V to ground: the fuse trips and the dock is dead.
  - **LED1 (green 0805, below the fuse, on the centre line):** the anode (pad 1, "+" in its datasheet) is the pad **toward R3**, on the left. Reversed, it stays dark.
  - **J1 (USB-C):** the opening faces out of the tab's top edge, its body in the notch; the four legs go into the plated slots.
  - F1 and R1–R3 have no polarity.
- [ ] Confirm the stock of C2848622 (the USB-C receptacle) at order time.

**After delivery (by hand):**

- [ ] J1: add solder to its four shell legs with an iron, as on the keyboard. The legs take the cable's forces.
- [ ] Then assemble the dock as in `mech/README.md` ("The dock").

### Tray, cover, pins and jig

| Check | Result | Evidence |
|---|---|---|
| Fit, with both cased halves seated, their pins compressed on the contacts, and the dock PCB (kicad-cli STEP, every 3D model) in its recess | 42 checks, 0 failed. Each case rests on the floor and the PCB; the pocket walls and the cover keep 0.4 mm from it; the two tray pieces meet 0.2 mm apart, and the cover sits 0.15 mm inside its recess. Every dock part keeps at least 0.3 mm from the cover (its pockets) and 0.75 mm from the tray (J1's legs in the hollow under it). The compressed pins touch only the halves' PCBs and the contacts, 1.98 mm from the case's window. A USB-C plug's overmold (12.4 × 6.5 mm) butts on the back face. J1's model, its legs on the footprint's slots, sits on the dock PCB with no overlap | `checks.json` → `fit` (rows `tray_*`, `dock*`, `* compressed`) |
| Guidance | The pockets are 2.6 mm deep with a 0.6 mm funnel. Their straight walls, less the case's 0.4 mm bottom chamfer, are 1.6 mm, above where the pins' tips meet the contacts (1.51 mm worst case), so a half is in them before it touches down | `checks.json` → `dock_pins` |
| Pin compression | 0.85 mm nominal. 0.55 to 1.15 mm by RSS of the pin's ±0.15 mm, its solder joint (0.1), the case's standoffs (0.15), the dock PCB's thickness (±0.16) and the recess depth (0.1): inside 0.2 mm to the 1.4 mm stroke. Worst case 0.19 to 1.51 mm | `checks.json` → `dock_pins` |
| Pin landing, per pin and axis | The case's and the board's play (moving and turning) solved from their outlines, plus the pin in its jig's bore (0.3), its tilt (0.16), the dock PCB on its bosses (0.25) and pocket to boss (0.1): 0.91 mm by RSS across a contact against 1.45 mm of room (the 3.2 mm pad less 0.15 mm at each edge), 0.90 mm along it against 2.85 mm. Worst case 1.89 mm across, past the 1.6 mm half-width only if every term lines up, and still short of the 1.95 mm at which a tip would reach the next contact | `checks.json` → `dock_pins` |
| The pins in the case's window | The pin is on the board, so the board's play in its case and the pin's own error move it in the window: 1.1 to 1.2 mm needed, 1.98 mm there at the least | `checks.json` → `dock_pins` |
| The board into its case, pins on | Tilted in under the lips, a pin's tip reaches the floor's top 2.7° to 3.2° from flat, up to 0.27 mm inward of its place; the window leaves at least 2.3 mm beyond it (1.27 mm needed with the board's play and MIN_GAP). The barrel's end, 0.5° from flat, needs 1.04 mm and has 1.98 mm | `checks.json` → `dock_pins` |
| The pins off the dock | Free, they stand 0.85 mm below the case's underside (1.25 mm worst case); the shortest allowed feet (2.5 mm, less their 0.4 mm seat and 0.2 mm of squash) stand 1.9 mm, so the pins stay at least 0.65 mm off the desk | `checks.json` → `dock_pins` |
| Hardware | Magnets: 0.8 mm wall round each inside the PCB's hole, 0.98 mm between the MK1 pockets and the PCB's recess; pockets 3.4 mm deep under a 0.6 mm skin (10 × 3 mm magnets). Feet: through-holes, any foot up to 4.4 mm tall docks; each foot moves at most 1.4 mm against 2.0 mm of room. Cover: at least 0.72 mm over every part (over J1; 0.6 mm needed), and its LED pinhole is clear. USB-C: J1's model, on its slots, puts its mouth on the back face and its axis 4.0 mm above the table, as `params.py` says; a plug's overmold stays 0.75 mm off the table. The opening round J1's mouth cuts 0.28 mm into the back face's top chamfer | `checks.json` → `hardware` (side `dock`) |
| Soldering jig, per half | Its plate, legs and feet keep clear of every bottom part (nearest: SW11's socket, 1.44 mm); each foot at least 1.77 mm inside the board's edge; each plunger held 1.45 mm deep in a 1.25 mm bore, its tip 0.55 mm inside the 2.0 mm plate (0.3 mm with the longest pin), each barrel 0.55 mm below the plate; of each pad's two ends past the flange, 1.24 mm² each is in view from above for the iron (at least 1.0 required) | `checks.json` → `fit` (rows `pin_jig_*`), `hardware` |
| Bed | Each tray piece 119.6 × 101.2 × 6.6 mm; the cover 25.3 × 28.4 × 2.6 mm; each jig 73.3 × 24.7 × 7.8 mm | `checks.json` → `bed` |
| Slicing (0.20 mm Standard, Bambu PLA Basic, no supports) | Each tray piece: 42 min, 27.2 g. The cover: 4 min, 1.5 g. Each jig: 6 min, 1.4 g. No slicer warnings | `slice.json` |

The play of a case in its pocket and of a board in its case is a linear program over a move and a small turn (`play.Play`): every short stretch of the outline may move outward by at most the clearance, and each locating screw by its play. On a rectangle it gives the clearance at every point, as it should.

Renders (`render/`): `tray-{iso,top,back,under}.png` (the tray with the dock PCB, and the cover from the top and back), `dock_cover-under.png`, `dock-iso.png` (with both cased halves, their shells and pins), `dock-pin-section.png` (a cut through the left half's middle pin: tray, dock PCB and contact, the compressed pin, the case's floor and window, the half's PCB), `pin_jig_{left,right}-under.png` (each jig on its board, with the pins).

None of this needed a change to the keyboard PCB.

What only a print can tell: the magnets' pull through the 0.6 mm skin on the case's M5 washers (two N52 10 × 3 mm per half against the pins' 3 to 3.5 N; dock step 6 checks it), and the pins' real free height (measure it, `mech/README.md`).
