# Dock PCB parts (phase 7 research)

`dock-pcb/parts.json` lists the parts chosen here; `scripts/parts/bom_check.py --dock` rechecks their stock (`dock-bom.md`).

**Check date: 2026-10-24.** Live stock comes from `python3 scripts/parts/jlc.py check ... --need 30`, run at **2026-10-24T14:38:48Z**. All 15 parts listed below passed with at least 30 in JLC stock. Prices are JLC assembly-library prices at check time, in USD per unit.
Datasheets were saved with `jlc.py datasheet` to `docs/datasheets/`.

## Update 2026-10-25: the dock redesign

The dock was redesigned before it was ordered (docs/ARCHITECTURE.md, decision log of 2026-10-25): the pins moved onto the halves, the dock went flat, and the USB-C moved to the back. What changes here:

- **The pogo pins (C5221284) leave the dock's BOM.** The owner buys six loose from LCSC and solders three on each half's TP1 pads with a printed jig. Live stock: 6,413 at 2026-10-25T13:57:53Z (`jlc.py check C5221284 --need 6`). The pin research in section 1 still holds: the same pin, the same 5.2 mm from the case's underside to the half's pads, now measured from the other end.
- **The dock's contacts are a footprint, not a part** (DOCK_CONTACTS, `scripts/parts/custom_parts.py --dock`): three bare 3.2 × 6.0 mm pads per half at the pins' 4 mm pitch, GND / 5 V / GND. Nothing is assembled on them, and **ENIG is required**: the pins press on bare copper finish, and HASL is neither flat nor wear-resistant.
- **USB-C: HRO TYPE-C-31-M-28A (C2848622), replacing C2927029.** The cover over the receptacle must be flush with the tray's top, 2.6 mm above the board, so the receptacle had to be mid-mount: its body sinks into a notch in the board and stands 1.58 mm above its top (a top-mount one stands 3.2 mm). It is power-only (6 pins: CC1, CC2, VBUS and GND twice), 5 A, 20 V, rated 3,000 mating cycles, which is plenty for a cable that stays plugged in. HRO also makes the keyboard's receptacle; its EasyEDA CAD imports. Its 3D model needs its own offset (review M2): placed with its legs on the footprint's slots, its mouth is 2.80 mm ahead of the front legs, as HRO's drawing gives (6.8 mm body, front legs 4.00 mm from its back), and that is what puts the mouth on the tray's back face. JLC stock 15,510 at 2026-10-25T13:57:41Z (`dock-bom.md`). Also in stock at the same search (2026-10-25T12:53:04Z): DEALON USB-TYPE-C-012 (C2927032), also mid-mount, only 912 in stock; and the recessed "TYPE-C 6P CB1.6/CB0.8 (073)" (C2858274, C2858273), rated 3 A and 5,000 cycles.
- **Footprint fixes** (`dock-pcb/parts.json`): the notch ends where HRO's layout puts it, 0.5 mm behind the rear legs, with a 1.0 mm round relief behind each inner corner so the router's radius stays off the housing. HRO's land pattern leaves 0.16 mm from the signal pads (A5, B5, A9, B9, A12, B12) to the notch's end, so the pads are trimmed 0.14 mm on the notch side (1.26 mm long), for the 0.3 mm copper-to-edge JLC needs; their back ends, where the tails solder, stay. The four shell legs are pin-in-paste, and the footprint's own Edge.Cuts is dropped (the board's notch comes from `geometry.json`).
- The fuse, TVS, CC resistors, LED and its resistor are unchanged.

## Recommendation

