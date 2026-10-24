# urchin++ architecture

The decisions below were made deliberately. Change one only with a reason, and record the change in the decision log at the end.

## Keyboard (per half, left and right)

**Layout.** The original Urchin geometry: 17 keys per half, Kailh Choc v1 switches in Kailh Choc hotswap sockets, Choc spacing. Extracted by script from `reference/urchin/main.kicad_pcb`, including the board outline and the tenting-puck mount (`Tenting_Puck2_no_pads`), so existing tenting accessories stay compatible.

**Wiring.** Direct pin: every key gets its own GPIO. No diode matrix, no diodes. ZMK's direct kscan is interrupt-driven, which keeps idle power low.

**Board sides.** All SMD parts are on the bottom, alongside the hotswap sockets, so JLC assembles one side only. The top carries switches and the battery. Left and right are separate layouts (the original is a panel of two separate halves; one-sided bottom assembly rules out mirroring a layout), but they share one circuit definition and are panelized together into one order.

**MCU.** Ebyte E73-2G4M08S1C, a pre-certified nRF52840 module, so there's no RF matching to verify. Fallback if out of stock: Holyiot 18010. The module sits on the bottom in the old nice!nano area with its antenna end on the board edge, in the notch where the nice!nano's USB port was (both halves, same orientation). The keep-out applies on every layer: no copper, traces, parts, or battery inside it. The module has no 32 kHz crystal, so the internal RC oscillator is used; configure ZMK and the bootloader to match.

**GPIO map.** Each half has its own key-to-GPIO map, because the module isn't mirrored but the key layout is: `scripts/circuit/gen_halves.py` assigns the 17 keys and the five GPIO functions (status LED R/G/B, CHG and PGOOD sense) to free module pads by shortest total path around the module (`hardware/pinmap.json`), and writes the per-half wiring (`hardware/halves.ato`). The shared circuit is `hardware/core.ato`.

**Power path.**

```
USB-C VBUS ──Schottky──┐
                        ├──> BQ24073 IN ── OUT ──[slide switch]──> nRF52840 VDDH
dock pads 5V ─TVS─Schottky┘           └── BAT ── protected LiPo
```

- **Charger: TI BQ24073** (was BQ24075; see the decision log). Power-path type (the system runs from the input supply while charging). Input rated to 28 V with 6.6 V overvoltage shutdown. On the exposed dock pad an SMF6.0A TVS clamps ESD and transients; a sustained source above about 7 V would destroy the TVS (it fails short, protecting the rest). USB100 mode: the input is limited to about 95 mA, so a ~200 mAh cell charges at about 0.45C. The status (CHG) and power-good (PGOOD) pins go to GPIOs so firmware knows the charging state.
- **The diodes** make the pads input-only. A 10 kΩ pull-down holds USB VBUS low while docked (D1 leaks back from VIN), so a docked half isn't seen as USB-connected. A metal surface across the pads can't drain or short the battery.
- **Switch placement** between the charger output and VDDH, so the battery still charges while the board is switched off.
- **No external regulator.** The battery drives the nRF52840's high-voltage input (VDDH) directly, following the module datasheet's reference circuit.
- **No battery divider.** ZMK's `zmk,battery-nrf-vddh` driver measures the voltage internally, so there's no leakage path.

**Battery.** A protected 401730 LiPo (4.0 × 17 × 30 mm, about 180 mAh), the largest cell that fits the old nice!nano area on top below the antenna keep-out. Wires are soldered to pads (BT1), no JST connector, to save height. It sits on 1 mm foam tape.

**USB-C.** On the bottom at the inner board edge, below the power switch (the old nice!nano port position now holds the antenna; see the decision log). 5.1 kΩ CC pull-down resistors, a USBLC6-2 for ESD on D+/D- and VBUS. Used for flashing; it also charges. Only USB VBUS reaches the nRF52840's VBUS pin, so a docked half doesn't look USB-connected to the firmware.

**Indicators.**
- Status: a plain (non-addressable) RGB LED, reverse-mounted on the bottom and shining up through a hole, driven by GPIOs via `zmk-rgbled-widget`. It blinks battery level on wake and connection state on profile changes, then stays dark.
- Charge: a second LED of the same type, powered from the charger input (zero battery cost): red on CHG, green on PGOOD, so amber = charging, green = charged.
- Fallback if reverse-mount parts aren't stocked: side-view LEDs at the inner board edge.

**Programming and reset.**
- A reset button; double-tap enters the UF2 bootloader.
- SWD pads (VDD, SWDIO, SWDCLK, RESET, GND) at 2.54 mm pitch for the one-time bootloader flash. Use a probe that follows the target voltage on VTref (e.g. a J-Link) with pyOCD, which can also unlock APPROTECT if a module ships locked: a blank module runs its I/O at 1.8 V (decision log).

