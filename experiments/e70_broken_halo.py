#!/usr/bin/env python3
"""e70 — the broken halo: what the bank hears when the voice
cracks.

Refinement cycle marrying e68 (the forecast + compressor law)
and e69 (the crack): when the bowed voice breaks onto its
fundamental-less multiphonic, the drive spectrum is REWRITTEN
— and the sympathetic bank re-lights accordingly. Measured on
e69's certified crack, rebuilt here sample-exact:

  - the crack rewrites the drive: the healthy hold crowns h2;
    the broken hold crowns h3 with h1 and h2 collapsed to
    <= 6% of the crown. (And the flavors vary: e66's slam was
    {2,5,7}, e69's hold {3,5}, this piece's ghost {3,6} — a
    crack is a FAMILY of states, so every take must measure
    its own.)
  - the halo hears it: isolated-drive A/B (same string, sung
    vs broken segment) reshuffles the taraf ledger — crown
    C -> Sa', share gains x12.6 (Sa') and x3.4 (ma) against
    x0.2-0.4 for the fifth-family, rank agreement 0.38.
  - the boundary of the forecast, logged honestly: ma's x3.4
    gain has NO lattice address (no drive line within 25c of
    any ma mode, n,m <= 8), and every coincidence forecast of
    the gain ledger — v2 and v3, tol 15c and 25c — scores
    <= 0.15. The recruiter there is the string's OWN barrier
    contact, invisible to any coincidence model. v2/v3 rank
    strings; they cannot rank what intermodulation builds.
  - THE TREBLE WINDOW: fdbow sizes its grid from the phrase's
    HIGHEST note (stability), so one Sa' in the line coarsens
    the whole take: N 96 -> 58, and e69's certified phrase at
    N=58 loses its heal entirely (ga returns at presence 0.000
    vs 0.69 on the native grid). Recipes are PER-GRID — the
    top note silently retunes the instrument.

The piece: "the ghost duet" — Sa rises through Re to ga; the
voice cracks and stays broken for 2.2 s, a ghost of ga whose
{3,6} lattice lands 2c from komal ni's h2 and h4. The ni
taraf string rises (x1.27 vs the no-crack control), Re's
string starves (x0.58), and the ghost sings enough C into the
mix that ni is the CHROMA'S SECOND CLASS, above the drone's
Pa and the sung ga. Then the mute, and home to Sa.

    python3 experiments/e70_broken_halo.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdbow, fdpluck2, fdsym

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def prof8(seg, f0):
    X = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    fr = np.fft.rfftfreq(len(seg), 1.0 / SR)
    return np.array([float(X[(fr >= n * f0 * 0.95)
            & (fr <= n * f0 * 1.05)].max()) for n in range(1, 9)])


LOOP_S = 9.6
L = int(LOOP_S * SR)
tt = np.arange(L) / SR
SA, RE, GA = hz(50), hz(52), hz(53)
BANK = [50, 52, 53, 55, 57, 59, 60, 62]
BHZ = [hz(n) for n in BANK]


def e69_take(N=0):
    """e69's certified crack piece, sample-exact."""
    KN = [(0.0, 50), (1.4, 50), (1.8, 53), (4.75, 53),
            (6.2, 53), (6.6, 52), (7.1, 52), (7.4, 50),
            (9.6, 50)]
    f0t = np.interp(tt, [t for t, _ in KN],
            [hz(m) for _, m in KN])
    VBK = [(0.0, 0.085), (0.7, 0.105), (1.8, 0.11),
            (2.9, 0.11), (8.5, 0.085), (9.6, 0.085)]
    vbt = np.interp(tt, [t for t, _ in VBK],
            [v for _, v in VBK])
    vb = vbt.copy()
    FB = 1e4 * vbt
    j = (tt >= 3.0) & (tt < 3.2)
    vb[j] = 0.03
    mu = (tt >= 4.5) & (tt < 4.75)
    vb[mu] = 0.0
    FB[mu] = 1e3
    re = (tt >= 4.75) & (tt < 8.5)
    vb[re] = np.minimum(np.interp(tt[re] - 4.75,
            [0.0, 0.6, 4.0], [0.085, 0.105, 0.105]), vbt[re])
    FB[re] = 1e4 * vb[re]
    lift = tt >= 8.5
    vb[lift] = 0.0
    FB[lift] = 0.0
    return fdbow(f0t, LOOP_S, FB=FB, vb=vb, sig0=4.0, raw=True,
            N=N)


