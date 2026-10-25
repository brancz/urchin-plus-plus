# mech: printed parts

build123d CAD for the printed parts, generated from the routed boards (docs/ARCHITECTURE.md, "Case" and "Dock").

| Part | Count | Prints | Notes |
|---|---|---|---|
| `case_{left,right}` | 1 per half | floor down, no supports | Tray under the PCB, its walls ending 0.2 mm below the PCB's top. Openings for USB-C, the power switch, the reset button, the charging pads and the tenting puck; a pin at each of the two holes at the antenna end. |
| `shell_{left,right}` | 1 per half | upright, as it sits (the STL is already placed), no supports; the slice irons its top surfaces | Over the PCB: the switch plate (the switches clip into it), a well round the keys with the rim about 1 mm below the keycaps, and a flat lid over the battery with windows over the LEDs. Two screws from below hold it; no hardware shows from the top. |
| `tray_{left,right}` | 1 each, one dock | floor down, no supports | The dock: a pocket for each cased half, split between the pockets, with a finger notch in each outer wall. The dock PCB lies in a recess across both pieces. The magnet pockets are open below, under a 0.6 mm skin the printer bridges; the holes under the case's feet go right through. |

Build everything (STEP export of the boards, parts, fit checks, renders, slicing):

```bash
scripts/mech/build.sh OUT        # RENDER=0 skips the PNGs, SLICE=0 Bambu Studio, PREVIEW=0 the 3D preview
```

