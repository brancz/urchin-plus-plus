# JLC's placement preview, checked part by part

These crops come from the owner's screenshots of JLC's placement preview for the keyboard order, taken on 2026-10-30. The view is from the bottom, where every part sits. In JLC's preview, a magenta dot marks a model's pin 1, and magenta "+" and "−" marks show a diode's or LED's anode and cathode. The light stripe on each diode body is the model's cathode band. White marks are our own silkscreen and drill holes, from our Gerbers.

Each part was compared with the pad-1 position and the pad nets of `hardware/layouts/{left,right}/*.kicad_pcb`, in bottom view (mirrored X). Pad 1 is the cathode on every diode: D1 and D2 point VBUS and DOCK_5V into VIN, D3 clamps DOCK_5V to GND, and D4 and D5 sink into the charger's open-drain outputs.

| Part | Pad 1 in bottom view, left half / right half | JLC's preview |
|---|---|---|
| U1 (module) | top-left / top-left, antenna at the ear | matches on both halves |
| U2 (QFN-16) | right side, bottom pin / left side, top pin | magenta dot and model dot on the same pin, next to our silkscreen dot |
| U3 (SOT-23-6) | top row, right pin / bottom row, left pin | matches on both halves |
| D1, D4, D5 (SOD-323) | cathode right / cathode left | band and "−" on the cathode side on both halves |
| D2 (SOD-323), D3 (SMF) | cathode right / cathode left | matches on both halves (`dock-diodes.png`; left half on the left) |
| LED1, LED2 | top-left / bottom-right; pins 2–4 run around the corners as in the footprint | "+" and pin-1 dot on our pad 1; JLC's pin numbers 2–4 sit on our pads 2–4 |
| J1 (USB-C) | opening at the short edge | matches on both halves |
| SW35 (slide switch) | lever past the short edge | matches on both halves |

The other parts are resistors, ceramic capacitors and a two-pad button, none of them polarised. JLC lists 60 assembled designators and none unassembled, the same count as `../positions.csv`.

The LED models' gold pads sit inboard of our pads, as expected: JLC overlays its own footprint for C409782, with pads at ±1.45 mm, while ours are at ±1.70 mm (`../README.md`).
