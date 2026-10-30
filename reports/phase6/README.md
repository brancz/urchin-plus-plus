# Phase 6 — fabrication outputs

Date: 2026-10-18. `scripts/fab/build.sh` builds the bundle: locally into `fab/` (gitignored), and in CI as the `jlc-bundle` artifact.

## The bundle

| File | What |
|---|---|
| `fab/jlc/urchin-panel-2designs-gerbers.zip` | Gerbers and drill files of the panel: copper, mask, paste, silkscreen, outline, plated and non-plated drill (KiKit `fab jlcpcb`) |
| `fab/jlc/bom.csv` | BOM in JLC's format (Comment, Designator, Footprint, LCSC Part #), 18 lines. Copy: `bom.csv` here |
| `fab/jlc/positions.csv` | CPL (Designator, Mid X, Mid Y, Layer, Rotation), 60 placements, all on the bottom (B). Copy: `positions.csv` here |
| `fab/panel/panel.kicad_pcb` | The panel; layout described below |
| `fab/panel/drc.md` | Panel DRC: 0 errors; the excused ones are all inherited (copy here) |
| `fab/panel/outline.txt` | Each half's outline in the panel against the half (`scripts/checks/panel_outline.py`; copy here) |
| `fab/panel/fills.txt` | Each half's GND pours in the panel against the half's (`scripts/checks/panel_fills.py`; copy here) |
| `fab/step/{left,right}.step` | 3D models of the halves |
| `fab/render/panel-{top,bottom}.png` | Renders of the bare panel (copies here). The panel can't resolve the parts' 3D models, so the halves' renders with parts are in `reports/phase4/` |

**The panel.** 239.6 × 105.65 mm (outline), 2 layers, 1.6 mm.

- Both halves sit where the original panel had them, with a 2.54 mm gap.
- A 5 mm frame runs on all four sides, 3 mm from the boards at the top and bottom and 4 mm at the sides. The USB-C receptacle and the slide switch reach 1 mm past each half's short edge, so that edge needs a frame too.
- Each half has seven tabs. Six are 4 mm wide: two to the top frame, two to the bottom, and the original two across the gap. The seventh, 2 mm wide, goes to the side frame beside the antenna. There the keep-out keeps copper away from its mouse bites, and they leave 0.95 mm of board to the case hole in the ear.
  - Each gap tab is shared by both halves and carries a row of mouse bites on each side. JLC's viewer therefore shows 12 bridges in all: 4 top, 4 bottom, 2 across the gap, 2 at the sides.
  - Mouse bites are 0.5 mm holes at 1.0 mm, 0.1 mm inside the board edge, placed clear of the original's overhanging socket pads.
- There are 3 tooling holes of 1.152 mm in the frame corners (top left, top right, bottom left) and 3 fiducials on each side next to them (1 mm copper, 2 mm mask opening).
- Each half is 109.6 × 89.7 mm.

Designators carry a side suffix (`U1_L`, `U1_R`), and nets an `L-`/`R-` prefix. The silkscreen prints the suffixed designators, because they are what the BOM and CPL name.

**The CPL.** atopile writes no schematic, so `kikit fab jlcpcb --assembly` can't run. `scripts/fab/jlc_assembly.py` computes the positions with the same KiKit functions, for KiCad's native bottom-side footprints: Y negated, rotation = 180° − KiCad angle. The footprints are JLC's own (EasyEDA), so no per-part corrections apply. The script fails if:

- a placed part has no LCSC number;
- anything assembled is on the top;
- per-half quantities differ from `hardware/parts.json`.

**Parts.** 18 LCSC parts; stock checked 2026-10-18T18:22Z for 5 panels (`bom.md`).

- **Basic (11):** resistors, capacitors, 1N5819WS, TS-1088.
- **Extended (7), each with JLC's extended-part fee:**
  - E73-2G4M08S1C (C356849), with the lowest stock: 1 176;
  - BQ24073RGTR (C15220);
  - TYPE-C-31-M-12 (C165948);
  - USBLC6-2SC6 (C7519);
  - SMF6.0A (C123790);
  - MSK12C02 (C431540);
  - MHT151RGBCT (C409782).

## JLC upload checklist (gate 3, done by the human)

**PCB:**

- [ ] Upload `urchin-panel-2designs-gerbers.zip`. JLC's viewer should show 2 layers: the frame, two halves, 12 bridges with mouse bites, 3 tooling holes and the fiducials.
- [ ] **Different Design: 2.** The panel holds two different boards, the left and the right half. JLC's form defaults to 1, and JLC then finds the second design in review and holds the order until a supplement is paid (the first order, 2026-10-25: $14.60 with VAT).
- [ ] **Base material** FR-4, **2 layers**, **1.6 mm**, 1 oz copper.
- [ ] **Surface finish ENIG**: the dock contacts need it.
- [ ] **Solder mask green.** The USB-C receptacle and the charger QFN have 0.5 mm pitch with 0.2 mm mask dams between pads. JLC holds dams that narrow reliably only in green; other colours need wider dams.
- [ ] **Delivery format "Panel by Customer".** Edge rails: none to add; the frame is in the Gerbers. Panel size as above.
- [ ] **Remove mark / order number:** JLC's default placement is fine; nothing is reserved for it.
- [ ] **Quantity:** 5 panels, JLC's minimum, is 5 keyboards. PCBA can be fewer (2 or more).

