"""The pinion's teeth and the rack's, one profile.

An involute pinion — sixteen teeth on a 240 mm pitch circle, 20° pressure
angle (formlab.clearance.PINION) — and the straight-flanked rack that is its
conjugate: a rack's involute is a straight line at the pressure angle, so the
rack's teeth are trapezoids. The one profile feeds four places:

  - tools/build_clockwork.gear extrudes `tooth_polygon` for each tooth of a
    pinion (the flywheel keeps its decorative box teeth);
  - formlab.gantry.rack cuts the rack's teeth by `rack_half`;
  - formlab.pawl.tooth_distance measures the roller against `tooth_polygon`
    inset by the bevel (so its corners are round, as the built tooth's are);
  - tools/test_gantry.py rolls the two together (`mesh_gap`) — a
    separating-axis test between convex polygons, no dependency.

Everything is in the disc's plane. A tooth's frame has u radial from the axle
and v tangential, tip toward +u; tooth i's frame is turned i·2π/16 from +x in
the disc's home frame, so the tips stay at the multiples of 2π/16 the pawl's
kinematics assume (`pawl.tooth_distance`, `ClockworkMotion.tooth_distance`).
"""
import numpy as np
try:
    from .clearance import PINION
except ImportError:   # bare import (formlab/ on sys.path, from Blender)
    from clearance import PINION

PRESSURE = np.radians(20)      # the flanks' pressure angle
BACKLASH = .003                # each tooth thinner than half the pitch by this at the pitch line, rack and pinion alike
BEVEL = .004                   # the teeth's corners are rounded this much: build_clockwork's bevel, and the distance field's
TEETH = PINION['teeth']; R_PITCH = PINION['r_pitch']; R_TIP = PINION['r_tip']; R_HUB = PINION['r_hub']
PITCH = 2*np.pi*R_PITCH/TEETH
R_BASE = R_PITCH*np.cos(PRESSURE)   # the involute unrolls from here; below it the flank runs radially into the hub
ROOT = R_HUB-.003                   # the tooth reaches this far into the hub, so the joined mesh shows no seam
FLANK_SAMPLES = 6
PSI_PITCH = (PITCH/4-BACKLASH/2)/R_PITCH   # half the tooth's angular thickness at the pitch circle

def _inv(a): return np.tan(a)-a

def half_angle(rho):
    """Half the tooth's angular thickness at radius rho (>= R_BASE): the involute's polar equation."""
    a = np.arccos(np.clip(R_BASE/np.asarray(rho, float), -1, 1))
    return PSI_PITCH+_inv(PRESSURE)-_inv(a)

def tooth_polygon():
    """One tooth as a convex counter-clockwise polygon (N, 2) in its frame:
    the root edge inside the hub, a radial run up to the base circle, the
    involute flank sampled to the tip, the tip land, and down the other side."""
    rho = np.linspace(R_BASE, R_TIP, FLANK_SAMPLES); ps = half_angle(rho); pb = ps[0]
    right = np.c_[rho*np.cos(ps), -rho*np.sin(ps)]; left = right[::-1]*[1, -1]
    return np.vstack([[ROOT*np.cos(pb), -ROOT*np.sin(pb)], right, left, [ROOT*np.cos(pb), ROOT*np.sin(pb)]])

def inset(poly, b):
    """A convex counter-clockwise polygon offset inward by b: each edge's line
    shifted along its inward normal, consecutive lines intersected."""
    poly = np.asarray(poly, float); n = len(poly); lines = []
    for i in range(n):
        a = poly[i]; c = poly[(i+1) % n]; e = (c-a)/np.linalg.norm(c-a)
        lines.append((a+np.array([-e[1], e[0]])*b, e))
    out = []
    for i in range(n):
        (p1, e1), (p2, e2) = lines[i-1], lines[i]
        det = e2[0]*e1[1]-e1[0]*e2[1]; d = p2-p1
        s = (d[1]*e2[0]-d[0]*e2[1])/det                 # p1 + s e1 = p2 + t e2, by Cramer
        out.append(p1+s*e1)
    return np.array(out)

def convex_distance(px, py, poly):
    """Signed distance from points (px, py) to a convex counter-clockwise
    polygon: negative inside. Vectorised over the points."""
    px = np.asarray(px, float); py = np.asarray(py, float); n = len(poly)
    inside = np.ones(np.broadcast(px, py).shape, bool); dmin = np.full(inside.shape, np.inf)
    for i in range(n):
        ax, ay = poly[i]; bx, by = poly[(i+1) % n]; ex = bx-ax; ey = by-ay; L2 = ex*ex+ey*ey
        t = np.clip(((px-ax)*ex+(py-ay)*ey)/L2, 0, 1)
        dmin = np.minimum(dmin, np.hypot(px-(ax+t*ex), py-(ay+t*ey)))
        inside &= (ex*(py-ay)-ey*(px-ax)) >= 0
    return np.where(inside, -dmin, dmin)

def rack_half(s):
    """Half the rack tooth's thickness at distance s from the pinion's axle:
    a straight flank at the pressure angle, half a pitch less the backlash at
    the pitch line, wider away from the axle (the tooth's tip is toward it)."""
    return PITCH/4-BACKLASH/2+(np.asarray(s, float)-R_PITCH)*np.tan(PRESSURE)

def pinion_tooth(i, x):
    """Tooth i's polygon in the carriage's frame — the axle at the origin, the
    rack toward +v — for the carriage at rail position x (spun x / r_pitch)."""
    a = i*2*np.pi/TEETH+x/R_PITCH; c = np.cos(a); s = np.sin(a); P = tooth_polygon()
    return np.c_[P[:, 0]*c-P[:, 1]*s, P[:, 0]*s+P[:, 1]*c]

def rack_tooth(k, x, s_tip, s_root, embed=.006):
    """Rack tooth k — centred at (k + ½)·pitch along the rail — as a convex
    counter-clockwise polygon in the carriage's frame for the carriage at x:
    its tip at s_tip from the axle, its root `embed` into the strip at s_root."""
    xc = (k+.5)*PITCH-x; s0 = s_root+embed; h0 = rack_half(s0); h1 = rack_half(s_tip)
    return np.array([[xc+h0, s0], [xc+h1, s_tip], [xc-h1, s_tip], [xc-h0, s0]])

def separation(A, B):
    """Separating-axis distance between two convex polygons: the widest gap
    along any edge normal of either (positive: apart; a lower bound on the
    true distance, exact when a face is the closest feature)."""
    best = -np.inf
    for P in (A, B):
        for i in range(len(P)):
            e = P[(i+1) % len(P)]-P[i]; n = np.array([-e[1], e[0]])/np.linalg.norm(e)
            pa = A@n; pb = B@n; best = max(best, pb.min()-pa.max(), pa.min()-pb.max())
    return best

def mesh_gap(x, s_tip, s_root):
    """The least separation between any pinion tooth and any rack tooth for
    the carriage at x, and which pair: (gap, (rack k, pinion i))."""
    worst = (np.inf, None)
    racks = [(k, rack_tooth(k, x, s_tip, s_root)) for k in range(-2, 3)]
    for i in range(TEETH):
        P = pinion_tooth(i, x)
        if P[:, 1].max() < s_tip-.002: continue
        for k, R in racks:
            g = separation(P, R)
            if g < worst[0]: worst = (float(g), (k, i))
    return worst
