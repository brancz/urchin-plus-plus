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
FLOOR = 1.2                  # 6 layers
GAP = 3.6                    # floor to PCB underside: BOTTOM_PARTS_H plus 0.34 mm
Z_PCB_BOTTOM = FLOOR + GAP   # 4.8: the dock's pins reach this high
Z_PCB_TOP = Z_PCB_BOTTOM + PCB_T
SEAM_GAP = 0.2               # the walls end this far below the PCB's top: the shell sits on the
                             # PCB, never on them, even when the board is PCB_T_TOL thin
Z_WALL_TOP = Z_PCB_TOP - SEAM_GAP

BOSS_D = 6.0                 # standoff under each case hole (cut back around nearby parts)
PART_CLEAR = 0.3             # standoff to a bottom part's courtyard

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
SCREW_L_TOL = 0.29           # an M2 x 8's length, either way (ISO 4759-1 grade A: js15)
PILOT_MIN_ROOF = 0.6         # the shell over a pilot hole's end: three layers
SHELL_SCREW_MIN_KEYCAP = 2.5 # a hole outside the keep-out takes a screw if it's this far from every keycap
MIN_BOSS_WALL = 1.0          # printed wall round a pilot hole
M2_MIN_D = 1.886             # an M2 thread's smallest major diameter (6g)
MIN_THREAD = 2.0             # least thread engagement of a screw in a printed part
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
DOCK_WINDOW_MARGIN = 1.5     # around the charging pads, for the pogo pins soldered on them (checked)
PUCK_CLEAR = 0.75            # around the tenting puck's outline
DISC_D = 10.0                # steel for the dock magnets (the board's MK1/MK2 marker): an M5 washer,
                             # DIN 125 / ISO 7089, zinc-plated steel, 10 x 1 mm with a 5.3 mm hole
DISC_T = 1.2                 # its recess in the case's underside: the washer is at most 1.1 mm
                             # thick (ISO 7089), so it never stands proud; 6 layers
DISC_PAD = (0.8, 0.4)        # the floor is no thicker, so a pad inside over each recess: its wall
                             # round the recess, and the skin over it
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

# --- Dock (docs/ARCHITECTURE.md, Dock) -------------------------------------------------------
# The halves sit side by side in their cases, inner edges facing, as in use, in two shallow
# pockets of a flat tray. Each half carries three pogo pins soldered on its charging pads, their
# plungers out through the case's window; the dock PCB lies in a recess in the tray, flush with
# its floor, with a flat gold pad under each pin. A thin printed plate covers each pocket's
# floor, the PCB included: through a slot in it the pins reach their pads, and only the pads
# show. The tray prints as two pieces split between the pockets; the dock PCB lies across both,
# and a printed cover over the PCB's back tab (the USB-C receptacle and the small parts) joins
# them.
POCKET_CLEAR = 0.4           # case to pocket wall (see the pin landing terms for why not more)
DIVIDER = 3.0                # wall between the pockets at the cases' inner edges
TRAY_WALL = 3.0              # around the tray
TRAY_EDGE_TOP = 1.0          # chamfers on the tray's outer edges
TRAY_EDGE_BOTTOM = 0.4
SPLIT_GAP = 0.2              # between the two tray pieces
FUNNEL = 0.6                 # 45° lead-in at the top of every pocket wall
POCKET_DEPTH = 2.6           # the straight walls reach above the lowest pin tip plus the case's
                             # bottom chamfer, so a half is guided before its pins meet the pads

# Magnets: an N52 10 x 3 mm disc under each of the case's steel washers, glued into a pocket from
# below. Two per half outweigh the three pins (up to 3 x 1.2 N) with the half's weight on top.
MAGNET = (10.0, 3.0)
MAGNET_FIT = 0.2
MAGNET_SKIN = 0.4            # printed skin over the magnet, under the floor plate (two layers)
MAGNET_WALL = 0.8            # least printed wall around a magnet, inside the dock PCB's hole
MAGNET_POCKET_H = MAGNET[1] + 0.4  # the magnet, and room for its glue
Z_DOCK = MAGNET_POCKET_H + MAGNET_SKIN  # 3.8: the tray's floor in the pockets and the dock PCB's
                                        # top, above the table
