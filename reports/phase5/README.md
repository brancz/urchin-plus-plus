# Phase 5 — validation

Date: 2026-10-18. Every verification layer from docs/ARCHITECTURE.md, run on the routed boards in `hardware/layouts/` and the panel from `scripts/fab/build.sh`.

| # | Layer | Result | Evidence |
|---|---|---|---|
| 1 | atopile's own checks, plus every intended connection on the board | Both halves build. `connectivity.py` checks all 187 numbered pads per half against a netlist written from the datasheets. It also checks the LCSC number per designator and the module GPIO table. OK. | `reports/phase4/connectivity-*.json`, `netlist-*.txt` |
| 2 | KiCad DRC against JLC's capabilities | Halves: 0 errors, 0 unconnected. Panel: 0 errors. Excused: 7 per half and 14 on the panel, all inherited from the original (`hardware/drc_allow.json`). | `reports/phase4/drc-*.md`, `reports/phase6/drc.md` |
| 3 | Custom checks | All OK:<br>– antenna keep-out on both layers: no copper (pours included), no parts, battery ≥ 3 mm away;<br>– part spacing, holes, edge, tenting puck, single-sided assembly;<br>– rule 1 zero deviation on both halves (CI fetches the original), each half's outline in the panel within 2 µm outside the tabs, and the panel's GND pours equal to the halves' apart from the mouse bites;<br>– placement and every rule area equal their sources;<br>– unique UUIDs; designators. | `reports/phase4/clearance-*.json`, `geometry-*.json`, `reports/phase6/outline.txt`, `fills.txt`; `hardware_all.sh`, `geometry_all.sh`, `fab/build.sh` |
| 4 | After every `ato build` | Guardrails, snapshot, stale-net repair, board diff: OK. The build settles, and `--frozen` changes nothing on the routed boards. | `scripts/ato_build.sh`, CI |
| 5 | Renders, inspected by the reviewer | 3D top/bottom per half and panel, copper per layer | `reports/phase4/*.png`, `reports/phase6/panel-*.png` |
| 6 | STEP fit check against the dock | **Not yet.** The dock is phase 7. STEP files of both halves are produced (`fab/step/`, CI artifact `jlc-bundle`), with 3D model offsets checked against the footprints by STEP export (phase 3 review M3). | — |
| 7 | ZMK firmware builds for both halves | **Not yet** (phase 8). The pin maps it needs are in `hardware/pinmap.json`. | — |
| 8 | JLC's DFM check on upload | **Human, at gate 3.** See the checklist in `reports/phase6/README.md`. | — |

Layers 6 and 7 belong to phases that don't block the PCB order (PLAN.md: phases 7 and 8 can run while JLC builds the boards).

## Reviews

Phases 2 and 3 were reviewed, and every finding is fixed or dispositioned (`reports/phase2/review.md`, `reports/phase3/review.md`). The full reviewer pass for phases 4–6 found no high-severity issues. Its 4 medium and 4 low findings are fixed or dispositioned in `review.md` here. A second reviewer pass checked those dispositions, found 4 more medium and 7 low findings, and those are fixed or dispositioned there too (`review.md`, "Second review"). A third pass confirmed every second-review disposition and found one more medium (a side-tab mouse bite too close to a case-hole ear) plus lows, all handled in `review.md`, "Third review". It judged the bundle ready for fabrication and assembly.

## Known limitations, accepted

- **Hand assembly after delivery:**
  - the 34 Kailh Choc hotswap sockets (not stocked at JLC);
  - the two 401730 cells, soldered to BT1 on 1 mm foam tape;
  - the rubber feet (≥ 3.5 mm tall, ≥ 5 mm for use with a USB cable plugged in);
  - the steel discs;
  - nylon screws in the case holes beside the antenna;
  - extra solder on J1's four shell legs.
- **First flash** needs an SWD probe that follows the target voltage (e.g. J-Link). A blank module runs its I/O at 1.8 V.
- **Docking leaves VBUS reading 0.**  R11 holds VBUS low, so firmware learns about dock power only through PGOOD.
- **Charging can slow on a weak dock supply:** the charger reduces its input current below about 4.5 V at VIN (phase 2 review L1). Check this at bring-up.
- **Inherited from the original (rule 1):**
  - socket pads overhang the outline in five places, and the board router trims them;
  - the puck courtyard overlaps socket courtyards.
- **The right half uses module pins 1 and 2 for keys** (decision log). Their traces leave away from the antenna.
- **Traces under the module** (`review.md`, M1 in numbers):
  - slow signals on the module side;
  - LED_B under the right module's RF end;
  - the left half's USB pair and keys on the far layer.

  The module side is about half ground. Expect somewhat less radio range than an ideal layout; measure it at bring-up (PLAN success criteria).
- **The battery reading is the charger's 4.4 V output while input power is present** (VDDH). Firmware should report "charging" then (phase 8).
