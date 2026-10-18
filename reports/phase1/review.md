# Phase 1 review: findings and dispositions

The reviewer subagent checked commit 9c53d80 on 2026-10-18, using artifacts only. It reran the scripts, compared every footprint against the original with pcbnew, fed the check deliberately broken boards, and ran DRC on the previews. Repro material is in `scratch/review1/`.

It confirmed as correct:

- the switches, including the rotated thumbs
- the left/right identification
- the outline split (54 of 66 Edge.Cuts kept; only tab stubs and slot ends dropped)
- the tab closures, which run 4 µm inside the mouse-bite break line
- the puck and case-hole geometry
- the generated parts' pads
- the recorded source commit and SHA-256

| # | Finding | Disposition |
|---|---|---|
| H1 | geometry.py passed wrong boards: extra or duplicate footprints, socket pads moved to F.Cu or reshaped or rotated, NPTH holes reshaped, Edge.Cuts inside a footprint. | **Fixed.** Every pad is compared in full: position, size, shape, orientation, drill, plating, and copper and mask layers of the 2-layer stack; only paste is excluded. Extra mechanical footprints fail, and footprint Edge.Cuts are included. All the reviewer's mutated boards now fail for their own reasons. The benign ones (a reversed arc, rotation by 360°, a round hole on the other side) fail only on the case holes the old previews still contained. |
| H2 | The outline check was circular: it compared against urchin.json, and the closures were never validated. | **Fixed.** The outline and closures are derived from the original board in geometry.py itself. Each closure must be vertical (collinear) between two open ends of the original half outline. urchin.json is only checked for agreement. The reviewer's tampered outline fails. |
| H3 | No CI enforcement of rule 1, because reference/ is gitignored. | **Fixed.** `scripts/geometry/fetch_reference.sh` fetches duckyb/urchin at the recorded commit and verifies the SHA-256 (tested from an empty reference/). `scripts/checks/geometry_all.sh` runs in CI: it re-extracts the geometry, regenerates the parts byte for byte, and checks the previews and, once they exist, the real boards. |
| H4 | Hand-soldered sockets were an undocumented architecture change. | **Fixed.** Logged in ARCHITECTURE.md with the stock evidence: C5333465 is sold out at LCSC and at JLC (0), and the only other entries are C99… global-sourcing placeholders with 0 stock, all checked 2026-10-18. The log also records what to revisit if stock returns. |
| H5 | The original geometry fails DRC: socket pads overhang the outline. | **Dispositioned.** Inherited from the original, and rule 1 forbids moving switches or the outline. Logged as documented DRC exclusions to be applied in phase 5. JLC's router trims about 15% of the pad, leaving enough for hand-soldering. |
| M1 | Overlapping holes were undercounted, and the overlap with a puck hole was missed. | **Fixed.** Per half, the case hole overlapping a puck hole and the smaller of the two overlapping case holes are dropped, by rule, in extract.py and independently in geometry.py, with the reasons recorded. |
| M2 | Case-hole pads sit 0.25 mm from the edge. | **Fixed.** Case holes are non-plated, so there is no copper near the edge. |
| M3 | Phase 1 decisions weren't logged, and PLAN.md wasn't updated. | **Fixed.** ARCHITECTURE.md decision log, PLAN.md status. |
| L | Part generation was non-deterministic (UUIDs). | **Fixed.** UUIDs are derived from the part and item index; CI regenerates and compares. |
| L | Socket pads kept B.Paste. | **Fixed.** Paste removed from the socket pads. |
| L | The KEY_CHOC courtyard covers only the socket body, not its pads. | **Noted for phase 3.** Bottom-space checks use pads and courtyards. |
| L | The puck courtyard overlaps switch courtyards. | **Dispositioned.** Inherited, and becomes a DRC exclusion (H5). |
| L | Reversed arcs failed the check. | **Fixed.** Arcs match on endpoints, with the midpoint within 50 nm. |
| L | The duplicate-edge message was empty. | **Fixed.** Multiset comparison, which reports each item. |
| L | Case-hole records had ambiguous refs and layers. | **Dispositioned.** Placement keys on position and footprint only, and the parts are front-side; geometry.py ignores refs. |
| L | The 3D model path for KEY_CHOC doesn't resolve. | **Open, for phase 7.** The STEP fit check needs socket bodies; a model will be added then. Renders don't depend on it. |
| L | The parts have never been through `ato build`. | **Phase 2/3.** The real build uses them, through the wrapper's guardrails and board diff. |
| L | The evidence pointed at a gitignored board. | **Fixed.** The preview boards are in `reports/phase1/preview/`. |
| Info | ARCHITECTURE.md called the original reversible. | **Fixed.** Corrected. |
