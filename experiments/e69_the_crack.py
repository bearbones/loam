#!/usr/bin/env python3
"""e69 — the crack and the return.

Brand-new expressive class: a composed BREAK in the bowed
voice. e64 pinned the cliff and noted "hysteresis keeps a
fallen phrase fallen"; e66 met the fundamental-less
multiphonic and built the detector for it. This cycle makes
the failure playable — a designed crack, a measured healing
gesture, and the physics of both:

  - THE CRACK IS PRESSURE WITHOUT SPEED. Dragging the bow to
    vb=0.03 for 0.2 s while the force stays at the ratio
    schedule knocks a certified hold onto the fundamental-less
    multiphonic branch. The control: the same slowdown with FB
    following the ratio rule (force easing with the bow) does
    NOT crack — the trigger is the ratio violation, not the
    slowing.
  - THE BROKEN STATE IS STICKY AND DECEPTIVE. It holds
    healthy rms to the end of the phrase (the voice breaks but
    does not stop), it survives to the last window without a
    gesture (the phrase cannot heal itself), and lock_ratio
    reads it as MORE locked than the true tone (odd-rich
    {5,7}*f0 lines land in the odd set) — fund_presence, now
    promoted to the ruler kit, is the one that tells the truth.
  - THE MUTE IS THE MEDICINE, NOT THE PAUSE. A bare 0.25 s
    lift then shelf re-attack fails: the string still RINGS
    its multiphonic (t60 1.7 s) and the new bow locks onto
    what it hears. The same 0.25 s spent pressing the bow at
    zero speed — friction with vb=0 is a pure damper — kills
    the ring, and the shelf re-attack comes home.

The piece: Sa rises to ga; mid-hold the voice cracks (rms
stays, fundamental gone — a ghost of ga); the bow presses the
string to silence and re-enters on the shelf; ga returns,
falls through Re, home to Sa, lift into the seam.

    python3 experiments/e69_the_crack.py [outdir]
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


LOOP_S = 9.6
L = int(LOOP_S * SR)
tt = np.arange(L) / SR
SA, RE, GA = hz(50), hz(52), hz(53)

# the written line: Sa - ga (crack mid-hold; mute; return) -
# Re - Sa. The crack and the mute are BOW gestures, not notes:
# f0 holds ga straight through the break.
KN = [(0.0, 50), (1.4, 50), (1.8, 53), (4.75, 53), (6.2, 53),
        (6.6, 52), (7.1, 52), (7.4, 50), (9.6, 50)]
f0t = np.interp(tt, [t for t, _ in KN], [hz(m) for _, m in KN])
VBK = [(0.0, 0.085), (0.7, 0.105), (1.8, 0.11), (2.9, 0.11),
        (8.5, 0.085), (9.6, 0.085)]
vbt = np.interp(tt, [t for t, _ in VBK], [v for _, v in VBK])

CRACK_A, CRACK_B = 3.0, 3.2
MUTE_A, MUTE_B = 4.5, 4.75


def take(crack=True, heal="mute", mute_fb=1e3):
    """crack: drag vb to 0.03 with FB held at the ratio
    schedule (pressure without speed). heal: 'mute' presses
    the bow at zero speed then shelf re-attacks; 'gap' lifts
    for the same 0.25 s; 'none' plays on, broken."""
    vb = vbt.copy()
    FB = 1e4 * vbt          # the schedule, frozen BEFORE gestures
    if crack:
        j = (tt >= CRACK_A) & (tt < CRACK_B)
        vb[j] = 0.03
    else:
        # the ratio-kept control: same slowdown, force follows
        j = (tt >= CRACK_A) & (tt < CRACK_B)
        vb[j] = 0.03
        FB = 1e4 * vb
    if heal != "none":
        mu = (tt >= MUTE_A) & (tt < MUTE_B)
        vb[mu] = 0.0
        FB[mu] = mute_fb if heal == "mute" else 0.0
        re = (tt >= MUTE_B) & (tt < 8.5)
        vb[re] = np.minimum(np.interp(tt[re] - MUTE_B,
                [0.0, 0.6, 4.0], [0.085, 0.105, 0.105]), vbt[re])
        FB[re] = 1e4 * vb[re]
    lift = tt >= 8.5
    vb[lift] = 0.0
    FB[lift] = 0.0
    return fdbow(f0t, LOOP_S, FB=FB, vb=vb, sig0=4.0, raw=True)


sar = take()                              # the piece
x_none = take(heal="none")                # hysteresis control
x_gap = take(heal="gap")                  # pause-only control
x_kept = take(crack=False, heal="none")   # ratio-kept control


def win(x, a, b):
    return x[int(a * SR):int(b * SR)]


PRE = (2.1, 2.9)          # ga before the crack
BRK = (3.3, 4.4)          # the broken hold
BACK = (5.6, 6.1)         # ga returned
HOME = (7.7, 8.4)         # Sa home

# ---- 1. the crack is pressure without speed --------------------
fp_pre = ruler.fund_presence(win(sar, *PRE), GA)
fp_brk = ruler.fund_presence(win(sar, *BRK), GA)
fp_kept = ruler.fund_presence(win(x_kept, *BRK), GA)
check("the crack is pressure without speed",
        fp_pre >= 0.06 and fp_brk <= 0.03 and fp_kept >= 0.06,
        f"ga sings at presence {fp_pre:.2f}; drag with force "
        f"held: {fp_brk:.3f} (broken); same drag with force "
        f"following the ratio rule: {fp_kept:.2f} (unharmed) — "
        f"the trigger is the ratio violation, not the slowing")
check("the voice breaks but does not stop",
        rms(win(sar, *BRK)) >= 0.6 * rms(win(sar, *PRE)),
        f"broken-hold rms {rms(win(sar, *BRK)):.3f} vs sung "
        f"{rms(win(sar, *PRE)):.3f} — a ghost of ga, not a "
        f"silence")
lk_brk = ruler.lock_ratio(win(sar, *BRK), GA)
check("the broken state fools the lock detector",
        lk_brk >= 0.5,
        f"lock_ratio reads {lk_brk:.1f} on the fundamental-less "
        f"multiphonic ({{5,7}}*f0 lands in the odd set) — "
        f"fund_presence is the ruler that tells the truth "
        f"(promoted this cycle)")

# ---- 2. hysteresis: the phrase cannot heal itself --------------
fp_none = ruler.fund_presence(win(x_none, *HOME), SA)
fp_home = ruler.fund_presence(win(sar, *HOME), SA)
check("the phrase cannot heal itself",
        fp_none <= 0.05 and fp_home >= 2.5 * fp_none,
        f"no gesture: presence still {fp_none:.3f} at the last "
        f"hold, 4.6 s after the crack; with the gesture "
        f"{fp_home:.3f} — hysteresis keeps a fallen phrase "
        f"fallen (e64), unless the bow intervenes")

# ---- 3. the mute is the medicine, not the pause ----------------
fp_gap_back = ruler.fund_presence(win(x_gap, *BACK), GA)
fp_gap_home = ruler.fund_presence(win(x_gap, *HOME), SA)
fp_back = ruler.fund_presence(win(sar, *BACK), GA)
check("the mute is the medicine, not the pause",
        fp_gap_back <= 0.01 and fp_gap_home <= 0.05
        and fp_back >= 0.3,
        f"a bare 0.25 s gap re-locks onto the ringing "
        f"multiphonic (back at {fp_gap_back:.3f}, home "
        f"{fp_gap_home:.3f}); the same 0.25 s pressing the bow "
        f"at zero speed — friction as a damper — kills the "
        f"ring, and ga returns at {fp_back:.2f}")

# ---- 4. the healed voice passes the certified gates ------------
HOLDS = (("Sa", 0.3, 1.3, SA), ("ga", *PRE, GA),
        ("ga'", *BACK, GA), ("Re", 6.7, 7.05, RE),
        ("Sa'", *HOME, SA))
locks = [ruler.lock_ratio(win(sar, a, b), f)
        for _, a, b, f in HOLDS]
fps = [ruler.fund_presence(win(sar, a, b), f)
        for _, a, b, f in HOLDS]
ts, fsc = ruler.pitch_contour(sar, fmin=80.0, fmax=500.0)
worst_hold = 0.0
for nm, a, b, f in HOLDS:
    sel = (ts >= a) & (ts <= b)
    med = float(np.median(fsc[sel]))
    worst_hold = max(worst_hold, abs(1200 * np.log2(med / f)))
check("every sung hold is certified, before and after",
        min(locks) >= 0.2 and min(fps) >= 0.05
        and worst_hold <= 25.0,
        f"lock >= {min(locks):.2f}, presence >= {min(fps):.2f}, "
        f"worst hold {worst_hold:.1f}c across "
        f"Sa - ga | crack | ga - Re - Sa")
dev_all = []
for a0, b0 in ((0.3, 2.9), (5.6, 8.3)):
    sel = (ts >= a0) & (ts <= b0)
    dline = np.interp(ts[sel], tt, f0t)
    dev_all.extend(np.abs(1200 * np.log2(fsc[sel] / dline)))
check("the sung line follows the written one",
        float(np.median(dev_all)) <= 15.0,
        f"median |dev| {float(np.median(dev_all)):.1f}c over "
        f"the segments where the voice sings")
wrs = np.array([rms(win(sar, a, a + 0.3))
        for a0, b0 in ((0.3, 2.9), (5.0, 8.3))
        for a in np.arange(a0, b0 - 0.3, 0.3)])
check("the voice holds through both lives",
        float(wrs.min() / wrs.max()) >= 0.4,
        f"sung-segment rms min/max "
        f"{float(wrs.min() / wrs.max()):.3f}")
t60r = ruler.decay_t60(sar[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("the lift rings into the seam",
        abs(t60r / 1.725 - 1) <= 0.3,
        f"release t60 {t60r:.2f} s (design 1.73)")

# ---- the mix ---------------------------------------------------
BANK = [50, 52, 53, 55, 57, 59, 60, 62]
BHZ = [hz(n) for n in BANK]
sarn = sar / np.abs(sar).max()
_, tb = fdsym(BHZ, sarn, buses=True, jawari=True, gain=5000.0)
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
        f"taraf/sarangi {halo_db:.1f} dB (the bank keeps "
        f"ringing ga's ghost through the break)")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=69)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(sar_mix, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
# claim shape follows the phrase: ga is the featured note —
# sung, broken, mourned, returned — and earns clear second
cu = ruler.chroma_uniform(mix.mean(axis=1))
order = np.argsort(cu)[::-1]
m01 = cu[order[0]] / cu[order[1]]
m12 = cu[order[1]] / cu[order[2]]
check("Sa leads, the cracked-and-healed ga is second",
        order[:2].tolist() == [2, 5] and m01 >= 1.3
        and m12 >= 1.4,
        f"D {cu[2]:.2f} > F {cu[5]:.2f} (x{m01:.2f}) > rest "
        f"(x{m12:.2f})")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e69_the_crack.wav")
write_wav(wav, out)
ruler.report(out, "the_crack")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)
