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

- **Charger: TI BQ24073** (was BQ24075; see the decision log). Power-path type (the system runs from the input supply while charging). Input rated to 28 V with overvoltage protection, which matters for exposed pads. USB100 mode: the input is limited to about 95 mA, so a ~200 mAh cell charges at about 0.45C. The status (CHG) and power-good (PGOOD) pins go to GPIOs so firmware knows the charging state.
- **The diodes** make the pads input-only. A metal surface across the pads can't drain or short the battery.
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
- SWD pads (SWDIO, SWCLK, GND, 3V3) at 2.54 mm pitch for the one-time bootloader flash. Use a Raspberry Pi Pico running `debugprobe` with pyOCD, which can also unlock APPROTECT if a module ships locked.

**Charging contacts.** Three ENIG pads on the bottom (GND / 5V / GND, symmetric) in a gap between sockets near the electronics. Thin steel discs are stuck to the bottom for the dock magnets. Rubber feet sit taller than the tallest bottom component.

**PCB.** 2 layers, 1.6 mm, ENIG finish (required for the pads).

## Dock

- **Dock PCB:** one long, thin board spanning both pockets. USB-C input in the middle (CC resistors, polyfuse, power LED), SMD pogo pins at each end, matching the pad positions. Its own small JLC order, built by the same pipeline.
- **Tray:** build123d, PETG print. Two pockets generated from the real board outlines exported by kicad-cli, with chamfered funnel walls and neodymium magnets under the steel-disc positions. Each pocket fits its half only one way.
- **Behavior:** drop a half in roughly the right spot; the walls and magnets seat it onto the pins.

## Firmware

- **ZMK, split, no dongle.** A custom board definition, not a shield, because the MCU is on the board. It lives in `firmware/` as a ZMK module.
- **Bootloader:** Adafruit nRF52 UF2 bootloader built for this board.
- **Modules:** `zmk-rgbled-widget`. Battery reporting via `zmk,battery-nrf-vddh`. Charging state read from the BQ24073 status pins (CHG_SENSE, PGOOD_SENSE; GPIOs per half in `hardware/pinmap.json`).

## Toolchain

| Job | Tool |
|---|---|
| Agent | Claude Code (Opus); fresh-context `reviewer` subagent at every gate |
| Geometry extraction | Python + KiCad pcbnew API, from the original board file |
| Circuit | atopile 0.15.7, local atomic parts only (no atopile part picker), built only via `scripts/ato_build.sh`. Mechanical footprints (tenting-puck mount, holes, logos) are atopile atomic parts too. Dependency tree frozen in `constraints/atopile.txt` |
| Footprints / 3D models | easyeda2kicad (from LCSC part numbers), upgraded with kicad-cli and wrapped as atopile atomic parts by `scripts/parts/import_lcsc.py` |
| Board files | KiCad 9.0.9, headless via kicad-cli and pcbnew Python |
| Placement | Python script: switches at extracted coordinates, electronics at agent-defined coordinates |
| Routing | Scripted critical nets (power, USB pair, antenna zone), then Freerouting 2.5.0 for the rest |
| Panel + fab outputs | KiKit: left+right panel with mouse bites, fiducials, tooling holes; `kikit fab jlcpcb` for Gerbers, BOM, CPL with rotation corrections |
| Dock CAD | build123d |
| Firmware build | ZMK in GitHub Actions |
| First flash | Raspberry Pi Pico + debugprobe + pyOCD |
| CI | GitHub Actions in the `kicad/kicad:9.0.9` image (pinned by digest): toolchain check → round-trip → ato build → board checks → KiKit outputs → firmware |

## Verification layers

1. atopile's own checks, plus a script that every intended connection exists on the board
2. kicad-cli DRC against JLC's capabilities
3. Custom checks: antenna keep-out, pad positions, battery clearance, single-sided assembly, geometry matches the original
4. After every `ato build` (`scripts/ato_build.sh`): KiCad format/feature guardrails (including footprints atopile would mangle), a pre-build snapshot, stale-net repair, and a board diff in build mode against the snapshot. In CI, every pushed commit's boards are also compared with their parent (`scripts/checks/board_history.sh`)
5. Rendered layer images and a 3D view, inspected by the reviewer
6. STEP export fit-checked against the dock CAD
7. ZMK firmware builds for both halves
8. JLC's DFM check on upload (done by the human)

## Open items to verify

Resolved in phase 2 (2026-10-18): E73 stock, assemblability, VDDH wiring and crystal (decision log); Kailh socket (hand-soldered); stock of every keyboard part (`reports/phase2/bom.md`); `ElectricPower` net names (the circuit names plain signals). Still open:

- SMD pogo pins for the dock: stock (phase 7)
- easyeda2kicad footprints: silkscreen overlaps their own pads (DRC warnings in phase 0); every footprint's pads are reviewed against its datasheet land pattern at gate 1 (`reports/phase2/footprints.md`)
- KiKit's `fab jlcpcb --assembly` needs a schematic, which atopile doesn't produce: build BOM/CPL from atopile's BOM and `kicad-cli pcb export pos` (phase 6)
- Bottom-side parts use bottom-side library footprints (decision below): check that `kicad-cli pcb export pos` and JLC's rotation corrections give the right orientation for them (phase 6)

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
