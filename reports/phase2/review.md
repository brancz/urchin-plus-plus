# Phase 2 review: findings and dispositions

The reviewer subagent checked commit c2bc47d on 2026-10-18, using artifacts and datasheets only. It rebuilt the project on a scratch copy and ran nine deliberate mutations of the circuit and the part tables. It checked every pin of every part against its datasheet. Scratch material is in `scratch/review2/`.

It confirmed as correct:

- all 43 E73 module pins (table, footprint, bottom-mounted chirality)
- the BQ24073 configuration: USB100 at 95 mA, TS, ILIM, ISET, timers, TD, CE
- the USB-C, USBLC6-2, slide-switch, button and LED pinouts
- every diode polarity
- the expected netlist in `connectivity.py`
- the BOM: LCSC numbers, values, voltage ratings, per-half quantities and the stock date
- that no reserved pin is used
- that no absolute maximum is exceeded in any power-path state (switch off, docked, USB, both, battery only)

The fixes are in the commit that follows phase 3 ("Address phase 2 review …") unless noted.

| # | Finding | Disposition |
|---|---|---|
| H1 | The committed boards weren't what a rebuild produces, so `hardware_all.sh --frozen` (CI) failed. atopile moves a new mechanical footprint's reference field to its library layer on the second build. | **Fixed.** The phase 3 commit carries settled boards. `scripts/ato_build.sh` now rebuilds until an `ato build --frozen` changes nothing (at most 4 builds). The same mechanism catches the second case found since: a footprint swapped to another library part gets its pad nets only on the second build. |
| M1 | When docked, D1's reverse leakage (5–100 µA) charges VBUS toward VIN, so the nRF52840 would see USB power. | **Fixed.** R11, 10 kΩ from VBUS to GND (C25744, already in the BOM), holds VBUS under 1 V even at 100 µA leakage. It draws 0.5 mA from a USB host. |
| M2 | The checks missed swapped resistor values and a consistently misread module pin table. | **Fixed.** `connectivity.py` now checks the LCSC number of every assembled designator, which catches value swaps. It also holds its own copy of the E73 datasheet GPIO table (p.6), against which both `parts.json` and the pin map are checked. Re-running the reviewer's m2 (R1/R4 swap) and m4 (P0.02/P0.03 swap) now fails. |
| M3 | Routability of the pin map wasn't shown, given inner-row module pads and the left half's USB pins facing away from J1. | **Fixed (phase 4).** Freerouting routes both halves completely with the JLC rules (`reports/phase4/`). The inner-row pads escape through tented vias. The module datasheet's caution (p.8) is about high-frequency and power traces under the module. Key and LED lines are static. The bottom layer under the module's core is ground pour (a rule area keeps tracks and vias off it). The USB pair crosses under the module only on the far layer (F.Cu), with ground on the module side, which is what the datasheet allows. |
| L1 | In USB100 mode the charger's input-voltage regulation (4.35–4.63 V) can throttle charging when the source sags, because the Schottky drops about 0.33 V. | **Accepted, noted for bring-up** (phase 9): check VIN while docked. A 5.0 V dock with short wiring stays above 4.6 V. |
| L2 | Thin logic-low margin on the CHG/PGOOD sense inputs through 1N4148W (about 0.8 V against a 0.99 V limit). | **Fixed.** D4/D5 are now B5819W Schottky diodes (already in the BOM; Vf about 0.25 V at 0.25 mA), so the input sees about 0.45 V. 1N4148W removed. |
| L3 | Status LED green and blue would be dim (high forward voltage) at 470 Ω. | **Fixed.** Green and blue use 220 Ω (C25091, basic part): about 2.5 mA typical, at most 3.6 mA, within standard drive. Red stays at 470 Ω. P0.30 (low-frequency pin) carries only a static LED level. |
| L4 | 4.7 µF X5R 0603 on the charger's OUT and BAT keeps only about half its value at 4.2–4.4 V, below the 4.7 µF minimum. | **Fixed.** C3/C4 are 10 µF 10 V (C19702, already in the BOM). |
| L5 | (a) Thermal pad gets 100 % paste. (b) The bottom-side footprints were the left-right mirror turned by 180°, and every pad kept an extra 180°, so custom pad shapes (the QFN thermal pad's notch) sat rotated about their centres. | (a) **Accepted.** 100 % paste on a 1.7 mm thermal pad is EasyEDA/JLC's own pattern for this part and common at JLC. (b) **Fixed** in `footprint_to_bottom.py`: the footprint is turned back to 0° before writing, and the texts keep their angles. All parts were re-imported. A pcbnew comparison shows every pad position, size, graphic and text identical, with only the custom pad shapes now correct (the notch is next to pin 1). The pad positions are KiCad's native bottom-side representation; phase 6 uses KiCad's standard bottom-side rotation handling and checks every part in JLC's preview. |
| L6 | Locating posts modelled as plated holes without copper; USB-C shell legs have no paste. | **Fixed** (phase 3): unnumbered plated holes without a ring become non-plated in the import. The shell legs: JLC assembles C165948 routinely with this footprint. The JLC upload checklist (phase 6) includes confirming the leg soldering. |
| L7 | SMF5.0A standoff (5.0 V) is below USB's 5.25 V. The 28 V rationale doesn't hold for the exposed pads. | **Fixed.** SMF6.0A (C123790, MDD, 6.0 V standoff). ARCHITECTURE.md's power-path text now says the TVS clamps ESD and transients, and that a sustained source above about 7 V would destroy the TVS (it fails short, protecting the rest). |
| L8 | Small land-pattern deviations (E73 pad width, B5819W, switch, USB-C slots, USBLC6, 0402). | **Accepted.** All within normal tolerance and JLC's own library footprints. No change. |
| L9 | Documentation errors. | **Fixed.** Placement count (29), PLAN status, the first-flash probe (ARCHITECTURE and PLAN now say a probe that follows the target voltage, e.g. J-Link), the battery text, and a note in `footprints.md` that the LED land pattern is shown front-side (the datasheet draws the reverse type from the light side). The 1N4148W manufacturer question is moot (part removed). |
| L10 | CI doesn't regenerate the committed reports; `bom_check.py` isn't in CI. | **Partly fixed.** CI runs `bom_check.py` as an informational step (network-dependent, so it doesn't fail the build). Phase reports are dated snapshots, not regenerated. Each README lists the commands that reproduce it. |
| L11 | The antenna keep-out has no datasheet dimension; keys sit on the pins next to the antenna. | **Fixed.** The pins next to the antenna are excluded where their traces would run along the antenna end: P1.11, P1.10 and P1.06 on the left half, and P1.06 on the right half, where pins 1 and 2 face the keys and are needed for routing (decision log). The keep-out definition and its rationale are in the phase 3 decision log. |
| L12 | No battery temperature sensing (fixed 10 kΩ on TS); nothing prevents soldering the battery reversed. | **Accepted, recorded.** A protected cell with its own protection board. BT1 is marked + and −. Bring-up step 2 measures polarity at the pads before the cell is connected. |
