# mech: printed parts

build123d CAD for the printed parts, generated from the routed boards (docs/ARCHITECTURE.md, "Case" and "Dock").

| Part | Per half | Prints | Notes |
|---|---|---|---|
| `case_{left,right}` | 1 | floor down, no supports | Tray under the PCB, walls flush with its top. Openings for USB-C, the power switch, the reset button, the charging pads and the tenting puck. |
| `cover_{left,right}` | 1 | roof down (the STL is already flipped), no supports | Over the battery and the controller, with windows over the LEDs. |

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
| 3 | M2 × 6 mm nylon female-female hex standoff | On those screws, above the PCB |
| 3 | M2 × 3 nylon pan-head screw | Hold the cover onto the standoffs. Not M2 × 4: it would meet the M2 × 8 inside the standoff |
| 2 | 10 × 1 mm steel disc | Glued flush into the recesses on the case's underside, for the dock's magnets |
| 4 | 6 mm round rubber foot | In the shallow seats on the case's underside |

The hardware around the controller is nylon on purpose: two of those holes are inside the antenna keep-out, where nothing conductive may go.

The other 3.8 mm holes take no screws. They sit right beside the switches, under the keycaps' edges, where no screw head fits; the original Urchin's plate cases pass posts through them. The case supports the board under them, and two lips on the outer wall hold that edge down. The tenting puck mounts to the PCB through the round opening in the case floor, as on the original Urchin; the 3.8 mm hole next to it gets no standoff, because the puck covers it.

## Assembly

1. Press the insert into the standoff beside the thumb keys. Glue in the steel discs; stick on the feet.
2. Tilt the half and slide its outer edge (the pinky column) under the two lips, then lower the controller side. The USB-C receptacle and the power switch drop through their openings in the inner wall.
3. Pass the nylon M2 × 8 screws up from the underside through the three controller holes and thread a standoff onto each, finger-tight.
4. Screw down the hole beside the thumb keys: M2 × 5 with its washer.
5. Screw the cover onto the standoffs with the M2 × 3 nylon screws.
