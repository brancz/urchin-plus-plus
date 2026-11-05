# mech: printed parts

build123d CAD for the printed parts, generated from the routed boards (docs/ARCHITECTURE.md, "Case" and "Dock").

| Part | Count | Prints | Notes |
|---|---|---|---|
| `case_{left,right}` | 1 per half | floor down, no supports | Tray under the PCB, its walls ending 0.2 mm below the PCB's top. Openings for USB-C, the power switch, the reset button, the charging pads and the tenting puck; a pin at each of the two holes at the antenna end. |
| `shell_{left,right}` | 1 per half | upright, as it sits (the STL is already placed), no supports; the slice irons its top surfaces | Over the PCB: the switch plate (the switches clip into it), a well round the keys with the rim about 1 mm below the keycaps, and a flat lid over the battery with windows over the LEDs. Two screws from below hold it; no hardware shows from the top. |
| `tray_{left,right}` | 1 each, one dock | floor down, no supports | The dock: a 6.8 mm slab with a shallow pocket for each cased half, split between the pockets. The dock PCB lies in a recess across both pieces, flush with the tray's floor in the pockets. The magnet pockets are open below, under a 0.4 mm skin the printer bridges; the holes under the case's feet go right through. |
| `dock_cover` | 1, one dock | as it sits (the STL is already placed), no supports | Fills the tray over the dock PCB's tab at the back, flush with its top: a pocket over each part, the USB-C's mouth open at the back face, a pinhole over the power LED. Glued in; it holds the PCB down. |
| `dock_floor_{left,right}` | 1 each, one dock | flat, as it sits, no supports; the slice irons its top | A 0.4 mm plate over each pocket's floor and the dock PCB in it, so the empty dock shows no circuit board: only the three gold contacts, through a slot. Holes under the case's feet and the tenting puck, as in the tray. Glued down. |
| `pin_jig_{left,right}` | 1 per half (a tool) | plate down, no supports | Holds the three pogo pins upright while they're soldered (below). |

Build everything (STEP export of the boards, parts, fit checks, renders, slicing):

```bash
scripts/mech/build.sh OUT        # RENDER=0 skips the PNGs, SLICE=0 Bambu Studio, PREVIEW=0 the 3D preview
```

`OUT/preview.html` is a 3D preview of the finished keyboard and dock (both halves with switches, keycaps and battery; on the desk, in the dock, exploded, or X-ray): open it in a browser. The latest one is committed as `reports/phase7/preview.html`, and GitHub Pages serves it at https://brancz.github.io/urchin-plus-plus/ (`.github/workflows/pages.yml`). The switches and keycaps in it are simplified; everything else is the parts and boards as built. `OUT/stl/` has the printable STLs, `OUT/slice/*.3mf` the same parts sliced for a Bambu Lab A1 mini (0.4 mm nozzle, 0.20 mm Standard, Bambu PLA Basic); open a 3MF in Bambu Studio and print. `OUT/checks.json` lists every fit check. `mech/data/*.json` is extracted from the boards by `scripts/mech/board_data.py`; rerun it after any board change (CI fails if it's stale).

## Hardware per half

| Qty | Part | Where |
|---|---|---|
| 2 | M2 × 8 pan-head screw, steel (DIN 7985 or ISO 7045) | From the case's underside, one beside the thumb keys and one at the battery's far end. Each goes up through a standoff and the PCB into the shell, where it cuts its own thread |
| 3 | Pogo pin, Yiyuan YTC1P-4020-01 (LCSC C5221284), 6.0 mm | Soldered on the charging pads (TP1), plunger down through the case's window (below). Buy them loose from LCSC |
| 2 | M5 washer, DIN 125 / ISO 7089, zinc-plated steel (10 × 1 mm) | Glued into the recesses on the case's underside, for the dock's magnets. Not stainless: A2 is barely magnetic. A plain 10 × 1 mm steel disc works too |
| 4 | 6 mm round rubber bumper, 3 mm tall | In the shallow seats on the case's underside. On 3 mm feet the pogo pins stay at least 0.75 mm off the desk; 2.5 mm feet still clear it, by 0.25 mm at worst. The dock's holes for them go right through, so any height below 4.6 mm still docks |
| 3 | Only with the tenting puck: M2 button-head screw (ISO 7380, 3.5 mm head), as long as the puck needs | From the top, through the PCB into the puck. A 4 mm pan head hits two switches |

