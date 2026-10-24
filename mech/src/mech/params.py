"""Every dimension the cases and the dock tray use, with where it comes from.

Board features (outline, holes, pads, part positions) are never typed here: they come from
mech/data/*.json, which scripts/mech/board_data.py extracts from the routed boards.
Lengths in millimetres. z = 0 is the case's underside.
"""

# --- Printing (Bambu Lab A1 mini, 0.4 mm nozzle, 0.2 mm layers) -------------------------
BED = (180.0, 180.0, 180.0)  # build volume
FIT = 0.4                    # clearance between a printed wall and the part it surrounds
LAYER_H = 0.2                # layer height (0.20 mm Standard)

# --- The board (docs/ARCHITECTURE.md, reports/phase3/README.md) --------------------------
PCB_T = 1.6                  # also in mech/data/*.json ("thickness"); checked against it
PCB_T_TOL = 0.16             # JLC: +-10 % on 1.6 mm
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
LIP_OVER = 0.8               # how far a lip reaches over the PCB
LIP_T = 0.8                  # 4 layers
LIP_PLAY = 0.2               # between the PCB's top and the lip: one layer, so the lip's underside
                             # is on a layer boundary, and a board 0.16 mm thick still fits
MIN_LIP_HOLD = 0.3           # the lip stays this far over the board's edge (RSS of its play)
MIN_LIP_TILT = 5.0           # degrees a nominal board can tilt in under the lips
LIP_MIN_EDGE = 30.0          # the straight outer edge the lips sit on is at least this long

# The three 2.2 mm holes around the controller (H6/H7/H8 on the left half, H2/H3/H4 on the
# right) hold the PCB and the battery cover: an M2 x 16 nylon screw from the case's underside,
# through the standoff, the PCB and a post printed on the cover, into an M2 nylon nut on the
# cover's roof. Two of these holes are inside the antenna keep-out, so all hardware there is
# nylon (CLAUDE.md rule 6: nothing conductive near the antenna). The posts replace bought
# nylon standoffs: two of the holes are 2.6 mm from a keycap's edge, so a standoff could be at
# most 4 mm across flats, and no shop in Germany sold one (2026-10-24; the narrowest were 5 mm).
# The checks move each post by the cover's play on the screws, and each nut by its screw's play
# in the PCB's hole, toward the keycap beside it.
SCREW_CLEAR_D = 2.4
HEAD_D = 4.4                 # M2 pan head (nylon: 4.0 mm) plus clearance
HEAD_DEPTH = 1.8             # the head stays inside the underside, clear of the dock
NYLON_HEAD_H = 1.6           # M2 nylon pan head: 1.3 to 1.6 mm tall
M2_MIN_D = 1.886             # an M2 thread's smallest major diameter (6g)
COVER_POST_LEN = 6.0         # the cover's post, from the PCB's top to the roof
COVER_POST_D = 4.0           # 0.85 mm of wall (two lines) round the bore; 0.62 mm from the keycap
COVER_BORE_D = 2.3           # the post's bore: prints about 2.2, a sliding fit that locates the
                             # cover on the screws
COVER_BORE_CHAMFER = 0.3     # lead-in at the bore's bottom, for the screw pushed up from below
COVER_SCREW_L = 16.0         # nylon M2 x 16 pan head, DIN 7985 (no M2 x 14 in nylon)
NUT = (4.62, 1.6)            # M2 nut, DIN 934: 4 mm across flats (4.62 across corners), 1.6 mm
                             # tall; assembled with a flat toward the keycap beside it
MIN_THREAD = 2.0             # least thread engagement of a screw in a printed part or an insert
                             # (5 turns of M2); a full DIN 934 nut (0.8 d) is the standard instead
MIN_TIP_GAP = 0.3            # between a screw's tip and a hole's bottom

USB_OPENING_W = 13.0         # USB-C plug overmolds are up to about 12.4 mm wide
RESET_HOLE_D = 2.5           # poke hole under the reset button (a pin or paper clip)
DOCK_WINDOW_MARGIN = 1.5     # around the charging pads, for the dock's pins (the dock checks size it)
PUCK_CLEAR = 0.75            # around the tenting puck's outline
DISC_D = 10.0                # steel for the dock magnets (the board's MK1/MK2 marker): an M5 washer,
                             # DIN 125 / ISO 7089, zinc-plated steel, 10 x 1 mm with a 5.3 mm hole