sar69 = e69_take()
healthy = sar69[int(2.0 * SR):int(2.9 * SR)]
broken = sar69[int(3.3 * SR):int(4.4 * SR)]

# ---- 1. the crack rewrites the drive ---------------------------
ph = prof8(healthy, GA)
ph /= ph.max()
pb = prof8(broken, GA)
pb /= pb.max()
check("the crack rewrites the drive",
        int(np.argmax(ph)) == 1 and int(np.argmax(pb)) == 2
        and max(pb[0], pb[1]) <= 0.1,
        f"healthy crowns h2 (h1..h4 "
        f"{np.round(ph[:4], 2).tolist()}); broken crowns h3 "
        f"with h1/h2 at {pb[0]:.2f}/{pb[1]:.2f} — a different "
        f"instrument mid-phrase")

# ---- 2. the halo hears the crack -------------------------------
def ledger(seg):
    d = np.zeros(int(4.5 * SR))
    d[:len(seg)] = seg / np.abs(seg).max()
    _, tb_ = fdsym(BHZ, d, buses=True, jawari=True, gain=5000.0)
    return np.sqrt((tb_[:, int(0.2 * SR):] ** 2).mean(axis=1))


mh = ledger(healthy)
mb = ledger(broken)
gain = (mb / mb.sum()) / (mh / mh.sum())
i62, i55 = BANK.index(62), BANK.index(55)
losses = [float(gain[BANK.index(n)]) for n in (57, 59, 60)]
check("the halo hears the crack",
        BANK[int(np.argmax(mh))] == 60
        and BANK[int(np.argmax(mb))] == 62
        and spearman(mh, mb) <= 0.55
        and gain[i62] >= 5.0 and gain[i55] >= 2.0
        and max(losses) <= 0.6,
        f"isolated-drive A/B: crown C -> Sa', rank agreement "
        f"{spearman(mh, mb):.2f}; share gains Sa' x{gain[i62]:.1f}"
        f", ma x{gain[i55]:.1f}; the fifth-family falls to "
        f"{[round(v, 2) for v in losses]}")

# ---- 3. the boundary of the forecast ---------------------------
best_addr = min(abs(1200 * np.log2((n * GA) / (m * hz(55))))
        for n in range(1, 9) for m in range(1, 9))
meas_gain = gain
best_sp = -np.inf
for tol in (15.0, 25.0):
    for extra in ({}, {"comp": (20.0, 0.736, 7.25, 0.10)}):
        pf = {}
        for nm, pw in (("h", ph), ("b", pb)):
            pf[nm] = ruler.sympathy_forecast(np.full(500, GA),
                    2.5 / 500, BHZ, drive_w=pw, integrate=True,
                    node=0.93, tap=0.12, vel=True,
                    tol_cents=tol, **extra)
        pg = (pf["b"] / pf["b"].sum()) \
            / (pf["h"] / pf["h"].sum() + 1e-12)
        best_sp = max(best_sp, spearman(pg, meas_gain))
check("the gain crown has no lattice address",
        best_addr >= 25.0 and best_sp <= 0.3,
        f"ma gains x{gain[i55]:.1f} with its nearest lattice "
        f"line {best_addr:.0f}c away (n,m <= 8); best gain "
        f"forecast (v2/v3, tol 15/25c) spearman {best_sp:.2f} "
        f"— the recruiter is the string's own contact, and a "
        f"coincidence model is blind there. Logged as the "
        f"boundary of v2/v3's domain")

# ---- 4. the treble window --------------------------------------
def grid_N(f0max, kappa=0.3):        # fdbow's own sizing rule
    aa = (2.0 * f0max / SR) ** 2
    bb = (2.0 * kappa / SR) ** 2
    return max(min(int(np.sqrt((-aa + np.sqrt(aa * aa
            + 2.4 * bb)) / (2 * bb))), 180), 24)


N_ga, N_sap = grid_N(GA), grid_N(hz(62))
sar58 = e69_take(N=N_sap)
fp_back_nat = ruler.fund_presence(
        sar69[int(5.6 * SR):int(6.1 * SR)], GA)
