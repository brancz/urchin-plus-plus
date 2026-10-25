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

# --- Case ---------------------------------------------------------------------------------
WALL = 2.0                   # side wall
EDGE_TOP = 0.6               # chamfer on the outer top edge
EDGE_BOTTOM = 0.4            # chamfer on the outer bottom edge (also offsets first-layer squish)
FLOOR = 1.6                  # 8 layers
GAP = 3.6                    # floor to PCB underside: BOTTOM_PARTS_H plus 0.34 mm
Z_PCB_BOTTOM = FLOOR + GAP   # 5.2: the dock's pins reach this high
Z_PCB_TOP = Z_PCB_BOTTOM + PCB_T
SEAM_GAP = 0.2               # the walls end this far below the PCB's top: the shell sits on the
                             # PCB, never on them, even when the board is PCB_T_TOL thin
Z_WALL_TOP = Z_PCB_TOP - SEAM_GAP

BOSS_D = 6.0                 # standoff under each case hole (cut back around nearby parts)
PART_CLEAR = 0.3             # standoff to a bottom part's courtyard

# Heat-set inserts: the dock's tray holds its PCB with two (M2 x 3, CNC Kitchen's, 3.2 mm hole).
INSERT_D = 3.2
INSERT_DEPTH = 4.0           # the insert sits in the top 3 mm; 1 mm below it for displaced plastic
INSERT_L = 3.0

# Lips over the PCB's outer edge, opposite the controller. The board tilts in under them,
# outer edge first, and the controller side is screwed down. Each lip stands on the wall's
# inner part (LIP_ANCHOR wide), so the shell's wall can wrap round it.
LIP_COUNT = 2
LIP_LEN = 10.0
LIP_OVER = 0.8               # how far a lip reaches over the PCB
LIP_T = 0.8                  # 4 layers
LIP_ANCHOR = 0.8             # the lip's foot on the wall, from the wall's inner face
LIP_PLAY = 0.2               # between the PCB's top and the lip: one layer, so the lip's underside
                             # is on a layer boundary, and a board 0.16 mm thick still fits
MIN_LIP_HOLD = 0.3           # the lip stays this far over the board's edge (RSS of its play)
MIN_LIP_TILT = 5.0           # degrees a nominal board can tilt in under the lips
LIP_MIN_EDGE = 30.0          # the straight outer edge the lips sit on is at least this long
LIP_CLEAR = 0.3              # the shell's pocket round each lip

# The shell is screwed on from below: an M2 x 8 steel pan-head screw at each hole outside the
# antenna keep-out with room round it (the hole beside the thumb keys, and the controller hole
# at the battery's far end), up through the case's standoff and the PCB into a pilot hole in the
# shell, where it forms its own thread. The other 3.8 mm holes sit 1.5 mm from a switch, with no
# room for a screw. At the two holes inside the antenna keep-out, where nothing conductive may
# go (CLAUDE.md rule 6), a pin printed on the standoff passes up through the PCB into the
# shell: the pins line up the case, the PCB and the shell. Under the shell, every screw is
# hidden.
SCREW_CLEAR_D = 2.4
HEAD_D = 4.4                 # M2 pan head (4.0 mm) plus clearance
HEAD_DEPTH = 1.8             # the head stays inside the underside, clear of the dock
SHELL_SCREW_L = 8.0          # M2 x 8 pan head, DIN 7985 / ISO 7045, steel
SHELL_SCREW_HEAD = (4.0, 1.6)
PILOT_D = 1.7                # an M2 machine screw cuts its thread in a 1.7 mm printed hole
SCREW_TIP_ROOM = 0.6         # the pilot hole reaches this far past the screw's tip
SHELL_SCREW_MIN_KEYCAP = 2.5 # a hole outside the keep-out takes a screw if it's this far from every keycap
MIN_BOSS_WALL = 1.0          # printed wall round a pilot hole
M2_MIN_D = 1.886             # an M2 thread's smallest major diameter (6g)
MIN_THREAD = 2.0             # least thread engagement of a screw in a printed part or an insert
                             # (5 turns of M2)
MIN_TIP_GAP = 0.3            # between a screw's tip and a hole's bottom
PIN_D = 1.9                  # printed pin in the PCB's 2.2 mm hole
PIN_INTO_SHELL = 1.0         # how far the pin reaches above the PCB, into the shell's post
PIN_CHAMFER = 0.3
PIN_BORE_D = 2.3             # the post's bore round the pin
PIN_BORE_ROOM = 0.4          # the bore reaches this far past the pin's tip
MIN_PIN_ENGAGE = 0.6         # the pin reaches at least this far into the bore, with a board
                             # PCB_T_TOL thick
POST_D = 4.0                 # the shell's posts round the controller holes, from the PCB to the roof