**Charging contacts.** Three ENIG pads on the bottom (GND / 5V / GND, symmetric) in a gap between sockets near the electronics. Thin steel discs are stuck to the bottom for the dock magnets. Rubber feet sit taller than the tallest bottom component (for the bare board; in the printed case they go on the case's underside, see the 2026-10-24 dock entry).

**PCB.** 2 layers, 1.6 mm, ENIG finish (required for the pads).

## Dock

- **The halves dock in their cases** (owner's choice, 2026-10-24). The tray's pockets fit the case outline. The case floor has a window over each half's charging pads (TP1), and the steel discs sit in recesses on the case's underside at MK1/MK2.
- **Dock PCB:** one long, thin board under a tray for both halves. USB-C input in the middle (CC resistors, polyfuse, TVS, power LED), SMD pogo pins at each end. The pins stand on the board's top, which lies flush with the pocket floor, and reach each half's pads through the case's window. It is assembled on its top (the keyboard's rule 2 is about the halves), its own small JLC order built by the same pipeline (`dock-pcb/`, `scripts/dock/`). The board follows the tray: `mech dock-geometry` writes its outline, magnet cutouts and the positions of the pins, the USB-C receptacle and the screws to `dock-pcb/geometry.json`.
- **Tray:** build123d (`mech/src/mech/tray.py`). Two pockets generated from the case outlines, with chamfered funnel walls deep enough to guide a half before it meets the pins, a finger notch in each outer wall, through-holes for the case's feet, neodymium magnets under the steel discs, and a through-hole under each tenting puck. Each pocket fits its half only one way. The owner's printer (Bambu Lab A1 mini) prints at most 180 × 180 × 180 mm, and a tray for both halves is about 240 mm wide. So the tray prints as two pieces split between the pockets, and the dock PCB, screwed into each piece, ties them together.
- **Behavior:** drop a half in roughly the right spot; the walls and magnets seat it onto the pins.

## Case

- **Printed tray case per half** for prototyping, on the owner's A1 mini.
  - Floor plus walls up to the top of the PCB, keys exposed.
  - A cover over the battery and electronics area.
  - An opening over the tenting-puck mount, so the puck screws on through the case.
  - Openings for USB-C, the power switch and the charging pads.
  - The PCB is held by nylon screws and standoffs at the controller (which also carry the battery cover), one screw into a heat-set insert beside the thumb keys, and two lips over its outer edge.
- **Generated from the routed boards.** `scripts/mech/board_data.py` extracts every feature the CAD needs (outline, holes, pads, part courtyards, puck, steel discs, feet) into `mech/data/{left,right}.json`, and `mech/` (build123d) builds each half's parts from its own data, never by mirroring. CI checks that the data is current.
- **A machined aluminium case may follow.** Metal around the module would block Bluetooth, so that case must leave the antenna end open or use a non-metal window there. The printed case keeps the same openings, so it can serve as that case's model.

## Firmware

- **ZMK, split, no dongle.** A custom board definition, not a shield, because the MCU is on the board. It lives in `firmware/` as a ZMK module.
- **ZMK main, pinned to a commit**, on Zephyr 4.1. Builds run in ZMK's build image, pinned by digest (`toolchain.env`).
- **Bootloader:** Adafruit nRF52 UF2 bootloader built for this board: one LED-less build for both halves.
- **Modules:** `zmk-rgbled-widget`. Battery reporting via `zmk,battery-nrf-vddh`, wrapped by `urchin,battery-power-aware`, which reads the BQ24073 status pins (CHG_SENSE, PGOOD_SENSE; GPIOs per half in `hardware/pinmap.json`) so a docked or charging half doesn't report the charger's output as a full battery.
- Details and the first-flash procedure: `firmware/README.md`; decisions: the 2026-10-24 decision-log entry.

## Toolchain

| Job | Tool |
|---|---|
| Agent | Claude Code (Opus); fresh-context `reviewer` subagent at every gate |
| Geometry extraction | Python + KiCad pcbnew API, from the original board file |
| Circuit | atopile 0.15.7, local atomic parts only (no atopile part picker), built only via `scripts/ato_build.sh`. Mechanical footprints (tenting-puck mount, holes, logos) are atopile atomic parts too. Dependency tree frozen in `constraints/atopile.txt` |
| Footprints / 3D models | easyeda2kicad (from LCSC part numbers), upgraded with kicad-cli and wrapped as atopile atomic parts by `scripts/parts/import_lcsc.py` |
| Board files | KiCad 9.0.9, headless via kicad-cli and pcbnew Python |
| Placement | Python script: switches at extracted coordinates, electronics at agent-defined coordinates |
| Routing | `scripts/routing/route.py`: Freerouting 2.5.0 for every net (GND included), with the antenna keep-out and the module-core rule area as keep-outs, then a GND pour on both layers |
| Panel + fab outputs | KiKit: left+right panel with mouse bites, fiducials, tooling holes; `kikit fab jlcpcb` for Gerbers, BOM, CPL with rotation corrections |
| Dock CAD | build123d |
| Firmware build | ZMK in GitHub Actions |
| First flash | SWD probe that follows the target voltage (e.g. J-Link) + pyOCD |
| CI | GitHub Actions in the `kicad/kicad:9.0.9` image (pinned by digest): toolchain check → round-trip → ato build → board checks → KiKit outputs → firmware |

## Verification layers

1. atopile's own checks, plus a script that every intended connection exists on the board
2. kicad-cli DRC against JLC's capabilities
3. Custom checks: antenna keep-out, pad positions, battery clearance, single-sided assembly, geometry matches the original
4. After every `ato build` (`scripts/ato_build.sh`): KiCad format/feature guardrails (including footprints atopile would mangle), a pre-build snapshot, stale-net repair, and a board diff in build mode against the snapshot. In CI, every pushed commit's boards are also compared with their parent (`scripts/checks/board_history.sh`)
5. Rendered layer images and a 3D view, inspected by the reviewer
6. STEP exports of the halves and the dock board fit-checked against the printed cases, covers and dock tray, with the dock pins' landing and compression (`scripts/mech/build.sh`)
7. ZMK firmware builds for both halves
8. JLC's DFM check on upload (done by the human)

## Open items to verify

Resolved in phase 2 (2026-10-18): E73 stock, assemblability, VDDH wiring and crystal (decision log); Kailh socket (hand-soldered); stock of every keyboard part (`reports/phase2/bom.md`); `ElectricPower` net names (the circuit names plain signals). Still open:

- SMD pogo pins for the dock: stock (phase 7)
- easyeda2kicad footprints: silkscreen overlaps their own pads (DRC warnings in phase 0); every footprint's pads are reviewed against its datasheet land pattern at gate 1 (`reports/phase2/footprints.md`)
- Bring-up: docked and charged with the power switch off, D4's (1N5819WS) reverse leakage, up to 0.5 mA, might faintly light the red charge LED (phase 8 review). Look for it in the dark.
- JLC's live placement preview for the bottom side: the CPL convention (Y negated, rotation 180° − KiCad angle, as KiKit's `MirrorBottom`) was traced pin by pin by two reviews, but only JLC's preview at order time confirms it (checklist in `reports/phase6/README.md`)

Resolved in phase 6 (2026-10-18): BOM and CPL without a schematic come from `scripts/fab/jlc_assembly.py`, which uses KiKit's position functions on the panel. The bottom-side rotation convention was checked by the phases 4–6 reviews against every polarised part's pin 1.

## Decision log

Append entries as `YYYY-MM-DD: decision — reason`.