| Function | Part | LCSC | Why |
|---|---|---|---|
| Pogo pin (x6, 3 per half) | Yiyuan YTC1P-4020-01 | **C5221284** | True SMD with no tail. 6.0 mm free height and 1.4 mm stroke give 0.8 mm compression at 5.2 mm and leave 0.6 mm before it bottoms out. Thickest gold of the candidates. 6.4k in stock. The only good-fitting pin with EasyEDA CAD, so `import_lcsc.py` can import it. |
| USB-C receptacle | DEALON USB-TYPE-C-009 | **C2927029** | Power-only 6-pin, 5 A, 10,000 cycles, 27k stock. The EasyEDA symbol already names its pins VBUS/GND/CC1/CC2. |
| Polyfuse | Bourns MF-NSMF050-2 | **C75464** | 1206, 0.5 A hold / 1.0 A trip, 13.2 V max, 0.15 to 0.70 ohm. Reputable datasheet, 72k stock. |
| CC1, CC2 pull-downs (x2) | UNI-ROYAL 0402WGF5101TCE 5.1k | **C25905** | Basic part, the same one the keyboard uses. Each CC pin needs its own resistor. |
| Power LED | KENTO KT-0805G (green) | **C2297** | Basic part. JLC has no basic green 0603. |
| LED resistor | UNI-ROYAL 0402WGF2201TCE 2.2k | **C25879** | Basic part. Gives about 1.1 mA, a deliberately dim LED for a bedside dock. |
| VBUS TVS (optional) | MDD SMF6.0A | **C123790** | The keyboard's dock TVS. Its 6.0 V standoff covers USB's 5.25 V maximum (SMF5.0A does not). |

Suggested topology: USB-C VBUS → F1 polyfuse → node "5V". The TVS (D1), the LED and its resistor, and the center pogo pin of each half all hang off that node. The outer pogo pins, the USB GND pins and the shell go to GND. Each CC pin gets its own 5.1k resistor to GND. Putting the TVS *after* the fuse matters: a sustained overvoltage that makes the TVS conduct then trips the fuse instead of burning out the TVS.

Extended parts in this BOM: the pogo pin, the USB-C receptacle, the fuse and the TVS (four in total). JLC has no basic PTC fuse or 5 to 6 V TVS: every candidate I searched was extended.

---

## 1. Pogo pins

Requirement: the tip must reach a pad 5.2 mm above the dock PCB top (1.6 mm case floor + 3.6 mm air) with about 0.5 to 1.5 mm of compression. That means a free height of about 5.7 to 7.0 mm and at least 1 mm of stroke.

"Free" is the uncompressed height above the PCB top. "Bottom" is the fully compressed tip height (maximum compression).

| Rank | MPN (maker) | LCSC | Free height | Working height / bottom | At 5.2 mm: compression / reserve to bottom | Spring force | Body | Rating, plating | Mount, land pattern | JLC stock | Library | JLC price | Datasheet |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | YTC1P-4020-01 (Shenzhen Yiyuan) | C5221284 | 6.0 mm (barrel A=4.0 + plunger B=2.0) | stroke D=1.4 mm, so 4.6 mm (see note) | **0.8 / 0.6 mm** | 100 ±20 gf at "normal working height" | flange Ø2.0×0.5, barrel Ø1.5, domed plunger Ø0.9 | 12 V; 1.5 A (datasheet), LCSC lists 2.5 A; ≤100 mΩ. Plunger 10 µin Au, barrel 5 µin Au over Ni | Flat-flange SMD, no tail. EasyEDA footprint: Ø2.3 mm round SMD pad. EasyEDA 3D model is 6.0 mm tall (matches the datasheet) | 6,413 | extended | 0.158 @1, 0.127 @50, 0.093 @1000 | `docs/datasheets/C5221284_YTC1P-4020-01.pdf` |
| 2 | YTC1P-4020-01R (Shenzhen Yiyuan) | C48783831 | 6.00 ±0.15 | working 5.00, bottom 4.60 | 0.8 / 0.6 mm | 80 ±15 gf at 5.0 mm | same body as #1 | 12 V, 1 A, ≤50 mΩ. 1 µin Au flash | Flat-flange SMD. **No EasyEDA CAD** (the EasyEDA API returns 404), so it needs a hand-written atopile part. #1's Ø2.3 mm pad fits it | 836 | extended | 0.199 @1, 0.158 @50 | `docs/datasheets/C48783831_YTC1P-4020-01R.pdf` |
| 3 | KTR60003UT01-R (Dongguan KeRui) | C55342465 | 6.00 ±0.15 | normal working 5.10, max working 5.20, bottom 4.50 | 0.8 / 0.7 mm; 5.2 mm is the top of its working range | 30 ±8 gf at 5.1 mm | flange Ø2.0×0.5, barrel Ø1.5, plunger Ø0.9 | 12 V, 1 A, ≤50 mΩ. Plunger 3 µin Au | Flat-flange SMD. **No EasyEDA CAD** (404). #1's pad fits it | 1,050 | extended | 0.142 @1, 0.113 @50 | `docs/datasheets/C55342465_KTR60003UT01-R.pdf` |
| 4 | YZP0063-20068-01 (Xinyangze) | C5157248 | 6.00 ±0.15 above the flange | working 5.00, bottom 4.30 | 0.8 / 0.9 mm (best centered) | 25 gf ±20% at 5.0 mm | flange Ø2.0×0.5, barrel Ø1.5, R0.45 tip | 12 V, 1 A, ≤100 mΩ. 3 µin Au | **Ø0.7×0.8 mm locating tail.** EasyEDA footprint has a Ø0.8 mm hole plus a custom pad. Its 3D model is wrong: 5.0 mm above the board, the datasheet says 6.0. Datasheet p.4 shows bulk (bag) packaging | 401 | extended | 0.55 @1, 0.33 @100 | `docs/datasheets/C5157248_YZP0063-20068-01.pdf` |