DOCK_FLOOR_T = 0.4           # the floor plate over each pocket's floor (two layers)
DOCK_FLOOR_CLEAR = 0.15      # its outline inside the pocket's
DOCK_FLOOR_PLAY = DOCK_FLOOR_CLEAR + 0.2  # how far it moves in the pocket, with both outlines as printed
DOCK_FLOOR_SLOT = 0.4        # its slot over a half's three contacts reaches this far past them
Z_POCKET = Z_DOCK + DOCK_FLOOR_T  # 4.2: the pocket floor: the cases' undersides
RELIEF_DEPTH = 1.0           # hollow below the dock PCB under the receptacle's legs and the fuse
FUSE_RELIEF = 2.0            # the hollow reaches this far past the fuse's centre

DOCK_PCB_T = 1.6
DOCK_PCB_CLEAR = 0.3         # recess around the dock PCB's outline (JLC routes it to +-0.2 mm)
BOSS_CLEAR = 0.15            # the PCB's holes around the magnet bosses: these locate the bar,
                             # one beside each half's pads
DOCK_CONTACT = (3.2, 6.0)    # the flat ENIG pad under each pin: at 4 mm pitch, 0.8 mm between pads
BAR_RIM = 2.5                # dock PCB beyond the pads and magnet holes, for its traces
BAR_END = 1.0                # dock PCB beyond the outermost pads (1 mm of tray between its recess
                             # and the next magnet's pocket)
SPINE_W = 6.0                # each arm of the dock PCB, from its bar back to the tab under the case
PCB_INSET = 1.5              # the dock PCB inside the pockets' walls, where it lies in their floor
TAB_HALF_W = 12.5            # the dock PCB's tab at the back, between the halves: the USB-C and parts.
                             # Its recess clears the round ends of the pockets' inner walls by 1.5 mm.
TAB_LEAD = 0.5               # the tab reaches this far forward of the pockets' straight inner walls'
                             # ends, so the cover, not a sliver of tray, forms the rounded walls behind
PARTS_CLEAR = 0.8            # dock PCB parts to the pockets' outline
DOCK_PCB_ORIGIN = (150.0, 100.0)  # KiCad position of the tray's centre line and pad row

# The cover over the tab: it fills the recess outside the pockets, flush with the tray's top,
# rests on the PCB and holds it down, with a pocket over each part and a hole over the LED.
COVER_CLEAR = 0.15           # the cover's outline inside its recess
COVER_PART_CLEAR = 0.3       # its pockets round the parts' bodies, and above them
COVER_MIN_SKIN = 0.6         # three layers over the tallest part
LED_HOLE_D = 1.2             # over the dock's power LED

# Dock USB-C receptacle: HRO TYPE-C-31-M-28A (C2848622, docs/datasheets/C2848622_TYPE-C-31-M-28A.pdf),
# power only, mid-mount: its body sinks into a notch in the dock PCB and stands 1.58 mm above and
# below the board's top, so the cover over it stays flush with the tray's top. Its mouth is flush
# with the tray's back face.
DOCK_USB_BODY = (8.94, 6.8, 1.58)  # width, depth, height above the PCB's top
DOCK_USB_AXIS = 0.0          # plug axis above the PCB's top (checked against its 3D model)
DOCK_USB_FRONT = 5.28        # its mouth, ahead of the footprint's origin: 2.80 mm ahead of the front
                             # legs (the drawing's 6.8 mm body less 4.00); the body's back is at -1.52
DOCK_USB_NOTCH = (9.2, 1.62)  # the PCB's notch: width (the shell plus 0.13 mm a side; the housing
                              # below the board at its back is 8.34 wide), and how far behind the
                              # footprint's origin it ends (HRO's layout: 0.5 mm behind the rear legs)
DOCK_USB_NOTCH_RELIEF = 1.0   # a round relief behind each inner corner: JLC's 1.0 mm router reaches them
DOCK_USB_LEGS = (5.58, -1.12, 2.48)  # its four shell legs through the PCB: x either side, and
                                     # the front and back pairs' y (footprint, mouth at +y)

# Pogo pins (C5221284, docs/datasheets/C5221284_YTC1P-4020-01.pdf), three per half, soldered by
# hand on the half's charging pads (TP1), plunger down through the case's window: 6.0 mm free from
# the flange's base, 4.6 mm fully compressed. Docked, each stands on a dock contact DOCK_FLOOR_T
# below the pocket floor, so it is Z_PCB_BOTTOM less its solder plus DOCK_FLOOR_T (5.15 mm) long:
# 0.85 mm compressed. Off the dock, the free tips stand 1.25 mm below the case and the feet hold
# them off the desk.
PIN_FREE = 6.0
PIN_BOTTOM = 4.6
PIN_FLANGE = (2.0, 0.5)
PIN_BARREL = (1.54, 4.0)     # diameter, length from the flange's base
PIN_TIP_D = 0.9
PIN_SOLDER = 0.05            # solder under the flange
PIN_PAD_MARGIN = 0.15        # the tip's apex stays this far inside the dock's pad
MIN_COMPRESSION = 0.2        # the pins stay at least this far compressed (contact force)

