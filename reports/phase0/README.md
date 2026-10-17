# Phase 0 — toolchain proof

Date: 2026-10-17. Machine: macOS (arm64), bash 3.2. CI: GitHub Actions, `kicad/kicad:9.0.9` image (bash 5) plus a macOS syntax job.

## Exit criteria

| Criterion (docs/PLAN.md) | Result | Evidence |
|---|---|---|
| Clean round-trip report | **KiCad 10.0.7: fails.** atopile can't rebuild a board KiCad 10 has saved. **KiCad 9.0.9** (the documented fallback): all 11 steps pass | `kicad10-probe/`, `roundtrip/` |
| CI green on an empty build | see "CI" below | GitHub Actions run |
| Exact tool versions and Freerouting checksum in SETUP.md | recorded; `scripts/checks/toolchain.sh --local` passes, including the frozen dependency trees | `docs/SETUP.md`, `toolchain.env`, `constraints/`, `roundtrip/toolchain.txt` |
| Repo layout, `.gitignore`, CI skeleton | done | repo root, `.github/workflows/ci.yml` |
| Reviewer pass | done; every finding fixed or dispositioned | `review.md` |

## Round-trip (`scripts/roundtrip/run.sh`, also run in CI)

The fixture (`scripts/roundtrip/fixture/`) is a two-resistor divider, a decoupling capacitor (LCSC C25744, C1525), and a mechanical M2 hole. It is built in a throwaway git repo, and every build goes through `scripts/ato_build.sh`, the same wrapper the real boards use.

| Step | What it proves | Result |
|---|---|---|
| 1 build | first build through the wrapper | 4 footprints, format 20241229 |
| 2 pcbnew edit | outline, moves and rotations, 2 tracks, a via, a two-layer GND zone, the hole placed; saved by KiCad 9 | DRC 0 errors, 0 unconnected |
| 3 rebuild | every edit survives: `board_diff --strict` (empty semantic diff, identical canonical pcbnew serialization) | pass; DRC identical to step 2 |
| 4 idempotent | a second rebuild and `ato build --frozen` change nothing | pass |
| 5 add a part | exactly one footprint added; nothing else changes | pass, after `fix_stale_nets` re-pointed 3 copper items atopile left on old net numbers |
| 6 stable | rebuild and `--frozen` change nothing after placing the new part | pass |
| 7 uncommitted save | net churn, then a pcbnew save without a commit (KiCad renumbers nets), then rebuild: a free MID via stays MID | pass |
| 8 rename | net MID → MIDPOINT in the circuit: copper follows, and board_diff reports a rename | pass |
| 9 foreign footprint | a footprint atopile didn't create is deleted by `ato build`, and the wrapper fails | pass (fails as expected) |
| 10 Freerouting | rip up, DSN export, Freerouting 2.5.0, SES import | 10 tracks + 1 via; DRC 0 errors, 0 unconnected |
| 11 KiKit | `kikit fab jlcpcb` | 16 Gerber/drill files |

Steps 2, 3, and 10 have DRC warnings only: `silk_overlap` and `silk_over_copper`, all from the easyeda2kicad footprints' own silkscreen (F5).

A mutation check confirmed that step 7 catches the problem it's meant to catch. With the wrapper's baseline switched back to HEAD (the original design), step 7 fails: the MID via gets "fixed" onto GND.

## KiCad 10 probe (`scripts/roundtrip/kicad10_probe.sh`)

atopile builds the fixture, and KiCad 10.0.7's pcbnew edits and saves it (format 20260206). Rebuilding then fails with `UnexpectedType in kicad.pcb.Layer field 'tenting'`, both with atopile 0.15.7 and with 0.15.9, the last CLI release. KiCad 10 writes `(tenting (front yes) (back yes))` into every board's setup, so every KiCad 10-saved board is affected.

## Findings about the toolchain

| # | Finding | Disposition |
|---|---|---|
| F1 | atopile (0.15.7 and 0.15.9) can't read any board saved by KiCad 10. | KiCad 9.0.9 per the fallback, installed side by side at `/Applications/KiCad9`. The guardrail rejects KiCad files newer than KiCad 9's formats, and every KiCad-using script checks the version first. |
| F2 | atopile's part server is gone: NXDOMAIN since about 2026-07-18 (atopile#1829). 0.15.8+ needs a login to a legacy endpoint (HTTP 401 without one), and the CLI is end-of-life (`upstream-checks.txt`). | All parts are local atomic parts from `scripts/parts/import_lcsc.py`, so builds are offline. Stay on 0.15.7, with its dependency tree frozen in `constraints/`. |
| F3 | atopile re-creates a net under a new number when fewer than 80% of its pads already carry its name, and leaves that net's tracks, vias, and zones behind: on macOS on the old, now meaningless number; on Linux (CI) on net 0. KiCad recomputes the net of copper that touches a pad on load, but copper that doesn't (stitching vias, stubs) and zones (resolved by `net_name`) end up on the wrong net or none. | `scripts/fix_stale_nets.py` matches every copper item by UUID to the pre-build snapshot and puts it back on the net it had there, renumbered or renamed as needed. The wrapper runs it on every build. Steps 5, 7, 8, on both platforms. |
| F4 | atopile deletes every footprint it didn't create. | Every footprint is an atopile part, mechanical ones too: atomic part, explicit `has_designator`, `exclude_from_bom`/`exclude_from_pos_files`. Steps 2 and 9. |
| F5 | easyeda2kicad footprints draw silkscreen over their own pads. | Open item for phase 2: check each footprint against its datasheet land pattern. |
| F6 | atopile re-syncs every footprint from its library on each build and matches items by geometry only, so two items with the same geometry on different layers get merged. Seen here: an F.CrtYd circle became B.CrtYd. | The guardrail rejects such footprints in `parts/`; `board_diff --mode build` fails if an existing footprint's graphics, pads, or attributes change while its library footprint doesn't. |
| F7 | `kicad-cli fp/sym upgrade` writes files in its own KiCad version's format. Parts first imported under KiCad 10 didn't load in KiCad 9. | The importer refuses a `kicad-cli` that isn't the pinned version; the guardrail checks every `.kicad_mod`/`.kicad_sym`. |
| F8 | `has_datasheet` makes `ato build` download the URL, and LCSC's is a product page. | The importer doesn't emit it. Datasheets go in `docs/datasheets/`. |
| F9 | Instance net-name traits on `ElectricPower.hv/lv` are ignored. | Open item for phase 2: name rails on plain signals. |
| F10 | KiKit's `fab jlcpcb --assembly` needs a schematic, and atopile produces none. | Open item for phase 6: BOM from atopile, CPL from `kicad-cli pcb export pos`. |

## CI

The first CI run is linked here once it has completed.

## Reproduce

```bash
scripts/checks/toolchain.sh --local
scripts/roundtrip/run.sh scratch/roundtrip reports/phase0/roundtrip
scripts/roundtrip/kicad10_probe.sh /Applications/KiCad/KiCad.app reports/phase0/kicad10-probe
scripts/roundtrip/upstream_checks.sh > reports/phase0/upstream-checks.txt
```