- 2026-10-17: Initial architecture as above, agreed in planning.
- 2026-10-17: KiCad 10.0.7 instead of 9, gated on a clean atopile round-trip test (phase 0). Fallback: latest KiCad 9.0.x.
- 2026-10-17: Keep the original tenting-puck mount instead of adding M2 holes.
- 2026-10-17: KiCad 9.0.9 instead of 10.0.7 — the phase 0 round-trip failed: atopile 0.15.7 (and 0.15.9) can't parse any board saved by KiCad 10 (new `(tenting (front yes) (back yes))` setup syntax). KiCad 9.0.9 passes the full round-trip. `scripts/checks/kicad_guardrails.py` now also rejects board files newer than the KiCad 9.0 format (20241229).
- 2026-10-17: Stay on atopile 0.15.7 although its CLI is end-of-life — the part server it uses is gone (DNS removed July 2026), 0.15.8+ needs a login to a legacy endpoint, and 0.16+ is a hosted app rather than a pinnable CLI. 0.15.7 works fully offline once parts are local, and it still writes the KiCad 9 format we need.
- 2026-10-17: Every part is an atopile atomic part generated from its LCSC number by `scripts/parts/import_lcsc.py` (easyeda2kicad → kicad-cli upgrade → `is_atomic_part` + `has_part_picked` with the LCSC number); no parametric `Resistor`/`Capacitor` picking — the picker needs the dead server, and explicit LCSC numbers are what rule 3 requires anyway.
- 2026-10-17: `ato build` runs only through `scripts/ato_build.sh`, which repairs stale net numbers, runs the guardrails and the board diff — atopile re-creates a net under a new number when fewer than 80% of its pads already carry its name (e.g. a third pad on a two-pad net) but leaves tracks, vias and zones on the old number. `scripts/fix_stale_nets.py` re-points them by name using the previous commit's net table; the phase 0 round-trip proves it.
- 2026-10-17: KiCad 9.0.9 is installed side by side with KiCad 10 at `/Applications/KiCad9` (owner's choice, to keep KiCad 10 for other projects); `KICAD_PY` and `PATH` point at KiCad 9, and the guardrail rejects anything a KiCad 10 save would produce.
- 2026-10-17: CI runs in the official `kicad/kicad:9.0.9` Docker image pinned by digest, not the Ubuntu PPA, because PPAs drop superseded versions and the pin would break on KiCad's next point release.
- 2026-10-17: Every footprint on a board is an atopile component, mechanical ones included (tenting-puck mount, holes, logos): an atomic part without an LCSC number, with an explicit `has_designator` and the footprint attributes `exclude_from_bom exclude_from_pos_files` — atopile deletes every footprint it doesn't own on each build (phase 0 review C1; round-trip steps 2 and 9).
- 2026-10-17: Footprint libraries must not contain two items of one type with the same geometry on different layers (enforced by the guardrail) — atopile re-syncs every footprint from its library on each build and matches items by geometry only, so it merges such items and moves one onto the other's layer (seen in phase 0: an F.CrtYd circle became B.CrtYd). `board_diff.py --mode build` also fails if an existing footprint's pads, graphics or attributes change while its library footprint is unchanged.
- 2026-10-17: Supersedes the stale-net entry above: the baseline for `fix_stale_nets.py` and `board_diff.py` in `scripts/ato_build.sh` is a snapshot taken just before `ato build`, not the previous commit (net numbers only mean something relative to the file they came from, and KiCad renumbers nets on every save; phase 0 review C2, round-trip step 7), and fix_stale_nets matches copper by UUID to that snapshot instead of inferring from numbers, because atopile behaves differently per platform (stale numbers on macOS, net 0 on Linux). Committed history is checked separately in CI.
- 2026-10-17: atopile's and KiKit's Python dependency trees are frozen in `constraints/` (`scripts/freeze_constraints.sh`) and installed with them locally and in CI — both pin few dependencies, and atopile's end-of-life CLI won't get fixes for breaking upstream releases.
- 2026-10-18: Every assembled part's library footprint is stored bottom-side (B.Cu), written by `scripts/parts/footprint_to_bottom.py` (`import_lcsc.py --side bottom`, the default), and a board footprint must sit on its library footprint's side (guardrail) — atopile re-syncs footprints by flipping them to the library's side and back, and on bottom-side footprints the flip corrupts text rotations on every build (permanent `--frozen` failure; phase 0 review 2, C-1). With bottom-side libraries no flip happens; the round-trip proves it at 15 and 270 degrees.
- 2026-10-18: The guardrail mirrors atopile's own data model (`faebryk/core/zig/src/sexp/kicad/pcb.zig`): anything atopile would drop on the next build is rejected beforehand — locks on footprints, tracks and zones, footprint-owned zones, `fp_curve`, text boxes, groups, extra zone outlines. Consequences: no locks (protect scripted routes by script, not by lock), and keep-outs are board-level rule areas — the antenna keep-out (rule 6) is drawn on the board by script from the module datasheet, never inside the module footprint.
- 2026-10-18: `scripts/ato_build.sh` is all-or-nothing: if `ato build` or any check fails, the boards are restored from the pre-build snapshot (with `.kicad_pro`/`.kicad_dru`) and the failed result is kept in `build/ato_build-failed/`, so a rerun fails the same way instead of accepting the damage (review 2, M-2/M-3).
- 2026-10-18: `fix_stale_nets.py` leaves copper on its net number when that number is unchanged and still exists (atopile renamed the net in place) and restores by name only when the number is gone or zeroed; board_diff accepts copper whose net changes together with all its pads (renames and swapped names) and nothing else (review 2, M-1).
- 2026-10-18: `Board-Diff-Allow:` lines count anywhere in a commit message, and `board_history.sh` skips merge commits (the commits they bring in are checked individually) (review 2, M-5).
- 2026-10-18: Geometry keeps the original board's coordinates (each half's layout uses them), so the zero-deviation check is a direct comparison. The original is a two-half panel; each half's edge is closed across the two tab openings with straight segments collinear with that edge (the only derived outline segments). CI fetches duckyb/urchin at the recorded commit, verifies the SHA-256, and checks that the geometry file, the mechanical parts and every board reproduce it (`scripts/checks/geometry_all.sh`).
- 2026-10-18: Kailh Choc hotswap sockets (CPG135001S30, LCSC C5333465) are hand-soldered, not JLC-assembled — sold out at LCSC and JLC on 2026-10-18 (only C99… global-sourcing entries with no stock). The original's combined switch+socket footprint is kept unchanged (exact holes and pads), excluded from the BOM and position files, with no paste on the socket pads so JLC's bottom stencil prints none there. If the socket comes back in stock, assembling it needs a separate bottom-side socket footprint (revisit then).
- 2026-10-18: Case mounting holes are kept for case compatibility but made non-plated (same drill): three per half sit 0.25 mm from the edge, and plating serves no purpose. Two per half are dropped because their drills overlap a tenting-puck hole (rule-1 geometry) or a larger case hole — overlapping drills are a fabrication risk.
- 2026-10-18: Inherited from the original and kept as documented DRC exclusions (rule 1 forbids moving them): socket pads that overhang the outline by up to 0.4 mm (left SW5, SW17; right SW22, SW27, SW32 — the router trims them, leaving ~85% of the pad), and the tenting puck's bottom courtyard overlapping socket courtyards.
- 2026-10-18: BQ24073 instead of BQ24075 — the BQ24075 regulates OUT to 5.4–5.6 V, above the E73 module's 5.5 V absolute maximum (datasheet: "超过5.5V 永久烧毁模块"); anything up to the 6.6 V OVP threshold on the exposed dock pads would reach VDDH. The BQ24073 is the same family (6.6 V OVP, 28 V input rating) with OUT regulated to 4.4 V (4.5 V max). It lacks SYSOFF, which isn't used (the slide switch powers off).
- 2026-10-18: Charger in USB100 mode (EN1 = EN2 = low): the BQ24073's fast-charge current can't be set below 150 mA, too much for a ~200 mAh cell; USB100 limits the input to 95 mA, so the cell charges at ~90 mA (~0.45 C). ISET = 5.1 kΩ (175 mA programmed; sets the ~6 mA termination threshold), ILIM = 5.1 kΩ (required, unused in this mode), TS = 10 kΩ (no thermistor), TMR open (default timers), TD and CE low.
- 2026-10-18: No 32.768 kHz crystal (the E73 has none; the LFRC oscillator is used, as planned) and REG0 runs as an LDO: the module contains REG1's DC/DC inductors and the VDD/VDDH/DECUSB capacitors but not REG0's inductor, and DCCH stays unconnected. Firmware must not enable REG0's DC/DC; REG1's DC/DC may be enabled.
- 2026-10-18: Both LEDs are the reverse-mount common-anode RGB MHT151RGBCT (one extended part instead of two): status LED anode on VDD, cathodes via 470 Ω to GPIOs (active low); charge LED anode on the charger input, red cathode via 1 kΩ to CHG (on while charging), green via 1 kΩ to PGOOD (on while input power is good), so amber = charging, green = charged, at zero battery cost. CHG and PGOOD reach their GPIOs through 1N4148W diodes so the LEDs' input-side voltage never reaches a GPIO. EasyEDA's footprint was corrected to the datasheet's reverse-mount land pattern with the 2.1 mm hole.
- 2026-10-18: The first SWD flash needs a probe that follows the target voltage (e.g. J-Link, VTref): a blank nRF52840 in high-voltage mode runs VDD at the 1.8 V default until the bootloader sets UICR.REGOUT0 to 3.3 V, and a Raspberry Pi Pico's fixed 3.3 V I/O can't safely drive or reliably read 1.8 V SWD. Bring-up (phase 9) must set REGOUT0 first.
- 2026-10-18: The module sits with its antenna end on the board edge in the old nice!nano notch (top edge, y = 39.846, centred in the notch), same orientation on both halves, and USB-C moves from the nice!nano's port position to the inner board edge (bottom side, below the slide switch). The antenna needs the board edge and copper-free surroundings; the notch is the only edge next to the controller area that no key or socket crowds, and the battery fits below the keep-out on top. USB-C on the inner edge points the cable at the other half, which is fine for flashing and charging. Supersedes "USB-C: same position as the original nice!nano's port".
- 2026-10-18: Per-half GPIO maps generated from geometry (`scripts/circuit/gen_halves.py`, Hungarian assignment on path length around the module and its antenna end) instead of one shared map: the module can't be mirrored (single-sided assembly), so on one half the keys face pins 26-43 and on the other pins 1-10. The socket pad nearer the module is each key's GPIO, the other its ground. P0.18 (reset) and P0.09/P0.10 (NFC) are never assigned.
- 2026-10-18: nRF52840 VBUS is fed from USB VBUS only (before its Schottky), not from the charger input, so a docked half isn't seen as USB-powered by ZMK; the dock state is read from PGOOD.
- 2026-10-18: The tenting-puck footprint gets a 2 mm silkscreen cross at its centre — atopile 0.15.7 crashes ("min() iterable argument is empty") placing designators on a footprint whose silkscreen is only circles and arcs. Pads, holes and outline are unchanged (rule 1).
- 2026-10-18: `scripts/checks/connectivity.py` checks every numbered pad of each half against a netlist written from the datasheets' pin numbers (not from the .ato sources), plus the generated pin map cross-checked with the E73 pin table; nothing unlisted may be connected.
- 2026-10-18: Placement source: `hardware/placement.json` for the left half's electronics and mechanical outlines, mirrored for the right half (x' = 2 × 128.397 − x, rotation' = −rotation); keys, puck and case holes from the geometry file. `scripts/placement/place.py --check` runs in CI.
- 2026-10-18: Antenna keep-out = the module's antenna end (module-local y −10.98 to −7.58, 0.06 mm short of the first pad row; the datasheet gives no dimension, so the antenna section itself is the minimum) widened to ±9.4 mm to cover the notch's ears, extended past the edge; a rule area on both copper layers forbids tracks, vias and pour, and `scripts/checks/clearance.py` rejects copper pads, parts and the battery in it. The two 2.2 mm case holes in the ears stay (case compatibility) as non-plated holes with no copper; use nylon screws there.
- 2026-10-18: Battery: 401730 cell (4.0 × 17 × 30 mm, ~180 mAh) on top, y 46.75–77.25 (3.5 mm clear of the keep-out), over J1's and SW35's through-hole joints, which are shorter than the board (1.01 mm and 0.55 mm), on 1 mm foam tape. Its outline is a mechanical part (BT2) so courtyard checks cover it.
- 2026-10-18: Dock contacts (TP1) at the bottom centre, (178, 85) on the left half and mirrored on the right, outside the tenting puck, with 10 mm steel-disc positions on either side (MK1/MK2); D2/D3 next to them. Rubber feet: four 6 mm positions near the corners (MK3–MK6), at least 3.5 mm tall; the free-space search found no room for wider ones.
- 2026-10-18: JLCPCB design rules live in each half's `.kicad_pro`, written by `scripts/placement/board_setup.py` (0.15 mm min track/space, 0.3/0.6 mm vias, 0.3 mm copper-to-edge); DRC errors are excused only through `hardware/drc_allow.json` (the two inherited ones).
- 2026-10-18: Unnumbered plated holes without an annular ring (the USB-C and slide-switch locating pegs) become non-plated in `scripts/lib/footprint.py` sanitize; KiCad flagged them as zero-width annular rings.
- 2026-10-18: atopile moves the reference field of a new mechanical footprint to its library footprint's layer on the second build only; that one-time change was accepted with `BOARD_DIFF_ARGS="--allow field-placement:*/Reference"`, and later builds are stable (`--frozen` passes).
- 2026-10-18: Phase 2 review changes (reports/phase2/review.md): R11 10 kΩ VBUS pull-down; CHG/PGOOD sense diodes are B5819W Schottkys (more logic-low margin; 1N4148W dropped); status LED green/blue use 220 Ω (red stays 470 Ω); charger OUT and BAT capacitors are 10 µF (4.7 µF X5R loses half at 4.4 V); dock TVS is SMF6.0A (C123790; 6.0 V standoff covers USB's 5.25 V); module pins 1, 2 and 42 (next to the antenna) are never assigned to keys or LEDs.
- 2026-10-18: Bottom-side library footprints keep KiCad's native representation of a flipped footprint (pad positions mirrored top-bottom, i.e. the left-right mirror turned 180°) but with the footprint and pad angles turned back to 0° (`footprint_to_bottom.py`); before, every pad carried an extra 180°, which rotated custom pad shapes about their centres. Placement rotations are therefore KiCad-native for bottom parts, and phase 6 applies KiCad's usual bottom-side rotation handling for JLC.
- 2026-10-18: `scripts/ato_build.sh` rebuilds until `ato build --frozen` changes nothing (at most 4 builds): atopile settles new footprints' field layers and swapped footprints' pad nets only on the second build (phase 2 review H1). Before a build, a footprint whose library part was replaced is not a guardrail failure (`kicad_guardrails.py --prebuild`).
- 2026-10-18: Phase 3 review changes (reports/phase3/review.md): clearance.py uses exact intersection tests and checks rule-area settings and pour fill area after a fresh fill; LED holes 1.8 mm (0.25 mm to the pads; datasheet 2.1 mm); 3D model offsets in `parts.json` (`model`), checked by STEP export; right half's default rotation is 180 − rotation (mirrors two-terminal pin order); libraries carry no item UUIDs (atopile copied them onto every instance) and boards must have unique UUIDs (guardrail); DRC allow-list names the overhanging sockets per half. Feet: at least 5 mm tall for use with a USB cable plugged in. Nylon screws in the ear holes beside the antenna.
- 2026-10-18: All four diodes are 1N5819WS (C191023, SOD-323, basic part) instead of B5819W (SOD-123): same 40 V/1 A Schottky function at half the footprint, which the crowded area under the module needed for routing.
- 2026-10-18: Routing is Freerouting on every net instead of hand-scripted critical routes. The nets here are slow (USB full speed at 12 Mb/s, static key and LED lines, ≤100 mA power), so there's no impedance or length requirement a script would have to meet. The script makes the router respect what it otherwise ignores: the routing boundary is inset 0.7 mm (Freerouting keeps only track and via centres inside it; 0.3 mm copper-to-edge plus a via radius), vias are 0.7/0.3 mm (0.2 mm ring; with 0.15 mm clearance their holes stay 0.5 mm apart, JLC's hole-to-hole), clearance is 0.17 mm for routing (Freerouting undershoots near pads; the rule is 0.15 mm), the router's neck-downs at pads are widened to JLC's 0.127 mm 2-layer minimum (the design rule's minimum track; elsewhere tracks are 0.15–0.3 mm), and GND stubs closer than 0.3 mm to the edge are dropped when the pour keeps them connected. Freerouting's result depends on track widths, so it runs four width variants in parallel (signal/power 0.2/0.3, 0.15/0.25, 0.175/0.3, 0.15/0.3 mm) and keeps the most complete. GND is routed as a net too, so connectivity never depends on the pour. CI doesn't re-route (the result isn't reproducible to the micron); it checks the committed routed boards with full DRC, the keep-out checks and connectivity. The one place it can't finish is the USB-C receptacle's paired pins (D+ on A6/B6 and D- on A7/B7 interleave, VBUS on two pads), so those joins are scripted (`scripts/routing/preroutes.py`, in the connector's own frame) and fixed before routing: D- as a U under the receptacle body, D+ and VBUS through vias with a top-layer link behind the pads. Freerouting's own "0 unrouted" proved wrong (its session can miss whole nets), so each attempt is imported and counted with KiCad's connectivity, and the best is kept.
- 2026-10-18: Antenna-adjacent module pins: P1.11/P1.10/P1.06 (pins 1, 2, 42) stay unused on the left half, but the right half uses pins 1 and 2 for keys. There they face the keys and their traces leave sideways, away from the antenna, about 4 mm from its end where the ground pour runs anyway. The right half needs them: its other side (pins 26–43) faces the inner edge, which the switch and USB-C crowd, and with only 17 GPIOs elsewhere five functions landed there and the board didn't route. Supersedes the earlier "pins 1, 2 and 42 are never assigned" for the right half.
- 2026-10-18: Phases 4–6 review changes (reports/phase5/review.md):
  - **Track widening.** After routing, `scripts/routing/widen.py` widens every track narrower than 0.15 mm to 0.15 mm wherever KiCad's DRC allows, which gives margin over JLC's 0.127 mm minimum.
  - **Routing runs 24 variants**, not four. There are eight signal/power width pairs: 0.2/0.3, 0.15/0.25, 0.175/0.3, 0.15/0.3, 0.127/0.25, 0.127/0.3, 0.175/0.25 and 0.2/0.25 mm. Each runs at a routing clearance of 0.17, 0.175 and 0.18 mm.
    - Freerouting is deterministic for a given input, so these variants are the only way to get different results. The right half routed completely only at 0.175 mm.
    - The script keeps the most complete result, then the one with fewest vias.
    - It runs six Freerouting processes at a time, each taking about 2 GB.
    - Supersedes "four width variants" above.
  - **Module ground (M1).** `route.py` now adds three things after the pours:
    - a solid-connection GND zone on B.Cu under U1 (its courtyard grown 1.2 mm, no thermal spokes on the module's GND pads);
    - GND stitching vias: a 5 mm grid over the board, a fence 0.9 mm outside the antenna keep-out's edge, and a ring around the module at 1.6 mm steps;
    - a via is kept only where it lies wholly inside GND copper on both layers, outside rule areas and part bodies, and 0.5 mm hole-to-hole from every other hole.

    A rule area keeping a 2 mm band under the module's RF end clear on both layers was tried and taken out. With it, Freerouting could no longer route the module's inner pins, and its sessions dropped nets. The only trace it moved is a static key line on the far layer, 0.8 mm from the antenna section.

    Slow signals (keys, LEDs, SWD, status sense) may still pass under the module's digital part on B.Cu outside MODULE_CORE. The E73 datasheet (p.8) forbids high-frequency digital, high-frequency analog and power traces under the module, and none of those run there.
  - **No vias under the USB-C receptacle's shell (L1).** A rule area `J1_SHELL` (J1's courtyard, both layers) forbids vias there; tracks may still pass under it, insulated by solder mask.
  - **J1 pin-in-paste (M3).** J1's four through-hole shell legs get bottom paste apertures (`paste_pads` in `hardware/parts.json`), so reflow solders them. Hand soldering is not needed.
  - **Panel (M2, L2).**
    - The panel has a 5 mm frame on all four sides, because J1 and SW35 reach 1 mm past the halves' inner edges, which are the panel's short edges.
    - Each half is held by tabs: two to the top frame, two to the bottom, the original two across the gap, and one to the side frame beside the antenna, where the keep-out keeps copper away from the mouse bites. All tabs are placed clear of the overhanging socket pads.
    - The layout plugin sets each half's tab boundary itself, because KiKit's bounding-box partition drops a side where the two halves' boxes differ by tens of µm.
    - Mill radius is 0.5 mm, the original's smallest inside corner, and the mouse bites sit 0.1 mm inside the edge.
    - KiKit's arc approximation (128 chords per circle, up to 0.025 mm off on the large arcs) is replaced in the layout plugin by one within 0.5 µm. KiKit's arc reconstruction is off, because it re-fit arcs up to 0.012 mm off.
    - `scripts/checks/panel_outline.py` checks that the panel keeps each half's outline outside the tabs, within 2 µm.
  - **Silkscreen (L3).** Text is 1.0 mm with a 0.15 mm stroke, JLC's legibility guidance. The custom parts' outlines are 0.15 mm lines. The original footprints keep their 0.12 mm lines, and JLC's own footprints keep their 0.06 mm marker dots.
- 2026-10-18: Phases 4–6 second review changes (reports/phase5/review.md, second review):
  - **LED lens hole.** The MHT151RGBCT's lens is 1.4 × 1.25 mm, so its diagonal (1.88 mm) didn't fit the 1.8 mm hole. The hole is now the datasheet's 2.1 mm, and the four pads sit 0.15 mm further out (centres at x ±1.70). That keeps 0.265 mm between hole and copper and still overlaps the LED's end terminals by 0.3 mm. Supersedes the 1.8 mm hole in the phase 3 review entry.
  - **C1 is 4.7 µF** (C23733, 0402, basic part), replacing 100 nF. The saved E73 datasheet doesn't show the module carrying the regulator's (REG0) output capacitor on VDD, and the same footprint takes the larger value at no routing cost. This qualifies the earlier claim that the module contains the VDD capacitor.
  - **U2's exposed-pad paste** shrinks 0.15 mm per side, to 68% coverage, as in TI's example stencil (BQ24073 datasheet p.41). A new `paste_margin` fixup does it.
  - **Stitching under the module.**
    - `stitch()` now allows GND vias under U1's body, which is what its datasheet wants under a module, and adds a 1.6 mm candidate grid under and within 3 mm of it.
    - It also tests candidates against the pours filled without island removal. Under the module the top pour is islands between the far-layer tracks, and a via is what connects an island; the refill after keeps only the islands that got one.
    - The routed boards were restitched with `route.py --restitch`.
  - **RF band on the module side: tried, then dropped.** A rule area keeping tracks off B.Cu under the module's RF end would have moved LED_B (right half) and KEY_R0C4's escape (left half). Neither Freerouting's completion passes nor a hand route could reconnect those nets around it: the pad's only other ways out are blocked by the inner pad column and neighbouring escapes. Those traces stay, and are accepted in the review.
  - **Post-routing repairs.**
    - `route.py --ripup-drc` removes only the copper in DRC errors, for completion passes to redo; here those passes left gaps.
    - `scripts/routing/joins.py` swaps hand-specified segments from `hardware/routing_joins.json`. They are the few short edits the LED pad move needed and the router couldn't make, and they are what the final boards got.
  - **Panel.**
    - The side tab moved into the antenna keep-out's stretch of edge and narrowed to 2 mm. Its mouse bites at y 39.4–42.4 stay clear of copper and leave 0.95 mm of board to the ear's case hole (third review M1). `panel_outline.py` checks that every mouse bite leaves ≥ 0.8 mm to any hole. Before, KiKit's refill cut the only link of a 21 mm² piece of the right half's top pour and island removal dropped it.
    - `scripts/checks/panel_fills.py` (run by `fab/build.sh`) checks that the panel's GND pours equal the halves' apart from the mouse bites. It allows at most 1 mm² of extra copper per layer, and none inside the antenna keep-out.
  - **J1's legs are hand-soldered after delivery.** The pin-in-paste apertures equal the pads and fill the barrels only partly, and overprinting isn't safe 0.23 mm from the SMD pins. Supersedes "Hand soldering is not needed" in the first-review entry.
- 2026-10-19: The pre-build guardrail (`kicad_guardrails.py --prebuild`) again refuses a footprint whose library footprint isn't found if it has no `atopile_address`. Such a footprint isn't an atopile part, and the build would delete it. An atopile part whose library part was swapped still passes, because the build replaces it. Refines the 2026-10-18 "ato_build settle" entry; the phase 0 round-trip (step 9) checks the refusal.
- 2026-10-24: Gate 3 passed: the owner ordered 5 panels with assembly of 2 (Standard PCBA) at JLC, after checking the placement preview of every polarized part on both halves against the checklist.
- 2026-10-24: Firmware (phase 8):
  - **ZMK main, pinned to a commit** (4dd95d78, Zephyr 4.1, the new board format), not the v0.3.0 release (Zephyr 3.5, old board format). The owner's current Urchin runs ZMK main, and a board written for Zephyr 3.5 would need porting at the next ZMK release. ZMK's manifest names Zephyr by a branch, so `firmware/config/west.yml` overrides it with that branch's commit.
  - zmk-rgbled-widget is pinned to its main branch, which tracks ZMK main.
  - **Builds run in ZMK's build image**, pinned by digest (`ZMK_BUILD_IMAGE`). Locally they run through Docker; the bootloader uses the same image's Zephyr SDK GCC.
  - **Board:** a custom board with two halves, `urchin_pp_left` (central) and `urchin_pp_right`. The key GPIOs, LED and charger-status pins, the matrix transform and ZMK Studio's physical layout are generated from `hardware/pinmap.json` and `hardware/geometry/urchin.json` (`scripts/firmware/gen_board.py --check`).
  - **Keymap:** the owner's (brancz/urchin-zmk-firmware), with battery and connection indicators added on the settings layer. ZMK Studio runs on the left half.
  - **Power configuration:**
    - REG0 stays disabled in the devicetree, because Zephyr turns REG0's DC/DC on whenever `&reg0` is enabled and the module has no inductor for it (nice!nano's board enables it, so it must not be copied).
    - REG1 runs as DC/DC.
    - The 32 kHz clock is the RC oscillator (no crystal; P0.00/P0.01 carry keys and the LED).
    - P0.18 is configured as reset (`gpio-as-nreset`).
  - **Battery reporting:** `urchin,battery-power-aware` wraps `zmk,battery-nrf-vddh`. It reports the measured level on battery, the last pre-input level while charging, and 100 % once charged, by reading PGOOD and CHG at each sample with their pull-ups on only during the read. It resolves the phases 4–6 second review's L4 (VDDH reads the charger's 4.4 V on input power).
  - **Bootloader:** Adafruit nRF52 bootloader 0.11.0, with S140 6.1.1 and the same flash layout as nice!nano.
    - One build serves both halves, with no LED, because each half's LED pins are key inputs on the other half.
    - It sets UICR.REGOUT0 to 3.3 V on first start.
    - Its USB ID is the pid.codes test VID/PID 1209:0001: private use only, not for a distributed product.
