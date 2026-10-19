# BOM stock check

Checked against the JLC assembly library at 2026-10-18T18:22:46Z, for 5 panels (both halves each). Quantities are per half.

| LCSC | Part | Manufacturer | Package | Library | Qty/half | Needed | JLC stock | Role | Datasheet |
|---|---|---|---|---|---|---|---|---|---|
| C356849 | E73-2G4M08S1C | Chengdu Ebyte Elec Tech | SMD,18x13mm | extended | 1 | 10 | 1176 | nRF52840 module (Ebyte E73-2G4M08S1C) | [pdf](../../docs/datasheets/C356849_E73-2G4M08S1C.pdf) |
| C15220 | BQ24073RGTR | Texas Instruments | QFN-16-EP(3x3) | extended | 1 | 10 | 30700 | Li-ion charger with power path (TI BQ24073RGTR) | [pdf](../../docs/datasheets/C15220_BQ24073RGTR.pdf) |
| C165948 | TYPE-C-31-M-12 | Korean Hroparts Elec | SMD | extended | 1 | 10 | 361943 | USB-C receptacle, USB 2.0 (HRO TYPE-C-31-M-12) | [pdf](../../docs/datasheets/C165948_TYPE-C-31-M-12.pdf) |
| C7519 | USBLC6-2SC6 | STMicroelectronics | SOT-23-6L | extended | 1 | 10 | 33798 | USB D+/D- and VBUS ESD protection (ST USBLC6-2SC6) | [pdf](../../docs/datasheets/C7519_USBLC6-2SC6.pdf) |
| C191023 | 1N5819WS | Guangdong Hottech | SOD-323 | basic | 4 | 40 | 4264600 | Schottky diodes: USB VBUS and dock 5V into the charger input (D1, D2), CHG/PGOOD sense into GPIOs (D4, D5) (1N5819WS, SOD-323) | [pdf](../../docs/datasheets/C191023_1N5819WS.pdf) |
| C123790 | SMF6.0A | MDD(Microdiode Semiconductor) | SOD-123FL | extended | 1 | 10 | 115166 | TVS on the exposed dock 5V pad (SMF6.0A: 6.0 V standoff covers USB's 5.25 V) | [pdf](../../docs/datasheets/C123790_SMF6.0A.pdf) |
| C431540 | MSK12C02 | SHOU HAN | SMD,8x2.8mm | extended | 1 | 10 | 206702 | power slide switch between charger OUT and VDDH (MSK12C02) | [pdf](../../docs/datasheets/C431540_MSK12C02.pdf) |
| C720477 | TS-1088-AR02016 | XUNPU | SMD,4x3mm | basic | 1 | 10 | 624296 | reset button on P0.18 (TS-1088-AR02016) | [pdf](../../docs/datasheets/C720477_TS-1088-AR02016.pdf) |
| C409782 | MHT151RGBCT | MEIHUA | SMD-4P,3.2x1.6mm | extended | 2 | 20 | 13005 | reverse-mount RGB LEDs, common anode: status (GPIO) and charge (CHG/PGOOD) (MHT151RGBCT) | [pdf](../../docs/datasheets/C409782_MHT151RGBCT.pdf) |
| C25744 | 0402WGF1002TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | basic | 2 | 20 | 21197517 | 10k: charger TS (no thermistor); VBUS pull-down (holds VBUS low against D1's reverse leakage when docked) | [pdf](../../docs/datasheets/C25744_R0402_10k.pdf) |
| C25905 | 0402WGF5101TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | basic | 4 | 40 | 5087097 | 5.1k: USB-C CC1, CC2; charger ILIM, ISET | [pdf](../../docs/datasheets/C25905_R0402_5k1.pdf) |
| C11702 | 0402WGF1001TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | basic | 2 | 20 | 21695829 | 1k: charge LED red and green | [pdf](../../docs/datasheets/C11702_R0402_1k.pdf) |
| C25117 | 0402WGF4700TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | basic | 1 | 10 | 1343824 | 470R: status LED red | [pdf](../../docs/datasheets/C25117_R0402_470R.pdf) |
| C25091 | 0402WGF2200TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | basic | 2 | 20 | 2274516 | 220R: status LED green and blue (higher forward voltage than red) | [pdf](../../docs/datasheets/C25091_R0402_220R.pdf) |
| C23733 | CL05A475MP5NRNC | Samsung Electro-Mechanics | 0402 | basic | 1 | 10 | 2101461 | 4.7uF 10V 0402: VDD, the module regulator's output (the E73 datasheet doesn't say the module carries the nRF52840's 4.7 uF REG0 capacitor itself; phases 4-6 second review L3) | [pdf](../../docs/datasheets/C23733_C0402_4u7_10V.pdf) |
| C15849 | CL10A105KB8NNNC | Samsung Electro-Mechanics | 0603 | basic | 1 | 10 | 9246132 | 1uF 50V 0603: charger IN (sees up to 26 V on overvoltage) | [pdf](../../docs/datasheets/C15849_C0603_1uF_50V.pdf) |
| C19666 | CL10A475KO8NNNC | Samsung Electro-Mechanics | 0603 | basic | 1 | 10 | 3525848 | 4.7uF 16V 0603: nRF VBUS | [pdf](../../docs/datasheets/C19666_C0603_4u7_16V.pdf) |
| C19702 | CL10A106KP8NNNC | Samsung Electro-Mechanics | 0603 | basic | 3 | 30 | 11095152 | 10uF 10V 0603: VDDH bulk, charger OUT and BAT (4.7 uF minimum after DC bias at 4.4 V) | [pdf](../../docs/datasheets/C19702_C0603_10uF_10V.pdf) |

Problems: none