Notes on the pogo pins:
- **#1's datasheet is a series table, and one of its columns is ambiguous.** It gives C = 4.6 mm for the 4020 size under the heading "Working Height", with D = 1.4 = 6.0 − 4.6. The same maker's drawing for the identical-body 4020-01R (#2) calls 4.6 mm "Max. Compression", and LCSC lists #1's "Operational Height" as 4.6 mm. **Treat 4.6 mm as the hard bottom.** Either reading gives 0.8 mm compression at 5.2 mm with 0.6 mm in reserve.
- **Tolerance stack.** Pin free height ±0.15 plus about ±0.25 for the printed tray, case and seating gives 0.4 to 1.2 mm of compression with #1, #2 or #3. None of them bottoms out. The solder under the flange raises the pin by about 0.05 mm, which adds compression slightly.
- **The 5.2 mm can only be tuned upward.** You can recess the PCB below the pocket floor. You cannot raise it, because the case floor rests on the pocket floor around the window. That is why all four ranked pins have their working height at or below 5.2 mm.
- **Spring force sets the magnet budget.** Contact force is the spring force alone. The magnets only keep the half from being lifted. With #1, 3 pins at up to about 100 to 120 gf push each half up with about 3 to 3.5 N. #3 (30 gf) pushes with only about 1 N. **Decided: #1** (2026-10-24, docs/ARCHITECTURE.md decision log): firmer contact, it is the only one of the four with EasyEDA CAD (so `import_lcsc.py` imports it and its 3D model checks the fit), and two N52 10 × 3 mm magnets per half outweigh its 3 to 3.5 N. #3 (light, a thinner contact-force margin) needs a hand-written part. Both are fine electrically at 100 mA on ENIG.
- #1, #2 and #3 have the same Ø2.0 flange and Ø0.9 tip, so the footprint geometry is interchangeable. Only #1 can be imported automatically.
- Pin tip Ø0.9 on the half's 2.5 × 4.0 mm pads leaves ±0.8 mm of lateral capture along the 2.5 mm side and ±1.55 mm along the 4.0 mm side. At 4.0 mm pitch with Ø2.3 mm dock pads, the copper gap between pins is 1.7 mm.
- No vendor in #1 to #3 gives a recommended land pattern. Use the EasyEDA Ø2.3 mm pad: a 0.15 mm fillet ring around the Ø2.0 flange.

Rejected (all live JLC parts checked the same day):
- BWCD-L6.5W2.0H2.0 C2826552 and L6.0 C2826551 (Bat Wireless; 4.7k and 4.9k stock, about $0.05 to $0.08, true SMD, 100 gf). The datasheet gives no stroke, working height or bottom height, only the exposed plunger length (2.0 mm). The EasyEDA 3D model for the L6.0 is 7.0 mm tall. Too risky for a fit-critical part.
- KTR65003UT01-R C55342466: free 6.5 mm, bottom 5.40 mm. It would bottom out at 5.2 mm.
- YZP0355-20072-02 C5157360: free 6.2, working 5.2, bottom 5.0. Only 0.2 mm reserve.
- YZ109515070R-01 C5157436: free 7.0, working 5.5, bottom 5.0. 1.8 mm compression and 0.2 mm reserve at 5.2 mm.
- YZP0061-15070-01 C5157356: free 5.8 mm with a tail. Only 0.6 mm compression at 5.2 mm.
- YTC1P-4520-01 C5221294: free 6.5, C = 5.1. If 5.1 is the bottom, that leaves 0.1 mm reserve.
- KH-204065-DZ C530676: free 6.5 mm, no stroke specified, 93 in stock.
- Xinyangze `…D-0x` parts (for example C5157458, 20k stock) are double-ended, not SMD. `…F-0x` parts are right-angle.