DISC_T = 1.2                 # its recess in the case's underside: the washer is at most 1.1 mm
                             # thick (ISO 7089), so it never stands proud; 6 layers
FOOT_RECESS = 0.4            # shallow seat for each stick-on rubber foot
FOOT_SEAT = 0.4              # the seat's diameter over the foot's

SWITCH_H = 1.6              # MSK12C02 slide switch body below the PCB (its 3D model)
SWITCH_SLOT_MARGIN = 1.5     # power switch slot, beyond the switch body at each end
SWITCH_SCOOP_R = 8.0         # finger scoop on the outside of the wall at the power switch
SWITCH_SCOOP_DEPTH = 1.2     # leaves 0.8 mm (two lines) of wall beside the slot

# --- Battery cover --------------------------------------------------------------------------
# The cells sold as 401730 are longer than the board's 17 x 30 mm outline (BT2): 32 x 17.5 x
# 4.3 mm with their protection board (EEMB), or 32 x 17 x 4 +-0.5 mm. The checks model the
# largest of both, centred on the outline with its antenna-side end on the outline's end (3.75
# mm from the keep-out) and its extra length toward the wire pads (BT1): up to 0.4 mm over the
# pads' ends, where it lies on its foam above their solder joints.
CELL = (17.5, 32.5, 4.5)     # width, length, thickness
FOAM_T = 1.0                 # the cell sits on 1 mm foam tape (docs/ARCHITECTURE.md)
JOINT_H = 0.8                # a 28 AWG wire soldered flat on a pad, its insulation 0.8 mm across
CELL_KEEPOUT_GAP = 3.0       # cell to the antenna keep-out, as scripts/checks/clearance.py
ROOF_T = 1.6
Z_ROOF_BOTTOM = Z_PCB_TOP + COVER_POST_LEN  # 0.5 mm above the largest cell
SKIRT_LIFT = LAYER_H         # the skirt ends this far above the wall's top, so the posts clamp
                             # the PCB even when the board is PCB_T_TOL thin
KEYCAP = (17.5, 16.5)        # Kailh Choc keycap (MBK) footprint
KEYCAP_MARGIN = 0.8          # the roof and skirt stay this far from every keycap (the posts and
                             # nuts reach closer: see COVER_POST_D)
COVER_BEYOND_HOLES = 5.0     # the cover ends this far beyond its outermost holes (along y)
LED_WINDOW_D = 3.0           # over the status and charge LEDs, which shine up through the PCB

# --- Dock tray (docs/ARCHITECTURE.md, Dock) --------------------------------------------------
# The halves sit side by side in their cases, inner edges facing, as in use. The tray prints
# as two pieces split between the pockets; the dock PCB lies in a recess across both and its
# screws hold them together.
POCKET_CLEAR = 0.4           # case to pocket wall (see the pin landing terms for why not more)
DIVIDER = 3.0                # wall between the pockets at the cases' inner edges
TRAY_WALL = 3.0              # around the tray
TRAY_EDGE_TOP = 1.0          # chamfers on the tray's outer edges
TRAY_EDGE_BOTTOM = 0.4
Z_DOCK = 7.0                 # pocket floor above the table: the cases' underside, the dock PCB's top
FUNNEL = 1.2                 # 45° lead-in at the top of every pocket wall
FINGER_NOTCH = (9.0, 1.0)    # radius, and height above the floor: a notch in each pocket's outer
                             # wall, to get a finger to the case's side and tilt the half out
SPLIT_GAP = 0.2              # between the two tray pieces
RELIEF_DEPTH = 1.2           # hollow below the dock PCB under the receptacle's legs and the fuse
FUSE_RELIEF = 2.0            # the hollow reaches this far past the fuse's centre

DOCK_PCB_T = 1.6
DOCK_PCB_CLEAR = 0.3         # recess around the dock PCB's outline (JLC routes it to +-0.2 mm)
BOSS_CLEAR = 0.15            # the PCB's holes around the magnet bosses: these locate the bar,
                             # one beside each half's pins