The two holes at the antenna end get no hardware: they are inside the antenna keep-out, where nothing conductive may go. A pin printed on the case's standoff goes up through each and into the shell, so the case, the PCB and the shell line up. The 3.8 mm holes between the keys sit 1.5 mm from a switch, with no room for a screw; the shell covers them, and two lips on the case's outer wall hold that edge of the PCB down.

Before the top shell (2026-10-25), the halves used a battery cover held by nylon screws and nuts, and a screw with a heat-set insert beside the thumb keys. The shell needs none of that: if you bought it, the nylon M2 × 16 screws, the nylon nuts, the case's M2 × 3 insert and its M2 × 5 screw and washer are spare. Since the dock's redesign (2026-10-25) it takes no screws or inserts either, so all the M2 × 3 inserts and M2 × 5 screws are spare.

**The cell.** Cells sold as 401730 are usually 32 mm long with their protection board, up to 32 × 17.5 mm and 4.5 mm thick: longer than the board's 17 × 30 mm outline. Fit it before the case:

1. Cut the 1 mm foam tape to the outline (17 × 30 mm) and stick it inside the outline, so it stays off the wire pads (BT1).
2. Solder the wires to BT1 first, red to "+", black to "−", with the cell held beside the board (check the polarity with a meter). The protection board's end, where the wires come out, goes toward BT1.
3. Lay the cell on the foam, centred, with its far end on the outline's end nearer the antenna, and let the extra length reach toward BT1. The longest cells reach up to 0.4 mm over the pads' ends and partly over the two LEDs' light holes; on the foam they ride 0.2 mm above the solder joints. Keep the joints flat, the wire along the pad.

The shell's lid clears a cell up to 32.5 × 17.5 × 4.5 mm on 1 mm foam tape, laid centred on the outline as above. Its wall between the cell and the keys is 0.5 mm thick; a cell pushed off-centre toward the keys stops the shell from sitting flat.

The tenting puck mounts to the PCB through the round opening in the case floor, as on the original Urchin; the 3.8 mm hole next to it gets no standoff, because the puck covers it. Its screws' heads sit on the PCB under the shell, which has a pocket over each, so the puck goes on before the shell.

**The pogo pins.** Solder them before the board goes into its case, with its jig (`pin_jig_left` or `pin_jig_right`, matching the half). A soldering iron with a fine tip, thin solder wire and flux are enough.