# Tolerances, each the most it can be off either way. The checks add them up both linearly (the
# worst case) and as a root sum of squares (independent errors: the spread to expect).
# A free pin's length below the half's pad:
PIN_HEIGHT_TOL = {
    "pin free height (+-0.15 in its 4020-01R sibling's datasheet, C48783831)": 0.15,
    "pin on its hand-soldered joint": 0.1,
}
# The half's pads above the case's underside:
CASE_HEIGHT_TOL = {"case underside to the PCB's standoffs (print)": 0.15}
# The dock's contacts against the pocket floor, either way:
DOCK_HEIGHT_TOL = {"floor plate thickness (print)": 0.05}
# ...and only deeper: where the dock PCB stands proud of the tray's floor, the plate and the case
# rest on it, and the contacts stay DOCK_FLOOR_T under the case.
DOCK_DEPTH_TOL = {
    "dock PCB thickness (1.6 mm +-10 %)": 0.16,
    "tray recess depth (print)": 0.1,
}
# Where a pin lands on its dock pad, and where it stands in the case's window. How far the case
# moves and turns in its pocket, and the board in its case, is worked out from their outlines and
# these clearances.
POCKET_PLAY = POCKET_CLEAR + 0.2  # plus the pocket's and the case's outlines as printed
BOARD_WALL_PLAY = FIT + 0.1       # PCB to the case's wall, plus the print
BOARD_SCREW_PLAY = 0.4            # M2 in the PCB's 2.2 mm and the case's 2.4 mm holes (0.1 + 0.2),
                                  # plus 0.1 for where the printer puts the hole
BOARD_PIN_PLAY = 0.25             # a printed pin in the PCB's 2.2 mm hole (0.15), plus 0.1 for the print
PIN_TOL = {                       # the pin on the half
    "pin soldered on its pad, in the jig (its bore's 0.18 mm a side, and the print)": 0.3,
    "pin tilt (1.5 degrees over 6 mm)": 0.16,
}
DOCK_TOL = {                      # the pad on the dock
    "dock PCB on the magnet bosses (its milled holes +-0.2 mm)": BOSS_CLEAR + 0.1,
    "pocket to boss (one print)": 0.1,
}

# The jig that holds a half's three pins upright while they're soldered (board out of its case,
# bottom up): a plate over the pins with a bore round each plunger, standing on the board on two
# legs with a peg into the board's holes either side of the pads, and on two feet beside the pins.
# Seen from above, the plate leaves each pad's ends (past the flange) open for the iron.
JIG_GAP = 4.6                # the plate's underside above the PCB: past every bottom part (GAP tall)
                             # and the pins' barrels
JIG_PLATE_T = 2.0            # the plungers' tips end inside it, at least JIG_TIP_INSET short of its
                             # top (the face printed on the bed, with its first layer's squish) with
                             # the longest pin
JIG_TIP_INSET = 0.3
JIG_BORE_CLEAR = 0.35        # bore over the plunger's diameter: a printed hole comes out about 0.1 small
JIG_LEAD = 0.3               # 45° lead-in on each bore, where the plunger comes in
JIG_COLLAR = 0.8             # wall round each bore: two perimeters
JIG_LEG_D = 5.0
JIG_PEG_CLEAR = 0.2          # peg under the board hole's diameter
JIG_PEG_LEN = 1.2            # into the 1.6 mm board
JIG_BAR_W = 5.0              # the plate's arms from the strip's ends to each leg and foot
JIG_STRIP = 1.8              # the strip joining the collars along the pin row: inside the flanges
JIG_STRIP_END = 4.5          # it runs this far past the end pins, where the arms start
JIG_PAD_VIEW = 1.0           # mm², of each pad's end past the flange, in view from above past the
                             # plate (grown by MIN_GAP): room for the iron
JIG_FOOT_D = 4.0
JIG_FOOT_ALONG = 9.0         # each foot from the pins' centre along their row, either way...
JIG_FOOT_OUT = 3.5           # ...and this far out from it, away from the legs: the pins stand
                             # between the legs and the feet

FOOT_H = 3.0                 # the case's rubber feet: 6 mm round bumpers, at least 3 mm tall
FOOT_SQUASH = 0.2            # how far a foot gives under a hand on the keys
FOOT_POCKET = 5.0            # the hole under a foot in the tray and the floor plate, diameter
                             # over the foot's; it goes through, so a taller foot fits too
