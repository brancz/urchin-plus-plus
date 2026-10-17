# scripts

Every generator and check, runnable headless; CI runs the same scripts.

| Script | Runs with | Purpose |
|---|---|---|
| `ato_build.sh PROJECT [args]` | bash | The only way to run `ato build`: preflight and guardrails, pre-build snapshot, build, stale-net repair, board diff (build mode) per board |
| `fix_stale_nets.py BOARD --against BEFORE` | python3 | Re-point copper at nets atopile re-created or renamed |
| `parts/import_lcsc.py --parts-dir DIR C…` | python3 | LCSC part → atopile atomic part (easyeda2kicad + kicad-cli upgrade) |
| `freeze_constraints.sh [--check]` | bash | Freeze atopile's and KiKit's dependency trees into `constraints/` |
| `checks/board_diff.py BOARD …` | `$KICAD_PY` | Semantic board diff; fails on removals and copper net changes (`--mode build`: anything atopile shouldn't touch; `--strict`: any change) |
| `checks/board_history.sh RANGE` | bash | CI: every commit's boards vs their parent; `Board-Diff-Allow:` trailers for intended removals |
| `checks/kicad_guardrails.py PATH…` | python3 | Fail on files newer than KiCad 9, KiCad 10-only features, and footprints atopile would mangle |
| `checks/toolchain.sh [--local\|--kicad]` | bash | Installed tools match `toolchain.env` (and `constraints/` with `--local`) |
| `roundtrip/run.sh [WORK] [OUT]` | bash | Phase 0 toolchain proof: 11 steps through the wrapper, Freerouting, KiKit |
| `roundtrip/edit_board.py`, `pcb_ops.py`, `autoroute_smoke.py` | `$KICAD_PY` | pcbnew operations used by the round-trip |
| `roundtrip/kicad10_probe.sh KICAD10_APP [OUT]` | bash | Evidence that atopile can't rebuild a board KiCad 10 saved |
| `roundtrip/upstream_checks.sh` | bash | Evidence for the atopile part-server and end-of-life facts |
| `lib/` | — | Shared helpers: S-expression reader/writer, `toolchain.env` reader |

Scripts that import `pcbnew` must stay Python 3.9-compatible (KiCad's bundled Python on macOS). Shell scripts must parse under macOS's bash 3.2. CI checks both.
