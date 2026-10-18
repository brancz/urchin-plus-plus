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
| `lib/` | — | Shared helpers: S-expression reader/writer, `toolchain.env` reader |

Scripts that import `pcbnew` must stay Python 3.9-compatible (KiCad's bundled Python on macOS). Shell scripts must parse under macOS's bash 3.2. CI checks both.