- 2026-10-24: Phase 8 review changes (`reports/phase8/review.md`):
  - **LED outputs are open-drain.** A half flashed with the other half's image then can't drive a key's pin high against the switch.
  - **The battery driver keeps the last on-battery level in GPREGRET2**, which survives resets and the wake from deep sleep, so a half that wakes or restarts while charging doesn't report full. It samples CHG over 600 ms (the charger blinks it at 2 Hz on a fault) and reports 100 % only on two consecutive "charged" samples.
  - **The bootloader build is reproducible** (`SOURCE_DATE_EPOCH`).
  - **lvgl and hal_stm32 come from ZMK's pins.**
  - **The SWD probe:** one whose I/O follows VTref down to 1.8 V (e.g. a J-Link), not a Raspberry Pi Pico.
- 2026-10-24: Both halves' battery levels (owner's choice). The left half fetches the right half's level, offers it to the host as a second Battery Service, and its LED blinks both levels (`firmware/config/urchin_pp_left.conf`). macOS shows only the first Battery Service, so the Mac still displays the left half; the second is there for an app or script. The settings-reset images build without the user config, which is meant for the real firmware.
- 2026-10-24: A macOS menu-bar app shows both halves' battery levels (owner's request; `menubar/`).
  - **Swift Package, AppKit status item, CoreBluetooth.** It's built with Apple's Command Line Tools, so Xcode isn't needed, and signed ad-hoc. It never pairs or connects on its own; it reads the Battery Services of the keyboard macOS has connected.
  - **The halves are told apart by descriptors, not by service order.** Zephyr's level has presentation description 0x0106 "main". ZMK's proxy levels have 0x0108 "auxiliary" and the user description `Peripheral <n>`. A 0 from a peripheral shows as "no reading", because that's how ZMK reports one that isn't connected.
  - **Swift is pinned:** `SWIFT_VERSION` 6.3.1 from Command Line Tools / Xcode `XCODE_VERSION` 26.4.1. CI selects that Xcode on the macos-26 runner, and `scripts/menubar/build.sh` refuses any other Swift.
  - Only the decoding and labelling are unit-tested. The Bluetooth path waits for bring-up.
