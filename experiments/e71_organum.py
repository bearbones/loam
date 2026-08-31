#!/usr/bin/env python3
"""e71 — organum: the bass window, and parallel fourths that
beat at the rate the strings choose.

New-idea cycle. Two findings braided into one piece:

THE BASS WINDOW. The certified treble bow (FB = 1e4*vb) is
per-grid (e70), and below the phrase it simply fails: at the
bass grids (midi 45/47/48, N 125-144) it leaves lock_ratio at
0.01-0.02 — the string never speaks. The bass wants a
four-times heavier bow: FB = 4e4*vb at vb ~ 0.10 locks all
three notes (lock 0.7-1.2, fund_presence 0.49-1.00), and the
window has a hard ceiling — k = 5e4 at midi 48 is total
silence (0.00/0.000). Inside the pocket the voice is DARK:
at ni- the fundamental is the strongest line in the spectrum
(fund_presence 1.00, prof8 crowns h1) where the treble voice
crowns h2. A different voice, not a transposed one.

THE BEAT CHAIN, CLOSED. Parallel ET fourths beat where melody
h3 meets bass h4 (~440/494/523 Hz). Score arithmetic promises
|3*hz(hi) - 4*hz(lo)| ~ 0.5 Hz; the strings sound 0.23 Hz on
the low fourth — friction flattening moves the lines, so the
prediction must come from each voice's OWN sounded line.
ruler.partial_freq (born here: parabolic vertex on three log
bins, ~0.01 Hz on 5 s windows, where hps_pitch's 0.5c grain
is ~0.4 Hz of error) closes it: predicted 0.23/0.60/0.63 Hz,
measured 0.23/0.61/0.61. Two ruler lessons pinned as gates:
(1) beat_profile's default min_rate = 0.25 sits ABOVE the slow
fourth's 0.23 Hz beat, so the ruler returns the log-envelope's
2nd harmonic — exactly 2x — and the 1.5 s detrend eats the
depth (3.1 dB shown, 9.0 real). A rate window is a claim about
what you expect; size it to the prediction. (2) A just-
intonation control must be tuned by SOUNDED pitch, not
command: re-commanding the bass so its h4 lands on the
melody's h3 collapses the 52/47 beat 5.4 -> 0.5 dB and shrinks
the line separation to <= 0.07 Hz.

The piece: "organum" — Sa-Re-ga-Re-Sa on the treble bow, and
a second voice in strict parallel fourths below (Pa-Dha-ni-
Dha-Pa) on the heavy bow, ninth-century two-part organum sung
by one instrument's two windows. Every hold sounds its fourth
within 7c of ET, the bass keeps fund_presence 0.84-1.00 in
the mix, and both voices obey the same release law into the
seam (t60 1.72 vs design 1.73).

    python3 experiments/e71_organum.py [outdir]
"""

import os
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


def w(x, a, b):
    return x[int(a * SR):int(b * SR)]


def prof8(seg, f0):
    X = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    fr = np.fft.rfftfreq(len(seg), 1.0 / SR)
    return np.array([float(X[(fr >= n * f0 * 0.95)
            & (fr <= n * f0 * 1.05)].max()) for n in range(1, 9)])


def steady(midi, k, dur, vtop):
    """One held note: shelf attack 0.085 -> vtop over 0.6 s,
    FB = k*vb throughout. First second dropped (settling)."""
    return steady_f(hz(midi), k, dur, vtop)


def steady_f(f0, k, dur, vtop):
    tp = np.arange(int(dur * SR)) / SR
    vbp = np.interp(tp, [0.0, 0.6, dur], [0.085, vtop, vtop])
    return fdbow(f0, dur, FB=k * vbp,
            vb=vbp, sig0=4.0, raw=True)[SR:]


print("== part 1: the bass window ==")

pocket = {}
for m in (45, 47, 48):
    x = steady(m, 4e4, 6.0, 0.10)
    pocket[m] = (ruler.lock_ratio(x, hz(m)),
            ruler.fund_presence(x, hz(m)), x)