fp_back_58 = ruler.fund_presence(
        sar58[int(5.6 * SR):int(6.1 * SR)], GA)
check("the top note silently retunes the instrument",
        N_ga >= 1.5 * N_sap and fp_back_nat >= 0.3
        and fp_back_58 <= 0.01,
        f"one Sa' in a phrase coarsens the whole take's grid "
        f"(N {N_ga} -> {N_sap}), and e69's certified heal dies "
        f"there: ga returns at {fp_back_58:.3f} vs "
        f"{fp_back_nat:.2f} native — recipes are PER-GRID")

# ---- the piece: the ghost duet ---------------------------------
KN = [(0.0, 50), (1.2, 50), (1.6, 52), (2.4, 52), (2.8, 53),
        (6.4, 53), (6.65, 50), (9.6, 50)]
f0t = np.interp(tt, [t for t, _ in KN], [hz(m) for _, m in KN])
VBK = [(0.0, 0.085), (0.7, 0.105), (1.6, 0.11), (3.6, 0.11),
        (8.5, 0.085), (9.6, 0.085)]
vbt = np.interp(tt, [t for t, _ in VBK], [v for _, v in VBK])
CR_A, CR_B, MU_A, MU_B = 4.0, 4.2, 6.4, 6.65


def take(crack=True):
    vb = vbt.copy()
    FB = 1e4 * vbt
    if crack:
        j = (tt >= CR_A) & (tt < CR_B)
        vb[j] = 0.03
    mu = (tt >= MU_A) & (tt < MU_B)
    vb[mu] = 0.0
    FB[mu] = 1e3
    re = (tt >= MU_B) & (tt < 8.5)
    vb[re] = np.minimum(np.interp(tt[re] - MU_B,
            [0.0, 0.6, 4.0], [0.085, 0.105, 0.105]), vbt[re])
    FB[re] = 1e4 * vb[re]
    lift = tt >= 8.5
    vb[lift] = 0.0
    FB[lift] = 0.0
    return fdbow(f0t, LOOP_S, FB=FB, vb=vb, sig0=4.0, raw=True)


sar = take(True)
ctl = take(False)         # same phrase, no crack gesture


def w(x, a, b):
    return x[int(a * SR):int(b * SR)]


HOLDS = (("Sa", 0.3, 1.1, SA), ("Re", 1.9, 2.3, RE),
        ("ga", 3.1, 3.9, GA), ("Sa'", 7.4, 8.4, SA))
locks = [ruler.lock_ratio(w(sar, a, b), f) for _, a, b, f in HOLDS]
fps = [ruler.fund_presence(w(sar, a, b), f)
        for _, a, b, f in HOLDS]
ts, fsc = ruler.pitch_contour(sar, fmin=80.0, fmax=500.0)
worst_hold = 0.0
for nm, a, b, f in HOLDS:
    sel = (ts >= a) & (ts <= b)
    med = float(np.median(fsc[sel]))
    worst_hold = max(worst_hold, abs(1200 * np.log2(med / f)))
check("the voice sings its line around the ghost",
        min(locks) >= 0.2 and min(fps) >= 0.05
        and worst_hold <= 25.0,
        f"lock >= {min(locks):.2f}, presence >= {min(fps):.2f}, "
        f"worst hold {worst_hold:.1f}c across Sa-Re-ga | ghost "
        f"| Sa")
fp_gh = ruler.fund_presence(w(sar, 4.3, 6.3), GA)
fp_ctl = ruler.fund_presence(w(ctl, 4.3, 6.3), GA)
check("the ghost holds for two seconds",
        fp_gh <= 0.03 and fp_ctl >= 0.08
        and rms(w(sar, 4.3, 6.3)) >= 0.55 * rms(w(sar, 3.1, 3.9))
        and ruler.lock_ratio(w(sar, 4.3, 6.3), GA) >= 0.5,
        f"broken presence {fp_gh:.3f} (control sings through at "
        f"{fp_ctl:.2f}), rms {rms(w(sar, 4.3, 6.3)):.3f}, and "
        f"lock_ratio still fooled at "
        f"{ruler.lock_ratio(w(sar, 4.3, 6.3), GA):.1f}")