- 2026-10-24: Phase 7 scope (owner's choices):
  - The halves get printed tray cases: low tray, keys exposed, tenting puck usable through the case.
  - The halves dock inside their cases.
  - The tray for both halves prints as two keyed pieces on one long dock PCB, because the owner's A1 mini prints at most 180 mm and the tray is about 240 mm wide.
  - Alternatives considered: two separate docks with a USB-C each (two cables), and an upright stand (less certain seating).
  - Supersedes "steel discs stuck to the bottom" of the PCB: they move to the case's underside.
- 2026-10-24: Printed case details:
  - **Stack:** 1.6 mm floor, 3.6 mm to the PCB's underside (the USB-C receptacle, the tallest bottom part, is 3.26 mm), walls flush with the PCB's top. The battery cover's roof sits 6 mm above the PCB (the cell on its foam tape is 5 mm).
  - **Mounting:**
    - The three 2.2 mm holes around the controller take M2 × 8 nylon screws from below into 6 mm nylon F-F standoffs, and M2 × 3 nylon screws hold the cover. Nylon because two of those holes are inside the antenna keep-out (rule 6). M2 × 4 at the top would meet the M2 × 8 inside the standoff.
    - **Only one of the four 3.8 mm holes takes a screw:** the one beside the thumb keys, an M2 × 5 with a 5 mm washer into an M2 × 3 heat-set insert. The others sit 2.1 mm from a switch body and under a keycap's edge, where no washer fits (the original's plate cases pass posts through them). They get plain standoffs. Two lips on the outer wall hold the outer edge: the board tilts in under them, then the controller side screws down. A screw goes wherever a washer clears every keycap, so the rule is in code (`case.screwed`), not a list of holes.
    - **The standoff under the hole next to the tenting puck is omitted:** it would overlap the puck.
  - **The power switch's slot is open to the wall's top,** like the USB-C notch: the switch's actuator reaches past the board's edge, so the board can only drop in through it.
  - **Standoffs are cut back** 0.3 mm from every bottom part's courtyard.
  - **Fit checks:**
    - Each printed part is checked against kicad-cli's STEP of the routed half. Modelled hotswap sockets, battery, switch bodies and keycaps are added. The hardware's heads, washers and standoffs are checked the same way. There must be no overlap, and at least 0.25 mm gap except where parts are meant to touch.
    - Every screw's thread engagement and tip clearance is computed from the stack.
    - No metal may sit in the antenna keep-out.
    - Every part that reaches past the case's cavity must do so inside a full-height wall opening (insertion).
    - Each STL must fit the 180 mm bed.
  - **Slicing:** Bambu Studio's own A1 mini profiles (0.20 mm Standard, PLA Basic), flattened by `scripts/mech/slice.py`, so each part's print time and any slicer warning are part of the evidence. CI skips slicing (no Linux CLI build of that version).
  - **After the phase 7 second review** (`reports/phase7/review.md`): the lips sit 0.2 mm (one layer) over the PCB, so their underside is on a layer boundary and a board 0.16 mm thick still fits, and reach 0.8 mm over it; checks cover their height, the tilt a board goes in at, and how far they hold its edge with its play. The standoffs are modelled as up to 4 mm hex. The power-switch scoop leaves 0.8 mm of wall.