Through-hole pogo pins are not needed: several SMD pins fit the height.

## 2. USB-C receptacle

| MPN (maker) | LCSC | Contacts | Mounting | Body W×D×H | Rating | Durability | JLC stock | Library | JLC price | Datasheet |
|---|---|---|---|---|---|---|---|---|---|---|
| **USB-TYPE-C-009 (DEALON)** | **C2927029** | 6P: A5/B5 CC, A9/B9 VBUS, A12/B12 GND | Right-angle top-mount SMD, 4 THT shell legs (plated oval slots, 0.5×1.2 mm drill, 1.0×1.7 mm pads) | 8.94 × 6.80 × 3.2 mm | 5 A, 5 V | 10,000 cycles | 27,575 | extended | 0.043 @1, 0.034 @100 | `docs/datasheets/C2927029_USB-TYPE-C-009.pdf` |
| TYPE-C-31-M-17 (HRO) | C283540 | 6P, same pinout and footprint geometry | Right-angle top-mount SMD, 4 THT shell legs (0.6×1.2 mm slots) | 8.94 × 6.80 × 3.16 mm | 5 A, 20 V | 3,000 cycles | 17,203 | extended | 0.199 @1, 0.162 @50 | `docs/datasheets/C283540_TYPE-C-31-M-17.pdf` |
| TYPE-C-31-M-12 (HRO), the keyboard's part | C165948 | 16P (USB 2.0) | Right-angle **top-mount (not mid-mount)** SMD, 4 THT shell legs and 2 Ø0.5 locating pegs | 8.94 × 7.35 × 3.26 mm | 5 A, 20 V | 10,000 cycles | 326,194 | extended | 0.187 @1, 0.148 @50 | `docs/datasheets/C165948_TYPE-C-31-M-12.pdf` (already in repo) |

- C283540 is the drop-in alternate, from the same maker as the keyboard's receptacle. Its EasyEDA pins are numbered rather than named: 1=B12, 2=B9, 3=A5, 4=B5, 5=A9, 6=A12, and the shell is "0".
- C165948 would also work, but D+/D− stay unconnected and its 0.3 mm-pitch pads are finer than a power-only board needs.
- With only CC pull-downs (no PD), any source supplies 5 V only. Each CC pin gets its own 5.1 kΩ. A shared resistor is out of spec, and some sources then refuse to supply power.

## 3. Resettable polyfuse

| MPN (maker) | LCSC | Package | Ihold / Itrip (23 °C) | Vmax | R min / R1max | Trip time | JLC stock | Library | JLC price | Datasheet |
|---|---|---|---|---|---|---|---|---|---|---|
| **MF-NSMF050-2 (Bourns)** | **C75464** | 1206 | 0.50 / 1.00 A | 13.2 V (100 A Imax) | 0.15 / 0.70 Ω | ≤0.1 s at 8 A | 72,279 | extended | 0.059 @1, 0.046 @200 | `docs/datasheets/C75464_MF-NSMF050-2.pdf` |
| SMD0805B050TF (Brightking), alternate | C269104 | 0805 | 0.50 / 1.00 A | 6 V | 0.15 / 0.85 Ω | ≤0.1 s | 1,990,161 | extended | 0.024 @1 | (not saved) |

- Dock load is at most about 0.2 A (2 × about 95 mA for the BQ24073 in USB100 mode, plus the LED). That drops at most 0.14 V across the fuse at R1max.
- Ihold derates to 0.44 A at 40 °C and 0.32 A at 70 °C, which is still above the load.
- **What it guards against:** a coin or paper clip across the exposed 5V/GND pins when no half is docked.
- One fuse means a short at one half's pins also cuts power to the other half until the short is removed. Two fuses, one per half, would isolate the halves. That is optional.

