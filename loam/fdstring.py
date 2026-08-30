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
    comparison."""
    dt = 1.0 / SR
    c = 2.0 * f0                       # L = 1, so c = 2 L f0
    if N <= 0:
        # largest stable grid with margin: a N^2 + b N^4 <= 0.6
        a = (2.0 * f0 / SR) ** 2
        b = (2.0 * kappa / SR) ** 2
        N = int(np.sqrt((-a + np.sqrt(a * a + 2.4 * b)) / (2 * b)))
        N = max(min(N, 180), 24)
    dx = 1.0 / N
    lam2 = (c * dt / dx) ** 2
    mu2 = (kappa * dt / dx ** 2) ** 2
    assert lam2 + 4 * mu2 <= 1.0, "unstable grid: shrink N or kappa"

    x = np.linspace(0.0, 1.0, N + 1)
    u = np.where(x < pick, x / pick, (1 - x) / (1 - pick)) * pluck_m
    u[0] = u[-1] = 0.0
    up = u.copy()
    steps = int(dur * SR)
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
        un = (2 * u - B * up + lam2 * lap - mu2 * bi
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
