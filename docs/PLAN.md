# urchin++ plan

## Goals

1. **Integrated keyboard.** Two Urchin halves with the exact original key layout and every electronic part on the PCB, no daughter board.
2. **Upload-ready manufacturing.** One command produces the Gerber zip, BOM, and CPL files that JLCPCB accepts for fabrication and assembly without manual fixes.
3. **Overnight dock charging.** Drop both halves into a tray; they snap into place and charge. USB-C still works for flashing and charging.
4. **Working firmware.** ZMK split, battery reporting, a status LED, a charging state, all built in CI.
5. **AI-driven with evidence.** Every step is generated and verified by agents, and every claim is backed by a committed report.

## Success criteria

- Key geometry matches the original exactly (script-verified, zero deviation).
- DRC clean against JLC rules; all custom checks pass; reviewer findings resolved.
- JLC accepts the upload with every part matched and every rotation correct in its preview.
- On bring-up: both halves pair, every key registers, battery level reports, charging works over USB and over the dock, and the board charges while switched off.
- Typing range and battery life comparable to a nice!nano build.

## Phases

Each phase ends with its outputs committed under `reports/<phase>/` and a `reviewer` pass. **Human gates** are marked 🛑: stop and wait for approval.

### Phase 0 — Toolchain proof
- KiCad round-trip: throwaway atopile project in `scratch/roundtrip/`, edit the board through pcbnew (move a footprint, add a track and a zone), commit, `ato build` again, diff, DRC. Stop on any unexpected change. (Planned on KiCad 10; it failed, so the pipeline uses KiCad 9.0.9 per the fallback. `scripts/roundtrip/run.sh` covers this and more.)
- Scaffold the repo layout from CLAUDE.md, `.gitignore`, and a CI skeleton that runs on every push.
- Record exact tool versions and the Freerouting jar checksum in `docs/SETUP.md`.
- **Exit:** clean round-trip report, CI green on an empty build.

### Phase 1 — Geometry
- Extract switch positions and rotations, the outline, the tenting-puck mount, and the USB/controller area from the original board.
- Produce a geometry file (YAML/JSON) as the single source for placement.
- **Exit:** a script that overlays the extracted geometry on the original and reports zero deviation; renders of both halves.

### Phase 2 — Circuit and parts
- atopile circuit for one half (shared by both): module, charger, power path, USB-C, ESD, LEDs, switch, reset, SWD pads, charging pads, direct-pin wiring for 17 keys.
- Pin assignment for the module that keeps routing short and leaves the antenna side free.
- Part selection against live LCSC stock; datasheets saved; resolve the open items in ARCHITECTURE.md.
- **Exit:** netlist, BOM with LCSC numbers and stock check date, pin map, review. 🛑 **Gate 1: circuit approval.**

### Phase 3 — Placement
- Place switches and sockets from the geometry file, then the electronics block in the old controller area, the battery, pads, LEDs, and steel-disc positions.
- Check bottom space: tenting puck, charging pads, sockets, rubber feet.
- **Exit:** placement renders (top, bottom, 3D), keep-out check, clearance report. 🛑 **Gate 2: placement approval.**

### Phase 4 — Routing
- Script the critical routes (power path, USB differential pair, ground pour, antenna keep-out zone), then Freerouting for key traces.
- **Exit:** fully routed boards, DRC clean, board-diff check clean.

### Phase 5 — Validation
- Run every verification layer from ARCHITECTURE.md. Full reviewer pass with datasheets.
- **Exit:** a single validation report with every check green or explicitly dispositioned.

### Phase 6 — Fabrication outputs
- KiKit panel (left + right), `kikit fab jlcpcb`, rotation corrections, a BOM/CPL sanity check (every placed part has an LCSC number, nothing on the top side).
- **Exit:** a release-candidate bundle under `fab/` with renders and a checklist for the JLC upload. 🛑 **Gate 3: order approval** (the human uploads and orders).

### Phase 7 — Dock
- Dock PCB (atopile → KiCad → fab outputs, same pipeline).
- build123d tray from the exported board outlines, with pockets, funnel walls, magnet seats, and pogo positions; STEP fit check with both halves; STL output.
- **Exit:** dock fab bundle, STL files, fit-check report.

### Phase 8 — Firmware
- ZMK board definition for both halves, keymap (port the original Urchin keymap), rgbled-widget, VDDH battery driver, charging-state input.
- Adafruit nRF52 bootloader for this board.
- **Exit:** CI builds firmware for both halves and the bootloader; artifacts attached to the run.

Phases 7 and 8 can run in parallel with waiting for JLC delivery.

### Phase 9 — Bring-up (human, with agent guidance)
1. Visual check of the delivered boards.
2. Without a battery: power from USB, use a multimeter to check the charger output voltage and polarity at the battery pads, then VDDH and 3V3.
3. Flash the bootloader over SWD with the Pico; unlock APPROTECT if needed.
4. Flash ZMK over USB; test every key.
5. Connect the battery; test pairing, battery reporting, LEDs, power switch.
6. Test charging over USB, then over the dock, then with the switch off.
- **Exit:** a bring-up log in `reports/bringup/`; issues filed for a revision if needed.

## Status

Update this section whenever a phase moves.

| Phase | Status | Notes |
|---|---|---|
| 0 Toolchain proof | done (2026-10-18) | KiCad 10 failed the atopile round-trip, so KiCad 9.0.9 per the fallback. The 12-step round-trip passes locally and in CI (run 39119942514). Two reviewer rounds dispositioned in `reports/phase0/review.md`. Decisions in ARCHITECTURE.md (local atomic parts, bottom-side library footprints, all-or-nothing `ato_build.sh`). |
| 1 Geometry | not started | |
| 2 Circuit and parts | not started | |
| 3 Placement | not started | |
| 4 Routing | not started | |
| 5 Validation | not started | |
| 6 Fab outputs | not started | |
| 7 Dock | not started | |
| 8 Firmware | not started | |
| 9 Bring-up | not started | |
