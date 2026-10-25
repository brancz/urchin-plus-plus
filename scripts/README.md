# scripts

Every generator and check, runnable headless; CI runs the same scripts.

| Script | Runs with | Purpose |
|---|---|---|
| `ato_build.sh PROJECT [args]` | bash | The only way to run `ato build`: preflight and guardrails, pre-build snapshot, build, stale-net repair, board diff (build mode); all or nothing |
| `fix_stale_nets.py BOARD --against BEFORE` | python3 | Put copper back on the nets atopile moved it off (matched by UUID) |
| `parts/import_lcsc.py --parts-dir DIR C…` | python3 | LCSC part → atopile atomic part (easyeda2kicad + kicad-cli upgrade; bottom-side footprint by default) |
| `parts/footprint_to_bottom.py DIR NAME` | `$KICAD_PY` | Rewrite a library footprint as a bottom-side footprint |
| `freeze_constraints.sh [--check\|--check-constrained]` | bash | Freeze atopile's and KiKit's dependency trees into `constraints/`; check exact match (local) or that everything installed is pinned (CI) |
| `checks/board_diff.py BOARD …` | `$KICAD_PY` | Semantic board diff; fails on removals and copper net changes (`--mode build`: anything atopile shouldn't touch; `--strict`: any change) |
| `checks/board_history.sh RANGE` | bash | CI: every non-merge commit's boards vs their parent; `Board-Diff-Allow:` lines for intended removals |
| `checks/kicad_guardrails.py PATH…` | python3 | Fail on files newer than KiCad 9, KiCad 10-only features, content atopile would drop or mangle, footprints flipped against their library |
| `geometry/extract.py` | `$KICAD_PY` | Original Urchin → `hardware/geometry/urchin.json` (switches, outline, puck, case holes, controller area) |
| `geometry/mechanical_parts.py` | `$KICAD_PY` | Original key/puck/hole footprints → atopile parts in `hardware/parts/` |
| `geometry/preview.py OUT` | `$KICAD_PY` | Boards built from the geometry file, for the phase 1 check and renders |
| `checks/geometry.py BOARD --half H` | `$KICAD_PY` | Zero-deviation check of a half's board against the original board |
| `parts/jlc.py search\|check\|datasheet` | python3 | Live JLC/LCSC part search, stock check, datasheet download |
| `render.sh BOARD OUT` | bash | Top and bottom 3D renders |
| `checks/toolchain.sh [--local\|--kicad]` | bash | Installed tools match `toolchain.env` (and `constraints/` with `--local`) |
| `roundtrip/run.sh [WORK] [OUT]` | bash | Phase 0 toolchain proof: 12 steps through the wrapper, board history, Freerouting, KiKit |
| `roundtrip/edit_board.py`, `pcb_ops.py`, `autoroute_smoke.py` | `$KICAD_PY` | pcbnew operations used by the round-trip |
| `roundtrip/kicad10_probe.sh KICAD10_APP [OUT]` | bash | Evidence that atopile can't rebuild a board KiCad 10 saved |
| `roundtrip/upstream_checks.sh` | bash | Evidence for the atopile part-server and end-of-life facts |
| `parts/custom_parts.py [--dock]` | `$KICAD_PY` | Parts without an LCSC number: battery, dock and SWD pads; battery outline, steel discs, rubber feet. With `--dock`, the dock board's: its flat contacts (DOCK_CONTACTS) |
| `parts/bom_check.py [--dock]` | python3 | Live JLC stock for every part, datasheet present, per-half (per dock board) quantities match atopile's BOM |
| `parts/footprint_report.py OUT` | python3 | Pad tables and SVGs of every assembled footprint, for review against the datasheets |
| `circuit/gen_halves.py [--check]` | python3 | Per-half GPIO assignment from geometry → `hardware/halves.ato`, `hardware/pinmap.json` |
| `placement/place.py BOARD --half H [--check]` | `$KICAD_PY` | Positions from the geometry file and `hardware/placement.json`; outline; rule areas: antenna keep-out, module core, no vias under J1's shell |
| `placement/board_setup.py [--check]` | python3 | JLC design rules and net classes in each board's `.kicad_pro` (both halves and the dock) |
| `placement/silk.py BOARD [--check]` | `$KICAD_PY` | Bottom designators mirrored, 1.0 mm text with a 0.15 mm stroke; small passives' designators hidden |
| `placement/unique_uuids.py BOARD [--check]` | python3 | Give every board item its own UUID |
| `routing/route.py BOARD WORK` | `$KICAD_PY` | Freerouting (up to 24 width and clearance variants, several at a time, each checked with KiCad's connectivity), exact positions restored, sub-micron router stubs dropped, neck-downs widened, GND pour on both layers, module ground zone and stitching vias; `--ripup`, `--ripup-nets`, `--ripup-drc`, `--complete-only`, `--restitch` |
| `routing/joins.py BOARD --half H` | `$KICAD_PY` | Hand-specified track edits from `hardware/routing_joins.json` where the router can't reconnect a short gap |
| `routing/widen.py BOARD [--to 0.15]` | `$KICAD_PY` | Widen thin tracks to 0.15 mm wherever KiCad's DRC allows (the last step of `route.py`) |
| `routing/preroutes.py` | `$KICAD_PY` (module) | Scripted critical routes: the USB-C receptacle's paired pins on a half; the 5 V trunk on the dock, and its CC pull-downs' GND via |
| `checks/connectivity.py BOARD --half H` | `$KICAD_PY` | Every pad on its datasheet-intended net; LCSC number per designator; module GPIO table |
| `checks/clearance.py BOARD --half H` | `$KICAD_PY` | Part spacing, holes, edge, tenting puck, rule 2 sides, antenna keep-out (rule 6) |
| `checks/drc.py BOARD --half H` | python3 | KiCad DRC (zones refilled) with the allow-list in `hardware/drc_allow.json`; `--half dock` for the dock board |
| `mech/board_data.py [--check]` | `$KICAD_PY` | Each half's mechanical features (outline, holes, pads, courtyards, puck, discs, feet) → `mech/data/{left,right}.json` |
| `mech/build.sh [OUT]` | bash | STEP export of the halves and the dock board, `mech dock-geometry --check`, then the printed parts (`mech/`, build123d: cases, covers, the dock tray's two pieces) with their fit, hardware, insertion and dock pin checks, renders (`RENDER=0` skips) and slicing (`SLICE=0` skips) |
| `mech/slice.py STL_DIR OUT` | python3 | Bambu Studio slices for the A1 mini (system profiles, flattened); print time, weight and warnings → `slice.json` |
| `checks/hardware_all.sh [--out DIR] [ato args]` | bash | All of the above for both halves, after `ato_build.sh` (CI) |
| `render/placement_views.sh BOARD OUT`, `render/copper_views.sh BOARD OUT`, `render/svg_to_png.py` | bash/uv | 2D layer views for reports |
| `checks/panel_outline.py PANEL LEFT RIGHT` | `$KICAD_PY` | Each half's outline in the panel, apart from the tabs, within 2 µm (rule 1) |
| `checks/panel_fills.py PANEL LEFT RIGHT` | `$KICAD_PY` | The panel's GND pours equal the halves' apart from the mouse bites (no copper dropped by KiKit's refill) |
| `fab/build.sh [OUT]` | bash | Panel (KiKit, `hardware/panel.json`, `fab/panel_layout.py`; rules from `fab/panel_project.py`), panel outline and pour checks, panel DRC, Gerbers, BOM and CPL (`fab/jlc_assembly.py`), renders, copper SVGs, STEP |
| `dock/place.py [BOARD] [--check]` | `$KICAD_PY` | The dock board's outline and magnet cutouts from `dock-pcb/geometry.json` (written by `mech dock-geometry` from the tray), the contacts and USB-C where the geometry puts them, the rest from `dock-pcb/placement.json`; parts kept inside the parts area; visible designators; no tracks or vias under J1's shell (rule area J1_SHELL) |
| `dock/connectivity.py [BOARD]` | `$KICAD_PY` | Every dock pad on its datasheet-intended net, LCSC number per designator, no other nets |
| `dock/fab.sh [OUT]` | bash | Dock JLC bundle: placement, UUID, connectivity and DRC checks, Gerbers, top-side BOM and CPL (`fab/jlc_assembly.py --dock`), renders, copper SVGs, STEP |
| `lib/` | — | Shared helpers: S-expression reader/writer, `toolchain.env` reader |

Scripts that import `pcbnew` must stay Python 3.9-compatible (KiCad's bundled Python on macOS). Shell scripts must parse under macOS's bash 3.2. CI checks both.
