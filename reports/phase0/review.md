# Phase 0 review: findings and dispositions

The reviewer subagent (artifacts only) ran on 2026-10-17 and reproduced each "verified" finding in throwaway repos. Every finding below was fixed or dispositioned. The fixes were checked against the reviewer's repro scripts and are covered by the round-trip steps listed.

## Critical

| # | Finding | Disposition |
|---|---|---|
| C1 | atopile deletes every footprint it doesn't own (e.g. a mounting hole placed through pcbnew), and the round-trip never covered it. | **Fixed, plus an architecture decision.** Every footprint is an atopile component, including mechanical ones as atomic parts with no LCSC number, an explicit `has_designator`, and footprint attributes `exclude_from_bom exclude_from_pos_files` (ARCHITECTURE.md decision log). Verified: such a part is placed, survives rebuilds, and stays out of the BOM. Round-trip step 2 places one, and step 9 shows that a foreign footprint gets deleted and the wrapper fails. |
| C2 | `fix_stale_nets.py` compared against HEAD, so after an uncommitted pcbnew save it moved correct copper onto the wrong net. | **Fixed.** `ato_build.sh` snapshots each board before `ato build` and uses the snapshot as the baseline for both `fix_stale_nets.py` and `board_diff.py`. fix_stale_nets now matches copper by UUID instead of inferring from net numbers; the first CI run showed that on Linux atopile zeroes such copper's net rather than leaving a stale number. board_diff now matches copper by geometry and fails on any net change that isn't a rename. Round-trip step 7 reproduces the reviewer's scenario. Mutation check: with the old HEAD baseline, step 7 fails ("via net 3 (MID) -> 2"). |
| C3 | CI had never run, `reports/phase0/` wasn't committed, and `review.md` was missing. | **Fixed** by this commit and push. The CI run is linked in README.md. |

## Major

| # | Finding | Disposition |
|---|---|---|
| M1 | board_diff and fix_stale_nets exited 0 whenever they found no baseline (a symlinked path, a moved board, a shallow clone). | **Fixed.** Paths go through `realpath`. A bad revision exits 2, and a missing baseline fails unless `--allow-new` is given. `board_history.sh` fails on a bad range, and new and renamed boards are handled explicitly. |
| M2 | `ato_build.sh` checked nothing, and exited 0, when the boards weren't under `layouts/`. Nothing exercised the wrapper. | **Fixed.** Boards are found anywhere in the project (excluding `build/` and backups), and zero boards after a build is a failure. The round-trip now runs every build through the wrapper. |
| M3 | A net renamed in place got orphaned to net 0, and board_diff failed. | **Fixed.** fix_stale_nets keeps the number when the old name is gone and the number now carries a name that didn't exist before. board_diff detects renames from pad nets and accepts copper that follows a rename. Round-trip step 8. |
| M4 | `--strict` wasn't "any difference": it ignored arc bulge, keepout rules, zone settings, DNP/BOM/position attributes, pad geometry, and design rules. | **Fixed.** The snapshot now covers all of those, plus footprint graphics, holes in zones, and Bezier control points. `--strict` also requires identical canonical pcbnew serialization (order-free item lists sorted). Every case in the reviewer's `bd_cases.py` now fails, and the no-op control passes. That stricter comparison exposed atopile's footprint-merge bug (README.md F6), which is now guarded against. |
| M5 | The local environment still points at KiCad 10, while SETUP.md claims it was switched. | **Fixed in docs, owner action pending.** SETUP.md states what `~/.zshrc` must contain. `ato_build.sh` and `run.sh` stop on a KiCad version mismatch (`toolchain.sh --kicad`), so a session on KiCad 10 fails immediately instead of producing KiCad 10 files. The owner chose to install side by side and update `~/.zshrc` themselves. |
| M6 | CI artifacts would silently not upload from the container job. | **Fixed.** The round-trip writes to `ci-out/` in the workspace, and upload-artifact uses `if-no-files-found: error`. |
| M7 | CI reinstalls atopile and KiKit with unpinned dependency trees. | **Fixed.** `constraints/atopile.txt` and `constraints/kikit.txt` are frozen from this machine (`scripts/freeze_constraints.sh`) and used by CI and SETUP.md. `toolchain.sh --local` reports drift. |
| M8 | CI never compares a commit with its parent. | **Fixed.** `scripts/checks/board_history.sh` checks every pushed commit's boards against the parent (full-depth checkout). Intended removals are declared with `Board-Diff-Allow:` trailers. Verified against the round-trip repo's history: a commit that drops a track fails, and passes once it carries the trailer. |

## Minor

| # | Finding | Disposition |
|---|---|---|
| m1 | The zone repair didn't update `net_name`, and F3 described the mechanism wrongly. | **Fixed.** Zones get `net_name` rewritten too, and F3 is reworded (pad-connected copper is recomputed by KiCad; free copper and zones are not). |
| m2 | Duplicate footprint keys produced false failures. | **Fixed.** Duplicates are keyed by UUID, and copper and drawings are multisets. The reviewer's `bd_dup.py` passes. |
| m3 | An environment variable could silently disable the format guardrail. | **Fixed.** No overrides at all; the guardrail prints the limits it applies. KiCad 10 evidence now comes from a separate probe script. |
| m4 | `ato_build.sh` hid board_diff's stderr and ran the guardrails only after `ato build`. | **Fixed.** Only known wx noise is filtered. The guardrails run before the build, so a KiCad 10 board gets the guardrail's message instead of atopile's parse error. |
| m5 | Evidence provenance: a hand-added line, overwritten logs, and a wrong file count. | **Fixed.** Evidence is regenerated by scripts only. Each build has its own log, and the Gerber count excludes directories (16). |
| m6 | `files.zip` (old docs) would be committed. | **Not committed.** It's the owner's file, left untracked; the owner can delete it. |
| m7 | The bash 3.2 and Python 3.9 rules aren't enforced. | **Fixed.** A CI job on macOS runs `/bin/bash -n` (3.2) on all scripts and compiles `scripts/` with Python 3.9. Locally, the round-trip itself runs under bash 3.2. |
| m8 | The documented verify step dirtied the repo. | **Fixed.** `run.sh` defaults to `scratch/`. |
| m9 | Phase 1 can't run in CI because `reference/` is gitignored. | **Deferred to phase 1**, recorded as an open item in ARCHITECTURE.md: commit the extracted geometry, or fetch the original repo at a pinned commit in CI. |
| m10 | PLAN.md still describes a KiCad 10 round-trip. | **Fixed.** The phase 0 text notes the fallback. |

## Nits

- `edit_board.py` docstring: fixed.
- "DNS removed July 2026" now has evidence: `upstream-checks.txt` quotes atopile#1829 ("Since ~2026-07-18").
- The via key includes the via type, and overlapping identical tracks are counted: fixed.
- Zone named "GND_TOP" on both layers: renamed to "GND".
- Fixture parts have no datasheets: not applicable. They are test fixtures that are never fabricated; rule 3 applies to BOM lines.