- 2026-10-24: Dock details (phase 7; parts research in `reports/phase7/dock-parts.md`):
  - **The dock PCB is assembled on its top.** Its pins and USB-C face up, and JLC assembles one side. Rule 2 stays the halves' rule.
  - **Parts:** YTC1P-4020-01 pogo pins (C5221284; 6.0 mm free, 1.4 mm stroke: 0.8 mm compressed at the halves' 5.2 mm pad height), the power-only DEALON USB-TYPE-C-009 (C2927029), one MF-NSMF050-2 polyfuse (0.5 A hold) for both halves, an SMF6.0A TVS after it (a sustained overvoltage then trips the fuse instead of burning the TVS), 5.1 kΩ on each CC pin, and a green 0805 LED at about 1 mA. Of the four pins that fit, it's the only one with EasyEDA CAD, so it's imported and its 3D model checks the fit. The halves draw about 95 mA each, so one fuse serves both; a short across either half's pins stops both charging until it cools.
  - **Tray:** pockets 0.4 mm larger than the case all round, 8.2 mm deep, with a 1.2 mm 45° funnel. The straight walls reach 7.0 mm, above the tallest free pin tip (6.46 mm worst case) plus the case's 0.4 mm bottom chamfer, so a half is guided before it meets the pins, and the pins stay below the rim with nothing docked (phase 7 review M1). A notch (9 mm radius, down to 1 mm above the floor) in each pocket's outer wall lets a finger reach the case's side to tilt the half out against the magnets (L7). The two pieces meet 0.2 mm apart on the centre line between the pockets, with no key: the dock PCB lies in a recess across both and an M2 × 5 screw holds it into an M2 × 3 heat-set insert in each piece. That replaces "two pieces that key together". Once the PCB has aligned them, the pieces are glued at the split, so the PCB's solder joints don't take the joint's bending (L6).
  - **Dock PCB in the tray:** 0.3 mm clearance round its outline (JLC routes outlines to ±0.2 mm), and 0.15 mm round the magnet bosses, which pass through its holes and locate the bar beside each half's pins (M2, L1). The screws sit 8.3 mm either side of the receptacle, leaving 1.7 mm of printed wall between each insert and the hollow under the receptacle (M5); the tab between the pockets is 21 mm wide for them. That hollow (1.2 mm deep) also runs under the polyfuse, which reaches 125 °C when tripped, so the PCB doesn't sit on PLA there (L5).
  - **Magnets:** an N52 10 × 3 mm disc under each steel disc, glued into a pocket from below under a 0.6 mm printed skin; the pocket also fits 10 × 5. Where the dock PCB passes over a magnet, it has a 12.1 mm hole round the tray's boss, which holds the magnet inside it with a 0.8 mm wall. Two per half outweigh the three pins' 3 to 3.5 N.
  - **Feet:** the tray has a through-hole (10 mm, for the 6 mm feet) under each foot, so the feet's height doesn't affect docking; any foot up to 7.4 mm tall fits (H1, M3). The hardware list asks for 6 × 2 mm bumpers. The earlier minimums (3.5 mm, 2026-10-18; 5 mm with a USB cable plugged in, phase 3 review) were for the bare board. In the case, the floor covers the bottom parts, and a plugged-in cable's overmold (up to 6.5 mm tall, centred on the receptacle about 3.6 mm above the underside: it hangs 3.26 mm below the PCB) stays about 0.3 mm above the case's underside, in the full-height USB-C notch.
  - **Pin tolerance stacks** (`mech/src/mech/dock_checks.py`, phase 7 review M2/L2). Each term is the most it can be off either way. The checks add the terms linearly (the worst case) and as a root sum of squares (RSS, independent errors). The RSS must be within the limit, and the worst case is reported.
    - **Landing:** how far a case moves and turns in its pocket (0.6 mm clearance with print error), and the board in its case (0.5 mm to the wall, 0.4 mm at its three locating screws), is solved from their outlines as a small linear program, not estimated. Added to that: the dock PCB on its bosses (0.25 mm), pocket to boss (0.1), the pin on its land (0.15) and its tilt (0.1). The RSS is 0.86 mm against the 1.1 mm the tip has across the halves' 2.5 mm pads (0.15 mm kept from the edge). The worst case is 1.69 mm, past the pad's 1.25 mm half-width in that direction; along the pads' 4 mm length it stays on. Every term would have to line up for a miss, and the pocket's clearance can be tightened in a reprint once a print is measured. The keyboard PCB is unchanged.
    - **Window:** the case's window in the floor clears the pins' flanges in the worst case (1.54 mm needed, 1.75 mm there), which is why its margin round the pads is now 1.5 mm.
    - **Compression:** the pin's ±0.15 mm, its solder joint, the dock PCB's ±10 % thickness, the recess depth and the case's standoffs give 0.51 to 1.09 mm by RSS, inside 0.2 mm (contact force) to the 1.4 mm stroke; the worst case is 0.19 to 1.41 mm. The pin's ±0.15 mm comes from its 4020-01R sibling's datasheet: measure a few pins when they arrive.
  - **No track under the receptacle's shell** (M4): a rule area J1_FRONT on F.Cu forbids tracks from 0.2 mm in front of J1's pad row to its front, so VBUS joins A9 and B9 behind the pads (`scripts/dock/place.py`). DRC enforces it.
  - **The 5 V trunk is scripted** (`scripts/routing/preroutes.py`): 0.5 mm on F.Cu along the strip between the magnet cutouts and the bar's lower edge, which Freerouting didn't find. B.Cu stays one ground pour.
  - **Library fixes** (`dock-pcb/parts.json`): the pogo pin's EasyEDA silkscreen (two circles, which crash atopile 0.15.7) is dropped and its zero-width courtyard replaced by the pad plus 0.25 mm. `sanitize()` now strips library item UUIDs for every part (atopile copies them onto every instance).
  - **Silkscreen:** only J1 and LED1 show designators, placed by `scripts/dock/place.py`; the rest would crowd the 19 mm tab.
  - **Surface finish:** atopile writes ENIG into the board on its first build. The dock's pads carry soldered pins, not contacts, so lead-free HASL is fine for the order and ENIG optional.
