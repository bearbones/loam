"""Finite-difference circular membrane with syahi loading.

The 2D member of the FD family (fdstring is the 1D): an explicit
scheme for the lossy membrane

    rho(x,y) u_tt = c^2 lap(u) + 2 sig1 lap(u_t) - 2 sig0 rho u_t

on a cartesian grid masked to a disc (Dirichlet boundary via the
mask), stable while lam = c dt/dx <= 1/sqrt(2) at rho=1 (loading
only slows the wave, so the uniform bound governs).

Why a DISC and why LOADING: a uniform circular membrane's modes
sit at Bessel ratios (1 : 1.593 : 2.136 : 2.296 ...) — between
the teeth of any harmonic comb, which is why a bare drum has no
pitch. The tabla's syahi (a mass-loaded center patch, rho rising
smoothly toward the middle) warps the mode shapes until their
frequencies cluster near integer multiples of the fundamental
(Raman). Both facts are measurable on this lattice and e55
measures them: the uniform drum is the control that proves the
lattice IS a membrane, the loaded drum is the claim.

The strike is an initial VELOCITY bump (a mallet imparts
momentum, not displacement); the model is linear, so strike
amplitude is pure level — position and width are the voicing.
"""

import numpy as np

from . import SR


def fddrum(f1: float, dur: float, amp: float = 1.0,
        strike=(0.55, 0.0), width: float = 0.18,
        load: float = 0.0, rs: float = 0.45,
        sig0: float = 6.0, sig1: float = 2e-4, sig_s: float = 0.0,
        N: int = 45, read=(0.35, 0.28),
        readout: str = "disp") -> np.ndarray:
    """One struck drum. f1 = the UNIFORM membrane's fundamental
    (2.405 c / 2 pi R); loading lowers every mode, so a loaded
    drum's sounding pitch is a measured quantity, not this
    parameter. strike/read are (x, y) in the unit disc; width is
    the mallet bump radius. load = syahi peak density above 1,
    rs = syahi radius: rho = 1 + load * max(0, 1-(r/rs)^2).
    sig0 sets ring (t60 ~ 6.9/sig0); sig1 damps highs first —
    but NOT inside the syahi, where /rho shrinks the damping
    term along with the stiffness: the loaded region's high
    cluster is nearly sig1-immune (measured, e55).

    sig_s adds damping INSIDE the syahi, scaled by the local
    loading fraction — the paste is lossy (gum + iron filings),
    not just heavy. Without it the heavy plug is a nearly
    decoupled resonator with its own slow internal mode BELOW
    the drum's fundamental (measured e55: -1 dB re: the
    fundamental, ringing for seconds — it flooded a bass-band
    measurement three rulers in a row before the mode itself
    was found).

    readout="disp" (default) reads displacement, not velocity.
    A drum starts at rest, so there is no DC-step/click problem
    (the reason fdstring reads velocity) — and velocity weighs
    mode k by k in amplitude, k^2 in power: the na's 7th-
    harmonic syahi cluster (komal Ni!) outshouted the comb x49
    and flipped the piece's chroma pole to C. readout="vel"
    keeps the bright variant as a voicing.
    ~N^2 node updates per sample — N=45 runs ~4x realtime."""
    dt = 1.0 / SR
    steps = int(dur * SR)
    dx = 2.0 / N
    c = 2.0 * np.pi * f1 / 2.405
    lam2 = (c * dt / dx) ** 2
    assert lam2 <= 0.5, "unstable grid: raise N or lower f1"
    ax = np.linspace(-1.0, 1.0, N + 1)
    X, Y = np.meshgrid(ax, ax, indexing="ij")
    r = np.sqrt(X ** 2 + Y ** 2)
    mask = (r < 1.0 - dx / 2).astype(float)
    prof = np.maximum(0.0, 1.0 - (r / rs) ** 2)
    rho = 1.0 + load * prof
    s0 = sig0 + sig_s * prof
    A = 1.0 + s0 * dt
    B = 1.0 - s0 * dt
    s1c = 2.0 * sig1 * dt / dx ** 2

    d = np.sqrt((X - strike[0]) ** 2 + (Y - strike[1]) ** 2)
    bump = np.where(d < width,
            0.5 * (1.0 + np.cos(np.pi * d / width)), 0.0) * mask
    u = np.zeros((N + 1, N + 1))
    up = -dt * bump                    # velocity strike
    ri = (int((read[0] + 1.0) / dx), int((read[1] + 1.0) / dx))
    out = np.empty(steps)
    lap = np.zeros_like(u)
    lapo = np.zeros_like(u)
    for t in range(steps):
        lap[1:-1, 1:-1] = (u[2:, 1:-1] + u[:-2, 1:-1]
                + u[1:-1, 2:] + u[1:-1, :-2] - 4 * u[1:-1, 1:-1])
        lapo[1:-1, 1:-1] = (up[2:, 1:-1] + up[:-2, 1:-1]
                + up[1:-1, 2:] + up[1:-1, :-2]
                - 4 * up[1:-1, 1:-1])
        un = (2 * u - B * up
                + (lam2 * lap + s1c * (lap - lapo)) / rho) / A
        un *= mask
        out[t] = un[ri] if readout == "disp" \
            else (un[ri] - u[ri]) * SR
        up, u = u, un
    fd = int(min(0.05, dur * 0.1) * SR)
    if fd > 0:
        out[-fd:] *= np.linspace(1, 0, fd)
    return out * amp / (np.max(np.abs(out)) + 1e-12) * 0.9