USB_OPENING_W = 13.0         # USB-C plug overmolds are up to about 12.4 mm wide
USB_PLUG = (12.4, 6.5)       # a USB-C plug's overmold, width and height
USB_AXIS = Z_PCB_BOTTOM - 1.2  # the half's receptacle (its 3D model, checked against it)
USB_WINDOW_TOP = USB_AXIS + USB_PLUG[1] / 2 + 0.35  # the shell's wall ends above the plug here
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

# --- Shell ------------------------------------------------------------------------------
# The shell covers the PCB: a deck on the PCB's top whose upper 1.2 mm is the switch plate,
# a well round each key, the rim just below the keycaps, and a raised lid over the battery.
# It prints upright, its underside on the bed.
# Kailh Choc v1 (docs/datasheets/Kailh_CPG135001D02_Choc-v1.pdf): the housing is 13.8 mm across below its 15 mm flange, the
# flange's underside 2.2 mm above the PCB; it clips into a 1.2 mm plate.
PLATE_T = 1.2
Z_PLATE_TOP = Z_PCB_TOP + 2.2
Z_PLATE_BOTTOM = Z_PLATE_TOP - PLATE_T
PLATE_CUTOUT = 14.0          # round the 13.8 mm housing; a printed hole comes out about 0.1 small
CLIP_RELIEF = 15.1           # below the plate, room for the clips (14.5 mm across) to spring out
SWITCH_HOUSING = 13.8
SWITCH_FLANGE = (15.0, 0.8)  # across, thick; its underside on the plate's top
SWITCH_CLIPS = (14.5, 1.0)   # across the hooks, and how high they reach above the PCB (they
                             # catch under the plate)
SWITCH_BODY_H = 5.0          # the housing's top above the PCB; the stem is above it
# Kailh Choc keycaps (MBK, 17.5 x 16.5 mm, 4 mm tall) sit on the stem, whose top is 8 mm above
# the PCB at rest and travels 3 mm. Pressed, a keycap's skirt can't reach lower than 2.2 mm
# above the PCB, or it would hit the 1.2 mm plates Choc boards use; the checks take 2.5 mm.
KEYCAP = (17.5, 16.5)
KEYCAP_LOW = 2.5             # its lowest point above the PCB, pressed
KEYCAP_REST = KEYCAP_LOW + 3.0
KEYCAP_TOP = KEYCAP_REST + 4.0
Z_RIM = Z_PCB_TOP + 4.6      # the rim and the deck round the keys: about 1 mm below a keycap at rest
KEYCAP_MARGIN = 0.8          # each key's well, beyond its keycap
RIM_MIN = 2.0                # narrower strips of rim between the wells drop to the plate
SHELL_PLAY = 0.1             # the shell on the switches (14.0 mm cutouts round 13.8 mm housings)
SHELL_EDGE = 0.6             # chamfer on the shell's top edges, and on its outer bottom edge: with
                             # the case's EDGE_TOP a V-groove hides the seam
PUCK_HEAD = (3.5, 1.3)       # the tenting puck's screws, M2 button heads (ISO 7380) on the PCB's
                             # top (a 4 mm pan head hits two switches); the deck has a pocket over
PUCK_HEAD_CLEAR = 0.3        # each, so the puck goes on before the shell
# The battery: cells sold as 401730 are longer than the board's 17 x 30 mm outline (BT2): 32 x
# 17.5 x 4.3 mm with their protection board (EEMB), or 32 x 17 x 4 +-0.5 mm. The checks model the
# largest of both, centred on the outline with its antenna-side end on the outline's end (3.75
# mm from the keep-out) and its extra length toward the wire pads (BT1): up to 0.4 mm over the
# pads' ends, where it lies on its foam above their solder joints.
CELL = (17.5, 32.5, 4.5)     # width, length, thickness
FOAM_T = 1.0                 # the cell sits on 1 mm foam tape (docs/ARCHITECTURE.md)
JOINT_H = 0.8                # a 28 AWG wire soldered flat on a pad, its insulation 0.8 mm across
CELL_KEEPOUT_GAP = 3.0       # cell to the antenna keep-out, as scripts/checks/clearance.py
CELL_CLEAR = 0.28            # the lid's cavity round the cell (MIN_GAP plus a little)
Z_ROOF_BOTTOM = Z_PCB_TOP + FOAM_T + CELL[2] + 0.5
LID_T = 1.2
Z_LID_TOP = Z_ROOF_BOTTOM + LID_T
# The lid comes closer to the keycaps than the wells do: the cell lies 1.16 mm from the nearest
# keycap's edge, and the lid needs a wall between them.
LID_MARGIN = 0.36            # MIN_GAP plus SHELL_PLAY, and a hair
LID_WALL = 1.2               # the lid's wall round its cavity...
LID_WALL_MIN = 0.5           # ...thinner beside the cell
LID_BEYOND_HOLES = 5.0       # the lid ends this far beyond its outermost holes (along y)
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
BOARD_PIN_PLAY = 0.25             # a printed pin in the PCB's 2.2 mm hole (0.15), plus 0.1 for the print
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
DOCK_USB_AXIS = 1.68         # plug axis above the PCB (datasheet)