1. Lay the board bottom up, on something flat. Tin the three TP1 pads lightly: a thin, flat layer, no blobs.
2. Stand a pin on each pad, flange down, plunger up, roughly centred.
3. Lower the jig over them, plate on top: each plunger goes into its bore, the two pegs into the board's holes either side, and the two feet rest on the board beside the pins. Every pin now stands upright at its place. If a plunger doesn't go in, open its bore with a 1.2 mm drill, by hand.
4. Touch the iron to each pad where it sticks out beyond the flange (at its ends; the plate leaves both ends of every pad open), with a little flux, until the solder under the flange melts and the pin settles flat. Come in at an angle under the plate's edge, keep each touch short (2 to 3 s) and keep the iron off the jig: it is PLA, and softens at about 60 °C. Don't add much solder: it must not wick up the barrel.
5. Let it cool and lift the jig straight off. Each pin should stand straight, 5.9 to 6.2 mm above the board (calipers to the plunger's tip; 6.05 mm nominal), and its plunger should spring back when pressed. Reflow one that leans or stands high.

## Assembly

1. Glue the steel washers into their recesses on the case's underside (CA), pushed all the way in; stick on the feet.
2. Tilt the half slightly (up to about 10°) and slide its outer edge (the pinky column) under the two lips, then lower the controller side onto the two pins at the antenna end. The USB-C receptacle and the power switch drop through their openings in the inner wall, and the pogo pins through the window in the floor; they stand 1.25 mm below the case's underside, and the feet keep them off the desk.
3. Fit the cell (above).
4. With the tenting puck: hold it in the floor opening and screw it on from the top, through the PCB.
5. Lay the shell over the PCB, its two pin holes over the pins. It sits on the PCB, just clear of the case's wall.
6. Turn the two M2 × 8 screws in from the underside until they're snug. The first time, each cuts its thread in the shell, so it turns stiffly; stop as soon as the head is down. The thread is plastic: don't force it, and on later fittings start it by hand.
7. Press each switch straight down through the plate into its socket until it clicks into the plate. To swap one later, pull it with a Choc switch puller.
8. Push on the keycaps.

## The dock

The dock PCB comes from JLC assembled (`scripts/dock/fab.sh` makes its bundle). Besides it, the two tray pieces, the cover and the two floor plates:

| Qty | Part | Where |
|---|---|---|
| 4 | Neodymium disc magnet, N52 10 × 3 mm | Glued into the four pockets on the tray's underside, pushed up against the skin. Polarity doesn't matter: they pull on steel washers. A 10 × 5 mm magnet no longer fits |
| 1 | USB-C cable and a 5 V supply | Any USB-C charger: the CC resistors ask for 5 V. The cable plugs in at the middle of the back edge |

1. Glue the magnets in from below (CA or epoxy) and let them set. From below, the magnet pockets are the two round holes in each piece that end under a thin skin (you can't see through them); the four of about the same size that go right through are for the case's feet, and the big one for the tenting puck.
2. Put the two pieces together on a flat surface and lay the dock PCB in its recess across both, gold contacts up, its two round holes over the round bosses (if it doesn't drop over them, sand the bosses, not the PCB). Add solder to the USB-C receptacle's four shell legs first, if that isn't done yet (JLC's checklist, `reports/phase7/README.md`). Then lift each bar (the board under a pocket, with the gold contacts) at its outer end, put one small drop of CA on the recess floor under it, and press it flat for a minute: JLC lets a board bow up to 0.75 %, and a bar that lifts presses the pins harder.
3. Check the cover's fit in the recess over the PCB's tab at the back: it sits flush with the tray's top, the receptacle's mouth open in the back face. Then put a few small drops of CA on the tray's floor round the recess (not on the PCB or its parts) and press the cover in. Hold it a minute.
4. Run thin CA glue into the 0.2 mm split from the outside and from below, keeping it out of the PCB's recess, and let it set.
5. Lay a floor plate in each pocket, smooth (ironed) face up, its slot over the three gold contacts and its holes over the tray's. Turned over, a plate also fits the other pocket, so check the face. Lift it out again and put a few small drops of gel CA on the bare tray floor, about 3 mm in from the outer wall and from the front and back walls: never on the PCB (it runs along the inner wall and under the contacts) and never near the slot or the holes, where it would show. Use as little as holds it: CA fumes leave a white bloom on black PLA, so leave the pocket open to air while it sets. Lay the plate back and press it flat for a minute.
6. Plug in the cable: the green LED shows through the cover's pinhole. Drop each cased half into its pocket. The walls guide it, and the magnets pull its steel washers down, its pins through the slot onto the gold contacts. To take a half out, lift it by its sides.
7. With a half docked, it should sit flat, not rock when you press on its corners, and take a definite pull to lift out: the magnets hold it down against the pins. A half that only rests on the pins still charges, so check this by hand. If it lifts with hardly any pull, the magnets are too far below the washers: 0.8 mm, the tray's 0.4 mm skin over them (`MAGNET_SKIN`) and the floor plate. That needs a CAD change, not a setting: a hole in each floor plate over each magnet brings it 0.4 mm closer. Its charge LED should light (amber while charging, green when full) and stay lit when you press on the half and let go. If it stays dark or flickers while USB charging works, the pins barely press on the contacts. Measure, with calipers, how far the pins' tips stand below the case's underside, the half lying upside down (1.25 mm nominal); less the floor plate's 0.4 mm, that is the compression (0.85 mm nominal, 0.54 mm least expected). The knob is the case's floor, `FLOOR` in `mech/src/mech/params.py`: each 0.2 mm (one layer) less lowers the board, and adds compression, by 0.2 mm, and brings the tips 0.2 mm nearer the desk under a half on its feet (0.75 mm to spare at worst, on 3 mm feet). Rebuild, and reprint the cases, not the tray or the plates.

If the LED goes out, unplug the cable: something is shorting the contacts (a coin or a clip on them), and the fuse has tripped. Clear it; the fuse resets once it cools.