lk = {m: v[0] for m, v in pocket.items()}
fp = {m: v[1] for m, v in pocket.items()}
check("the bass has its own bow",
        min(lk.values()) >= 0.6 and min(fp.values()) >= 0.4,
        f"k=4e4 at Pa-/Dha-/ni-: lock "
        f"{lk[45]:.2f}/{lk[47]:.2f}/{lk[48]:.2f}, fund "
        f"{fp[45]:.2f}/{fp[47]:.2f}/{fp[48]:.2f}")

ctl = {m: steady(m, 1e4, 6.0, 0.105) for m in (45, 47)}
clk = {m: ruler.lock_ratio(x, hz(m)) for m, x in ctl.items()}
cfp = {m: ruler.fund_presence(x, hz(m)) for m, x in ctl.items()}
check("the treble bow chokes down here",
        max(clk.values()) <= 0.05 and max(cfp.values()) <= 0.05,
        f"certified k=1e4 recipe at the bass grids: lock "
        f"{clk[45]:.2f}/{clk[47]:.2f}, fund "
        f"{cfp[45]:.3f}/{cfp[47]:.3f} — the window is real")

xcl = steady(48, 5e4, 6.0, 0.10)
check("the window has a ceiling",
        ruler.lock_ratio(xcl, hz(48)) <= 0.05
        and ruler.fund_presence(xcl, hz(48)) <= 0.05,
        f"k=5e4 at ni-: lock {ruler.lock_ratio(xcl, hz(48)):.2f}, "
        f"fund {ruler.fund_presence(xcl, hz(48)):.3f} — silence "
        f"one step past the pocket")

treb50 = steady(50, 1e4, 6.0, 0.105)
pb = prof8(w(pocket[48][2], 0.5, 4.5), hz(48))
pt = prof8(w(treb50, 0.5, 4.5), hz(50))
check("the bass voice is dark",
        int(np.argmax(pb)) == 0 and int(np.argmax(pt)) != 0,
        f"ni- crowns h1 (h1..h4 "
        f"{np.round(pb / pb.max(), 2).tolist()[:4]}); the treble "
        f"voice crowns h{int(np.argmax(pt)) + 1} — a different "
        f"voice, not a transposed one")

devs = {}
for m in (45, 47, 48):
    f4 = ruler.partial_freq(pocket[m][2], 4 * hz(m) * 0.985,
            4 * hz(m) * 1.015)
    devs[m] = 1200 * np.log2(f4 / (4 * hz(m)))
check("the heavy bow holds its pitch",
        max(abs(d) for d in devs.values()) <= 5.0,
        f"sounded dev at h4: {devs[45]:+.1f}/{devs[47]:+.1f}/"
        f"{devs[48]:+.1f}c — flattening under 3c across the "
        f"window")

print("== part 2: the beat chain ==")

DYADS = [
    # (hi, lo, band, dur, trend_s, min_rate, depth_gate)
    (50, 45, (400.0, 480.0), 14.0, 6.0, 0.10, 5.0),
    (52, 47, (450.0, 540.0), 6.0, 1.5, 0.25, 3.0),
    (53, 48, (480.0, 570.0), 6.0, 1.5, 0.25, 5.0),
]
takes = {}
beats = {}
for hi, lo, band, dur, tr, mr, dg in DYADS:
    A = steady(hi, 1e4, dur, 0.105)
    B = steady(lo, 4e4, dur, 0.10)
    f3 = ruler.partial_freq(A, 3 * hz(hi) * 0.985,
            3 * hz(hi) * 1.015)
    f4 = ruler.partial_freq(B, 4 * hz(lo) * 0.985,
            4 * hz(lo) * 1.015)
    pred = abs(f3 - f4)
    mixd = A / np.abs(A).max() + B / np.abs(B).max()
    br, bd = ruler.beat_profile(mixd, band[0], band[1],
            trend_s=tr, min_rate=mr)
    takes[(hi, lo)] = (A, B, f3, f4, mixd, band)
    beats[(hi, lo)] = (pred, br, bd)
    check(f"the {hi}/{lo} fourth beats as its lines say",
            abs(br / pred - 1) <= 0.25 and bd >= dg,
            f"own-bus lines {f3:.2f}/{f4:.2f} Hz predict "
            f"{pred:.2f} Hz; the mix beats at {br:.2f} Hz, "
            f"{bd:.1f} dB deep")

