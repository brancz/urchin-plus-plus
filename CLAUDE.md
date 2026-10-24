# urchin++ — standing brief

An integrated, wireless version of the Urchin split keyboard. The nice!nano daughter board is replaced by on-board electronics, and each half charges overnight by being dropped into a magnetic pogo-pin dock. Fabrication and assembly are at JLCPCB. Every design and verification step is done by AI agents; the human approves at three gates.

Read these before doing anything:

- `docs/PLAN.md`: goals, success criteria, phases, gates, and current status. **Update its status section whenever a phase moves.**
- `docs/ARCHITECTURE.md`: every hardware and tooling decision, with its rationale. **Append to its decision log when you make or change a decision.**
- `docs/SETUP.md`: machine setup, tool versions, and environment variables.

## Hard rules

1. **Exact layout.** Switch positions, rotations, the board outline, and the tenting-puck mount come from `reference/urchin/main.kicad_pcb` by script. Never redraw or approximate them. Any change to key geometry is a bug.
2. **Single-sided assembly.** Every assembled part goes on the bottom (B.Cu). Only switches and the battery are on top.
3. **Parts come from live JLC/LCSC data.** Every BOM line has an LCSC number checked for stock at the time of the check, and the check date is recorded in the BOM notes. Save each part's datasheet PDF to `docs/datasheets/<LCSC#>_<part>.pdf`.
4. **Pinned toolchain.** KiCad 9.0.9 (KiCad 10 failed the phase 0 round-trip; see ARCHITECTURE.md), atopile 0.15.7, Freerouting 2.5.0 (verify the jar's SHA-256 against `docs/SETUP.md`), KiKit 1.8.1, Java 25+ (Temurin 25 in CI). CI uses exactly the same versions; `toolchain.env` holds the pins and `scripts/checks/toolchain.sh` checks them.
5. **KiCad guardrails.** Never save a project board with KiCad 10, and use no KiCad 10-only board features: no via protection (IPC-4761) settings, no design variants, no time-domain tuning. Run `ato build` only through `scripts/ato_build.sh`: it runs `scripts/checks/kicad_guardrails.py`, snapshots every board, repairs net numbers atopile leaves stale, and runs `scripts/checks/board_diff.py` against the snapshot, failing on any unexpected removal of tracks, zones, vias, footprints, or footprint fields, and on anything else atopile has no business changing. CI also compares every pushed commit's boards with their parent (`scripts/checks/board_history.sh`); declare intended removals with a `Board-Diff-Allow:` commit trailer. Every footprint on a board must be an atopile component, mechanical ones included (tenting-puck mount, holes, logos): atopile deletes all others on each build.
6. **The antenna zone is sacred.** No copper on any layer, no traces, no parts, and no battery inside the module's antenna keep-out from its datasheet. A check script enforces it.
7. **Nothing is "done" without evidence.** Each phase ends with the outputs listed in `docs/PLAN.md` (reports, renders, diffs) committed under `reports/<phase>/`, and a `reviewer` subagent pass.
8. **Never order, never post anything externally.** The human uploads to JLC.

## Repo layout (target)

```
CLAUDE.md
toolchain.env    pinned tool versions (read by CI and scripts/checks/toolchain.sh)
docs/            PLAN.md, ARCHITECTURE.md, SETUP.md, datasheets/
hardware/        atopile project (ato.yaml, .ato sources, KiCad layouts for keyboard halves)
dock-pcb/        atopile project for the dock board
scripts/         geometry extraction, placement, routing, checks/ (all Python/shell, run headless)
reports/         per-phase evidence: DRC/ERC output, renders, diffs, reviewer findings
fab/             generated JLC outputs (gitignored; release builds attached to git tags)
mech/            build123d CAD (uv project): printed cases, battery covers, dock tray → STL
firmware/        ZMK module: board definition, keymap, bootloader build config
.github/workflows/  CI
reference/       original Urchin (gitignored, read-only)
scratch/         throwaway experiments (gitignored)
```

## How to run things

- KiCad Python: `"$KICAD_PY" script.py` (pcbnew only imports from KiCad's bundled Python).
- KiKit: `"$KICAD_PY" -m kikit.ui ...`
- Freerouting headless: `java -jar "$FREEROUTING_JAR" -de in.dsn -do out.ses`
- atopile: `scripts/ato_build.sh hardware` (never bare `ato build`). New parts: `python3 scripts/parts/import_lcsc.py --parts-dir hardware/parts C12345` (bottom-side footprint by default); atopile's own part picker no longer works. No locks and no footprint-owned zones: atopile drops them (keep-outs are board-level rule areas).
- Toolchain proof: `scripts/roundtrip/run.sh` (also runs in CI).
- Printed parts: `scripts/mech/build.sh OUT` (STEP export, build123d parts, fit checks, renders, Bambu Studio slicing; CI runs it with `RENDER=0`, and slicing is local only).
- Every generator and check is a script in `scripts/` that the CI workflow also runs. Avoid one-off commands that aren't captured in a script.

## Reviews

At every phase gate, invoke the `reviewer` subagent (`.claude/agents/reviewer.md`). Give it only artifacts and datasheets, never your reasoning. Fix or explicitly disposition every finding in `reports/<phase>/review.md` before asking the human to approve.

## Working style

The human is a very senior software engineer, not an electronics engineer. Be direct. Explain electrical decisions in a sentence when they matter. Ask when a decision isn't covered by ARCHITECTURE.md rather than guessing, and record the answer there.
