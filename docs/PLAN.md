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
2. Without a battery: power from USB and use a multimeter. Check the polarity at the battery pads; without a cell the charger's battery detection makes BAT switch on and off, so the reading wanders. Then, with the power switch on, check VDDH (about 4.4 V, the charger's system output) and VDD (1.8 V on a blank module; 3.0–3.3 V once the bootloader sets REGOUT0).
3. Flash the bootloader over SWD with a probe that follows the target voltage (e.g. J-Link; the module's I/O is at 1.8 V until the bootloader sets REGOUT0); unlock APPROTECT if needed.
4. Flash ZMK over USB; test every key.
5. Connect the battery; test pairing, battery reporting, LEDs, power switch.
6. Test charging over USB, then over the dock, then with the switch off.
- **Exit:** a bring-up log in `reports/bringup/`; issues filed for a revision if needed.

## Status

Update this section whenever a phase moves.

| Phase | Status | Notes |
|---|---|---|
| 0 Toolchain proof | done (2026-10-18) | KiCad 10 failed the atopile round-trip, so KiCad 9.0.9 per the fallback. The 12-step round-trip passes locally and in CI (run 39119942514). Two reviewer rounds dispositioned in `reports/phase0/review.md`. Decisions in ARCHITECTURE.md (local atomic parts, bottom-side library footprints, all-or-nothing `ato_build.sh`). |
| 1 Geometry | done (2026-10-18) | Zero deviation against the original, checked in CI from a fetched copy. Evidence in `reports/phase1/`. |
| 2 Circuit and parts | done (2026-10-18) | Both halves build; connectivity checked against a datasheet netlist; BOM in stock (`reports/phase2/`). Review findings fixed or dispositioned in `reports/phase2/review.md`. Gate 1 passed under the owner's standing instruction to continue to a JLC-ready bundle. |
| 3 Placement | done (2026-10-18) | Placement, antenna keep-out, clearance and DRC checks pass on both halves (`reports/phase3/`). Review findings fixed or dispositioned in `reports/phase3/review.md`. Gate 2 passed under the owner's standing instruction. |
| 4 Routing | done (2026-10-18) | Both halves fully routed with 0 DRC errors. Freerouting runs with scripted pre-processing (inset boundary, via spacing, 24 width and clearance variants) and scripted USB-C joins. After import: GND pour on both layers, a solid module ground zone, and stitching vias, including under the module. Rule areas keep copper off the antenna and the module's core, and vias from under the USB-C shell. Repairs after the second review: `route.py --ripup-drc`, `scripts/routing/joins.py`, `route.py --restitch`. Evidence in `reports/phase4/`. |
| 5 Validation | done (2026-10-18) | Every verification layer is green or dispositioned in `reports/phase5/README.md`. STEP fit (dock) and firmware build belong to phases 7 and 8. Two reviewer passes for phases 4–6; every finding is fixed or dispositioned in `reports/phase5/review.md`. |
| 6 Fab outputs | done (2026-10-18) | JLC bundle from `scripts/fab/build.sh` (also the CI artifact `jlc-bundle`): framed panel of both halves, Gerbers, BOM, CPL, renders, STEP. Upload checklist in `reports/phase6/README.md`. **Gate 3 passed 2026-10-24:** the owner checked JLC's placement preview against the checklist and ordered 5 panels with assembly of 2 (Standard PCBA). |
| 7 Dock | not started | |
| 8 Firmware | in progress (2026-10-24) | ZMK board `urchin_pp_left`/`urchin_pp_right` on ZMK main (pinned), the owner's keymap, zmk-rgbled-widget, a charger-aware battery driver, and the Adafruit nRF52 bootloader (`firmware/`). |
| 9 Bring-up | not started | |
