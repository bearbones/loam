"""Finite-difference stiff string with a curved jawari bridge.

Where Karplus-Strong models the string's *output* (a delay loop),
this models the string itself: Bilbao's explicit scheme for

    u_tt = c^2 u_xx - kappa^2 u_xxxx - 2 sig0 u_t + 2 sig1 u_txx

on N+1 nodes, stable while lambda^2 + 4 mu^2 <= 1 (lambda = c dt/dx,
mu = kappa dt/dx^2). Simulating displacement buys the one thing the
KS loop cannot do (measured, e41): DISTRIBUTED contact. A parabolic
barrier under the last stretch of string, apex exactly at the
termination, catches the string over many nodes at once; each
half-cycle the string wraps and unwraps along the curve, modulating
its effective length. That pumps energy UP the partial series — the
tanpura's jawari bloom, high partials swelling ~0.5 s after the
pluck instead of decaying from t=0.

Two geometry lessons paid for in failed runs:
- the apex must sit AT x = L. Putting the parabola's zero mid-zone
  pins the string there — measured as pitch f0/xb, the detuning
  itself naming the bug.
- contact must be an elastic penalty force (one-sided spring,
  K * penetration^alpha). Projection (max(u, barrier)) is a
  perfectly inelastic collision that eats the string alive.
"""

import numpy as np

from . import SR


def fdpluck(f0: float, dur: float, amp: float = 1.0,
        kappa: float = 0.3, sig0: float = 0.9, sig1: float = 1e-4,
        pick: float = 0.28, bridge: bool = True, zone: float = 0.10,
        gcurve: float = 0.2, K: float = 3e9, alpha: float = 1.3,
        pluck_m: float = 1.6e-3, N: int = 0,
        contact: str = "sav") -> np.ndarray:
    """One plucked note on the simulated string. bridge=True adds
    the jawari barrier (gcurve = parabola curvature, K/alpha the
    contact spring). pluck_m is the physical pluck displacement —
    the contact nonlinearity is amplitude-dependent, so pluck_m vs
    gcurve sets how hard the string works the bridge. ~1 s of
    compute per 1 s of audio.

    contact="sav" (default) integrates the barrier force through a
    scalar auxiliary variable psi = sqrt(2 phi + eps) per node,
    whose update is LINEAR in the unknown displacement — energy-
    stable at ANY K, so contact stiffness is a safe voicing knob
    (measured e43: K=1e12 rings where the explicit penalty NaNs at
    1e11). contact="penalty" keeps the plain explicit force for
    comparison.

    f0 may be an ARRAY of per-sample Hz (any length; resampled to
    the step count): time-varying tension, i.e. MEEND. Pitch lives
    in one coefficient (lambda^2 = (c dt/dx)^2), so bending is one
    multiply per step; the grid is sized for the trajectory's
    HIGHEST note, where stability is tightest."""
    dt = 1.0 / SR
    steps = int(dur * SR)
    f0 = np.asarray(f0, dtype=float)
    scalar_f0 = (f0.ndim == 0)
    f0max = float(f0) if scalar_f0 else float(f0.max())
    if N <= 0:
        # largest stable grid with margin: a N^2 + b N^4 <= 0.6
        a = (2.0 * f0max / SR) ** 2
        b = (2.0 * kappa / SR) ** 2
        N = int(np.sqrt((-a + np.sqrt(a * a + 2.4 * b)) / (2 * b)))
        N = max(min(N, 180), 24)
    dx = 1.0 / N
    mu2 = (kappa * dt / dx ** 2) ** 2
    assert (2.0 * f0max * dt / dx) ** 2 + 4 * mu2 <= 1.0, \
        "unstable grid: shrink N or kappa"
    if scalar_f0:
        lam2s = np.full(steps, (2.0 * float(f0) * dt / dx) ** 2)
    else:
        traj = np.interp(np.linspace(0, 1, steps),
                np.linspace(0, 1, len(f0)), f0)
        lam2s = (2.0 * traj * dt / dx) ** 2

    x = np.linspace(0.0, 1.0, N + 1)
    u = np.where(x < pick, x / pick, (1 - x) / (1 - pick)) * pluck_m
    u[0] = u[-1] = 0.0
    up = u.copy()
    out = np.empty(steps)
    ro = max(int(0.12 * N), 2)
    bz = x > 1.0 - zone
    bb = -gcurve * (1.0 - x[bz]) ** 2
    A = 1.0 + sig0 * dt
    B = 1.0 - sig0 * dt
    s1c = 2.0 * sig1 * dt / dx ** 2
    Kdt2 = K * dt * dt
    if contact == "sav":
        eta0 = np.maximum(bb - u[bz], 0.0)
        psi = np.sqrt(2.0 * K / (alpha + 1) * eta0 ** (alpha + 1)
                + 1e-24)
    lap = np.zeros(N + 1)
    lapo = np.zeros(N + 1)
    bi = np.zeros(N + 1)
    for t in range(steps):
        lap[1:-1] = u[2:] - 2 * u[1:-1] + u[:-2]
        lapo[1:-1] = up[2:] - 2 * up[1:-1] + up[:-2]
        bi[2:-2] = u[4:] - 4 * u[3:-1] + 6 * u[2:-2] - 4 * u[1:-3] \
            + u[:-4]
        bi[1] = u[3] - 4 * u[2] + 6 * u[1] - 4 * u[0] - u[1]
        bi[-2] = -u[-2] - 4 * u[-1] + 6 * u[-2] - 4 * u[-3] + u[-4]
        un = (2 * u - B * up + lam2s[t] * lap - mu2 * bi
                + s1c * (lap - lapo)) / A
        if bridge:
            if contact == "sav":
                eta = np.maximum(bb - u[bz], 0.0)
                g = K * eta ** alpha / psi
                # force at midpoint: g*(psi_next + psi)/2 with
                # psi_next = psi - g*(u_next - u_prev)/2 — linear
                # in u_next, so each node solves in closed form
                unb = (un[bz] + dt * dt / A
                        * (g * psi + g * g * up[bz] / 4.0)) \
                    / (1.0 + dt * dt * g * g / (4.0 * A))
                psi = psi - g * (unb - up[bz]) / 2.0
                un[bz] = unb
            else:
                pen = np.maximum(bb - u[bz], 0.0)
                un[bz] += Kdt2 * pen ** alpha / A
        un[0] = un[-1] = 0.0
        # velocity readout: a string released from rest starts at
        # v=0 exactly (displacement would start on a DC step and
        # click at every onset — and at the loop seam)
        out[t] = (un[ro] - u[ro]) * SR
        up, u = u, un
    r = int(min(0.05, dur * 0.1) * SR)
    if r > 0:
        out[-r:] *= np.linspace(1, 0, r)
    return out * amp / (np.max(np.abs(out)) + 1e-12) * 0.9