pg = prof8(w(sar, 4.3, 6.3), GA)
pg /= pg.max()
check("this ghost's flavor is {3,6}",
        int(np.argmax(pg)) == 2 and pg[5] >= 0.5
        and max(pg[0], pg[1]) <= 0.05,
        f"ghost profile crowns h3 with h6 at {pg[5]:.2f} — "
        f"third flavor observed (e66 {{2,5,7}}, e69 {{3,5}}): "
        f"measure your own ghost, always")

# the halo answer, paired against the no-crack control
eg, ec = {}, {}
for nm, x in (("crack", sar), ("ctl", ctl)):
    _, tb_ = fdsym(BHZ, x / np.abs(x).max(), buses=True,
            jawari=True, gain=5000.0)
    e = np.sqrt((tb_[:, int(4.3 * SR):int(6.3 * SR)] ** 2)
            .mean(axis=1))
    (eg if nm == "crack" else ec)["v"] = e
    if nm == "crack":
        tb = tb_
gsh = (eg["v"] / eg["v"].sum()) / (ec["v"] / ec["v"].sum())
i60, i52 = BANK.index(60), BANK.index(52)
addr2 = abs(1200 * np.log2((3 * GA) / (2 * hz(60))))
addr4 = abs(1200 * np.log2((6 * GA) / (4 * hz(60))))
check("the ghost feeds komal ni by address",
        gsh[i60] >= 1.15 and gsh[i52] <= 0.75
        and addr2 <= 5.0 and addr4 <= 5.0,
        f"vs the no-crack control: ni's string gains "
        f"x{gsh[i60]:.2f} (3*ga lands {addr2:.1f}c from its h2, "
        f"6*ga {addr4:.1f}c from its h4) while Re's starves at "
        f"x{gsh[i52]:.2f} — this flavor HAS a lattice address, "
        f"unlike ma's gain in the A/B")
t60r = ruler.decay_t60(sar[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("the lift rings into the seam",
        abs(t60r / 1.725 - 1) <= 0.3,
        f"release t60 {t60r:.2f} s (design 1.73)")
dev_all = []
for a0, b0 in ((0.3, 3.9), (7.3, 8.3)):
    sel = (ts >= a0) & (ts <= b0)
    dline = np.interp(ts[sel], tt, f0t)
    dev_all.extend(np.abs(1200 * np.log2(fsc[sel] / dline)))
check("the sung line follows the written one",
        float(np.median(dev_all)) <= 15.0,
        f"median |dev| {float(np.median(dev_all)):.1f}c where "
        f"the voice sings")
wrs = np.array([rms(w(sar, a, a + 0.3))
        for a0, b0 in ((0.3, 3.9), (7.0, 8.3))
        for a in np.arange(a0, b0 - 0.3, 0.3)])
check("the voice holds through both lives",
        float(wrs.min() / wrs.max()) >= 0.4,
        f"sung-segment rms min/max "
        f"{float(wrs.min() / wrs.max()):.3f}")

# ---- the mix ---------------------------------------------------
HALO_GAIN = 0.05
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b, p in zip(tb, pans):
    gg = (b[:L] / tnorm) * HALO_GAIN
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
sar_mix = sar * 0.85 / (np.abs(sar).max() + 1e-12) * 0.9
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1))
        / rms(sar_mix))
check("the halo sits under the voice",
        -32.0 <= halo_db <= -8.0,
        f"taraf/sarangi {halo_db:.1f} dB")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=70)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(sar_mix, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
# claim shape follows the phrase: the ghost is 2.2 s of {3,6}
# lattice, and BOTH lines land in the C pitch class — the
# broken voice sings komal ni into the chroma
cu = ruler.chroma_uniform(mix.mean(axis=1))
order = np.argsort(cu)[::-1]
check("the broken voice sings ni",
        order[0] == 2 and order[1] == 0
        and cu[2] >= 1.5 * cu[0],
        f"D {cu[2]:.2f} leads; the ghost's C is second at "
        f"{cu[0]:.2f} — above the drone's Pa ({cu[9]:.2f}) and "
        f"the sung ga ({cu[5]:.2f}): the crack composed a note "
        f"the bow never played")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e70_broken_halo.wav")
write_wav(wav, out)
ruler.report(out, "broken_halo")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)
