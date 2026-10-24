# mech: printed parts

build123d CAD for the printed parts, generated from the routed boards (docs/ARCHITECTURE.md, "Case" and "Dock").

| Part | Count | Prints | Notes |
|---|---|---|---|
| `case_{left,right}` | 1 per half | floor down, no supports | Tray under the PCB, walls flush with its top. Openings for USB-C, the power switch, the reset button, the charging pads and the tenting puck. |
| `cover_{left,right}` | 1 per half | roof down (the STL is already flipped), no supports | Over the battery and the controller, with windows over the LEDs. |
| `tray_{left,right}` | 1 each, one dock | floor down, no supports | The dock: a pocket for each cased half, split between the pockets, with a finger notch in each outer wall. The dock PCB lies in a recess across both pieces. The magnet pockets are open below, under a 0.6 mm skin the printer bridges; the holes under the case's feet go right through. |

Build everything (STEP export of the boards, parts, fit checks, renders, slicing):

```bash
scripts/mech/build.sh OUT        # RENDER=0 skips the PNGs, SLICE=0 skips Bambu Studio
```

`OUT/stl/` has the printable STLs, `OUT/slice/*.3mf` the same parts sliced for a Bambu Lab A1 mini (0.4 mm nozzle, 0.20 mm Standard, Bambu PLA Basic); open a 3MF in Bambu Studio and print. `OUT/checks.json` lists every fit check. `mech/data/*.json` is extracted from the boards by `scripts/mech/board_data.py`; rerun it after any board change (CI fails if it's stale).

## Hardware per half

| Qty | Part | Where |
|---|---|---|
| 1 | M2 × 3 heat-set insert (3.2 mm hole) | Into the standoff under the 3.8 mm hole beside the thumb keys, from the top, with a soldering iron (about 220 °C for PLA) |
| 1 | M2 × 5 pan-head screw and M2 washer (DIN 125, 5 mm) | Through that hole into the insert. The hole is wider than the screw head, hence the washer |
| 3 | M2 × 8 nylon pan-head screw | From the case's underside, through a standoff and one of the PCB's 2.2 mm holes around the controller |
| 3 | M2 × 6 mm nylon female-female hex standoff, at most 4 mm across flats | On those screws, above the PCB |
| 3 | M2 × 3 nylon pan-head screw | Hold the cover onto the standoffs. Not M2 × 4: it would meet the M2 × 8 inside the standoff |
| 2 | 10 × 1 mm steel disc | Glued flush into the recesses on the case's underside, for the dock's magnets |
| 4 | 6 mm round rubber bumper, about 2 mm tall | In the shallow seats on the case's underside. The dock's holes for them go right through, so any height up to 7 mm still docks |

The hardware around the controller is nylon on purpose: two of those holes are inside the antenna keep-out, where nothing conductive may go.

The other 3.8 mm holes take no screws. They sit right beside the switches, under the keycaps' edges, where no screw head fits; the original Urchin's plate cases pass posts through them. The case supports the board under them, and two lips on the outer wall hold that edge down. The tenting puck mounts to the PCB through the round opening in the case floor, as on the original Urchin; the 3.8 mm hole next to it gets no standoff, because the puck covers it.

## Assembly

1. Press the insert into the standoff beside the thumb keys. Glue in the steel discs; stick on the feet.
2. Tilt the half slightly (up to about 10°) and slide its outer edge (the pinky column) under the two lips, then lower the controller side. The USB-C receptacle and the power switch drop through their openings in the inner wall.
3. Pass the nylon M2 × 8 screws up from the underside through the three controller holes and thread a standoff onto each, finger-tight. Don't tighten them harder: the case's standoffs under the two holes at the antenna end have only about 0.5 mm of wall, where they make room for nearby parts.
4. Screw down the hole beside the thumb keys: M2 × 5 with its washer.
5. Screw the cover onto the standoffs with the M2 × 3 nylon screws.

## The dock

The dock PCB comes from JLC assembled (`scripts/dock/fab.sh` makes its bundle). Besides it and the two tray pieces:

| Qty | Part | Where |
|---|---|---|
| 4 | N52 neodymium disc magnet, 10 × 3 mm (10 × 5 also fits) | Glued into the four pockets on the tray's underside, pushed up against the skin. Polarity doesn't matter: they pull on steel discs |
| 2 | M2 × 3 heat-set insert (3.2 mm hole) | One in each tray piece, at the bottom of the PCB recess beside the USB-C notch |
| 2 | M2 × 5 pan-head screw | Through the dock PCB's holes into the inserts |
| 1 | USB-C cable and a 5 V supply | Any USB-C charger: the CC resistors ask for 5 V |

1. Press an insert into each tray piece. Glue the magnets in from below (CA or epoxy) and let them set. From below, the magnet pockets are the two round holes in each piece that end under a thin skin (you can't see through them); the four of about the same size that go right through are for the case's feet, and the big one for the tenting puck.
2. Put the two pieces together on a flat surface and lay the dock PCB in its recess across both, pins up, over the two round bosses (if it doesn't drop over them, sand the bosses, not the PCB). Screw it down.
3. Run thin CA glue into the 0.2 mm split from the outside and from below, keeping it out of the PCB's recess, and let it set. The joint, not the PCB, then holds the two pieces together.
4. Check that each pin stands 5.85 to 6.15 mm above the PCB (calipers). The dock's budget assumes that; its datasheet gives no tolerance. A pin that leans or sits high on its solder can be reflowed with an iron; if a pin is short or tall by more than that, note it and carry on to step 6, which shows whether it matters.
5. Drop each cased half into its pocket. The walls guide it onto the pins, and the magnets pull its steel discs down. The green LED shows the dock has power. To lift a half out, put a finger in the notch in the outer wall and tilt the half up.
6. With a half docked, its charge LED should light (amber while charging, green when full) and stay lit when you press on the half and let go. If it stays dark or flickers while USB charging works, the pins barely reach the pads. Measure, with calipers, the pins' height above the pocket floor (6.0 mm nominal) and the depth from the case's underside to its pads through the window (5.2 mm nominal): the difference is the compression (0.8 mm nominal). The knob is the case's floor, `FLOOR` in `mech/src/mech/params.py`: each 0.2 mm (one layer) less lowers the pads, and adds compression, by 0.2 mm. Reprint the case, not the tray.

If the LED goes out, unplug the cable: something is shorting the pins (a stray screw or clip in a pocket), and the fuse has tripped. Clear the pocket; the fuse resets once it cools.
