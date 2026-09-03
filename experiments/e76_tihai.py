#!/usr/bin/env python3
"""e76 — tihai: the countdown that lands on the sam.

Refinement of e75's jhala, landing the long-carried tihai +
gat mukhda thread. The strum engine is unchanged (0.12 s
grid, 80 slots, chikari filling every non-melody slot), but
the last quarter of the loop replaces the gat with a TIHAI:
the mukhda ga-Re-Sa (53-52-50) struck three times at a 7-slot
lag (0.84 s), arithmetic chosen so the third phrase's final
Sa lands EXACTLY on the sam — it IS the gat's own first
stroke of the next loop, struck harder (amp 1.3), with a
written crescendo across the three phrases (1.0/1.1/1.2).
Tihai arithmetic is a seam-lock in disguise: e75 locked rates
to integer bins per loop; a tihai locks a countdown to a
single instant.

Rulers earned:
  - SELF-SIMILARITY AT THE PHRASE LAG: the melody-band
    envelope correlates with itself at exactly 0.84 s inside
    the tihai (r23 0.97) and nowhere else in the loop
    (control max 0.13). ruler.flux_series is now public so
    experiments can slice and correlate the flux directly.
  - THE HANDS DECORRELATE THE FLUX: the 7-slot phrase lag is
    ODD in the 2-slot da/ra alternation — the lag that aligns
    the melody anti-aligns the chikari hands, and the flux
    correlation pays for it (r23 0.64 two-handed vs 0.81 with
    the alternation removed; the melody-band envelope, which
    cannot see the chikari, reads 0.97 either way). A control
    bus turns the mechanism from a guess into a measurement.
  - Drone strikes moved out of the tihai's windows (single
    strike per loop, early): a foreign attack inside a
    correlation window is a confound, designed away.

    python3 experiments/e76_tihai.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck2, fdsym

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


LOOP_S = 9.6
L = int(LOOP_S * SR)
DT = 0.12
NSLOT = 80
R_STROKE = 1.0 / DT
R_GROUP = 1.0 / (4 * DT)
LAG_S = 7 * DT                  # the phrase lag: 0.84 s
WIN_S = 0.78                    # correlation window (< lag)

LINE = [50, 52, 53, 55, 53, 52, 50, 48, 47, 48, 50, 52,
        53, 52, 50, 48]        # gat holds slots 0..60 now
CH_DA = (hz(62) * 2 ** (0.8 / 1200), 0.9, 0.38, 0.24)
CH_RA = (hz(62) * 2 ** (-3.2 / 1200), 0.9, 0.33, 0.33)

# the tihai: ga-Re-Sa at slot offsets 0,2,4; phrase starts at
# slots 62/69/76 so the third phrase's Sa falls on slot 80 ==
# slot 0 — the sam, which is the gat's own first stroke
T1, T2, T3 = 62, 69, 76
TIHAI = {}
for i, s0 in enumerate((T1, T2, T3)):
    g = 1.0 + 0.1 * i           # written crescendo
    for off, m in ((0, 53), (2, 52)):
        TIHAI[s0 + off] = (m, g)
    if s0 + 4 < NSLOT:          # phrase 3's Sa IS the sam
        TIHAI[s0 + 4] = (50, g)
MEL = {4 * i: (LINE[i], 1.3 if i == 0 else 1.0)
       for i in range(16)}
MEL.update(TIHAI)


def add_wrap(buf, at, v):
    idx = (int(at * SR) + np.arange(len(v))) % len(buf)
    np.add.at(buf, idx, v)


print("== the strum, with a countdown ==")

cache = {}
mel = np.zeros(L)
for s, (m, g) in MEL.items():
    if m not in cache:
        cache[m] = fdpluck2(hz(m), 1.2, amp=1.0, pick=0.28)
    add_wrap(mel, s * DT, g * cache[m])
da = fdpluck2(*CH_DA[:2], amp=CH_DA[2], pick=CH_DA[3])
ra = fdpluck2(*CH_RA[:2], amp=CH_RA[2], pick=CH_RA[3])


def chik_bus(alternate):
    buf = np.zeros(L)
    for s in range(NSLOT):
        if s in MEL:
            continue
        add_wrap(buf, s * DT,
                da if (s % 2 or not alternate) else ra)
    return buf


chik = chik_bus(True)
meln = mel / np.abs(mel).max()
chikn = chik / np.abs(chik).max()
chik1n = chik_bus(False)
chik1n /= np.abs(chik1n).max()

for nm, slots, wl, ww in (("gat", [4 * i for i in range(16)],
        5.0, 10.0), ("tihai", sorted(TIHAI), 5.0, 8.0)):
    errs = []
    for s in slots:
        m = MEL[s][0]
        idx = np.arange(int((s * DT + 0.02) * SR),
                int((s * DT + 0.42) * SR)) % L
        f = ruler.partial_freq(meln[idx], hz(m) * 0.96,
                hz(m) * 1.04)
        errs.append(abs(1200 * np.log2(f / hz(m))))
    check(f"the {nm} is played",
            float(np.median(errs)) <= wl and max(errs) <= ww,
            f"{len(slots)} fundamentals read back at median "
            f"{np.median(errs):.1f}c, worst {max(errs):.1f}c")

sar = 0.55 * meln + 0.35 * chikn
sar1 = 0.55 * meln + 0.35 * chik1n

print("== the countdown ==")

# phrase starts read from the mukhda's first note (ga, 174.6
# Hz — a band the chikari and the other tihai notes miss)
genv = ruler.band_env(np.concatenate([sar,
        sar[:int(2.5 * SR)]]), 171.0, 179.0, 0.01)
starts = []
for s0 in (T1, T2, T3):
    a = int((s0 * DT - 0.06) / 0.01)
    i = a + int(np.argmax(genv[a:a + 16]))
    starts.append((i * 0.01, float(genv[i])))
d12 = starts[1][0] - starts[0][0]
d23 = starts[2][0] - starts[1][0]
check("three phrases, one lag",
        abs(d12 - LAG_S) <= 0.025 and abs(d23 - LAG_S) <= 0.025,
        f"ga-band attacks at {starts[0][0]:.2f}/"
        f"{starts[1][0]:.2f}/{starts[2][0]:.2f} s — spacings "
        f"{d12:.3f}/{d23:.3f} vs the written 0.840; the third "
        f"phrase's Sa lands at slot 80 = the sam by the tihai "
        f"arithmetic 62 + 2x7 + 4 = 80")
check("the countdown grows",
        starts[1][1] / starts[0][1] >= 1.03
        and starts[2][1] / starts[1][1] >= 1.03,
        f"phrase attack levels rise x"
        f"{starts[1][1] / starts[0][1]:.2f} then x"
        f"{starts[2][1] / starts[1][1]:.2f} — the written "
        f"1.0/1.1/1.2 crescendo reads back")

menv0 = ruler.band_env(sar, 100.0, 210.0, 0.01)
nn = len(menv0)


def pk(t):
    idx = np.arange(int((t + 0.005) / 0.01),
            int((t + 0.10) / 0.01)) % nn
    return float(menv0[idx].max())


gpk = float(np.median([pk(4 * i * DT) for i in range(1, 16)]))
check("the sam is struck harder",
        pk(0.0) >= 1.05 * gpk,
        f"melody-band peak at the sam {pk(0.0) / gpk:.2f}x the "
        f"median gat stroke — the amp-1.3 arrival survives the "
        f"ringing tails, compressed from its written 1.3")


def env_corr(env, t0, dt):
    a = int(round(t0 / dt))
    lg = int(round(LAG_S / dt))
    w2 = int(round(WIN_S / dt))
    u = env[a:a + w2] - env[a:a + w2].mean()
    v = env[a + lg:a + lg + w2] - env[a + lg:a + lg + w2].mean()
    return float(np.dot(u, v) / (np.linalg.norm(u)
            * np.linalg.norm(v) + 1e-12))


def selfsim(x, band=None):
    xx = np.concatenate([x, x[:int(2.5 * SR)]])
    if band is None:
        env, dt = ruler.flux_series(xx)
    else:
        env, dt = ruler.band_env(xx, *band, 0.01), 0.01
    r12 = env_corr(env, T1 * DT - 0.03, dt)
    r23 = env_corr(env, T2 * DT - 0.03, dt)
    ctrl = max(env_corr(env, t0, dt)
            for t0 in np.arange(0.5, 6.2, 0.35))
    return r12, r23, ctrl


mr12, mr23, mctrl = selfsim(sar, band=(100.0, 210.0))
check("the phrase echoes at its lag and nowhere else",
        mr23 >= 0.90 and mr12 >= 0.40 and mctrl <= 0.35,
        f"melody-band envelope self-correlation at the 0.84 s "
        f"lag: r23 {mr23:.2f}, r12 {mr12:.2f} (phrase 1's "
        f"window still carries the gat's last stroke ringing "
        f"in-band), control max over the gat {mctrl:.2f}")

fr12, fr23, fctrl = selfsim(sar)
f112, f123, _ = selfsim(sar1)
check("the hands decorrelate the flux",
        f123 >= fr23 + 0.10 and f112 >= fr12 + 0.05
        and mr23 >= fr23 + 0.20 and fctrl <= 0.45,
        f"the 7-slot lag is ODD in the 2-slot da/ra "
        f"alternation, so the lag that aligns the melody "
        f"anti-aligns the hands: flux r23 {fr23:.2f} two-"
        f"handed vs {f123:.2f} single-stroke (r12 {fr12:.2f} "
        f"vs {f112:.2f}); the melody-band envelope cannot see "
        f"the chikari and reads {mr23:.2f} regardless")

print("== the strum still hums ==")

menv = ruler.band_env(sar, 100.0, 210.0, 0.01)
acc_m = [menv[int((s * DT + 0.03) / 0.01)] for s in MEL]
acc_c = [menv[int((s * DT + 0.03) / 0.01)]
        for s in range(NSLOT) if s not in MEL]
acc = float(np.median(acc_m) / np.median(acc_c))
check("the melody carries the accent",
        acc >= 1.4,
        f"melody-band accent ratio {acc:.2f} at melody slots "
        f"vs chikari slots")


def env_crown(x, lo, hi):
    ev = ruler.band_env(x, lo, hi, 0.05)[:192]
    le = np.log(ev + 1e-12)
    k = 41
    pad = np.concatenate([le[:k][::-1], le, le[-k:][::-1]])
    tr = np.convolve(pad, np.ones(k) / k, "same")[k:-k]
    sp = np.abs(np.fft.rfft((le - tr) * np.hanning(len(le))))
    return int(np.argmax(sp[8:80])) + 8


cr = env_crown(sar, 100.0, 210.0)
check("the gat cycle still crowns",
        cr == 20,
        f"melody-band envelope spectrum crowns at bin {cr} — "
        f"replacing the last four gat strokes with eight tihai "
        f"strokes does not dethrone the 20-cycle")


def flux_lines(x):
    fr, sp = ruler.flux_spectrum(x)
    m = (fr > 1.2) & (fr < 20.0)
    crown_f = fr[m][int(np.argmax(sp[m]))]
    crown_v = sp[m].max()
    out = {}
    for nm, lo, hi in (("group", 1.7, 2.5),
            ("stroke", 7.5, 9.2)):
        b = (fr >= lo) & (fr <= hi)
        i = int(np.argmax(sp[b]))
        out[nm] = (float(fr[b][i]), float(sp[b][i] / crown_v))
    return crown_f, out


crown_f, fx = flux_lines(sar)
check("the flux hums through the countdown",
        abs(crown_f / R_GROUP - 1) <= 0.015
        and abs(fx["stroke"][0] / R_STROKE - 1) <= 0.01
        and fx["stroke"][1] >= 0.5,
        f"flux crowns at {crown_f:.2f} Hz (group) with the "
        f"stroke line at {fx['stroke'][0]:.2f} Hz at "
        f"{fx['stroke'][1]:.2f}x crown — all 80 slots stay "
        f"struck; the tihai reassigns hands, not the clock")

cuc = ruler.chroma_uniform(chik)
runner = max(v for i, v in enumerate(cuc) if i != 2)
check("the chikari is one pitch",
        cuc[2] >= 2.5 * runner,
        f"chikari bus chroma class 2 at {cuc[2]:.2f} vs "
        f"runner-up {runner:.2f}")

# ---- the mix ---------------------------------------------------
_, tb = fdsym([hz(n) for n in [50, 52, 53, 55, 57, 59, 60, 62]],
        sar / np.abs(sar).max(), buses=True, jawari=True,
        gain=5000.0)
pans = np.linspace(-0.55, 0.55, 8)
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b_, p in zip(tb, pans):
    gg = (b_[:L] / tnorm) * 0.05
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
norm = np.abs(sar).max() + 1e-12
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1))
        / rms(sar * 0.85 / norm * 0.9))
check("the halo sits under the strum",
        -32.0 <= halo_db <= -8.0,
        f"taraf/strum {halo_db:.1f} dB")

# drone struck ONCE per loop, early and grid-aligned — a
# foreign attack inside a correlation window is a confound,
# so the tihai's windows (7.4-9.6 s and the sam) stay clean
DRONE = [("sa+", hz(50.015), 112, 0.96, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.16, -0.15, 0.50),
        ("SA", hz(38), 138, 3.36, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=76)
for name, f0d, n, at, pan, ampd in DRONE:
    loop.add(at, stereo(fdpluck2(f0d, 12.0, amp=ampd, N=n),
            pan))
loop.add(0.0, stereo(meln * 0.55 * 0.85 / norm * 0.9, 0.15))
loop.add(0.0, stereo(chikn * 0.35 * 0.85 / norm * 0.9, -0.35))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)
mono = mix.mean(axis=1)

xr12, xr23, xctrl = selfsim(mono, band=(100.0, 210.0))
check("the listener hears the countdown",
        xr23 >= 0.80 and xctrl <= 0.45,
        f"mastered mix melody-band self-correlation at the "
        f"phrase lag: r23 {xr23:.2f} (r12 {xr12:.2f}), control "
        f"max {xctrl:.2f} — the tihai survives drone, halo and "
        f"master")

mcrown_f, mfx = flux_lines(mono)
check("the mastered flux still hums",
        abs(mfx["stroke"][0] / R_STROKE - 1) <= 0.01
        and mfx["stroke"][1] >= 0.25
        and abs(mcrown_f / R_GROUP - 1) <= 0.015,
        f"mastered mix: flux crown {mcrown_f:.2f} Hz, stroke "
        f"line {mfx['stroke'][0]:.2f} Hz at "
        f"{mfx['stroke'][1]:.2f}x crown")
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

cu = ruler.chroma_uniform(mono)
check("Sa crowns the mix",
        int(np.argmax(cu)) == 2,
        f"chroma crowns class 2 at {max(cu):.2f}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e76_tihai.wav")
write_wav(wav, out)
ruler.report(out, "tihai")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")