BAR_RIM = 2.5                # dock PCB beyond the pin pads and magnet holes, for its traces
BAR_END = 1.3                # dock PCB beyond the outermost pin pads
TAB_HALF_W = 10.5            # the dock PCB's tab between the halves, for the USB-C and parts
PARTS_CLEAR = 0.8            # dock PCB parts and screw heads to the pockets' outline
DOCK_SCREW_DX = 8.3          # the two M2 screws, either side of the USB-C receptacle
MIN_INSERT_WALL = 1.0        # printed wall beside a heat-set insert's 3.2 mm hole
DOCK_SCREW_HEAD = (4.0, 1.6) # M2 x 5 pan head into an M2 x 3 heat-set insert below the PCB
DOCK_SCREW_L = 5.0
DOCK_PCB_ORIGIN = (150.0, 100.0)  # KiCad position of the tray's centre line and pad row

# Pogo pins (C5221284, docs/datasheets/C5221284_YTC1P-4020-01.pdf): free 6.0 mm above the dock
# PCB, 4.6 mm fully compressed; the half's pads are Z_PCB_BOTTOM (5.2 mm) above the floor.
PIN_FREE = 6.0
PIN_BOTTOM = 4.6
PIN_PAD_D = 2.3              # the dock PCB's land
PIN_FLANGE = (2.0, 0.5)
PIN_BARREL = (1.54, 4.0)     # diameter, top above the PCB
PIN_TIP_D = 0.9
PIN_PAD_MARGIN = 0.15        # the tip's apex stays this far inside the half's pad
MIN_COMPRESSION = 0.2        # the pins stay at least this far compressed (contact force)

# Tolerances, each the most it can be off either way. The checks add them up both linearly (the
# worst case) and as a root sum of squares (independent errors: the spread to expect).
# The pin tip's height above the pocket floor:
PIN_HEIGHT_TOL = {
    "pin free height (+-0.15 in its 4020-01R sibling's datasheet, C48783831)": 0.15,
    "pin on its solder joint": 0.05,
    "dock PCB thickness (1.6 mm +-10 %)": 0.16,
    "tray recess depth (print)": 0.1,
}
# The half's pads above the pocket floor:
CASE_HEIGHT_TOL = {"case underside to the PCB's standoffs (print)": 0.15}
# The pockets' straight walls reach above the tallest pin tip plus the case's bottom chamfer, so
# a half is guided before the pins meet it.
POCKET_DEPTH = 8.2
# Where the pin lands on the half's pad and stands in the case's window. How far the case moves
# and turns in its pocket, and the board in its case, is worked out from their outlines and
# these clearances.
POCKET_PLAY = POCKET_CLEAR + 0.2  # plus the pocket's and the case's outlines as printed
BOARD_WALL_PLAY = FIT + 0.1       # PCB to the case's wall, plus the print
BOARD_SCREW_PLAY = 0.4            # M2 in the PCB's 2.2 mm and the case's 2.4 mm holes (0.1 + 0.2),
                                  # plus 0.1 for where the printer puts the hole
DOCK_TOL = {
    "dock PCB on the magnet bosses (its milled holes +-0.2 mm)": BOSS_CLEAR + 0.1,
    "pocket to boss (one print)": 0.1,
    "pin on its 2.3 mm land (2.0 mm flange)": (PIN_PAD_D - PIN_FLANGE[0]) / 2,
    "pin tilt (1 degree over 6 mm)": 0.1,
}

# Magnets: an N52 10 x 3 mm disc (or N45 10 x 5 mm) under each of the case's steel washers, glued
# into a pocket from below. Two per half outweigh the three pins (up to 3 x 1.2 N) with the half's
# weight on top.
MAGNET = (10.0, 3.0)
MAGNET_FIT = 0.2
MAGNET_SKIN = 0.6            # printed floor between the magnet and the case's steel washer
MAGNET_WALL = 0.8            # least printed wall around a magnet, inside the dock PCB's hole
MAGNET_POCKET_H = 5.0        # deep enough for a 10 x 5 mm magnet too

FOOT_H = 2.0                 # the case's rubber feet: 6 mm round bumpers, 2 mm tall
FOOT_POCKET = 4.0            # the tray's hole under a foot, diameter over the foot's; it goes
                             # through, so a taller foot fits too

USB_BODY = (8.94, 6.8, 3.2)  # dock USB-C receptacle (C2927029): width, depth, height
USB_AXIS = 1.68              # plug axis above the PCB (datasheet)
USB_PLUG = (12.4, 6.5)       # a USB-C plug's overmold, width and height
