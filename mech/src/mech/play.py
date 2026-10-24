"""How far a point of a rigid part can move when the part moves and turns inside a clearance:
a case in its dock pocket, a board in its case (dock_checks, checks.lip_rows)."""

import math

import numpy as np
from scipy.optimize import linprog

AXES = {"x": (1.0, 0.0), "y": (0.0, 1.0)}
DIRECTIONS = [(math.cos(2 * math.pi * k / 16), math.sin(2 * math.pi * k / 16)) for k in range(16)]


class Play:
    """How far a point of a rigid body can move when the body moves and turns inside its own
    outline grown by `clearance`, and each (point, play) in `pins` stays within play of where it
    was: a linear program in (x, y, turn), first order in the turn (the turns here are below
    0.02 rad, so the error is under 0.01 mm). Every short stretch of the outline (step mm) may
    move outward along its normal by at most the clearance at both its ends."""

    def __init__(self, face, clearance, pins=(), step=0.5):
        pts = []
        for e in face.faces()[0].outer_wire().order_edges():
            n = max(1, math.ceil(e.length / step))
            seg = [e.position_at(i / n) for i in range(n + 1)]
            if pts and (seg[0] - pts[-1]).length > (seg[-1] - pts[-1]).length:
                seg.reverse()
            pts += seg[1:] if pts else seg
        a = np.array([(p.X, p.Y) for p in pts])
        b = np.roll(a, -1, axis=0)
        area = np.sum(a[:, 0] * b[:, 1] - b[:, 0] * a[:, 1]) / 2
        d = b - a
        keep = np.hypot(d[:, 0], d[:, 1]) > 1e-6
        a, b, d = a[keep], b[keep], d[keep]
        n = np.stack([d[:, 1], -d[:, 0]], axis=1) * (1 if area > 0 else -1)  # outward
        n /= np.hypot(n[:, 0], n[:, 1])[:, None]
        self.o = a.mean(axis=0)
        rows = [self._row(nn, p) for nn, ends in zip(n, zip(a, b)) for p in ends]
        bound = [clearance] * len(rows)
        for (sx, sy), play in pins:
            for u in DIRECTIONS:  # a 16-gon around the play circle: a hair looser than the circle
                rows.append(self._row(u, (sx, sy)))
                bound.append(play)
        self.a_ub, self.b_ub = np.array(rows), np.array(bound)

    def _row(self, u, p):
        """u . (displacement of p) for a move (tx, ty) and a turn t about o."""
        rx, ry = p[0] - self.o[0], p[1] - self.o[1]
        return [u[0], u[1], u[0] * -ry + u[1] * rx]

    def reach(self, q, u):
        res = linprog(-np.array(self._row(u, q)), A_ub=self.a_ub, b_ub=self.b_ub, bounds=[(None, None)] * 3,
                      method="highs")
        if res.status != 0:
            raise RuntimeError(f"mech: play: {res.message}")
        return -res.fun

    def along(self, q, axis):
        """The most q moves either way along an axis (x or y)."""
        u = AXES[axis]
        return max(self.reach(q, u), self.reach(q, (-u[0], -u[1])))

    def radial(self, q):
        return max(self.reach(q, u) for u in DIRECTIONS)