`OUT/preview.html` is a 3D preview of the finished keyboard and dock (both halves with switches, keycaps and battery; on the desk, in the dock, exploded, or X-ray): open it in a browser. The switches and keycaps in it are simplified; everything else is the parts and boards as built. `OUT/stl/` has the printable STLs, `OUT/slice/*.3mf` the same parts sliced for a Bambu Lab A1 mini (0.4 mm nozzle, 0.20 mm Standard, Bambu PLA Basic); open a 3MF in Bambu Studio and print. `OUT/checks.json` lists every fit check. `mech/data/*.json` is extracted from the boards by `scripts/mech/board_data.py`; rerun it after any board change (CI fails if it's stale).

## Hardware per half

| Qty | Part | Where |
|---|---|---|
| 2 | M2 × 8 pan-head screw, steel (DIN 7985 or ISO 7045) | From the case's underside, one beside the thumb keys and one at the battery's far end. Each goes up through a standoff and the PCB into the shell, where it cuts its own thread |
| 2 | M5 washer, DIN 125 / ISO 7089, zinc-plated steel (10 × 1 mm) | Glued into the recesses on the case's underside, for the dock's magnets. Not stainless: A2 is barely magnetic. A plain 10 × 1 mm steel disc works too |
| 4 | 6 mm round rubber bumper, about 2 mm tall | In the shallow seats on the case's underside. The dock's holes for them go right through, so any height up to 7 mm still docks |
| 3 | Only with the tenting puck: M2 button-head screw (ISO 7380, 3.5 mm head), as long as the puck needs | From the top, through the PCB into the puck. A 4 mm pan head hits two switches |

The two holes at the antenna end get no hardware: they are inside the antenna keep-out, where nothing conductive may go. A pin printed on the case's standoff goes up through each and into the shell, so the case, the PCB and the shell line up. The 3.8 mm holes between the keys sit 1.5 mm from a switch, with no room for a screw; the shell covers them, and two lips on the case's outer wall hold that edge of the PCB down.

Before the top shell (2026-10-25), the halves used a battery cover held by nylon screws and nuts, and a screw with a heat-set insert beside the thumb keys. The shell needs none of that: if you bought it, the nylon M2 × 16 screws, the nylon nuts, the case's M2 × 3 insert and its M2 × 5 screw and washer are spare. The dock still takes its own two inserts and two M2 × 5 screws.

**The cell.** Cells sold as 401730 are usually 32 mm long with their protection board, up to 32 × 17.5 mm and 4.5 mm thick: longer than the board's 17 × 30 mm outline. Fit it before the case:

1. Cut the 1 mm foam tape to the outline (17 × 30 mm) and stick it inside the outline, so it stays off the wire pads (BT1).
2. Solder the wires to BT1 first, red to "+", black to "−", with the cell held beside the board (check the polarity with a meter). The protection board's end, where the wires come out, goes toward BT1.
3. Lay the cell on the foam, centred, with its far end on the outline's end nearer the antenna, and let the extra length reach toward BT1. The longest cells reach up to 0.4 mm over the pads' ends and partly over the two LEDs' light holes; on the foam they ride 0.2 mm above the solder joints. Keep the joints flat, the wire along the pad.

The shell's lid clears a cell up to 32.5 × 17.5 × 4.5 mm on 1 mm foam tape, laid centred on the outline as above. Its wall between the cell and the keys is 0.5 mm thick; a cell pushed off-centre toward the keys stops the shell from sitting flat.

The tenting puck mounts to the PCB through the round opening in the case floor, as on the original Urchin; the 3.8 mm hole next to it gets no standoff, because the puck covers it. Its screws' heads sit on the PCB under the shell, which has a pocket over each, so the puck goes on before the shell.

## Assembly

1. Glue the steel washers into their recesses on the case's underside (CA), pushed all the way in; stick on the feet.
2. Tilt the half slightly (up to about 10°) and slide its outer edge (the pinky column) under the two lips, then lower the controller side onto the two pins at the antenna end. The USB-C receptacle and the power switch drop through their openings in the inner wall.
3. Fit the cell (above).
4. With the tenting puck: hold it in the floor opening and screw it on from the top, through the PCB.
5. Lay the shell over the PCB, its two pin holes over the pins. It sits on the PCB, just clear of the case's wall.
6. Turn the two M2 × 8 screws in from the underside until they're snug. The first time, each cuts its thread in the shell, so it turns stiffly; stop as soon as the head is down. The thread is plastic: don't force it, and on later fittings start it by hand.
7. Press each switch straight down through the plate into its socket until it clicks into the plate. To swap one later, pull it with a Choc switch puller.
8. Push on the keycaps.

## The dock

The dock PCB comes from JLC assembled (`scripts/dock/fab.sh` makes its bundle). Besides it and the two tray pieces:

| Qty | Part | Where |
|---|---|---|
| 4 | Neodymium disc magnet, N52 10 × 3 mm or N45 10 × 5 mm (the pocket fits both) | Glued into the four pockets on the tray's underside, pushed up against the skin. Polarity doesn't matter: they pull on steel washers |
| 2 | M2 × 3 heat-set insert (3.2 mm hole) | One in each tray piece, at the bottom of the PCB recess beside the USB-C notch |
| 2 | M2 × 5 pan-head screw | Through the dock PCB's holes into the inserts |
| 1 | USB-C cable and a 5 V supply | Any USB-C charger: the CC resistors ask for 5 V |

1. Press an insert into each tray piece. Glue the magnets in from below (CA or epoxy) and let them set. From below, the magnet pockets are the two round holes in each piece that end under a thin skin (you can't see through them); the four of about the same size that go right through are for the case's feet, and the big one for the tenting puck.
2. Put the two pieces together on a flat surface and lay the dock PCB in its recess across both, pins up, over the two round bosses (if it doesn't drop over them, sand the bosses, not the PCB). Screw it down.
3. Run thin CA glue into the 0.2 mm split from the outside and from below, keeping it out of the PCB's recess, and let it set. The joint, not the PCB, then holds the two pieces together.
4. Check that each pin stands 5.85 to 6.15 mm above the PCB (calipers). The dock's budget assumes that; its datasheet gives no tolerance. A pin that leans or sits high on its solder can be reflowed with an iron; if a pin is short or tall by more than that, note it and carry on to step 6, which shows whether it matters.
5. Drop each cased half into its pocket. The walls guide it onto the pins, and the magnets pull its steel washers down. The green LED shows the dock has power. To lift a half out, put a finger in the notch in the outer wall and tilt the half up.
6. With a half docked, it should sit flat, not rock when you press on its corners, and take a definite pull to lift out: the magnets hold it down against the pins. A half that only rests on the pins still charges, so check this by hand; if it lifts with hardly any pull, use 10 × 5 mm magnets in place of 10 × 3; past that, the knob is the tray's skin under the magnets, `MAGNET_SKIN`. Its charge LED should light (amber while charging, green when full) and stay lit when you press on the half and let go. If it stays dark or flickers while USB charging works, the pins barely reach the pads. Measure, with calipers, the pins' height above the pocket floor (6.0 mm nominal) and the depth from the case's underside to its pads through the window (5.2 mm nominal): the difference is the compression (0.8 mm nominal). The knob is the case's floor, `FLOOR` in `mech/src/mech/params.py`: each 0.2 mm (one layer) less lowers the pads, and adds compression, by 0.2 mm. Reprint the case, not the tray.

If the LED goes out, unplug the cable: something is shorting the pins (a stray screw or clip in a pocket), and the fuse has tripped. Clear the pocket; the fuse resets once it cools.
