#!/usr/bin/env python3
"""loam — "The Chamber". A machine that plays, and knows it.

Stage 4+5 of docs/chamber-spec.md. A through-composed 80 s piece for
a designed instrument — the first loam piece written for a MACHINE
rather than a room, and the first that remembers what it played:
every note is asked of the playability solver before it is written,
every event exports with its arm and its motion plan, every string
carries the shape clip the engine will draw. Not a loop; a Take.

The machine:
  harp    16 steel strings, D dorian from D3, three pick arms with
          overlapping reach (0-7, 4-11, 8-15). Pan follows geometry.
  rake    a 5-string bronze cluster (D A D F A), one raking bar —
          a chord is ONE event, a roll across the strings at onsets
          that follow the comb's path (0.541 s first to last; it was
          18 ms a string until PLAYERS M2, A13).
  bars    8 rosewood bars (D4-D5), two mallets.
  chamber the resonator: sympathetic() driven by harp+rake, printed
          to its own stem. No events — a bus that hums when the
          machine plays; the engine can show the chamber breathing.

Form, 84 BPM, 28 bars:
  unfold   0-8   arms wake one at a time over the chamber's hum
  pulse    8-16  euclid bass (3,8) under a dorian line (5,8); rakes
  rake+bars 16-24 mallets take the tune; rakes on 1 and 3
  coda     24-28 thinning; three arms strike D3 D4 D5 together;
                 the chamber rings out through a 6 s tail

Stems dry; the master alone through ir_room + convolve_tail, then
the lowpass/tanh/ceil chain. Exports render/chamber/{score.json,
stems/*.wav, shapes.f32, chamber.wav, track.png}.

    python3 songs/chamber.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Take, write_wav
from loam import ruler
from loam import motion_timing
from loam.score import Score, Instrument, Mechanism
from loam.rhythm import euclid, rotate, scale_notes
from loam.strings import sympathetic
from loam.space import ir_room, convolve_tail
from loam.fdstring import shape_library

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
ex = os.path.join(outdir, "chamber")
os.makedirs(ex, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


BPM = 84.0
SPB = 60.0 / BPM
BARS = 28
DUR = BARS * 4 * SPB                    # 80.0 s
TAIL = 6.0
SEED = 0xC4A
STEM_GAIN = 0.6722237195687149          # the stems' pinned gain (A17, at the export)


def beat(bar: float, b: float = 0.0) -> float:
    return (bar * 4.0 + b) * SPB


# ---- the machine ---------------------------------------------------------------
HARP_MIDIS = scale_notes(50, "dorian", 3)[:16]      # D3 .. E5
RAKE_MIDIS = [50, 57, 62, 65, 69]                   # D3 A3 D4 F4 A4
BAR_MIDIS = scale_notes(62, "dorian", 2)[:8]        # D4 .. D5

# An arm is 0.24 m wide across its pin axis in the model (formlab.linkage
# double parallelogram, world = 3 x score units): two arms of one
# mechanism keep 0.27 m = 0.09 score units apart at every moment.
ARM_CLEARANCE = 0.09
harp = Mechanism.build("harp", "plucked", "steel", HARP_MIDIS,
        arms=3, overlap=4, span=1.6, pos=[0.0, 0.0, 0.0],
        approach_s=0.09, recover_s=0.05, travel_s=0.02,
        pick_default=0.18, restrike_s=0.06)
# The neck fan: one scale degree per equal step, as a real harp is strung
# (the neck's curve comes from the lengths), gathered into the triangular
# frame — feet climb the diagonal soundboard from world y 0.66 to 2.30.
# Equal steps also give the three arms room: 0.109 m per string in the
# world against 0.27 m of arm, so neighbours sit three strings apart.
harp.fan(width=0.34, power=1.0, by="index", smooth=2,
        rise=((0.66 - 2.05) / 3, (0.66 + 1.64 - 2.05) / 3))
harp.arm_clearance = ARM_CLEARANCE
rake = Mechanism.build("rake", "raked", "bronze", RAKE_MIDIS,
        arms=1, span=0.5, pos=[-1.4, 0.2, 0.3], arm_kind="rake",
        approach_s=0.15, recover_s=0.10, travel_s=0.0,
        pick_default=0.28, restrike_s=0.10)
rake.fan(width=0.70, power=1.0, rise=((0.66 - 2.65) / 3, (0.66 + 1.36 - 2.65) / 3))
bars = Mechanism.build("bars", "struck", "rosewood", BAR_MIDIS,
        arms=2, overlap=2, span=0.9, pos=[1.5, -0.1, 0.4],
        arm_kind="mallet", approach_s=0.08, recover_s=0.04,
        travel_s=0.025, restrike_s=0.05, length_max=0.35)
bars.arm_clearance = ARM_CLEARANCE
inst = Instrument("the chamber", [harp, rake, bars])

take = Take(DUR, SEED, tail_s=TAIL)
sc = Score(take, "The Chamber", bpm=BPM, seed=SEED, instrument=inst)
sc.cue(0.0, "tempo", bpm=BPM, bars=BARS)

H = [f"harp{i:02d}" for i in range(16)]
R = [f"rake{i:02d}" for i in range(5)]
B = [f"bars{i:02d}" for i in range(8)]
rng = np.random.default_rng(SEED)
dropped = []
intended = [0]
# The composer's ledger (docs/goals/the-players.md, ruler 25): what was asked,
# what was played as written, what was played on an alternative string, and
# what was dropped. Exported in score.json's stats.
as_written = [0]
substituted = []


def ask_pluck(mech, t, sid, amp, voice, alt=None, **kw):
    """Write by asking. If refused, try the alternative string
    (a neighbour in the scale); if that is refused too, drop and
    remember."""
    intended[0] += 1
    if sc.can_play(mech, t, sid) is not None:
        as_written[0] += 1
        return sc.pluck(mech, t, sid, amp=amp, voice=voice, **kw)
    if alt is not None and sc.can_play(mech, t, alt) is not None:
        substituted.append((mech, t, sid, alt))
        return sc.pluck(mech, t, alt, amp=amp, voice=voice, **kw)
    dropped.append((mech, t, sid))
    return None


def ask_rake(t, up=True, amp=0.8, voice="rake"):
    """A roll, written by asking. Its onsets follow the comb's path
    (motion_timing.rake_onsets: RAKE_ROLL_S first to last, slow off the
    outer strings); spread_s is the roll's end over the four gaps, T/4,
    which is all the planner needs (its t_last is t + 4 spread_s)."""
    ids = R if up else R[::-1]
    on = motion_timing.rake_onsets(up)
    spread = on[-1] / (len(ids) - 1)
    intended[0] += 1
    if sc.can_play("rake", t, strings=ids, spread_s=spread) is None:
        dropped.append(("rake", t, "sweep"))
        return None
    as_written[0] += 1
    return sc.rake("rake", t, ids, amp=amp, spread_s=spread, onsets=on,
            voice=voice, dur=2.6)


def pick_for(amp: float) -> float:
    """Harder plucks land nearer the bridge (brighter): the arm's
    contact point IS the Jaffe-Smith comb position."""
    return float(np.clip(0.26 - 0.12 * amp, 0.10, 0.30))


# ---- unfold: bars 0-8 -------------------------------------------------------------
sc.cue(beat(0), "section", name="unfold")
sc.cue(beat(0), "camera", name="wide-dark")
for bar in range(0, 8):
    # arm0: the low ground, D on 1, A on 3
    ask_pluck("harp", beat(bar, 0), H[0], 0.9, "ground", pick=0.14)
    ask_pluck("harp", beat(bar, 2), H[4], 0.7, "ground", pick=0.18)
    if bar >= 4:                        # arm2: a rising run into the bar
        # asked BEFORE the answer on beat 3: the composer asks for the
        # most constrained voice first (only arm2 reaches the run)
        for k, si in enumerate([12, 13, 14, 15]):
            ask_pluck("harp", beat(bar, 3.0 + 0.25 * k), H[si],
                    0.45 + 0.08 * k, "run", alt=H[min(si + 1, 15)],
                    pick=0.22)
    if bar >= 2:                        # arm1 answers, mid register
        a = 0.6 + 0.1 * (bar % 2)
        # the neighbour BELOW when arm1 cannot reach H[7]: H[8] is as good
        # an answer, but it parks arm1 where the beat-3 answer wants to
        # land, and two arms 0.27 m wide cannot stand a string apart
        ask_pluck("harp", beat(bar, 1), H[7], a, "answer", alt=H[6],
                pick=pick_for(a))
        ask_pluck("harp", beat(bar, 3), H[9 if bar % 2 else 11], a,
                "answer", alt=H[10], pick=pick_for(a))
sc.cue(beat(2), "camera", name="arm0-close")
sc.cue(beat(4), "camera", name="arm2-run")
ask_rake(beat(7, 2), up=True, amp=0.9)           # the announcement

# ---- pulse: bars 8-16 ---------------------------------------------------------------
sc.cue(beat(8), "section", name="pulse")
sc.cue(beat(8), "camera", name="overhead")
bass_pat = euclid(3, 8)                          # x..x..x.
mel_pat = rotate(euclid(5, 8), 1)                # dorian line, offset
bass_seq = [0, 2, 4]
motif = [7, 9, 11, 9, 12, 11, 9, 7, 8, 11, 13, 11]
mi = bi = 0
for bar in range(8, 16):
    for step in range(8):
        t = beat(bar, step * 0.5)
        if bass_pat[step]:
            si = bass_seq[bi % 3] + (3 if bar % 4 == 3 else 0)
            ask_pluck("harp", t, H[si], 0.85, "bass", alt=H[si + 1],
                    pick=0.13)
            bi += 1
        if mel_pat[step]:
            si = motif[mi % len(motif)]
            a = 0.55 + 0.2 * (step == 0) + 0.1 * rng.random()
            ask_pluck("harp", t, H[si], a, "line", alt=H[si - 1],
                    pick=pick_for(a))
            mi += 1
    if bar in (12, 14):
        ask_rake(beat(bar), up=bar == 12, amp=0.85)
sc.cue(beat(12), "camera", name="rake-close")

# ---- rake and bars: bars 16-24 ---------------------------------------------------------
sc.cue(beat(16), "section", name="rake+bars")
sc.cue(beat(16), "camera", name="bars-close")
tune = [0, 2, 4, 5, 4, 2, 0, 3]
thin = rotate(euclid(3, 8), 2)
for bar in range(16, 24):
    for step in range(8):
        t = beat(bar, step * 0.5)
        if bass_pat[step]:
            si = bass_seq[(step // 3) % 3]
            ask_pluck("harp", t, H[si], 0.8, "bass", alt=H[si + 1],
                    pick=0.13)
        if thin[step] and bar % 2 == 0:
            si = 9 + (step * 2) % 5
            ask_pluck("harp", t, H[si], 0.5, "line", alt=H[si + 1],
                    pick=0.2)
        bi_ = tune[step] + (1 if bar % 4 == 2 else 0)
        bi_ = min(bi_, 7)
        if bar % 4 != 3:                 # the fourth bar belongs to the run
            ask_pluck("bars", t, B[bi_], 0.6 + 0.25 * (step % 4 == 0),
                    "mallets", alt=B[max(bi_ - 1, 0)])
    if bar % 4 == 3:
        # A run up the whole marimba, an eighth a bar. It was sixteenths
        # over two beats until the planner started charging what the
        # motion costs: these bars sit 0.386 m apart in the world and a
        # mallet arm crosses that in ratchet clicks, so a sixteenth at
        # this tempo asked the carriage for 6.5 m/s and the machine said
        # no (loam/motion_timing.py). Eighths cross it in three or four
        # clicks and the sweep reads as one long gesture instead.
        for k in range(8):
            ask_pluck("bars", beat(bar, 0.5 * k), B[k],
                    0.5 + 0.05 * k, "run", alt=B[min(k + 1, 7)])
    ask_rake(beat(bar, 0), up=True, amp=0.75)
    ask_rake(beat(bar, 2), up=False, amp=0.65)
sc.cue(beat(20), "camera", name="wide-lit")

# ---- coda: bars 24-28 ------------------------------------------------------------------
sc.cue(beat(24), "section", name="coda")
sc.cue(beat(24), "camera", name="pullback")
ask_rake(beat(24), up=False, amp=0.8)
ask_pluck("harp", beat(24), H[0], 0.9, "ground", pick=0.14)
for bar, (b0, b1) in zip((25, 26), ((0, 4), (7, 3))):
    ask_pluck("bars", beat(bar, 0), B[b0], 0.7, "mallets")
    ask_pluck("bars", beat(bar, 2), B[b1], 0.55, "mallets")
    ask_pluck("harp", beat(bar, 1), H[14 - (bar - 25) * 2], 0.5, "answer",
            pick=0.22)
ask_rake(beat(27, 0), up=True, amp=0.85)
final = [ask_pluck("harp", beat(27, 2), H[si], 0.95, "chord", pick=0.12)
         for si in (0, 7, 14)]           # D3 D4 D5: one arm each
sc.cue(beat(27, 2), "camera", name="all-arms")
sc.cue(DUR, "section", name="ring-out")

# ---- the chamber: a bus that hums ------------------------------------------------
drive = sc.bus("harp") + sc.bus("rake")
hum = sympathetic(drive, [38, 45, 50, 57, 62, 69], t60=5.0, damp=0.45,
        coupling=0.18, mix=1.0, loop=False, norm=True)
sc.bus("chamber")[:] = hum * 0.30

# ---- shapes: the strings' movies ------------------------------------------------------
clips = shape_library(picks=(0.12, 0.18, 0.22, 0.28), f0=220.0, t60=3.2,
        cache_dir=os.path.join(outdir, ".shapes"))
sc.attach_shapes(clips)

# ---- export, then the master --------------------------------------------------------
sc.ledger = dict(intended=intended[0], as_written=as_written[0],
        substituted=[[m, round(t, 6), w, p] for m, t, w, p in substituted],
        dropped=[[m, round(t, 6), w] for m, t, w in dropped])
# The stems' one gain is pinned (docs/goals/the-players.md A17): export would
# normalise it to the mix's peak, so a change to one stem (the rake's roll)
# rescaled every other and no stem stayed bit-identical. This is the value it
# normalised to before the roll changed (0.9 / the mix peak of 2026-10-04); the
# stems are written as int16 with no clipping, so the pinned mix must stay
# below full scale.
peak = float(np.max(np.abs(sc.mixdown()))) * STEM_GAIN
print(f"  pinned stem gain {STEM_GAIN!r}: mix peak {peak:.4f}")
assert peak < 1.0, f"the pinned stem gain clips the mix (peak {peak:.4f})"
doc = sc.export(ex, stem_gain=STEM_GAIN)
mix = sc.mixdown()
ir = ir_room(t60=2.2, size=1.3, bright=0.45, seed=SEED)
wet = convolve_tail(mix, ir, mix=0.28)[:take.n]
sos = butter(2, 7500.0, btype="low", fs=SR, output="sos")
out = sosfilt(sos, wet, axis=0)
out = np.tanh(out * 1.25) / np.tanh(1.25)
out *= 0.90 / np.max(np.abs(out))
write_wav(os.path.join(ex, "chamber.wav"), out)
sc.plot(os.path.join(ex, "track.png"), "The Chamber — the score, as played")

# ---- rulers -----------------------------------------------------------------------------
st = doc["stats"]
for d in dropped:
    print(f"    dropped {d[0]} {d[2]} at {d[1]:.3f}s (bar {d[1] / SPB / 4:.2f})")
check("zero conflicts, ≤ 5% of intended notes dropped",
        st["conflicts"] == 0 and len(dropped) <= 0.05 * intended[0],
        f"{st['events']} events of {intended[0]} intended; {len(dropped)} "
        f"dropped ({100 * len(dropped) / intended[0]:.1f}%) after "
        f"{st['refused']}/{st['asked']} asks refused; {st['conflicts']} "
        f"conflicts")
pc = ruler.plan_consistent(sc.events)
check("plan consistent (the engine's precondition)", pc["ok"],
        f"{pc['assigned']} assigned, overlaps {len(pc['overlaps'])}, "
        f"bad spans {len(pc['bad_span'])}, unassigned {len(pc['unassigned'])}")
check("stems re-sum to the canvas plus the chamber",
        np.max(np.abs(mix - sc.bus("chamber") - take.buf)) < 1e-9,
        f"max |mixdown - chamber - canvas| = "
        f"{np.max(np.abs(mix - sc.bus('chamber') - take.buf)):.1e}")
tail = out[-int(0.5 * SR):]
tail_db = 20 * np.log10(np.sqrt(np.mean(tail ** 2)) + 1e-15)
check("master peak 0.90, tail to silence",
        abs(np.max(np.abs(out)) - 0.9) < 1e-6 and tail_db < -60.0,
        f"peak {np.max(np.abs(out)):.3f}; last 0.5 s {tail_db:.1f} dBFS")

hs = sc.bus("harp")
h_ev = [e for e in sc.events if e["mech"] == "harp"]
rec = ruler.score_recall(hs, [e["t"] for e in h_ev], tol_s=0.03,
        min_sep=0.15)
check("harp stem strikes when the score says",
        rec["recall"] >= 0.9,
        f"recall {rec['recall']:.3f} on {rec['findable']} findable of "
        f"{len(h_ev)} (latency {1000 * rec['latency_s']:.1f} ms, "
        f"{rec['extra']} extra onsets)")
ts = sorted(e["t"] for e in h_ev)
cents, locks = [], []
for e in h_ev:
    nxt = min([t for t in ts if t > e["t"]] + [1e9])
    prv = max([t for t in ts if t < e["t"]] + [-1e9])
    simul = sum(1 for t in ts if t == e["t"]) > 1
    # isolation: the before-window must not straddle an earlier attack
    if nxt - e["t"] >= 0.25 and e["t"] - prv >= 0.35 and not simul:
        f = ruler.onset_pitch(hs, e["t"], 100.0, 1400.0, win_s=0.2,
                t60=3.2)
        cents.append(1200 * np.log2(f / hz(e["midis"][0])))
        f0 = hz(e["midis"][0])
        lk = [ruler.onset_lock(hs, e["t"], f0 * r, t60=3.2)
              for r in (1.0, 2.0, 0.5, 1.5)]
        locks.append(lk)
cents = np.array(cents)
locks = np.array(locks)
n_off = int((np.abs(cents) >= 25.0).sum())
check("harp strikes ADD the written pitch (onset_pitch within 25 c, ≥ 90%)",
        len(cents) >= 8 and n_off <= 0.1 * len(cents),
        f"{len(cents)} isolated notes, {n_off} off by >= 25 c, median "
        f"{np.median(np.abs(cents)):.1f} c — the misses are the mixture's "
        f"(a fresh fundamental under a decaying partial at the same Hz)")
margin = locks[:, 0] / np.maximum(locks[:, 1:].max(1), 1e-9)
# >= 99%: the one known miss is an A4 a beat after an A3 bass whose 2nd
# partial cancels the fresh fundamental, with partial 5 at the pick's
# own null (5 * 0.19 ~ 0.95) — partial 3 alone cannot outvote the octave
check("isolated strikes lock to their written comb over octave, sub-octave, fifth (≥ 99%)",
        (margin > 1.0).mean() >= 0.99,
        f"{int((margin > 1.0).sum())}/{len(margin)}; lock(f0) median "
        f"{np.median(locks[:, 0]):.2f} vs octave {np.median(locks[:, 1]):.2f}, "
        f"sub-octave {np.median(locks[:, 2]):.2f}, fifth {np.median(locks[:, 3]):.2f}; "
        f"narrowest margin {margin.min():.2f}x")

ch = sc.bus("chamber")
e_drive = ruler.band_env(drive, 70.0, 700.0, win_s=0.25)
e_ch = ruler.band_env(ch, 70.0, 700.0, win_s=0.25)
corr = float(np.corrcoef(e_drive, e_ch)[0, 1])
cr = ruler.chroma(ch)
top2 = set(np.argsort(cr)[::-1][:2].tolist())
check("the chamber is driven, and hums the D-A dyad",
        corr > 0.5 and top2 == {2, 9},
        f"band-env corr {corr:+.3f}; chroma top-2 {sorted(top2)} (D=2, A=9) "
        f"at D {cr[2]:.2f}, A {cr[9]:.2f} — A crowns because every D "
        f"string's 3rd partial folds to A; the claim is the pair")

bs = sc.bus("bars")
b_ev = sorted((e for e in sc.events if e["mech"] == "bars"),
        key=lambda e: e["t"])
iso = [e for i, e in enumerate(b_ev)
       if (i + 1 == len(b_ev) or b_ev[i + 1]["t"] - e["t"] >= 0.6)
       and (i == 0 or e["t"] - b_ev[i - 1]["t"] >= 0.5)]
hits = 0
# a SHORT window: mode 4 rings 0.35x the fundamental's t60, so a
# 0.5 s window integrates it to 0.7% power and rel=0.02 hides it
for e in iso[:6]:
    a = int(e["t"] * SR)
    f0 = hz(e["midis"][0])
    mf = ruler.mode_freqs(bs[a:a + int(0.15 * SR)], k=4, fmin=200.0,
            fmax=2500.0, rel=0.003)
    ok1 = np.any(np.abs(mf / f0 - 1.0) < 0.03)
    ok4 = np.any(np.abs(mf / f0 - 4.0) < 0.12)
    hits += int(ok1 and ok4)
check("bars ring 1:4 (marimba tuning heard on the bus)",
        len(iso) >= 3 and hits >= min(len(iso[:6]), 3),
        f"{hits}/{len(iso[:6])} isolated strikes show f0 and ~4 f0")

acts = {e["actuator"] for e in final if e}
check("the final chord is three arms at once",
        len([e for e in final if e]) == 3 and len(acts) == 3,
        ", ".join(sorted(acts)))
sections = [c for c in sc.cues if c["kind"] == "section"]
cams = [c for c in sc.cues if c["kind"] == "camera"]
check("cues: sections and camera cuts exported",
        len(sections) >= 5 and len(cams) >= 8,
        f"{len(sections)} sections, {len(cams)} camera cuts")
check("every plucked event names a shape clip",
        all(e.get("shape") for e in sc.events if e["pick"] is not None)
        and all(e.get("shape") is None for e in sc.events
                if e["pick"] is None),
        f"{len(clips)} clips; picks used "
        f"{sorted({e['shape'] for e in sc.events if e.get('shape')})}")

ruler.report(out, "chamber")
if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")
