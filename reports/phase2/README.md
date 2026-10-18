# Phase 2 — circuit and parts

Date: 2026-10-18.

## Exit criteria

| Criterion (docs/PLAN.md) | Result | Evidence |
|---|---|---|
| Netlist | Both halves build with `scripts/ato_build.sh hardware` (guardrails, snapshot, stale-net repair, board diff). `scripts/checks/connectivity.py` checks all 185 numbered pads per half against a netlist written from the datasheets' pin numbers, independent of the .ato sources. Both halves: OK. | `netlist-{left,right}.txt`, `connectivity-{left,right}.json` |
| BOM with LCSC numbers and stock check date | 18 LCSC parts per half (29 placements), all in the JLC assembly library and in stock for 5 panels, checked 2026-10-18T11:46:48Z. Per-half quantities match atopile's BOM of each half. Datasheets saved for every part. | `bom.md`, `bom-stock.json` |
| Pin map | Per half, generated from geometry by `scripts/circuit/gen_halves.py`: 17 keys + 5 GPIO functions on the module's free GPIOs. | `pinmap.md`, `hardware/pinmap.json` |
| Open items in ARCHITECTURE.md resolved | E73 stock/assembly/VDDH/crystal, socket, part stock and net naming resolved; battery and bottom space move to phase 3; footprints reviewed here | `footprints/footprints.md`, ARCHITECTURE.md |
| Review | | `review.md` |

## Circuit (per half; `hardware/core.ato` + generated `hardware/halves.ato`)

```
USB-C J1 ─ VBUS ─┬─ USBLC6 U3 (ESD on VBUS, D+, D-)
                 ├─ nRF52840 VBUS (USB only) + 4.7 uF
                 └─ B5819W D1 ─┐
dock TP1 5V ─ SMF5.0A D3 ─ B5819W D2 ─┴─ VIN ─ BQ24073 U2 IN (1 uF 50 V)
                                         │    ├─ OUT = VSYS (4.7 uF) ─ slide switch SW35 ─ VDDH (10 uF) ─ E73 U1
                                         │    ├─ BAT = VBAT (4.7 uF) ─ BT1 pads ─ protected LiPo
                                         │    ├─ TS 10 k, ILIM 5.1 k, ISET 5.1 k; EN1 = EN2 = /CE = TD = GND; TMR open
                                         │    ├─ /CHG ─ 1 k ─ LED2 red;  /CHG ─ 1N4148W D4 ─ CHG_SENSE GPIO
                                         │    └─ /PGOOD ─ 1 k ─ LED2 green; /PGOOD ─ 1N4148W D5 ─ PGOOD_SENSE GPIO
                                         └─ LED2 common anode (charge LED, input-powered)
E73 VDD (REG0 LDO out, 100 nF) ─ LED1 common anode; R/G/B cathodes ─ 470 R ─ GPIOs (status LED, active low)
P0.18 = RESET_N ─ SW36 to GND, and SWD pad;  SWD pads TP2: VDD, SWDIO, SWDCLK, RESET, GND
17 keys: one socket pad to its GPIO (internal pull-up, active low), the other to GND
```

Electrical choices, each in a sentence (details and reasons in the ARCHITECTURE.md decision log):

- **Charger in USB100 mode** limits the input to about 95 mA, so the small cell charges at about 0.45C. The BQ24073's lowest programmable fast-charge current (150 mA) would be too much.
- **BQ24073, not BQ24075:** its 4.4 V output stays under the module's 5.5 V maximum. The BQ24075's 5.5 V output wouldn't.
- **Diodes on both inputs** keep the exposed dock pads from ever carrying battery or USB voltage. The **TVS** clamps static on the dock pad.
- **nRF52840 VBUS from USB only**, so a docked half doesn't look USB-connected to ZMK. The dock state is read from PGOOD.
- **Power switch between charger OUT and VDDH**, so the battery charges while the half is switched off.
- **Charge LED on the charger input:** it costs no battery. Red = charging (CHG low), green = input good (PGOOD low), so amber = charging and green = done.
- **Sense diodes:** the GPIOs read CHG and PGOOD through diodes. A GPIO sees a low through the diode, and never sees the LED's input-side voltage (up to 5 V) when the pin is released.
- **REG0 as an LDO** (DCCH unconnected): the module lacks REG0's inductor. **LFRC** clock: the module has no 32 kHz crystal.

## Per-half GPIO maps

The module can't be mirrored (single-sided assembly). Both halves use it in the same orientation, antenna up into the old nice!nano notch. So the left half's keys face module pins 26–43 and the right half's face pins 1–10, and each half needs its own map. `gen_halves.py` matches the 17 keys and the five GPIO functions to the module's 29 free GPIOs (P0.18 reset and the NFC pins P0.09/P0.10 excluded). It minimizes the total path length, where a path runs around the module body and its antenna end (no board exists beyond the antenna). Inner-row pads and the pads next to the antenna cost a little more. For each key, the socket pad nearer the module is the GPIO and the other one is ground. Targets for the functions are their resistors and diodes in `hardware/placement.json` (first-cut placement; phase 3 refines it and reruns the generator if the targets move). ZMK takes the GPIO lists from `hardware/pinmap.json`.

## Parts

All parts come from live JLC data (`scripts/parts/jlc.py`, `bom_check.py`). Each is imported by `scripts/parts/import_lcsc.py` as an atopile atomic part with a bottom-side footprint. Where EasyEDA's symbol was wrong or ambiguous, the pin names come from the datasheet (`hardware/parts.json` `pin_names`, with the page cited). The reverse-mount LED's footprint was corrected to the datasheet's land pattern (`fixups`). Pad-only parts without an LCSC number (battery pads, dock contacts, SWD pads) are generated by `scripts/parts/custom_parts.py` and excluded from BOM and CPL.

## Reproduce

```
python3 scripts/circuit/gen_halves.py --check --md reports/phase2/pinmap.md
scripts/checks/hardware_all.sh            # gen check, ato_build.sh, connectivity per half
python3 scripts/parts/bom_check.py --json reports/phase2/bom-stock.json --md reports/phase2/bom.md
python3 scripts/parts/footprint_report.py reports/phase2/footprints
"$KICAD_PY" scripts/checks/connectivity.py hardware/layouts/left/left.kicad_pcb --half left --netlist reports/phase2/netlist-left.txt
```

The boards in `hardware/layouts/` hold every footprint, unplaced; placement is phase 3.
