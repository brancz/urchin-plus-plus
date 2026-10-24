# Phase 8: firmware

Date: 2026-10-24. Sources are in `firmware/` (overview and first-flash procedure in `firmware/README.md`); build scripts in `scripts/firmware/`.

## Exit criteria

| Criterion (docs/PLAN.md) | Result | Evidence |
|---|---|---|
| CI builds firmware for both halves | `scripts/firmware/build.sh` builds the left half (split central, ZMK Studio), the right half, and a settings-reset image per half in ZMK's pinned build image. | CI job `firmware`, artifact `firmware` |
| CI builds the bootloader | `scripts/firmware/build_bootloader.sh` builds the Adafruit nRF52 bootloader 0.11.0 for urchin++ in the same image. | same artifact |
| Artifacts attached to the run | CI run 40096653403 (commit aab083e): all jobs green; artifact `firmware` holds the six images and the frozen manifest, every file byte-identical to the local build on Apple Silicon | `gh run view 40096653403` |

## What is built

| Image | Flash | RAM | Use |
|---|---|---|---|
| `urchin_pp_left.uf2` | 256 KB of 792 KB | 71 KB of 256 KB | left half: keys, BLE to host and right half, USB HID, ZMK Studio over USB, status LED, battery |
| `urchin_pp_right.uf2` | 188 KB | 39 KB | right half (BLE peripheral) |
| `settings_reset_{left,right}.uf2` | 66 / 54 KB | 18 / 13 KB | clears pairings, for re-pairing the halves |
| `urchin_pp_bootloader-0.11.0_s140_6.1.1.hex` | bootloader 31.7 KB of 38 KB | — | MBR, SoftDevice S140 6.1.1 and the bootloader: the one-time flash over SWD |
| `update-urchin_pp_bootloader-0.11.0_nosd.uf2` | — | — | bootloader updates over UF2 |

Every project is pinned: ZMK, Zephyr and zmk-rgbled-widget by commit in `firmware/config/west.yml` (resolved: `west-manifest-frozen.yml` here), and the build image, bootloader and intelhex in `toolchain.env`.

## How it was checked

Without hardware the firmware can only be built and inspected. Each of these was read from the build output, not the sources:

- **Compiled devicetree** (`build/.../zephyr/zephyr.dts`):
  - REG0 `disabled`: Zephyr would turn on REG0's DC/DC if it were enabled, and the module has no inductor for it.
  - REG1 in DC/DC mode.
  - `uicr` has `gpio-as-nreset` (P0.18 is the reset button).
  - The 17 key GPIOs per half are active-low with pull-ups, in kscan order.
  - The LEDs are active-low and open-drain (flags 0x7).
  - `zmk,battery` points to the charger-aware wrapper around `zmk,battery-nrf-vddh`, with PGOOD and CHG on the GPIOs `hardware/pinmap.json` gives.
- **Resolved Kconfig** (`.config`):
  - the left half is split central with USB and BLE; the right half is a BLE peripheral;
  - the 32 kHz clock is the RC oscillator, calibrated, with the 500 ppm accuracy BLE requires;
  - TX power +8 dBm with the Bluetooth controller on;
  - battery reporting through `URCHIN_BATTERY_POWER_AWARE`;
  - `RGBLED_WIDGET`; `ZMK_STUDIO` on the left half; deep sleep;
  - UF2 family 0xADA52840, matching the bootloader.
- **Reproducibility:** the ZMK images rebuild byte-identical (phase 8 review), and so does the bootloader since `SOURCE_DATE_EPOCH` is set (two builds, identical hex and UF2).
- **Build warnings:** none from this repo's sources. The only warning left is ZMK's own `KSCAN` deprecation, which every ZMK build shows.
- **Generated pin files:** `scripts/firmware/gen_board.py` writes the kscan, LED and charger-status pins and the physical layout from `hardware/pinmap.json` and the geometry file. It refuses a half that:
  - misses a key or function;
  - uses a GPIO twice;
  - uses P0.18 or P0.09/P0.10.

  Tested with all three mutations. `--check` runs in every build.
- **Keymap:** `firmware/config/urchin_pp.keymap` is the owner's `config/urchin.keymap` (brancz/urchin-zmk-firmware at 5bfccc6), unchanged apart from the header and two additions on the settings layer (`&ind_bat`, `&ind_con`).

## Left for bring-up (phase 9)

- **First flash:** over SWD with a probe that follows VTref; then check that VDD rises from 1.8 V to 3.3 V after the bootloader's first start.
- **Function checks:**
  - every key on both halves (positions in `firmware/README.md`);
  - LED colours, which also confirm the pin-1 orientation;
  - pairing, Studio;
  - battery level on battery, while docked, and when charged;
  - deep-sleep wake.
- **Battery driver:** check its behaviour against the real charger:
  - while charging it holds the pre-charge level, also across a wake from deep sleep (GPREGRET2);
  - after two samples with charging done and input power present, it reports 100 %.
