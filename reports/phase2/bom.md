# BOM stock check

Checked against the JLC assembly library at 2026-10-18T11:46:48Z, for 5 panels (both halves each). Quantities are per half.

| LCSC | Part | Manufacturer | Package | Library | Qty/half | Needed | JLC stock | Role | Datasheet |
|---|---|---|---|---|---|---|---|---|---|
| C356849 | E73-2G4M08S1C | Chengdu Ebyte Elec Tech | SMD,18x13mm | extended | 1 | 10 | 1174 | nRF52840 module (Ebyte E73-2G4M08S1C) | [pdf](../../docs/datasheets/C356849_E73-2G4M08S1C.pdf) |
| C15220 | BQ24073RGTR | Texas Instruments | QFN-16-EP(3x3) | extended | 1 | 10 | 30717 | Li-ion charger with power path (TI BQ24073RGTR) | [pdf](../../docs/datasheets/C15220_BQ24073RGTR.pdf) |
| C165948 | TYPE-C-31-M-12 | Korean Hroparts Elec | SMD | extended | 1 | 10 | 362231 | USB-C receptacle, USB 2.0 (HRO TYPE-C-31-M-12) | [pdf](../../docs/datasheets/C165948_TYPE-C-31-M-12.pdf) |
| C7519 | USBLC6-2SC6 | STMicroelectronics | SOT-23-6L | extended | 1 | 10 | 33987 | USB D+/D- and VBUS ESD protection (ST USBLC6-2SC6) | [pdf](../../docs/datasheets/C7519_USBLC6-2SC6.pdf) |
| C8598 | B5819W SL | Jiangsu Changjing Electronics Technology Co., Ltd. | SOD-123 | basic | 2 | 20 | 355451 | Schottky diodes: USB VBUS and dock 5V into the charger input (B5819W) | [pdf](../../docs/datasheets/C8598_B5819W.pdf) |
| C193402 | SMF5.0A | MDD(Microdiode Semiconductor) | SOD-123FL | extended | 1 | 10 | 557420 | TVS on the exposed dock 5V pad (SMF5.0A) | [pdf](../../docs/datasheets/C193402_SMF5.0A.pdf) |
| C431540 | MSK12C02 | SHOU HAN | SMD,8x2.8mm | extended | 1 | 10 | 207158 | power slide switch between charger OUT and VDDH (MSK12C02) | [pdf](../../docs/datasheets/C431540_MSK12C02.pdf) |
| C720477 | TS-1088-AR02016 | XUNPU | SMD,4x3mm | basic | 1 | 10 | 625888 | reset button on P0.18 (TS-1088-AR02016) | [pdf](../../docs/datasheets/C720477_TS-1088-AR02016.pdf) |
| C409782 | MHT151RGBCT | MEIHUA | SMD-4P,3.2x1.6mm | extended | 2 | 20 | 13327 | reverse-mount RGB LEDs, common anode: status (GPIO) and charge (CHG/PGOOD) (MHT151RGBCT) | [pdf](../../docs/datasheets/C409782_MHT151RGBCT.pdf) |
| C81598 | 1N4148W | ST(Semtech) | SOD-123 | basic | 2 | 20 | 4471433 | isolate the CHG and PGOOD GPIO reads from the charge LED's input-side supply (1N4148W) | [pdf](../../docs/datasheets/C81598_1N4148W.pdf) |
| C25744 | 0402WGF1002TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | basic | 1 | 10 | 21268709 | 10k: charger TS (no thermistor) | [pdf](../../docs/datasheets/C25744_R0402_10k.pdf) |
| C25905 | 0402WGF5101TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | basic | 4 | 40 | 5090682 | 5.1k: USB-C CC1, CC2; charger ILIM, ISET | [pdf](../../docs/datasheets/C25905_R0402_5k1.pdf) |
| C11702 | 0402WGF1001TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | basic | 2 | 20 | 21713612 | 1k: charge LED red and green | [pdf](../../docs/datasheets/C11702_R0402_1k.pdf) |
| C25117 | 0402WGF4700TCE | UNI-ROYAL(Uniroyal Elec) | 0402 | basic | 3 | 30 | 1344287 | 470R: status LED red, green, blue | [pdf](../../docs/datasheets/C25117_R0402_470R.pdf) |
| C1525 | CL05B104KO5NNNC | Samsung Electro-Mechanics | 0402 | basic | 1 | 10 | 29508857 | 100nF 0402: VDD | [pdf](../../docs/datasheets/C1525_C0402_100nF.pdf) |
| C15849 | CL10A105KB8NNNC | Samsung Electro-Mechanics | 0603 | basic | 1 | 10 | 9261920 | 1uF 50V 0603: charger IN (sees up to 26 V on overvoltage) | [pdf](../../docs/datasheets/C15849_C0603_1uF_50V.pdf) |
| C19666 | CL10A475KO8NNNC | Samsung Electro-Mechanics | 0603 | basic | 3 | 30 | 3529517 | 4.7uF 16V 0603: charger OUT, charger BAT, nRF VBUS | [pdf](../../docs/datasheets/C19666_C0603_4u7_16V.pdf) |
| C19702 | CL10A106KP8NNNC | Samsung Electro-Mechanics | 0603 | basic | 1 | 10 | 11153493 | 10uF 10V 0603: VDDH bulk | [pdf](../../docs/datasheets/C19702_C0603_10uF_10V.pdf) |

Problems: none
