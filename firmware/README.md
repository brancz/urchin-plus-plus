# firmware

ZMK firmware and the UF2 bootloader for urchin++ (phase 8).

| Path | What |
|---|---|
| `boards/urchin_pp/` | The ZMK board: `urchin_pp_left` (split central) and `urchin_pp_right`, Zephyr 4.1 board format. `urchin_pp.dtsi` holds what both halves share. The `*-pins.dtsi` and `*-layouts.dtsi` files are generated from `hardware/pinmap.json` and `hardware/geometry/urchin.json` by `scripts/firmware/gen_board.py`. |
| `drivers/`, `dts/bindings/` | `urchin,battery-power-aware`, the battery level ZMK reports (below) |
| `config/` | User config: `urchin_pp.keymap` (ported from brancz/urchin-zmk-firmware), `urchin_pp.conf`, and `west.yml` pinning ZMK, Zephyr and zmk-rgbled-widget to commits |
| `bootloader/urchin_pp/` | Board definition for the Adafruit nRF52 bootloader |
| `zephyr/module.yml`, `CMakeLists.txt`, `Kconfig` | Make this directory a Zephyr module (ZMK_EXTRA_MODULES) |

## Build

```sh
scripts/firmware/build.sh            # -> firmware/build/out/{urchin_pp_left,urchin_pp_right,settings_reset_*}.uf2
scripts/firmware/build_bootloader.sh # -> firmware/build/out/urchin_pp_bootloader-0.11.0_s140_6.1.1.hex, update-*.uf2
```

Both run in ZMK's build image (`ZMK_BUILD_IMAGE` in `toolchain.env`, pinned by digest), through Docker when `west` or the Zephyr SDK isn't installed locally. CI builds the same and attaches it as the `firmware` artifact. The first run downloads Zephyr and its modules into `firmware/build/ws`, which later runs reuse.

## Keymap

`config/urchin_pp.keymap` uses the Urchin's 34 positions: rows of 5 + 5 keys (0–29), then the thumbs (30 left outer, 31 left inner, 32 right inner, 33 right outer).

- Holding both left thumbs gives the settings layer: Bluetooth profiles, `&bootloader`, `&studio_unlock`. `&ind_bat` and `&ind_con` show the battery level and connection state on the status LED.
- ZMK Studio works over USB on the left half.

## First flash (bring-up, phase 9)

A new module has no bootloader. Flash it once over SWD, then everything else goes over USB.

1. Use an SWD probe whose I/O follows the target voltage (VTref), e.g. a J-Link. A blank module runs VDD at 1.8 V until the bootloader sets it to 3.3 V, and a fixed-3.3 V probe such as a Raspberry Pi Pico can't drive or read 1.8 V reliably.
2. Power the half from USB or its battery, with the power switch on: the switch sits between the charger and the module, so with it off the module has no supply even on USB. The probe doesn't power the board.
3. Connect to TP2, labelled on the silkscreen: G = GND, RS = reset, CK = SWDCLK, IO = SWDIO, V = VDD (to the probe's VTref).
4. Flash the bootloader with SoftDevice (pyOCD, version in `toolchain.env`):

   ```sh
   pyocd erase -t nrf52840 --chip     # a locked module (APPROTECT) is unlocked by this mass erase
   pyocd flash -t nrf52840 urchin_pp_bootloader-0.11.0_s140_6.1.1.hex
   ```

5. On its first start the bootloader programs VDD to 3.3 V (UICR.REGOUT0) and resets. Check with a meter that V reads about 3.3 V.
6. With USB connected, the half shows up as a drive named `URCHINPP`. Copy `urchin_pp_left.uf2` to the left half and `urchin_pp_right.uf2` to the right.

After that, double-tap the reset button (or use `&bootloader`) to get the `URCHINPP` drive again for updates. The bootloader is the same for both halves; the firmware is not, and nothing stops the wrong image from landing on a half. A half flashed with the other half's image shows dead or phantom keys: its key pins are the other half's LED and charger-status pins. No harm comes of it, because the LED outputs are open-drain, but flash the right image.

**Re-pairing the halves:** flash `settings_reset_left.uf2` and `settings_reset_right.uf2`, then the real firmware on both, and reset both halves at the same time.

## Behaviour

- **Status LED** (zmk-rgbled-widget): it blinks the battery level on start (green, yellow, red) and the connection state on profile changes.
- **Charge LED:** wired to the charger, no firmware: amber while charging, green when charged.
- **Battery level reported to the host.** The charger feeds the system from its input whenever input power is present, so VDDH reads its regulated 4.4 V instead of the cell. `urchin,battery-power-aware` reads the charger's PGOOD and CHG outputs at every sample and reports:
  - on battery: the measured level;
  - while charging: the last level measured before input power arrived;
  - once charged (seen on two samples in a row): 100 %.

  The last level on battery is also kept in a retention register (GPREGRET2), which survives resets and the wake from deep sleep. One case reads full while charging: after a power loss (battery disconnected) the half has no level measured on battery, and VDDH reads full until the first sample on battery.

  CHG is sampled over 600 ms, because it blinks at 2 Hz on a charger fault, and any active read counts as charging. The status pins' pull-ups are on only during a read.
- **Power:**
  - REG1 runs as DC/DC (the module has its inductors).
  - REG0 stays an LDO. Zephyr would enable its DC/DC if `&reg0` were enabled, and the module has no inductor for it.
  - The 32 kHz clock is the internal RC oscillator, because the module has no crystal.
  - P0.18 is the reset pin (`gpio-as-nreset`).
- **Deep sleep** after 30 minutes idle; any key wakes the half.

## Bootloader

One build of the Adafruit nRF52 bootloader serves both halves, and it drives no LED: each half's status-LED pins are key inputs on the other half.

- It enters update mode on a double-tap of reset.
- Its USB ID is the pid.codes test VID/PID 1209:0001, which is meant for private use and must not be used on a distributed product.
- The application lives at 0x26000 after SoftDevice S140 6.1.1, the same layout as nice!nano.