## 4. CC resistors

| MPN (maker) | LCSC | Specs | JLC stock | Library | JLC price | Datasheet |
|---|---|---|---|---|---|---|
| **0402WGF5101TCE (UNI-ROYAL)** | **C25905** | 5.1 kΩ ±1%, 62.5 mW, 0402 thick film (the same part as on the keyboard) | 4,235,514 | **basic** | 0.0023 | `docs/datasheets/C25905_R0402_5k1.pdf` (already in repo) |

## 5. Power LED and resistor

| MPN (maker) | LCSC | Specs | JLC stock | Library | JLC price | Datasheet |
|---|---|---|---|---|---|---|
| **KT-0805G (Hubei KENTO)** | **C2297** | 0805 (2.0×1.25×0.85 mm), emerald green 525 nm. Vf 2.6 to 3.1 V and 175 to 430 mcd at 5 mA. 30 mA max | 2,421,893 | **basic** | 0.016 | `docs/datasheets/C2297_KT-0805G.pdf` |
| **0402WGF2201TCE (UNI-ROYAL)** | **C25879** | 2.2 kΩ ±1% 0402. (5 V − about 2.5 V) / 2.2 kΩ ≈ 1.1 mA | 3,058,021 | **basic** | 0.0011 | `docs/datasheets/C25879_R0402_2k2.pdf` |
| 0402WGF1001TCE (UNI-ROYAL), brighter option | C11702 | 1 kΩ, about 2.4 mA | 19,435,785 | basic | 0.0013 | `docs/datasheets/C11702_R0402_1k.pdf` (already in repo) |

- No basic green 0603 exists. KT-0603G (C12624) is extended, and Everlight 19-217/GHC (C72043) is out of stock.
- The 0805 is the basic choice.

## 6. VBUS TVS (optional)

| MPN (maker) | LCSC | Specs | JLC stock | Library | JLC price | Datasheet |
|---|---|---|---|---|---|---|
| **SMF6.0A (MDD)** | **C123790** | SOD-123FL, unidirectional. VRWM 6.0 V, VBR 7.37 V max, VC 10.3 V at 19.4 A, 200 W (10/1000 µs) | 114,027 | extended | 0.036 @1 | `docs/datasheets/C123790_SMF6.0A.pdf` (already in repo) |

It matches the keyboard's dock-pad TVS (ARCHITECTURE.md, 2026-10-18). Any SMF5.0A (for example C193402) has a 5.0 V standoff below USB's 5.25 V maximum, so it would leak.

---

## Mechanical notes for the dock and tray CAD

- **Pogo pin (#1).**
  - The Ø2.0 × 0.5 mm flange is soldered to the PCB top.
  - The Ø1.5 mm barrel, with a Ø1.54 ring, rises to 4.0 mm above the PCB.
  - The Ø0.9 mm plunger tip is at 6.0 mm free and about 5.2 mm when docked.
  - The flange (0 to 0.5 mm) and the barrel sit inside the case floor's thickness (0 to 1.6 mm), so **the case window must clear Ø2.0 flanges plus the Ø2.3 mm pads**. That is at least about 11 × 3 mm for the 3-pin row at 4 mm pitch, plus print tolerance.
  - The barrel tops stay 1.2 mm below the half's PCB underside when docked.
- **USB-C (C2927029 or C283540).**
  - The receptacle body sits on the PCB top: 8.94 × 6.80 × about 3.2 mm, with the shell front at the board edge per the footprint.
  - The plug axis is about 1.6 to 1.7 mm above the PCB top.
  - A USB-C plug overmold (up to about 12.4 × 6.5 mm) therefore reaches roughly to the underside of a 1.6 mm PCB. The tray needs an edge opening of about 13 × 7 mm centered on the plug axis, with nothing under the board edge in front of the connector.
  - DEALON's layout assumes a 1.6 ±0.1 mm board.
- **LED.** It is a top-side 0805, 0.85 mm tall. If the tray covers the PCB, the LED needs a hole or a thin, translucent spot in the print.
- **EasyEDA 3D models are not trustworthy for the pins.** The C5157248 and C2826551 models do not match their datasheets. Build the fit-check geometry from the datasheet dimensions above.
