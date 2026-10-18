# urchin++ architecture

The decisions below were made deliberately. Change one only with a reason, and record the change in the decision log at the end.

## Keyboard (per half, left and right)

**Layout.** The original Urchin geometry: 17 keys per half, Kailh Choc v1 switches in Kailh Choc hotswap sockets, Choc spacing. Extracted by script from `reference/urchin/main.kicad_pcb`, including the board outline and the tenting-puck mount (`Tenting_Puck2_no_pads`), so existing tenting accessories stay compatible.

**Wiring.** Direct pin: every key gets its own GPIO. No diode matrix, no diodes. ZMK's direct kscan is interrupt-driven, which keeps idle power low.

**Board sides.** All SMD parts are on the bottom, alongside the hotswap sockets, so JLC assembles one side only. The top carries switches and the battery. Left and right are separate layouts (the original's reversible-PCB trick doesn't survive one-sided components), but they share one circuit definition and are panelized together into one order.

**MCU.** Ebyte E73-2G4M08S1C, a pre-certified nRF52840 module, so there's no RF matching to verify. Fallback if out of stock: Holyiot 18010. The antenna end sits at the outer board edge. The datasheet's keep-out applies on every layer: no copper, traces, parts, or battery inside it. The 32 kHz clock comes from the internal RC oscillator unless the module includes a crystal; configure ZMK and the bootloader to match.

**Power path.**

```
USB-C VBUS ──Schottky──┐
                        ├──> BQ24075 IN ── OUT ──[slide switch]──> nRF52840 VDDH
dock pads 5V ─TVS─Schottky┘           └── BAT ── protected LiPo
```

- **Charger: TI BQ24075.** Power-path type (the system runs from the input supply while charging). Input rated to 28 V with overvoltage protection, which matters for exposed pads. Charge current set to about 0.5C of the chosen cell. The status (CHG) and power-good (PGOOD) pins go to GPIOs so firmware knows the charging state.
- **The diodes** make the pads input-only. A metal surface across the pads can't drain or short the battery.
- **Switch placement** between the charger output and VDDH, so the battery still charges while the board is switched off.
- **No external regulator.** The battery drives the nRF52840's high-voltage input (VDDH) directly, following the module datasheet's reference circuit.
- **No battery divider.** ZMK's `zmk,battery-nrf-vddh` driver measures the voltage internally, so there's no leakage path.

**Battery.** A protected LiPo, the largest cell that fits the old nice!nano area on top at 4 mm thickness or less (expect roughly 150–250 mAh). Wires are soldered to pads, no JST connector, to save height. The exact cell is chosen in phase 2 from the real free area.

**USB-C.** Same position as the original nice!nano's port. 5.1 kΩ CC pull-down resistors, a USBLC6-2 for ESD on D+/D-. Used for flashing; it also charges.

**Indicators.**
- Status: a plain (non-addressable) RGB LED, reverse-mounted on the bottom and shining up through a hole, driven by GPIOs via `zmk-rgbled-widget`. It blinks battery level on wake and connection state on profile changes, then stays dark.
- Charge: a second LED driven by the charger's CHG pin, powered from the input supply (zero battery cost).
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
- **Modules:** `zmk-rgbled-widget`. Battery reporting via `zmk,battery-nrf-vddh`. Charging state read from the BQ24075 status pins.

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

## Open items to verify (phase 2 unless noted)

- E73-2G4M08S1C: LCSC stock, JLC assemblability, VDDH/DC-DC wiring, whether it has a 32 kHz crystal
- Kailh Choc hotswap socket: LCSC part, JLC assembly of bottom-side sockets
- BQ24075, USBLC6-2, slide switch, reverse-mount RGB and single LEDs, SMD pogo pins (dock): stock
- Battery cell dimensions vs free area (phase 3)
- Charging pads vs tenting puck vs sockets: space on the bottom (phase 3)
- Net names for `ElectricPower` rails: the type's own `hv`/`lv` suggestions win over instance traits, so name rails on plain signals (found in phase 0)
- easyeda2kicad footprints: silkscreen overlaps their own pads (DRC warnings in phase 0); review every footprint against its datasheet land pattern
- KiKit's `fab jlcpcb --assembly` needs a schematic, which atopile doesn't produce: build BOM/CPL from atopile's BOM and `kicad-cli pcb export pos` (phase 6)
- Bottom-side parts use bottom-side library footprints (decision below): check that `kicad-cli pcb export pos` and JLC's rotation corrections give the right orientation for them (phase 6)
- `reference/` is gitignored, so CI can't rerun geometry extraction from the original board: commit the extracted geometry file and its overlay report, or have CI fetch the original Urchin repo at a pinned commit (phase 1)

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