# lesson pinned: the default rate window returns the 2nd
# harmonic of a beat that sits below min_rate
pred0 = beats[(50, 45)][0]
br2, bd2 = ruler.beat_profile(takes[(50, 45)][4], 400.0, 480.0)
check("a rate window is a claim",
        1.6 <= br2 / pred0 <= 2.4,
        f"default min_rate=0.25 on the 0.23 Hz beat reads "
        f"{br2:.2f} Hz ({br2 / pred0:.1f}x) at {bd2:.1f} dB — "
        f"the fundamental sits below the window, so the ruler "
        f"returns the log-envelope's 2nd harmonic and the "
        f"1.5 s detrend eats the depth. Size the window to the "
        f"prediction")

promise = abs(3 * hz(50) - 4 * hz(45))
check("the score arithmetic is wrong",
        promise / pred0 >= 1.7,
        f"|3*hz(Sa) - 4*hz(Pa-)| promises {promise:.2f} Hz; "
        f"the strings sound {pred0:.2f} Hz — friction "
        f"flattening moved the lines. Predict from the sounded "
        f"lines, not the written notes")

# the tuned control: re-command the bass so its h4 lands ON
# the melody's h3 — tuned by SOUNDED pitch, not by 3:4 of the
# command (commanding just intonation fails: the bass's own
# flattening detunes it)
resid = {}
tuned_depth = {}
for hi, lo in ((52, 47), (53, 48)):
    A, B, f3, f4, _, band = takes[(hi, lo)]
    Bt = steady_f(hz(lo) * (f3 / f4), 4e4, 6.0, 0.10)
    f4t = ruler.partial_freq(Bt, 4 * hz(lo) * 0.985,
            4 * hz(lo) * 1.015)
    resid[(hi, lo)] = abs(f3 - f4t)
    mt = A / np.abs(A).max() + Bt / np.abs(Bt).max()
    tuned_depth[(hi, lo)] = ruler.beat_profile(mt, band[0],
            band[1])[1]
check("tuning the sounded pitch stops the beat",
        tuned_depth[(52, 47)] <= 0.4 * beats[(52, 47)][2]
        and max(resid.values()) <= 0.15,
        f"52/47 depth {beats[(52, 47)][2]:.1f} -> "
        f"{tuned_depth[(52, 47)]:.1f} dB; line residuals "
        f"{resid[(52, 47)]:.2f}/{resid[(53, 48)]:.2f} Hz — the "
        f"beat was never mystery, only geometry")

print("== part 3: the piece ==")

LOOP_S = 9.6
L = int(LOOP_S * SR)
tt = np.arange(L) / SR
KN_M = [(0.0, 50), (1.5, 50), (1.9, 52), (3.0, 52),
        (3.4, 53), (5.6, 53), (6.0, 52), (6.9, 52),
        (7.3, 50), (9.6, 50)]
KN_B = [(t, m - 5) for t, m in KN_M]


def voice(KN, k, vtop):
    f0t = np.interp(tt, [t for t, _ in KN],
            [hz(m) for _, m in KN])
    vbt = np.interp(tt, [0.0, 0.6, 8.5, 9.6],
            [0.085, vtop, vtop, 0.085])
    FB = np.where(tt >= 8.5, 0.0, k * vbt)
    return fdbow(f0t, LOOP_S, FB=FB, vb=vbt, sig0=4.0,
            raw=True), f0t


mel, f0m = voice(KN_M, 1e4, 0.105)
bas, _ = voice(KN_B, 4e4, 0.10)
meln = mel / np.abs(mel).max()
basn = bas / np.abs(bas).max()

