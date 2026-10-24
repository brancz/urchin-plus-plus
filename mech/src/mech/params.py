"""Every dimension the cases and the dock tray use, with where it comes from.

Board features (outline, holes, pads, part positions) are never typed here: they come from
mech/data/*.json, which scripts/mech/board_data.py extracts from the routed boards.
Lengths in millimetres. z = 0 is the case's underside.
"""

# --- Printing (Bambu Lab A1 mini, 0.4 mm nozzle, 0.2 mm layers) -------------------------
BED = (180.0, 180.0, 180.0)  # build volume
FIT = 0.4                    # clearance between a printed wall and the part it surrounds

# --- The board (docs/ARCHITECTURE.md, reports/phase3/README.md) --------------------------
PCB_T = 1.6                  # also in mech/data/*.json ("thickness"); checked against it
BOTTOM_PARTS_H = 3.26        # tallest bottom part: the USB-C receptacle (the module is 3.0)
SOCKET_H = 1.85              # Kailh Choc hotswap socket body, below the PCB
SWITCH_BODY = 15.0           # Kailh Choc v1 housing, 15 x 15 mm at its widest
SWITCH_BODY_H = 5.0          # housing height above the PCB; the stem and keycap are above it

# --- Case ---------------------------------------------------------------------------------
WALL = 2.0                   # side wall
EDGE_TOP = 0.6               # chamfer on the outer top edge
EDGE_BOTTOM = 0.4            # chamfer on the outer bottom edge (also offsets first-layer squish)
FLOOR = 1.6                  # 8 layers
GAP = 3.6                    # floor to PCB underside: BOTTOM_PARTS_H plus 0.34 mm
Z_PCB_BOTTOM = FLOOR + GAP   # 5.2: the dock's pins reach this high
Z_PCB_TOP = Z_PCB_BOTTOM + PCB_T
Z_WALL_TOP = Z_PCB_TOP       # low tray: walls end flush with the top of the PCB

BOSS_D = 6.0                 # standoff under each case hole (cut back around nearby parts)
PART_CLEAR = 0.3             # standoff to a bottom part's courtyard

# The 3.8 mm holes are the original's pass-through holes for its plate cases' posts, and most
# sit 2.1 mm from a switch body, under a keycap's edge: no screw head fits there. Only a hole
# whose washer clears every keycap gets a screw: an M2 x 5 with an M2 washer from the top
# into an M2 x 3 heat-set insert (3.2 mm hole) in the standoff. The others get plain standoffs,
# and LIPs on the outer wall hold that edge down.
INSERT_D = 3.2
INSERT_DEPTH = 4.0           # the insert sits in the top 3 mm; 1 mm below it for displaced plastic
INSERT_L = 3.0
PCB_SCREW_L = 5.0            # M2 x 5 pan head (DIN 7985: head 4.0 mm across, 1.6 mm tall)
PCB_SCREW_HEAD = (4.0, 1.6)
WASHER = (5.0, 0.3)          # M2 washer, DIN 125: 5 mm across, 0.3 mm thick

# Lips over the PCB's outer edge, opposite the controller. The board tilts in under them,
# outer edge first, and the controller side screws down.
LIP_COUNT = 2
LIP_LEN = 10.0
LIP_OVER = 0.6               # how far a lip reaches over the PCB
LIP_T = 0.8                  # 4 layers
LIP_PLAY = 0.1               # between the PCB's top and the lip
LIP_MIN_EDGE = 30.0          # the straight outer edge the lips sit on is at least this long

# The three 2.2 mm holes around the controller (H6/H7/H8 on the left half, H2/H3/H4 on the
# right) hold the PCB and the battery cover: an M2 x 8 nylon screw from the case's underside,
# through the standoff and the PCB, into a 6 mm M2 nylon female-female standoff, and an M2 x 3
# nylon screw from the cover's top into the standoff. Two of these holes are inside the
# antenna keep-out, so all hardware there is nylon (CLAUDE.md rule 6: nothing conductive near
# the antenna).
SCREW_CLEAR_D = 2.4
HEAD_D = 4.4                 # M2 pan head (nylon: 4.0 mm) plus clearance
HEAD_DEPTH = 1.8             # the head stays inside the underside, clear of the dock
NYLON_HEAD_H = 1.6           # M2 nylon pan head: 1.3 to 1.6 mm tall
STANDOFF_LEN = 6.0           # nylon M2 F-F standoff between the PCB and the cover
STANDOFF_D = 3.7             # its hex across corners (3.2 mm across flats)
COVER_LOWER_SCREW_L = 8.0
COVER_UPPER_SCREW_L = 3.0
MIN_THREAD = 2.0             # least thread engagement of any screw (5 turns of M2)
MIN_TIP_GAP = 0.3            # between two screw tips in a standoff, or a tip and a hole's bottom

USB_OPENING_W = 13.0         # USB-C plug overmolds are up to about 12.4 mm wide
RESET_HOLE_D = 2.5           # poke hole under the reset button (a pin or paper clip)
DOCK_WINDOW_MARGIN = 1.0     # around the charging pads, for the dock's pins
PUCK_CLEAR = 0.75            # around the tenting puck's outline
DISC_D = 10.0                # steel disc for the dock magnets (the board's MK1/MK2 marker)
DISC_T = 1.0                 # recessed flush into the case's underside
FOOT_RECESS = 0.4            # shallow seat for each stick-on rubber foot

SWITCH_H = 1.6              # MSK12C02 slide switch body below the PCB (its 3D model)
SWITCH_SLOT_MARGIN = 1.5     # power switch slot, beyond the switch body at each end
SWITCH_SCOOP_R = 8.0         # finger scoop on the outside of the wall at the power switch
SWITCH_SCOOP_DEPTH = 1.6     # leaves 0.4 mm of wall beside the slot

# --- Battery cover --------------------------------------------------------------------------
BATTERY_H = 4.0 + 1.0        # 401730 cell on 1 mm foam tape (docs/ARCHITECTURE.md)
ROOF_T = 1.6
Z_ROOF_BOTTOM = Z_PCB_TOP + STANDOFF_LEN  # 1 mm above the cell
KEYCAP = (17.5, 16.5)        # Kailh Choc keycap (MBK) footprint
KEYCAP_MARGIN = 0.8          # the cover stays this far from every keycap
COVER_BEYOND_HOLES = 5.0     # the cover ends this far beyond its outermost holes (along y)
COVER_HEAD_DEPTH = 0.8       # counterbore for the M2 x 4 screws' heads in the roof
LED_WINDOW_D = 3.0           # over the status and charge LEDs, which shine up through the PCB