def fdpluck2(f0: float, dur: float, amp: float = 1.0,
        kappa: float = 0.3, sig0: float = 0.9, sig1: float = 1e-4,
        pick: float = 0.28, zone: float = 0.10, gcurve: float = 0.2,
        K: float = 3e9, alpha: float = 1.3, pluck_m: float = 1.6e-3,
        N: int = 0, split: float = 0.006, kc: float = 1e5,
        angle: float = 0.6, buses: bool = False):
    """Two-POLARIZATION pluck (e48): the string vibrates in two
    transverse planes — vertical u (plucked, and the only one the
    jawari barrier touches) and horizontal v (starts at rest,
    detuned by `split`, fed only through a spring coupling of
    strength `kc` across the bridge zone). Two phenomena fall out
    and both are measured, not decorative:
      - delayed energy transfer: v blooms hundreds of ms after
        the pluck and rings within ~20 dB of u (kc=0: silence).
      - polarization beating: the mode pair rings `f0*split`
        apart, a slow shimmer riding every partial (measured on
        the v bus by ruler.beat_profile; at kc=1e5 the coupling's
        own mode split is below the detune and beat tracks
        design within an envelope bin).
    The pickup hears cos(angle)*u + sin(angle)*v. buses=True also
    returns the raw per-polarization velocity buses for own-bus
    measurement. Scalar f0 only (meend stays single-pol for now).
    ~2x fdpluck's compute."""
    dt = 1.0 / SR
    steps = int(dur * SR)
    f0h = f0 * (1.0 + split)
    if N <= 0:
        a = (2.0 * f0h / SR) ** 2
        b = (2.0 * kappa / SR) ** 2
        N = int(np.sqrt((-a + np.sqrt(a * a + 2.4 * b)) / (2 * b)))
        N = max(min(N, 180), 24)
    dx = 1.0 / N
    mu2 = (kappa * dt / dx ** 2) ** 2
    assert (2.0 * f0h * dt / dx) ** 2 + 4 * mu2 <= 1.0, \
        "unstable grid: shrink N or kappa"
    lam2v = (2.0 * f0 * dt / dx) ** 2
    lam2h = (2.0 * f0h * dt / dx) ** 2
    x = np.linspace(0.0, 1.0, N + 1)
    u = np.where(x < pick, x / pick, (1 - x) / (1 - pick)) * pluck_m
    u[0] = u[-1] = 0.0
    up = u.copy()
    v = np.zeros(N + 1)
    vp = v.copy()
    ou = np.empty(steps)
    ov = np.empty(steps)
    ro = max(int(0.12 * N), 2)
    bz = x > 1.0 - zone
    bb = -gcurve * (1.0 - x[bz]) ** 2
    A = 1.0 + sig0 * dt
    B = 1.0 - sig0 * dt
    s1c = 2.0 * sig1 * dt / dx ** 2
    kdt2 = kc * dt * dt
    eta0 = np.maximum(bb - u[bz], 0.0)
    psi = np.sqrt(2.0 * K / (alpha + 1) * eta0 ** (alpha + 1)
            + 1e-24)
    lap = np.zeros(N + 1)
    lapo = np.zeros(N + 1)
    bi = np.zeros(N + 1)
    lp2 = np.zeros(N + 1)
    lpo2 = np.zeros(N + 1)
    bi2 = np.zeros(N + 1)
    for t in range(steps):
        lap[1:-1] = u[2:] - 2 * u[1:-1] + u[:-2]
        lapo[1:-1] = up[2:] - 2 * up[1:-1] + up[:-2]
        bi[2:-2] = u[4:] - 4 * u[3:-1] + 6 * u[2:-2] - 4 * u[1:-3] \
            + u[:-4]
        bi[1] = u[3] - 4 * u[2] + 6 * u[1] - 4 * u[0] - u[1]
        bi[-2] = -u[-2] - 4 * u[-1] + 6 * u[-2] - 4 * u[-3] + u[-4]
        lp2[1:-1] = v[2:] - 2 * v[1:-1] + v[:-2]
        lpo2[1:-1] = vp[2:] - 2 * vp[1:-1] + vp[:-2]
        bi2[2:-2] = v[4:] - 4 * v[3:-1] + 6 * v[2:-2] \
            - 4 * v[1:-3] + v[:-4]
        bi2[1] = v[3] - 4 * v[2] + 6 * v[1] - 4 * v[0] - v[1]
        bi2[-2] = -v[-2] - 4 * v[-1] + 6 * v[-2] - 4 * v[-3] \
            + v[-4]
        un = (2 * u - B * up + lam2v * lap - mu2 * bi
                + s1c * (lap - lapo)) / A
        vn = (2 * v - B * vp + lam2h * lp2 - mu2 * bi2
                + s1c * (lp2 - lpo2)) / A
        un[bz] += kdt2 * (v[bz] - u[bz]) / A
        vn[bz] += kdt2 * (u[bz] - v[bz]) / A
        eta = np.maximum(bb - u[bz], 0.0)
        g = K * eta ** alpha / psi
        unb = (un[bz] + dt * dt / A
                * (g * psi + g * g * up[bz] / 4.0)) \
            / (1.0 + dt * dt * g * g / (4.0 * A))
        psi = psi - g * (unb - up[bz]) / 2.0
        un[bz] = unb
        un[0] = un[-1] = 0.0
        vn[0] = vn[-1] = 0.0
        ou[t] = (un[ro] - u[ro]) * SR
        ov[t] = (vn[ro] - v[ro]) * SR
        up, u = u, un
        vp, v = v, vn
    out = np.cos(angle) * ou + np.sin(angle) * ov
    r = int(min(0.05, dur * 0.1) * SR)
    if r > 0:
        out[-r:] *= np.linspace(1, 0, r)
    out = out * amp / (np.max(np.abs(out)) + 1e-12) * 0.9
    return (out, ou, ov) if buses else out