HOLDS = [("Sa/Pa-", 0.7, 1.4, 50), ("Re/Dha-", 2.2, 2.9, 52),
        ("ga/ni-", 3.9, 5.5, 53), ("Re/Dha-", 6.25, 6.8, 52),
        ("Sa/Pa-", 7.6, 8.4, 50)]
worst_iv = 0.0
worst_dev = 0.0
fps_hold = []
for name, a, b, m in HOLDS:
    pm = ruler.hps_pitch(w(meln, a, b))
    pbv = ruler.hps_pitch(w(basn, a, b))
    worst_dev = max(worst_dev,
            abs(1200 * np.log2(pm / hz(m))),
            abs(1200 * np.log2(pbv / hz(m - 5))))
    worst_iv = max(worst_iv,
            abs(1200 * np.log2(pm / pbv) - 500.0))
    fps_hold.append(ruler.fund_presence(w(basn, a, b),
            hz(m - 5)))
check("every hold sounds its fourth",
        worst_iv <= 10.0 and worst_dev <= 12.0,
        f"five holds, worst interval off ET-500 by "
        f"{worst_iv:.1f}c, worst sung dev {worst_dev:.1f}c — "
        f"strict organum, two windows, one law")
check("the bass sings dark in the mix",
        min(fps_hold) >= 0.6,
        f"fund_presence across holds "
        f"{min(fps_hold):.2f}-{max(fps_hold):.2f} — the "
        f"fundamental stays the crown under the melody")

ts, fsc = ruler.pitch_contour(meln, fmin=80.0, fmax=500.0)
sel = (ts >= 0.3) & (ts <= 8.4)
dline = np.interp(ts[sel], tt, f0m)
med_dev = float(np.median(np.abs(1200
        * np.log2(fsc[sel] / dline))))
check("the melody follows the written line",
        med_dev <= 15.0,
        f"median |dev| {med_dev:.1f}c over the sung span")

t60m = ruler.decay_t60(meln[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
t60b = ruler.decay_t60(basn[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("both voices obey the release law",
        abs(t60m / 1.725 - 1) <= 0.3
        and abs(t60b / 1.725 - 1) <= 0.3,
        f"release t60 mel {t60m:.2f} / bass {t60b:.2f} s "
        f"(design 1.73) — the heavy bow lifts like the light "
        f"one")

# ---- the mix ---------------------------------------------------
BANK = [50, 52, 53, 55, 57, 59, 60, 62]
BHZ = [hz(n) for n in BANK]
sar = meln * 0.55 + basn * 0.50
_, tb = fdsym(BHZ, sar / np.abs(sar).max(), buses=True,
        jawari=True, gain=5000.0)
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
check("the halo sits under the voices",
        -32.0 <= halo_db <= -8.0,
        f"taraf/organum {halo_db:.1f} dB")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=71)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
mel_mix = meln * 0.55 * 0.85 / (np.abs(sar).max() + 1e-12) * 0.9
bas_mix = basn * 0.50 * 0.85 / (np.abs(sar).max() + 1e-12) * 0.9
loop.add(0.0, stereo(mel_mix, 0.2))
loop.add(0.0, stereo(bas_mix, -0.2))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

cu = ruler.chroma_uniform(mix.mean(axis=1))
order = np.argsort(cu)[::-1].tolist()
check("two voices, one tonic",
        order[0] == 2 and cu[2] >= 1.5 * cu[order[1]]
        and set(order[:4]) == {2, 4, 5, 9},
        f"Sa leads ({cu[2]:.2f}, {cu[2] / cu[order[1]]:.1f}x "
        f"the runner-up) and the top four are exactly the sung "
        f"classes plus the organum's root: Re {cu[4]:.2f}, Pa- "
        f"{cu[9]:.2f}, ga {cu[5]:.2f} — the bass voice lifts "
        f"Pa- ABOVE the sung ga without re-keying the mix "
        f"(Dha-/ni-, two short dark holds, stay in the floor "
        f"at {cu[11]:.2f}/{cu[0]:.2f})")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e71_organum.wav")
write_wav(wav, out)
ruler.report(out, "organum")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")
