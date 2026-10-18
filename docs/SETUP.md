# urchin++ setup

Machine: macOS with Homebrew. CI must use the same tool versions.

`toolchain.env` at the repo root holds the same pins in machine-readable form; CI loads it, and `scripts/checks/toolchain.sh` compares it with what is installed. Change a version there and here together. atopile and KiKit pin few of their own dependencies, so their full trees are frozen in `constraints/` (`scripts/freeze_constraints.sh` regenerates them from this machine; `--check` reports drift); install both with those files as above.

## Tool versions (pinned)

| Tool | Version | Install |
|---|---|---|
| KiCad | 9.0.9 | `kicad-unified-universal-9.0.9.dmg` from the KiCad 9.0.9 release (kicad.org or `github.com/KiCad/kicad-source-mirror/releases/tag/9.0.9`), SHA-256 `75d16b7556c027e948bfe8836b1b419a6925bb6a8391339eabd9b9c8d1737df3`. Copy the DMG's `KiCad` folder to `/Applications/KiCad9` (`ditto`). Not the Homebrew cask: it tracks KiCad 10, which stays installed at `/Applications/KiCad` for other projects. |
| atopile | 0.15.7 | `uv tool install atopile==0.15.7 --python 3.14 --constraints constraints/atopile.txt --constraints constraints/atopile-extra.txt` |
| KiKit | 1.8.1 | `"$KICAD_PY" -m pip install -c constraints/kikit.txt kikit==1.8.1` (must live in KiCad's Python) |
| Freerouting | 2.5.0 | `freerouting-2.5.0.jar` from the freerouting GitHub release v2.5.0, saved as `~/tools/freerouting.jar` |
| Freerouting jar SHA-256 | `f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7` | Matches the digest GitHub publishes for the release asset (checked 2026-10-17). CI downloads the jar and verifies this hash. |
| Java | 27 locally (Homebrew `openjdk`); Temurin 25 in CI | Freerouting 2.5.0 needs Java 25+ |
| uv | 0.13.1 | Homebrew `uv`; CI pins the same version |
| easyeda2kicad | 1.0.1 | `uv tool install easyeda2kicad==1.0.1` |
| pyOCD | 0.45.1 | `uv tool install pyocd==0.45.1`, then `pyocd pack install nrf52840` (installs `NordicSemiconductor.nRF_DeviceFamilyPack` 8.44.1) |
| build123d | 0.13.0, locked in `dock/uv.lock` | `uv add build123d ocp_vscode` inside `dock/` |

CI runs in the official `kicad/kicad:9.0.9` Docker image, pinned by digest in `.github/workflows/ci.yml` and `toolchain.env`. The KiCad 9 PPA (`ppa:kicad/kicad-9.0-releases`, `9.0.9~ubuntu24.04.1`) is the fallback if that image ever disappears; PPAs drop superseded versions, so don't pin CI to it by default.

Pitfalls already hit:
- atopile on Python 3.13 silently installs old releases (0.2.x, 0.12.x). Newer releases need Python 3.14, so always install with `--python 3.14` and pin the version.
- Freerouting 2.5.0 fails on Java 21 with `UnsupportedClassVersionError` (class file 69). Use Java 25+.
- atopile can't read boards saved by KiCad 10 (`UnexpectedType in kicad.pcb.Layer field 'tenting'`), in 0.15.7 and 0.15.9 alike. That's why KiCad is 9.0.9. KiCad 10 is still installed on this Mac and is the default app for `.kicad_pcb` files: open project boards with `/Applications/KiCad9/KiCad.app` only. Saving in KiCad 10 converts the file, and `scripts/checks/kicad_guardrails.py` will reject it.
- Library files (`.kicad_mod`, `.kicad_sym`) written by a newer `kicad-cli` don't load in KiCad 9. `scripts/parts/import_lcsc.py` refuses to run unless `kicad-cli` on PATH is the pinned version, and the guardrail checks `parts/`.
- atopile's part server is gone: `components.atopileapi.com` stopped resolving in July 2026, 0.15.8+ needs `ato auth login` for a legacy endpoint, and the CLI is end-of-life (replaced by the hosted app at app.atopile.io, 0.16+). Generic parts (`new Resistor` with a value) therefore fail at "Picking parts". Every part is a local atomic part made by `scripts/parts/import_lcsc.py`, so builds need no network.
- Don't put `has_datasheet` on parts: `ato build` then tries to download it, and LCSC's URL is a product page. Datasheets live in `docs/datasheets/`.
- Run `ato build` only through `scripts/ato_build.sh` (see CLAUDE.md rule 5 and reports/phase0/).
- atopile deletes every footprint it didn't create, and re-syncs the ones it did from their library on each build, matching items by geometry only. So mechanical footprints must be atopile parts, footprint edits go into the part's `.kicad_mod` (never the board), and a footprint must not have two same-type items with identical geometry on different layers (the guardrail checks).
- atopile flips a footprint to its library's side and back on every build, and that corrupts bottom-side text rotations. Bottom-side parts therefore get bottom-side library footprints (`import_lcsc.py` does this by default); never flip a part on the board. KiCad's footprint editor saves library footprints front-side, so don't re-save part footprints in it.
- atopile drops content it doesn't model: locks (footprints, tracks, zones), zones inside footprints, `fp_curve`, text boxes, groups. The guardrail refuses boards and parts that contain them.
- `scripts/ato_build.sh` restores the boards if the build or a check fails; the failed result is in `<project>/build/ato_build-failed/`.
- macOS ships bash 3.2; shell scripts must parse with it (`bash -n`). It misreads quotes and parens inside `"$(...)"` and `${var:?message}`.
- KiCad's Python on macOS is 3.9: scripts that import `pcbnew` must stay 3.9-compatible.

## Environment (`~/.zshrc`)

KiCad 10 stays installed at `/Applications/KiCad`, so these lines must point at `/Applications/KiCad9`. Scripts that use KiCad check the version first (`scripts/checks/toolchain.sh --kicad`) and stop if they find KiCad 10.

```bash
export PATH="/Applications/KiCad9/KiCad.app/Contents/MacOS:$PATH"
export KICAD_PY="/Applications/KiCad9/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"
export FREEROUTING_JAR="$HOME/tools/freerouting.jar"
export PATH="$(brew --prefix openjdk)/bin:$PATH"
```

## Verify

```bash
scripts/checks/toolchain.sh --local                    # every pinned version and the jar hash
"$KICAD_PY" -m kikit.ui --help | head -1
java -jar "$FREEROUTING_JAR" -help | head -3           # Freerouting v2.5.0
pyocd list                                             # lists the Pico once connected
scripts/roundtrip/run.sh                               # full toolchain proof, ~2 min; output in scratch/roundtrip-report
```

## Hardware for bring-up

- Raspberry Pi Pico flashed with `debugprobe_on_pico.uf2` (raspberrypi/debugprobe releases; hold BOOTSEL, plug in, drag the file)
- Jumper wires for the SWD pads
- Multimeter
- 3D printer or JLC's 3D printing service (PETG) for the dock tray
- Neodymium disc magnets and thin steel discs (sizes chosen in phase 7)
- Two protected LiPo cells (chosen in phase 3)

## Fallback: KiCad 9 (used 2026-10-17)

The phase 0 round-trip failed on KiCad 10.0.7 (reports/phase0/), so the fallback was applied, side by side rather than replacing KiCad 10 (owner's choice): KiCad 9.0.9 from the DMG above into `/Applications/KiCad9`, KiKit 1.8.1 installed into its Python, verify block rerun. `~/.zshrc` must point at it as shown above.