def fdsym(f0s, drive: np.ndarray, amp: float = 1.0,
        kappa: float = 0.3, sig0: float = 0.12, sig1: float = 1e-4,
        node: float = 0.93, N: int = 0, buses: bool = False):
    """A bank of SYMPATHETIC strings (taraf, e53): S undisturbed
    lattices, one per Hz in f0s, forced at a shared bridge node
    by an external signal. No pluck, no barrier — every string
    starts at rest and rings only with what the drive feeds it,
    which is the whole point: a string tuned to the driving pitch
    accumulates energy coherently (resonance), a detuned
    neighbour integrates to nothing, and strings sharing a
    PARTIAL with the drive (e.g. a fifth below: its h3 ~ the
    drive's h2) bloom on that shared mode — cross-tuning
    sympathy, physics, not programming.

    sig0 defaults far below the played string's 0.9: a taraf's
    voice IS its long ring after the exciter dies (t60 ~ 6.9 /
    sig0 ~ 58 s of coherent memory; the audible halo hangs on
    for seconds).

    The bank is vectorized across strings — (S, N+1) arrays, one
    shared grid sized for the highest f0 — so S strings cost
    about one string's loop. Returns the normalized bank sum
    (len(drive) samples); buses=True also returns the RAW
    (S, steps) per-string velocity buses for own-bus
    measurement — selectivity and sustain live in their ratios,
    which normalization would erase."""
    dt = 1.0 / SR
    steps = len(drive)
    f0s = np.asarray(f0s, dtype=float)
    S = len(f0s)
    f0max = float(f0s.max())
    if N <= 0:
        a = (2.0 * f0max / SR) ** 2
        b = (2.0 * kappa / SR) ** 2
        N = int(np.sqrt((-a + np.sqrt(a * a + 2.4 * b)) / (2 * b)))
        N = max(min(N, 180), 24)
    dx = 1.0 / N
    mu2 = (kappa * dt / dx ** 2) ** 2
    assert (2.0 * f0max * dt / dx) ** 2 + 4 * mu2 <= 1.0, \
        "unstable grid: shrink N or kappa"
    lam2 = ((2.0 * f0s * dt / dx) ** 2)[:, None]
    u = np.zeros((S, N + 1))
    up = np.zeros((S, N + 1))
    outs = np.empty((S, steps))
    ro = max(int(0.12 * N), 2)
    ni = min(int(node * N), N - 1)
    A = 1.0 + sig0 * dt
    B = 1.0 - sig0 * dt
    s1c = 2.0 * sig1 * dt / dx ** 2
    fdt2 = dt * dt / A
    lap = np.zeros((S, N + 1))
    lapo = np.zeros((S, N + 1))
    bi = np.zeros((S, N + 1))
    for t in range(steps):
        lap[:, 1:-1] = u[:, 2:] - 2 * u[:, 1:-1] + u[:, :-2]
        lapo[:, 1:-1] = up[:, 2:] - 2 * up[:, 1:-1] + up[:, :-2]
        bi[:, 2:-2] = u[:, 4:] - 4 * u[:, 3:-1] + 6 * u[:, 2:-2] \
            - 4 * u[:, 1:-3] + u[:, :-4]
        bi[:, 1] = u[:, 3] - 4 * u[:, 2] + 6 * u[:, 1] \
            - 4 * u[:, 0] - u[:, 1]
        bi[:, -2] = -u[:, -2] - 4 * u[:, -1] + 6 * u[:, -2] \
            - 4 * u[:, -3] + u[:, -4]
        un = (2 * u - B * up + lam2 * lap - mu2 * bi
                + s1c * (lap - lapo)) / A
        un[:, ni] += fdt2 * drive[t]
        un[:, 0] = un[:, -1] = 0.0
        outs[:, t] = (un[:, ro] - u[:, ro]) * SR
        up, u = u, un
    out = outs.sum(axis=0)
    r = int(min(0.05, steps / SR * 0.1) * SR)
    if r > 0:
        out = out.copy()
        out[-r:] *= np.linspace(1, 0, r)
    out = out * amp / (np.max(np.abs(out)) + 1e-12) * 0.9
    return (out, outs) if buses else out