**If JLC's DFM check or an engineer asks about these, they are intended:**

- **Pads past the board outline:** five hotswap-socket pads overhang the outline (left SW5 and SW17, right SW22, SW27, SW32). They come from the original Urchin, and milling the outline trims them.
- **Parts past the board edge:** the USB-C receptacle (J1) and the slide switch's lever (SW35) reach about 1 mm past each half's short edge, into the gap before the frame. This is the intended edge mount, and the frame keeps 3 mm clear beyond them.
- **Silkscreen outside the outline or on pads:** silkscreen of the original key footprints near the edge, and markers inside JLC's own footprints. JLC clips both.
- **Plated slots with paste (J1's four shell legs):** intended pin-in-paste, so reflow solders the legs.

**Assembly:**

- [x] PCB Assembly on, **assembly side: Bottom**. Tooling holes: added by customer.
- [x] Upload `bom.csv` and `positions.csv`. All 18 BOM lines must match the LCSC numbers above, with nothing "not matched".
- [x] Choose **"Confirm parts placement"**, so JLC sends its placement for approval before production.
- [x] In JLC's placement preview, check every part against its own pads and its pin-1 mark one by one. Do not apply a blanket rotation. If JLC's bottom-side convention differed from KiCad's, the error would show either on every part, or only on the parts at ±90° (J1, SW35, C1, C3–C5, R4, R5). Correct the parts that look wrong, then send the list back so the CPL script can be fixed. Pay particular attention to:
  - **U1 (module):** the antenna end points to the board edge at the notch, with no copper under it.
  - **J1 (USB-C):** the opening faces out of the short edge; the four legs go into the plated slots.
  - **U2 (QFN-16):** the pin-1 dot matches the footprint's pin-1 corner.
  - **U3 (SOT-23-6).**
  - **D1, D2, D4, D5 (1N5819WS) and D3 (SMF6.0A):** the cathode band is on the side of the footprint's cathode mark.
  - **LED1/LED2 (reverse-mount RGB):** the body sits over the 2.1 mm hole, lens up through the board. JLC's preview overlays its own footprint for C409782, with pads at ±1.45 mm and no hole. Our pads sit at ±1.70 mm, deliberately, to keep the larger hole clear, so the offset is expected. JLC's part page should name the MPN MHT151RGBCT, the reverse-mount type; EasyEDA's symbol calls it MHT150RGBCT. Pin 1 is the common anode, and it sets which colour is which. Left half: pin 1 is at the corner toward the short edge and toward the module, (+1.70, −0.55) mm from the LED's centre in KiCad's top view. Right half: toward the short edge and away from the module, (−1.70, +0.55) mm.
  - **SW35 (slide switch):** the lever points out of the short edge.
  - Checked on 2026-10-30, after the owner had confirmed: every part matches on both halves (`jlc-placement/`).
- [x] Confirm the stock of C356849 (E73) at order time.

**After delivery (by hand):**

- [ ] Break the halves out of the frame. Snap the small side tab beside the antenna gently, or cut it with flush cutters: the ear's case hole is 0.95 mm from its mouse bites, and the module's corner pads about 1.8 mm. File the mouse-bite nubs.
- [ ] J1 (USB-C): add solder to its four shell legs with an iron. Reflow wets them through the pin-in-paste apertures, but the barrels fill only partly, and the legs are what hold the receptacle against cable forces.
- [ ] 34 Kailh Choc hotswap sockets (CPG135001S30), soldered on the bottom pads.
- [ ] 2 × 401730 protected LiPo cells (4.0 × 17 × 30 mm, ~180 mAh): red to BT1 "+", black to "−". Check polarity with a meter first (bring-up step 2). Mount on 1 mm foam tape. (Cells sold as 401730 are usually 32 mm long with their protection board, up to 32 × 17.5 mm and 4.5 mm thick; they fit. Solder the wires before the cell goes down: `mech/README.md`, "The cell".)
- [ ] Rubber feet at MK3–MK6: 6 mm wide, at least 3.5 mm tall, at least 5 mm for use with a USB cable plugged in. Steel discs at MK1/MK2 when the dock exists (phase 7). (Superseded for the printed case: 6 × 2 mm bumpers go on the case's underside, and M5 steel washers into its recesses; see `mech/README.md`.)
- [ ] Nylon M2 × 16 screws and nylon nuts for the three case holes around the controller (left H6/H7/H8, right H2/H3/H4), if a case is used (`mech/README.md`).
- [ ] LED1 and LED2, both halves: JLC soldered them without a guarantee (its engineering query of 2026-10-27, answered "proceed as-is"; ARCHITECTURE.md decision log). Under a loupe, each of the four pads should show a fillet up the LED's end. At bring-up, check that the status LED lights red, green and blue and the charge LED red and green. For one that doesn't, add flux and touch a fine iron with a little solder to the outer end of that pad, which reaches 0.5 mm past the LED.
- [ ] First flash over SWD (TP2) with a probe that follows the target voltage, e.g. J-Link with pyOCD. Then the UF2 bootloader and ZMK (phase 8).
