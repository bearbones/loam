# loam — log (newest at top)

## 2026-08-30 — session 43: the unbreakable bridge, and a record corrected (e43)

Chased session 42's open thread — energy-conserving collision to
fix the grid brittleness — and the first honest measurement
corrected the record instead: THE BRITTLENESS WAS THE OLD RULER.
e42 diagnosed "N=150 doesn't bloom" under the displacement
readout and single-signal env-peak ruler, then replaced both
(velocity readout for the seam, wet/dry ratio for the attack
tilt) without re-running the sweep. Under the shipped
measurement, every grid 130..160 blooms — with the plain penalty
contact AND the new one (7/7 each, asserted). Lesson earned:
when the ruler changes mid-session, every verdict issued under
the old ruler is unverified — re-sweep before logging it.

The SAV contact (scalar auxiliary variable, psi = sqrt(2phi+eps)
per node; midpoint force linear in the unknown, so each node
solves in closed form, no Newton) still earned its place as
fdpluck's default, for what it was actually built to guarantee:
  - ENERGY: lossless string with contact live, total discrete
    energy (string + psi^2/2 store) drifts 1.4e-12 relative —
    machine precision — vs the explicit penalty's 1.7e-2. The
    contact work telescopes as a difference of squares, exactly.
  - ANY K: penalty NaN-explodes at K=1e11; SAV rings at 1e12.
    Contact stiffness is now a voicing knob, not a footgun.
e42 re-run green under the new default (bloom 1.0s x3.3, enrich
x16.8 — same instrument, safer integrator). Smoke 71 green.

And the knob is musical: sustain enrichment across the K
staircase is an ARC — x3.5, x16.8, x6.7, x4.2, x0.8 for
K=3e8..1e12. An infinitely stiff bridge is a clean hard wall
and barely buzzes: a jawari filed too sharp goes dead, in the
simulation as on the instrument. Render sent: e43_savbridge.ogg,
the same A2 string five times, bridge stiffness x3000 end to
end, panned left to right.

Open threads: tension modulation for meend/glissando (c varying
per step — stability budget allows it if c stays under the grid
limit). Sympathetic strings driven by the FD tanpura. Raga
sketch over the drone. Two-polarization string coupled at the
bridge. Grandsire / touches with bobs (from e39).

## 2026-08-30 — session 42: the jawari, won (e42 + loam/fdstring.py)

e41's closing conjecture — bloom needs DISTRIBUTED contact plus
dispersion — built and CONFIRMED. New module loam/fdstring.py:
Bilbao's explicit stiff-string scheme (u_tt = c²u_xx − κ²u_xxxx
− 2σ₀u_t + 2σ₁u_txx, stable while λ²+4μ² ≤ 1) with a parabolic
barrier under the last 10% of string, elastic penalty contact
(K·pen^1.3). ~1 s compute per 1 s audio. The rulers, all green:
wet/dry 1.5-6 kHz envelope ratio peaks at 0.8 s at x3.5 (the
bloom, as WHAT THE BRIDGE ADDS — attack is common-mode and
cancels), sustain enrichment x18.8, pitch 110.0 exact both, late
RMS within 4 dB of the open string (the e41 damper result,
inverted). Render: Pa-sa-sa-SA tanpura cycle in D, middle
strings 3 cents apart, 12 s tails wrapping a 4.8 s loop.

Three lessons paid for in failed runs:
  - GEOMETRY: the barrier apex must sit AT the termination.
    First attempt put the parabola's zero mid-zone — the string
    got pinned there and the PITCH said so: 117.5 = 110/0.94,
    the detuning naming the bug's location exactly.
  - CONTACT: projection (max(u, barrier)) is a perfectly
    inelastic collision — it ate the string alive (late RMS
    −101 dB, enrichment x0.0). Elastic penalty force preserves
    the energy the bloom needs.
  - READOUT: displacement starts on a DC step (string released
    from a held shape) — clicked at every onset and killed the
    loop seam (p100). Velocity readout starts at exactly 0
    (released from REST) — seam p7.3, and it's what a pickup
    measures anyway.

Ruler lessons: env_peak_s + band_env promoted into ruler.py (the
e41 ad-hoc bloom clock, used twice = library). Ratio-of-band-envs
in matched bins is the honest "what did the process add, and
when" question; single-signal env peak was fooled by velocity's
+6 dB/oct attack tilt. And a caveat kept in the open: the
grazing-contact regime is GRID-BRITTLE — N=140 blooms at 110 Hz,
N=150 doesn't (verified at every readout node, so it's dynamics,
not measurement; α=2 Hertzian didn't cure it). N is therefore a
per-string VOICING parameter, swept and pinned per note like
walking the jawari thread on a real bridge (pa 140, sa 112,
SA 138).

Open threads: energy-conserving implicit collision (Bilbao &
Chatziioannou) would likely fix the grid brittleness — worth a
cycle. Sympathetic strings DRIVEN by the FD tanpura (feed it to
strings.sympathetic). Raga sketch over the drone (flute/ney).
Two-transversal-polarization string with coupling at the bridge.

## 2026-08-30 — session 41: the bridge that wouldn't buzz (e41 — a negative result, kept)

Chased e38's nonlinear-bridge thread to the tanpura: the jawari,
whose signature is the BLOOM — high partials swelling AFTER the
attack. Four bridge models went into the KS loop; every one
measured as something other than a jawari, and the failures were
more instructive than a success would have been:
  - one-sided saturator: a DAMPER (sustain 2.5-6 kHz x0.48 vs
    dry). Mechanism: anything riding the fundamental's positive
    half-cycle sees the transfer curve's derivative gain < 1 —
    modulation loss beats harmonic generation, every trip.
  - saturator + per-block RMS restitution: restores ENERGY, but
    the fundamental owns the energy — the high partials stay
    lost (late centroid 0.16x dry). Lossless-on-average is not
    lossless-per-band.
  - moving contact (displacement-dependent delay — the honest
    physics: the string's effective length shortens as it swings
    toward the curved bridge): pitch-exact, but the SWEPT
    fractional-delay interpolation smears highs (0.41x dry).
    Phase-modulation was right in intent; linear interp is a
    lowpass whose loss the modulation exercises.
  - hard obstacle at fixed height: barely engages — per-band
    ratios 1.12..1.31, uniform: GAIN, not spectral change.
Positive controls: all five keep HPS pitch at exactly 110.0 Hz,
all four bridges measurably alter the waveform, and a synthetic
bloom signal proves the bloom ruler reads a delayed HF max
correctly (0.8 s designed, 0.8 s read) — the negative is not a
blind ruler.

Conclusion, recorded: delayed-HF-max bloom needs DISTRIBUTED
contact along the bridge plus string dispersion (van Walstijn's
tanpura simulations have both); a point nonlinearity anywhere in
a KS loop either damps or does nothing. strings.py stays as
shipped (buzz/level params reverted before commit);
e41_bridgetrials.py keeps the evidence as 20 passing assertions.
Exhibit render sent: e41_bridgetrials.ogg (the same A2 pluck
through all five bridges, 4 s each: dry, saturator, restored,
contact, obstacle).

Open threads: a REAL jawari needs a waveguide with several
contact cells + a dispersion allpass — a proper future cycle
(maybe a new loam/waveguide.py); canon at the 4th; polyphonic
transcription; Risset decelerando; thunder doublet.

## 2026-08-30 — session 40: ouroboros (e40; ruler.transcribe, hps_pitch hardened)

The transcription thread, with a compositional customer: a
CIRCULAR CANON. One 32-beat D dorian line, composed by seeded
backtracking search to harmonize with itself rotated half the
loop — voice two is the same melody 16 beats behind, an octave
down, forever. Constraint theory lesson up front: each rotation
pair sounds in BOTH directions half a loop apart, so a P5 one way
is a P4 the other — the consonance set must be inversion-closed
{unison, 3rds, 6ths}: the form forces invertible counterpoint at
the octave, and the search's first "solution" (asymmetric set
with the fifth in) failed its own verifier. Stepwise motion, no
parallel octaves, range >= an octave, wrap obeys everything —
bar one is bar seventeen's counterpoint in both directions.
84 BPM, 22.9 s, two plucks + oh-drone, p89.4 seam.

ruler.transcribe (onset_times + hps_pitch per inter-onset window,
monophonic only) landed — and hardened hps_pitch through three
honest failures on the way to 32/32:
  - PARTIALS ARE NOT BINS: exact-bin downsampling demands partial
    h at bin h*i; real pluck partials drift a bin or three, one
    missed high partial lands on log(~0), and the true candidate
    loses to its own 3rd harmonic. Fix: dilate magnitudes
    (maximum_filter, +/-3 bins) before the harmonic sum.
  - the OCTAVE ERROR has a physical accomplice: pick=0.2 notches
    partial 5 (the pick-position comb), sabotaging f0's 5-term
    product while 2*f0's harmonic set dodges the notch. Fix:
    subharmonic rescue — genuine energy AT f*/2,3,4 means the
    subharmonic is the fundamental.
  - "genuine" must be TWO-SIDED: a KS fundamental can be 12x
    weaker than its own 2nd partial (8% of the octave peak, below
    any winner-relative bar) yet sit unmistakably above the
    spectral floor. >= 6% of winner AND >= 8x the dilated median.
Also: the dyad ruler's quarter-tone probe at +/-3% width
CONTAINED the peak it probed against (band [0.998f, 1.060f]) —
probes moved to 3/4-semitone +/-2% and Hann-tapered (rectangular
sidelobes flood narrow bands); 1.7x became 6684x. And a
truncated test pluck's hard stop reads as an onset (smoke fade).

All 5 rulers pass: a line exists, counterpoint holds (32/32
intervals consonant, 0 parallel perfects, range 19), the tune
comes back 32/32 exact from voice one's bus, designed-dyad
density 6684x probes, seam p89.4. e39 re-run green after the
hps changes (regression checked). dev_smoke 69. Render sent:
e40_ouroboros.ogg.

Open threads: canon at OTHER intervals (rotation + transposition:
canon at the 4th needs its own interval algebra); a crab canon
(retrograde needs non-loop rendering or palindromic melody);
polyphonic transcription (NMF or iterative subtraction — the
"different animal" the docstring warns about); Risset decel /
thunder doublet / taraf bridge still open.

## 2026-08-30 — session 39: Plain Bob Minor (e39; ruler.onset_times)

Permutation music: change ringing on the modal church bells. A
plain course of Plain Bob Minor — six bells, place notation
x.16 alternating with 12 at each lead end, five leads, 60
distinct rows, and the 60th change returns to rounds: the loop
IS the group-theoretic closure (design self-check asserts both).
G-major hexachord E5..G4, rounds descend; rope-circle panning,
tenor rings longest; the handstroke gap observed (one bell-space
of breath before every handstroke row). 93.6 s, 360 strikes,
tower reverb.

The cycle's real purpose: an honest customer for
ruler.onset_times (promised in e36). Spectral flux, local
median+MAD threshold, peak picking. Two earned rules:
  - in a REST the local median and MAD collapse together and the
    threshold chases noise: all four ghosts fired inside
    handstroke gaps, 130-210 ms after a strike (tail flutter).
    An absolute floor helps but cannot fully separate — measured
    flux distributions OVERLAP (faintest true strike 8.7 vs
    ghosts 40-53; a re-struck bell rises less over its own still-
    ringing tail). The separation that works is the CALLER'S
    PRIOR: min_sep just under the known pace (0.2 s vs 0.24
    spacing) makes each ghost lose the local-max contest to its
    parent peak. Detector generality stays; the pace knowledge
    lives in the experiment where it belongs.
  - spectral flux is blind to a strike at t=0 (it sits inside
    frame 0 with no prior frame to rise from) — smoke-test
    clicks start at 0.2 s, and the docstring says so.
  - (comparison-logic tuition, cheap but real: zip-aligning
    detected to designed sequences turns 4 insertions into ~340
    "errors" — 6.4% measured, worse than chance, which was
    itself the tell that alignment, not sound, was broken.)

Bell-order recovery: per-bell narrowband energy RISE at each
detected onset (rise, not level — ringing tails don't rise;
whole-tone spacing keeps prime bands disjoint). All 5 rulers
pass: course closes (60 distinct, returns to rounds), all 360
strikes counted, order recovered 98.9% (356/360), handstroke gap
2.02x a bell-space vs plain joins 1.00x, seam p32.1. dev_smoke
68 checks. Render sent: e39_plainbob.ogg.

Open threads: Risset decelerando / ITD treadmill (e36); thunder
ground-reflection doublet (e37); storm-harp dynamics + nonlinear
taraf bridge (e38); with onset_times + chroma + hps in the
drawer, a TRANSCRIPTION ruler (recover a full melody from a
render) is within reach — would let melodic experiments claim
their tunes; Grandsire or a touch with bobs/singles would test
the method machinery harder.

## 2026-08-30 — session 38: the storm harp (e38; ruler.flatness, ruler.chroma)

e37's open thread, the storm SONG: thunder as a chord source.
Four strikes (1.2/4.5/2.2/6.5 km) drive sympathetic() — the taraf
bank — tuned to nine strings on D/A/D/F/A/C/D/F/A. Pitch classes
{D,F,A,C} only, no E: "no foreign notes" stays falsifiable.
Broadband rumble in, D minor out — the sky plays the harp, the
strings ring 10 s, every tail wraps. Rain (soft, dark) and low
wind underneath. 40 s loop.

New rulers, both born of need and both wrong on the first cut —
the flatness tuition came in TWO installments:
  - ruler.flatness (Wiener entropy) for the TONALIZATION claim
    (noise in, chord out — deliberately blind to WHICH pitches;
    that's chroma's job). Installment one: a single wide-band
    flatness confounds TILT with tonality — post-e37 thunder
    crams its power into a few low bins, so the NOISE measured
    "tonal" (0.015) because most of the window was merely empty.
    Fix: Wiener entropy per octave band (tilted noise is still
    locally flat; only a comb is spiky inside its own octave).
    Installment two: the unweighted octave average let the quiet
    noise-floor octaves above the music outvote the loud combed
    ones (5x, needed 10x) — the POWER-WEIGHTED centroid lesson,
    now in its second home. Power-weighted: sky 0.50, harp 0.056.
  - ruler.chroma: 12-bin pitch-class power fold, normalized;
    docstring carries e35's warning that chroma claims are
    RELATIVE (top-k membership), never absolute floors.

Then the instrument met the ruler instead of the other way
around: 9x tonal at t60=6 s against a stated 10x design claim —
the threshold WAS the design, so the fix was more instrument
(t60 10 s, damp 0.3: sharper comb over the same drive floor),
not a quieter ruler. 14x, and a lovelier sustain for it.

All 5 rulers pass: tonalization 14x (0.50 -> 0.036), comb
selectivity 94x (tuned bands vs quarter-tone probes), strings
answer the sky (envelope corr 0.74 at +145 ms — response follows
excitation), no foreign notes (top-4 chroma exactly {C,D,F,A}),
scene seam p56.7. dev_smoke 67 checks (flatness noise/sine and
chroma A440 self-checks added). Render sent: e38_stormharp.ogg.

Open threads: Risset decelerando / ITD treadmill (e36); thunder
ground-reflection doublet (e37); the harp wants DYNAMICS — a
tension scalar a la e35 that walks the bank between tunings
(storm passes, mode brightens?); sympathetic() coupling is linear
— a nonlinear bridge (tanh on the drive tap) would give the taraf
its buzz.

## 2026-08-30 — session 37: thunder is geometry (e37, texture.thunder)

The open thread from e36: the storm had rain, wind, fire, water —
and no voice. texture.thunder(dist_km, strike_km) after Farnell:
thunder is not a sound, it's GEOMETRY — every meter of a
kilometers-long channel shocks at once, and what you hear is that
line source integrated over arrival time. Segment at height h
arrives at (sqrt(dist^2+h^2)-dist)/c, so duration is not a knob:
a 0.8 km strike smears over 9.6 s (the top of the bolt is far
even when the bottom is close), a 5.5 km one compresses to 3.8 s
of dark clap. Air absorption exp(-d/L) picks each arrival's
surviving spectrum, so the tail darkens CAUSALLY — later sound
walked farther. Crack = the nearest segments' N-wave (biphasic
snap + 0.8-5.2 kHz tear) dying as exp(-dist/1.2); afterclaps =
2-3 branch clusters at shared height/azimuth; sub = 25-80 Hz
decorrelated noise riding the event's own smoothed envelope.

Three synthesis flaws, all caught by rulers on bare buses
(norm=False, house rule):
  - an event-RELATIVE amplitude law ((d_min/d)^1.2) silently
    peak-normalizes every strike — the far strike measured only
    3.7 dB softer than the near one because each was loud
    relative to itself. Absolute 1/d^1.2: gap 30.7 dB. The
    per-call-normalization rule, now caught at DESIGN time.
  - L=1.8 km absorption was too gentle to darken a tail within
    one strike (tail centroid 1261 Hz — daylight). L=1.0.
  - WHITE bursts bandpassed to [28, fc] lose the rumble contest
    to their own mid band: a flat spectrum over a 1 kHz-wide band
    out-powers a 95 Hz-wide low band arithmetically. A shock's
    far-field spectrum peaks LOW — per-burst one-pole tilt at
    0.12*fc (scales with the burst's own darkness) fixed it, and
    the crack rightly inherited the highs. Also one crack lesson:
    the snap competes with SUMS of overlapping bursts — scale it
    to the local mix peak, not to one segment's amplitude.

All 7 rulers pass: distance darkens (centroid 205 vs 44 Hz),
crack is a crest (28.8 vs 20.2 dB), tail walked farther (470 vs
183 Hz within the near strike), tail rumbles (25-120 Hz density
4.6x the 500-2500 band), strike decays (peak window 0, -173 dB),
distance softens (-25.9 vs -56.6 dB unnormalized), scene seam
p18.1. dev_smoke 64 checks.

Scene: e37_stormfront.wav — 36 s loop, rain (soil-dark) + low
wind + three strikes at 0.8/5.5/2.5 km; the 29 s strike's tail
wraps into bar one per seam-craft rule 3. Render sent:
e37_stormfront.ogg.

Open threads: Risset decelerando / ITD-steered treadmill variant
(from e36); ruler.onset_times() when an experiment needs it
honestly; thunder wants a ground-reflection doublet and maybe
echo-off-terrain for canyon storms; a storm SONG (the stormfront
as a chord source — thunder through sympathetic strings?).

## 2026-08-30 — session 36: the ruler drawer, and the treadmill (e36)

Free-play session (director: "follow the winds of your own
creativity... and add tooling"; 30-min cron started to keep the
practice going).

Tooling first — loam/ruler.py, the consolidated measurement kit.
The log's recurring lesson is that the instrument is easy and the
ruler is hard, yet every experiment has re-hand-rolled (and once
per session, mis-rolled) the same measurements. Now the earned
version is the callable default, each with its tuition cited in
the docstring: hps_pitch (argmax lies), centroid_hz (POWER
weighted), band_density (power per sample — summed power scales
with window length), crest_db (peaks, not sums), width_corr
(>250 Hz), pulse_rate (envelope from the fast-decaying 1100-3500
band, high-passed at rate/2 so slow undulation can't bias long
lags), seam_rank (numeric twin of seam_report), rms_contour,
report(). dev_smoke now self-checks the rulers against signals
with KNOWN answers (a 440 pluck, a 500 Hz sine, a 3/s click
train) — the ruler drawer gets a ruler of its own. 63 checks.

e36_treadmill.py — the Risset rhythm: barber()'s rhythmic
sibling, an accelerando that gains one tempo-octave per loop and
never arrives. Six tempo layers at octave spacing, rate
R0*2^(k+t/T); loudness is a Gaussian window in log-rate. The
design theorem that buys the seam: every per-hit property (pitch,
pan, duration, gain) is a pure function of the octave position
o = k + t/T, so layer k at the seam IS layer k+1 at bar one — any
property keyed to k alone would jump at the wrap. Beat times from
integrating the exponential rate, t_n = T*log2(1 + n/(N*2^k));
N=72 divisible by 8 makes every layer's beat count an integer,
and the construction phase-locks the layers (layer k's hit n
coincides with layer k+1's hit 2n): one metric tree, forever
climbing. Pitch rides the rate (110 Hz tom at window center),
amp carries 2^(-o/2) so stream ENERGY density is window-shaped,
not rate-tilted. Under it, a barber'd oh-choir rises with the
rhythm — both staircases in one room.

Ruler lesson (one wrong first cut, mine, and this time the new
kit caught it in minutes): the handoff check compared layer k's
LATE rate to layer k+1's EARLY rate with the design ratio
inverted — the windows straddle o=k+1 (late center below it,
early center above), so design is 2^(-W/T)=0.846, not 1.18.
Measured 0.855 / 0.844 — the sound was right, the ruler's sign
was wrong. The genre continues.

All 11 rulers pass: seam p97.6; all six own-bus rate reads within
3% of design (1.12 vs 1.09 ... 7.32 vs 7.36); both handoffs at
0.85 vs design 0.846; mix stationary (RMS spread 1.61 dB over 8
windows — perpetual acceleration, flat loudness); onset-band
density half-ratio 0.981 (the scale-invariance claim, measured).
Render sent: e36_treadmill.ogg.

Open threads for next sessions: a Risset DECELERANDO variant
(negative exponent) and a stereo field where o also steers ITD;
texture.py still has no thunder; ruler.py wants an onset_times()
(spectral flux) once an experiment needs one honestly.

## 2026-08-15 — session 35: the mood seam (e35 — the blend, audible)

e35_moodseam.py — the mood ruling was going to be between two
renders and a SENTENCE ("wanderer as roam bed, spyglass entering
with tension"). This session turns the sentence into the third
render. One 48 s scene (a scene, not a loop — in-game music is
state-driven): wanderer tiles throughout; tension tau smoothsteps
up 10->16 s, holds, falls 30->38 s; spyglass enters at tau's foot
from its own bar 1 on its own clock, gain sqrt(tau); the wander
yields to sqrt(1 - 0.65 tau) — thinner, never gone. The one-system
thesis (both poles from the world's gut + glass, D ground, E
reserved) is what makes the seam this cheap: no key change, no
tempo negotiation, no ducking.

Ruler lessons (two dishonest first cuts, both mine):
  - summed rfft power scales with segment LENGTH — a 10 s window
    against a 7 s one inflated the hum ratio 0.35 -> 0.71. Power
    DENSITY (divide by N) or equal windows; and the yield law is
    read on the wander's OWN bus (house rule), the survival half
    on the mix where contamination can only help (one-sided).
  - an ABSOLUTE chroma floor blames the seam for harmonic leakage
    the poles already carry: the A2 drone's 3rd harmonic IS E4.
    The seam's honest claim is relative — it manufactures no NEW
    E (mix 0.221 vs pole max 0.701; the spy pole's own high
    fraction is A-harmonic leakage against a small D/F floor, not
    touched notes — its note-level claim passed in e31).

All 7 rulers pass: handover has no hole (min -30.9 vs roam -29.2
dB) and no spike, entry steps 0.2 dB, no new E, overlap roughness
0.140 vs solo max 0.165 (the D grounds do not beat), floor yields
exactly to law (own-bus 0.35 vs designed 0.35) and survives in
the mix (0.35). Render sent: e35_moodseam.ogg. The mood decision
packet is now complete: e31 (noir pole), e32 (dread pole), e35
(the seam between them). Integration shape if the blend is ruled
in: tau is the existing awareness ladder (music.gd already takes
NC.register_mix-style scalars), wander bed = roam register,
spyglass stems keyed in above tau ~0.25 with the sqrt law as
here; the 96 Hz line is already shared plumbing (e20/e22).

e34_drawcreak.py — the operator's bar for the draw: "unobtrusive
wood creak... sort of feel like a nice stretch." The shipped
tick-train (e20 -> NC.creak_voice) is discrete WOOD strikes whose
PITCH climbs with frac — physically a pluck gesture, and "plucking
strings one at a time" is the exact complaint on record. The idea:
a real creak is stick-slip friction, and the two voices invert on
both axes — the tick-train raises pitch and keeps rate sparse
(2 -> 13/s, never crossing the ~18/s fusion floor); the candidate
keeps the BODY fixed (170/430/860/1500 Hz limb modes + a papery
2400 Hz shear) and raises the slip RATE (18 -> 70/s, frac^1.4
hazard), so ticks fuse into a groan whose "pitch" is the rate
itself. The gesture ends in a settle (rate holds, amp relaxes over
0.35 s) — a stretch finishes, it doesn't cut off.

Ruler lessons, both earned by a wrong first cut:
  - crest over a RAMPING gesture measures the ramp, not the
    texture — both buses looked equally spiky until the window
    moved to the late, full-intensity half-second.
  - envelope periodicity under a LONG-RINGING mode is a
    subharmonic lie: the 170 Hz mode rings ~200 ms (4 slip
    periods of overlap early), and autocorr read 23/s as 11/s.
    Read the rate where pulses stay distinct — the high band
    (1100..3500 Hz; those modes decay in ~16 ms) — and bandpass
    the envelope to the pulse register so the 0.9 Hz breath
    undulation can't bias long lags.
  - one synthesis lesson too: a 0.9 ms jerk transient is a CLICK
    (crest within 2 dB of the plucks it was built to beat); a
    fiber lets go over ~2.5 ms. Softer slip = the whole
    unobtrusive claim, in one envelope constant.

All 9 rulers pass on RMS-matched buses: groan 6.6 dB smoother
(crest 14.7 vs 21.3 dB), never dark > 23 ms vs 440 ms tick gaps,
rate tracks the designed hazard (measured 24/63 vs designed
23/63, x2.6 rise), tick centroid climbs x1.11 while the groan
body holds x0.99. Render sent: e34_ab.ogg (tick-train, then
groan). Integration shape if ruled in: replace NC.creak_voice's
interval/pitch dict with a rate hazard (CREAK_RATE_LO/HI on
frac^1.4) and synth the groan into a one-shot the way
_synth_tread_heel bakes its glide — the body table is 5 (fc,Q,g)
rows in NC. TODO pointer left in nock dev/LOG.md.

e33_ledgerdrum.py — the operator accepted e29's cadence "but I'd
like a deeper drum for it." Design claim: the drum belongs to the
TALLY, not to a register — the same hall drum under both dresses
(the night closing is the world's own ceremony wherever you stand).
hall_drum = soft-beater kick 84->38 Hz, drive 1.25, no click, a
50-115 Hz room under it; hits on the word's first step and the
WALK'S LAST STEP (0.40), so the verdict note lands on the bloom.

Three deaths on the way, all instructive:
  - a RATIO ruler saturates against a dark baseline: "low-frac
    >= 3x the wood knock" demanded > 1.0 (the knock is already
    0.60). Depth ratios belong to the centroid (x0.05 measured);
    fractions get ABSOLUTE floors (0.99 >= 0.9).
  - the drum's first cut (drive 1.6, f1 40, room to 420 Hz) put
    its 3rd harmonic at 120 Hz — INSIDE e29's beating band — and
    buried flame's landing (x6.2 -> x1.4). Purify the fundamental
    (drive 1.25, f1 38: 3rd harmonic 114 < band floor) and darken
    the room (50-115 Hz).
  - even purified, a landing-time hit's 38-53 Hz tail leaks
    through the ruler's 2nd-order band edge (~20 dB at 1.7 oct)
    into the measurement window: common-floor dilution again
    (still x1.4). The DESIGN fix beat the ruler fix: move the hit
    to 0.40 — flame x3.9, lightning x8.7. Also: a common
    (verdict-blind) drum bus still breaks onset rulers through
    detector NONLINEARITY — subtract the known common track
    before measuring the pair (37.8 ms false spread -> 0.5 ms).

All rulers pass: deeper (centroid 62 vs 1224 Hz, low-frac 0.99),
minimal pair 0.5 ms both dresses, beating x3.9/x8.7, close < alarm
per dress. Render sent: e33_ledgerdrum.ogg. The cadence is now
OPERATOR-SHAPED end to end; integration recipe: e29's word tables
+ CADENCE_LEVEL + hall-drum synth (one voice, tally-owned) into
sfx/tally per the cycle-65 entry, drum constants NC-side
(DRUM_HITS as beat offsets, DRUM_LEVEL).

## 2026-08-15 — session 32: the wanderer's register (NOCK music, dread pole)

e32_wanderer.py — the second ruled mood pole (Diablo II /
Dishonored), to stand in the operator's A/B against e31's noir
spy. Tristram's lesson taken as RUBATO (a wandering 12-string owns
its own time — no BPM anywhere in the file), Dishonored's as the
FLOOR (a breathing dark that never lifts). One-system thesis
holds: gut string wander with the 12-string octave course
(+12 doubled, 0.55 amp, 14 ms behind, seeded cents — the shimmer),
over a dark D pad + the institution's own loop-quantized 96 Hz
line + wind through a loop-quantized slow lung. Landings
pentatonic, Bb passes for the gothic lean, E untouched.

New ruler earned: RUBATO IS MEASURABLE WITH A POSITIVE CONTROL —
search every uniform grid (period 0.25-1.3 s, circular-mean phase)
against measured onsets; the wander's best residual 26.1 ms
(want >= 25) while the SAME search on e22's lightning melody (the
on-grid control) finds 0.1 ms. A no-grid claim without a control
would be unfalsifiable. Floor: min/median 0.76, env CV 0.09
(between the hum's dead 0.06 and fire's 0.59 — a lung, not a
flicker). line_lock 96.0 Hz prominence 2.7e5. Home x20.1. Seam
p91.6.

Verdict: CANDIDATE (operator taste gate — the A/B against e31 is
the real ruling). Renders sent: e32_wanderer.ogg (loop + first 8 s
again), e32_wanderer_bare.ogg. Integration shape if ruled in:
WANDER table (t, midi, dur, amp) + grace dict NC-side, the pad and
lung from music.gd's existing padsynth/drone plumbing; rubato
means the loop needs no beat clock at all.

## 2026-08-15 — session 31: the spy's register (NOCK music, noir pole)

e31_spyglass.py — the operator ruled on e28's render: the shipped
registers read as "plucking guitar strings one at a time... too
lifeless," and gave two mood poles (TF2 Spy 60s-noir + high-fantasy
twist / Diablo II + Dishonored). This session takes the noir pole,
with a thesis that keeps the register system ONE system: the mood
is built from the world's own two timbres — gut string (flame)
walking a swung noir bass, struck glass (lightning) answering high
— so the spy sits anywhere on the tech gradient without a third
instrument family. Noir lives in the WALK: chromatic passing tones
on weak beats only (strong landings stay D-minor pentatonic; E,
the stained verdict pitch class, is never touched), backbeat brush
sweeps, an anticipation stab on the and-of-4, a bar-8 fill leaning
V->i into the wrap. 84 BPM, 8 bars, swing +0.12 beat (85.7 ms).

"Lifeless" was made a RULER, not a vibe: per-designed-note level
CV on the walk 0.248 vs the shipped e22 flame melody's 0.098
(x2.5, want >= 2) — the baseline's flatness is now a measured
fact, and any future mood must beat it. Other rulers: brush pocket
real (on-eighths 12 ms off design, off-eighths +97.6 ms vs
straight grid, design +85.7, both within 15 ms — e29's local
hysteresis onsets); phrase moves without breaking the loop
(half-vs-half envelope corr 0.79 < 0.9, seam rank p62.4); home
stays home (D pitch-class energy x14.6 over the loudest chromatic
passing class, want >= 4).

Verdict: CANDIDATE (operator taste gate). Renders sent:
e31_spyglass.ogg (loop + first half again, seam audible),
e31_spyglass_walk.ogg (bass+brushes bare). If ruled in, the
integration shape mirrors music.gd's loop builder: the walk is a
pluck table like MOTIF (beat, midi, amp), brushes a shaker clock,
answers reuse the glass voice — all constants NC-side. The
Diablo/Dishonored pole is the next session's sketch; the A/B is
the real ruling.

## 2026-08-12 — session 30: the patrol's tread (NOCK guard identity)

e30_patroltread.py — the premise had to be corrected by the code
first: NOCK's guards are NOT silent (g.stepped plays the archer's
step voices at -16 dB, pitch 0.85, faded 0.025 dB/px to a 900 px
cutoff). The real gap is IDENTITY: guards borrow the player's
feet — same voice, overlapping levels — so heard-not-seen, "whose
step was that?" is ambiguous, against the legibility law.

The candidate: the patrol's gait is a LAYER, not a new family.
tread(mat) = a boot-heel of pitch-drop mass (kick 120->48 Hz,
0.16 s) UNDER the floor's own shipped step voice, verbatim. WHO
is spectral weight (survives any distance gain — a level cue
never could); WHERE is inherited by construction (the floor
speaks its own word, already under nock contract).

Measured against the SHIPPED buffers (render_all dump): WHO — at
equal RMS, tread low-band (<250 Hz) fraction x7.6-x2200 the
archer step's per material, centroid x0.03-0.31 (want <= 0.6);
WHERE — ranking materials by centroid gives the same order in
both gaits (wood < carpet < metal < stone; tread ranked above
300 Hz where only the floor speaks); the edge — dressed with the
game's own law at the 900 px cutoff (-38.5 dB), tread peak 0.0102
clears nock's existence floor 0.005.

THREE ruler/design deaths, one lesson: (a) first invented answer
family buried the floor under the heel (all centroids ~100-200 —
power-weighted centroid reads the loudest BAND, and the heel owns
it); (b) a post-heel WINDOW ruler read stone's absence (grit is
spent by 50 ms — the floor answers THROUGH the boot, not after
it; separate by band, not time); (c) the second invented family
still contradicted the shipped ranking from the other side
(metal's 611 Hz ring read dark, wood's knock read bright). The
lesson closing all three: STOP INVENTING WHAT ALREADY SHIPS —
layer over the contract-covered voices and identity is free.

Verdict: shippable recipe, minimal integration: ONE new synth
(the heel) played under the existing step_%d voice in
_guard_noise's stepped hookup; material system untouched.
Render: e30_patroltread.wav (whose-step contrast on stone at
equal level x3, then a 12 s patrol pass under the shipped gain
law). Pointer in nock dev/LOG.md.


## 2026-08-12 — session 29: the ledger cadence (NOCK night close)

e29_ledgercadence.py — NOCK closes a night with tally ticks and no
music; the game's law is audio-as-information, so the candidate is
a closing cadence where THE VERDICT IS THE HARMONY. A MINIMAL
PAIR: clean and stained share every onset and every pitch except
the last — clean walks down and lands ON the tonic (D, the
motif's home), stained walks the same steps and lands on E, a
major 2nd over home, OUTSIDE the world's D-minor pentatonic. One
note carries the whole verdict. Dressing reuses e23's sting
dresses VERBATIM (gut+wood / glass+hum): the night's last word is
spoken in the same accents as its alarms. Level 0.5 — a close,
not an alarm (caught is 0.92).

Measured: the pair is real — onset spread clean-vs-stained 0.5 ms
in BOTH dresses (rhythm carries zero verdict information); every
note within 5.0 cents of design (e23's match-to-design ruler);
RESOLUTION IS AN AM MEASUREMENT, not a pitch label — mix each
final note with the tonic drone at matched RMS, bandpass to the
fundamentals' neighborhood (120-190 Hz), read the envelope's
12-24 Hz beating band (D3 vs E3 beat at 18.0 Hz): stained carries
x6.2 (flame) / x8.9 (lightning) the clean close's beating energy.
Cadence RMS < caught RMS in both dresses.

TWO ruler deaths, both reruns of known killers: (a) the global
onset picker (find_peaks on the envelope derivative) read a gut
pluck's partial-beating swell as an onset — 261 ms of phantom
"rhythm difference" in a pair constructed identical; e27's law
applies at any scale: measure each attack at its own designed
time, in a local window, by hysteresis crossing (derivative
argmax STILL smeared 10 ms on glass when only the landing pitch
changed). (b) unfiltered envelope beating gave clean flame a
false roughness floor (x1.5) — the pluck's own upper partials
beat among themselves (e27 again); bandpassing the mix to the
fundamentals' neighborhood before the envelope read restored the
contrast (0.11 vs 0.68).

Verdict: shippable recipe. In-game: two short words in music.gd
or sfx.gd built from the shipped pluck/strike voices, picked by
the ledger's clean/stained verdict at tally open, dressed by
register_mix at the arch. The stained landing (E over D) is the
information; the tick train stays. Render:
e29_ledgercadence.wav (flame clean/stained, lightning
clean/stained). Pointer in nock dev/LOG.md.


## 2026-08-12 — session 28: the held breath (NOCK full-draw music)

e28_heldbreath.py — the question the tape law never answered: NOCK's
music rides world_pitch down to 0.2x at full draw (cycle 46 ruling,
elegant on paper), but NOCK is MOBILE-FIRST and a phone driver keeps
almost nothing below ~300 Hz. Is the tune still THERE, on target
hardware, at the game's most dramatic instant?

Finding one is a ruler death worth keeping: the obvious ruler (RMS
survival through a 4th-order 300 Hz highpass) says the defect is
imaginary — survival only falls 0.97 -> 0.73, because a Karplus
pluck is mostly harmonics and the phone keeps them. THE DEFECT IS
REGISTER, NOT SILENCE: fundamental-band phone survival collapses
0.0565 -> 0.0028 (x20) along the game's own dilation curve, and the
phone-heard centroid falls 2727 -> 772 Hz (x0.28). The tune doesn't
vanish; it loses its pitch floor and its light — five-times-slow
rumble at the exact moment of the aim.

The candidate: THE HELD BREATH. As the draw deepens, the world's
music recedes on a dB-linear duck (HELD_DUCK_DB -24; -18 measured
x1.8 on the thesis ruler — stage not cleared) and the archer's own
body takes over ON ARCHER TIME, never dilated (the creak
precedent): a heartbeat whose rate rides frac (55 -> 108 bpm), each
thump a 62/52 Hz damped body the phone drops plus a 900-1800 Hz
valve CLICK the phone keeps — the click is deliberately the phone's
share. Thesis measured: at full draw the phone FOREGROUNDS the body,
p99.9 |phone(heart)| = 3.6x p99.9 |phone(ducked slow melody)|
(peaks, not sums — heartbeats are transients, the crest rule; an
RMS comparison flunked an audibly foreground heart at x0.7 by
diluting sparse thumps over silence). Heartbeat honesty: hysteresis-
onset rate within 0.0% of design at frac 0.5/1.0, lub-dub interval
fraction 0.32 exact. Release: ts and gains snap back over 40 ms;
snap-window max |delta| 0.018 vs hard-cut control 0.230 (x12.5
margin) — the world returns without a click.

Verdict: shippable recipe. In-game: keep the tape law untouched
(music.gd pitch_scale as is); add a draw duck on the music bus
(dB-linear in frac to HELD_DUCK_DB) and a heartbeat tick clock in
sfx on real_dt (like the creak), rate lerp 55->108 by frac, fading
in sin(frac*pi/2). VFX pairing candidate: the existing strain
wobble is the sight cue; the heart is its sound. Renders:
e28_ab_fulldraw.wav (shipped mush vs held breath, same scale, no
per-file normalize), e28_drawarc.wav (rest -> full draw -> release).
Pointer left in nock dev/LOG.md.


## 2026-08-12 — session 27: the borderland (NOCK mid-gradient music)

e27_borderland.py — the question behind nock's self-gated music
item (2): what should the tune do HALFWAY between the registers?
The in-game crossfade plays both loops at 50/50 — but flame is
swung +64 ms and lightning is dead on grid, so every swung note
arrives TWICE. Measured (each voice on its own bus at its own
designed time): 10/10 swung positions get both attacks at ear
parity (within 12 dB), 64 ms apart by e22's own banked tape. THE
FLAM IS REAL — the naive middle is not a blend, it is a rhythm
defect. Verdict on the self-gate: the middle register EARNS ITS
KEEP.

The candidate: THE BORDERLAND PLAYS LIGHTNING'S TIME WITH
FLAME'S HANDS — the same gut plucks, dead on grid (median |dev|
2.4 ms), dead in tune (worst +2.6 cents by parabolic-interpolated
narrow-band peak), no pan wander, over a floor keeping both
fires: thinned stove + faint hum, envelope CV 0.06 — strictly
between lightning 0.05 and flame 0.59, though the margin to
lightning is thin (the borderland floor is nearly institutional;
by design, but barely measurable). Seamless (seam p88.8). Walk
law for the game: squared-cosine borderland bump (half-width
0.35) over the cos/sin ends, power-normalized — flame ->
borderland -> lightning as one continuous walk.

THREE ruler deaths, one worth framing: the single-bus two-attack
flam detector died TWICE (8 ms envelope resolved pluck AM ripple
as attacks; 20-30 ms smoothing still read a "flam" in a SOLO
gut pluck — its slightly inharmonic partials BEAT, putting a
real secondary swell 40-80 ms after its own attack). No amount
of smoothing separates "two instruments in a pocket" from "one
string breathing" on a mixed bus. The flam lives across TWO
buses by construction — measure each voice's attack at its own
designed time, per bus, at ear parity. Also: raw FFT argmax at
110 Hz is a 5.3-cent bin — parabolic interpolation or the ruler
flunks an honestly tuned string on resolution (pluck() has true
fractional delay; the string was never out of tune).

Verdict: shippable recipe for music.gd whenever nock promotes
it: bake a third loop (same MOTIF, plucks on grid, no drift,
stove x0.22 + hum x0.025 bed), three-way power-normalized mix
with the bump width as an NC constant. Pointer in nock
dev/LOG.md.

## 2026-08-12 — session 26: chalk (NOCK sigil marks)

e26_chalk.py — the last cue family on the DESIGN list: the
chalk-sigil mark. The idea: THE MARK IS WRITTEN, NOT STAMPED. A
stamp is one event — any glyph, same thud; a written mark
carries its glyph in the sound. Each sigil is a fixed stroke
sequence and the stroke RHYTHM is the glyph's identity: loop
(checkpoint spiral — one long sweep, two short closes), coin
(peddler's cross — two quick equal cuts), ward (four even
pickets ending on a slow drag). Inside each stroke the hand is
audible: a velocity bell the chalk voices as brightness (the
lowpass corner rides the bell, 900 + 4200v Hz), and squeak
appears only at the deterministic upward crossing of 0.6 vmax —
the failure mode of a real hand, sparse, texture not signal.

Measured: counts exact (3/3, 2/2, 4/4); rhythm intervals within
16 ms of design; the three designs pairwise APART (> 60 ms
someplace); every stroke's mid-third centroid beats both end
thirds (the bell survives the render); loud-squeak fraction
0.06-0.08 of written time (< 0.25).

Two onset rulers died: (a) derivative peaks (the sting ruler)
landed 0.1-0.17 s late and doubled — a stroke is a SLOW SWELL,
its max rise rate sits mid-crescendo and chalk grain gives the
derivative several humps; a written mark's onset is where energy
BEGINS: hysteresis threshold crossing (the stone-skitter ruler),
8%/3%. (b) then intra-stroke grain dips (5 ms holes) re-armed
the hysteresis — 25 ms smoothing bridges them. And the absolute
crossing lag is detector bias, identical every stroke: rhythm
claims must compare INTERVALS, where the lag cancels — which is
what rhythm is.

Verdict: shippable recipe. In-game sigils (checkpoint chalk,
coin panel) currently share stamp-like blips; the candidate is
stroke-written cues where stroke count/rhythm = which sigil,
built as short stroke buffers played on a clock like the relight
telegraph (the tick-train pattern is already house grammar).
Pointer in nock dev/LOG.md. Cue list: COMPLETE — every family on
the DESIGN list now has a measured loam prototype.

## 2026-08-11 — session 25: the death of a hum (NOCK shatter)

e25_shatterhum.py — the lightning fixture's shatter, prototyped
as what connects the living 96 Hz hum to the silence after. The
idea: THE INSTITUTION'S TONE ONLY GOES FLAT WHEN YOU BREAK IT.
All of lightning's language is precise (e22/e23: grid-locked,
cycle-quantized, dead in tune) — so a thrown switch ends the hum
CLEANLY, inside a cycle, while a SMASHED tube loses its mains
lock and dies badly: the hum survives the crash for a moment and
glides flat, phase-continuous (frequency integrated into phase,
so there is no seam at the crash — the same hum, losing its
grip), tau 0.18 s, under a decaying rain of glass whose event
RATE is the instrument again (e24). The glide is the one detuned
thing lightning ever says, and only when the player has done
something loud and permanent.

Measured, each claim on its own bus: the lock holds (every
pre-crash window within 0.1 cents of 96.0 — parabolic-
interpolated peak); the death is monotone (81.6 -> 58.4 -> 42.4
-> 31.3 Hz, 16.6 semitones, every voiced window falling); the
crash is glass (power centroid 5290 Hz); the rain thins (7 -> 6
-> 1 ticks per 0.3 s window, one detection pass binned after);
and two deaths on ONE ruler — hum holds 0.709 s of energy after
the smash vs 0.021 s after the switch cut (34x contrast).

Two rulers died: (a) the pitch track invented NEGATIVE
frequencies (-94, -158 Hz) — parabolic interpolation at the band
edge fabricates peaks once the glide falls below what the band
can hold; the track needs the ruler's own floor (break below
25 Hz), not just an amplitude gate. (b) "the clean off is clean"
asserted the coda's post-cut tail was zero — a tautology, it
measured zeros written by construction (e24's silence lesson in
a new hat). Reframed as CONTRAST on the same ruler both sides:
hold-time after the event, smashed vs switched. And the clean
window must STRADDLE the ramp — starting at the cut sees only
the zeros again.

Verdict: shippable. In-game the smash already has its crash
(cycle 35's loud key ceremony); the candidate is the dying glide
as a new voice under it — and the CONTRAST is free lore: the
switch verb already kills the hum ambience instantly (gated on
lit), which e25 now rules is correct and load-bearing, not an
omission. Pointer in nock dev/LOG.md.

## 2026-08-11 — session 24: the water cycle (NOCK douse / relight)

e24_watercycle.py — the douse and the relight prototyped as one
lifecycle, because in NOCK they bracket the same thing: the
stealth window. The flame is a character; the water arrow only
kills it for a while. Design thesis under test: THE PAIR MUST
MEASURE THE WINDOW FOR THE EAR. The douse ends in genuine
silence (the prize is audible as absence); the relight
TELEGRAPHS — flint scrapes are a fixed-length countdown before
the whump brings the light back, so a player who hears tick one
knows exactly how long their darkness has left. Telegraph length
is grammar: 0.90 s, never varies.

One continuous ~10 s take over a faint night bed (96 Hz + air —
e20's world again): steady crackle -> splash + steam bloom
(crackle dies mid-hiss) -> the dark window -> three flint
scrapes -> catch whump (85 Hz down-chirp bloom, no click) ->
crackle reborn. The rebirth crackle is hand-rolled with RATE as
the instrument: seeded exponential gaps against an interpolated
rate (0.8 -> 6 events/s), because the whole story is an event-
rate arc (6 -> 0 -> ramp -> 6) and the ruler must count what the
code varies.

Measured, each claim on its own bus: steam POWER centroid cools
x2.2 (5742 -> 2582 Hz, want > 2); the window is real (lit rms
12x the dark gap, want > 8); telegraph 3 scrapes, first-scrape
-> whump 922 ms vs 900 design (within the 30 ms gate); rebirth
tick count per 1.4 s window strictly rises 1 -> 4 -> 7.

Three rulers died first, all on standing rules: (a) a
differencing highpass after the gliding lowpass was a +6 dB/oct
shelf that ERASED the glide — centroid pinned at 13 kHz
regardless of corner; glide + fixed 300 Hz butter instead. (b)
the dark gap measured as digital zero, ratio 1/8,579,315 — a
lying ruler; silence must be measured against a floor that
exists, hence the night bed. (c) rebirth counted [5,5,2]: the
40-200 Hz rumble shared the tick bus AND the threshold was per-
window (the per-call normalization sin) — rumble wobble out-
peaked sparse early ticks. Split ticks/rumble onto separate
buses, one detection pass, one threshold, bin afterward.

Verdict: shippable recipe for NOCK. In-game, the douse hiss
already exists (M4.2) but has no cooling glide and no telegraph
exists at all — the guard relight is currently instant-ish with
a generic cue. Integration would be: NC.RELIGHT_TELEGRAPH_S as
grammar, scrape tick train on the guard's relight duty, whump on
light restore, and the crackle rate ramp on the pool's rebirth.
Pointer in nock dev/LOG.md.

## 2026-08-11 — session 23: detection stings in two accents (NOCK)

e23_stings.py — the cue list's "sting per awareness state" meets
the e22 registers, and the law-2 tension (stings are GRAMMAR:
contract words, identical everywhere) resolves cleanly: THE
GESTURE IS THE WORD, THE REGISTER IS THE ACCENT. Three escalating
words in D minor pentatonic — notice (two notes, a rising
question), hunt (three circling), caught (four falling to a low
slam) — each dressed twice: flame (gut pluck + wood knock) and
lightning (struck glass + a 192 Hz hum swell leaning in as the
word lands). Unlike the e22 melody, stings take NO cents drift
and NO swing even in flame dress — the alarm is the one thing
the margins say precisely.

Measured: gesture identity holds across dresses — onsets within
6 ms of design, pitches within 10 cents (grammar HOLDS); rms and
duration rise strictly notice < hunt < caught in both dresses;
the accent is real (lightning tail/peak >2x flame's — glass and
hum sustain, gut dies).

THREE pitch rulers died getting there, each on a standing rule:
open-band HPS octave-erred (+1196/+2398 — bright even harmonics
outvote the fundamental through the product); band-limited HPS
then lied +237 cents about GLASS — HPS assumes HARMONIC spectra,
and glass's inharmonic 2.32x mode masquerades as the 2nd
harmonic of a false fundamental at 1.16x (band-edge clamp made
it look consistent). Match-to-design needs no harmonic model:
plain spectral peak within +/-15% of the designed fundamental,
correct for string and bell alike. New standing rule: HPS IS FOR
HARMONIC SOUNDS — never point it at a bell.

Verdict: shippable as NOCK's awareness cues whenever the game
promotes its detection blips to musical stings — the in-game
recipe would dress by NC.register_mix at the guard's x (the
alarm speaks the accent of the ground it stands on) while the
gesture stays fixed by law. Pointer updated in nock dev/LOG.md
(music TODO item 3 recipe; still self-gated).

## 2026-08-11 — session 22: the two registers (NOCK music)

e22_registers.py — first NOCK music sketch: the magitech gradient
as ONE identity re-clothed, not two tracks. The same 22-note
D-minor-pentatonic motif, same 75 BPM, same 8-bar seamless loop
length, walked from one end of the world to the other:
- FLAME (the margins): the motif on gut-damped Karplus pluck
  (damp 0.5, fingertip-soft excitation) with seeded ±8-cent
  per-note drift, swung 0.16 with a thinned euclid(7,16) shaker,
  marimba-wood answers, fire-crackle bed. Warm master (4.8k).
- LIGHTNING (the institution): the SAME motif note for note on
  struck glass two octaves up — dead on the grid, dead in tune —
  over a narrow-band PADsynth D drone and a cycle-quantized 96 Hz
  mains hum (e20's night tone: the institution's tone was under
  the margins all along). Bright master (9k), nothing loose.
Because key/tempo/length/phase agree, the in-game system is a
POSITION CROSSFADE: two synced loops, the mix knob tied to where
the level sits on the tech gradient. The demo render does exactly
that (8s flame / 8s crossfade / 8s lightning).

Measured (two rulers died honestly on the way):
- seam p97.1 / p89.8 — both clickless.
- grid deviation vs each note's DESIGNED time: flame's swung
  notes +63 ms (design +64), everything else 3-4 ms. The first
  swing ruler measured onset pair-ratios and assumed even eighths
  the motif never had — compare to the design, not to a meter.
- floor breathing (envelope CV): fire 0.59 vs hum 0.05 — the
  fire never stops breathing, the hum never breathes. Voice-bus
  rulers failed first: POWER centroid lost to the standing
  transient rule (a pluck's attack noise out-powers any steady
  line — glass NEVER wins on centroid), and note-sustain lost
  because struck glass is percussion too. The steadiness axis
  lives in the FLOOR, not the voice.
- the floor's identity: bed centroid 10.5 kHz broadband noise vs
  137 Hz line; hum-lock FFT peak 96.0 Hz exact with prominence
  >1e6 vs the fire's incidental x8 in the same band.
- loudness: institution presses x2.4 rms harder BY DESIGN — the
  stakes gradient as pressure, not just color.

Verdict: the one-motif crossfade is the shippable shape — the
gradient reads as the same tune losing its human hands, which is
exactly the game's fiction (harnessed lightning = harnessed
music). Worth a second sketch someday: a middle register (the
crossfade point as its own mood) and a detection-sting overlay
per awareness state in each register's vocabulary. Integration
pointer left in nock dev/LOG.md.

## 2026-08-11 — session 21: arrival by material (NOCK SFX)

e21_arrivals.py — the arrow's other end. The idea under test: the
four material arrivals (stone / wood / metal / body) read as ONE
vocabulary when they share a single excitation — a 3 ms broadhead
contact snap — and differ only in the resonator body it drives.
That is NOCK's uniform-grammar law done in audio: same word,
material timbre. Each material carries one measurable signature:
stone a 4-hit bounce train (no bite — the shaft skitters), wood a
deep thunk with the stuck shaft's 64 Hz cantilever quiver, metal a
long detune-beating lamp-tube ring (custom LAMP_T table — ANVIL's
ratios but long ring multipliers; smithy anvils are damped, thin
fixture steel is not) plus the shaft's drop-off tick, body a dark
thump + cloth breath with no modes worth the name. Impact speed
scales the family like loose_voice scales the launch: velocity
buys level AND hardness (knock + bright), so a soft lob arrives
darker, not just quieter.

Render: e21_arrivals.wav (14.1s one-shot: full-power row then
soft-lob row, 1.4s spacing, light exterior tail).

Measured, each claim on its own bus, explicit gains (strike()
peak-normalizes per call — the standing per-call-norm rule):
- centroid bright pair {stone 3792, metal 1297} > dark pair
  {wood 1137, body 109 Hz}. The first draft claimed a full
  ordering metal > stone and the ruler refused: broadband contact
  noise out-brightens any ring. BRIGHTNESS SEPARATES THE PAIRS;
  RING TIME SEPARATES STONE FROM METAL — the ear tells metal by
  sustain, not tint. Worth keeping as a design rule.
- T30 ring time (40 ms past the contact peak — measured at the
  peak, a knock's crest hands every material the same verdict):
  metal 0.428s = 1.7x wood 0.246 > body 0.134 > stone 0.049
  (dry stone doesn't ring; its energy lives in the bounce train).
- crest: stone 28.9 highest, body 6.2 lowest.
- metal beat 4.7 Hz vs design 5.2 (f0 900, 10 cents) — after two
  ruler fixes: bandpass the FUNDAMENTAL PAIR (every detuned mode
  beats at its own delta-f; the mixed bus is a committee) and
  detrend against the decay ramp, not the mean (the exponential
  slope is the loudest "low frequency" in any ring envelope).
- stone bounces: 4 envelope peaks (impact + 3 rebounds, designed).
- soft vs full: rms -3.5..-5.5 dB, centroid x0.41 stone / x0.72
  wood / x0.78 metal / x0.99 body — flesh has no hardness range,
  so the kill word only quiets, never re-tints.

Verdict: the shared-snap + body-swap structure is the shippable
shape — NOCK's in-game arrive_* family already exists but was
tuned by ear; e21's fingerprints (pair split, ring-time margin,
beat, bounce count, velocity-buys-hardness) are an auditable spec
for upgrading it. Integration pointer left in nock dev/LOG.md.

## 2026-08-11 — session 20: the draw (NOCK SFX)

e20_thedraw.py — first NOCK cue prototype: the signature verb. The
idea under test: the draw cue is not a creak, it is the WORLD
dilating audibly. Archer-time sounds (stick-slip fiber ticks whose
density AND pitch ride the draw fraction, a bowed-wood limb groan,
a hemp tension gliss) stay at speed while the night bed (fire +
wind + a 96 Hz night tone) tape-slows underneath on the eased
dilation curve (1 - 0.8*frac^1.6, floor 0.2x — the NOCK ruling)
and whip-snaps back in 0.35s at release. Slow-motion fire reads
as the flame-lit-margins register doing the slomo's work for it.
Release = Karplus twang + WOOD limb thunk + resonator-swept whoosh
(3k -> 350 Hz); overheld hold gets accelerating tremor AM plus a
thin 2.2k whine.

Two renders: e20_draw_full.wav (10.5s: bed / build / overheld
strain / loud flat release / afterglow) and e20_draw_soft.wav
(6s: the frac-0.2 lure lob — a handful of ticks, barely-dipped
bed, low quiet whoosh).

Measured (each claim on its own bus — the first tick count ran on
the mixed creak bus and counted groan wobbles, 15 vs 19; routed
the ticks to their own bus and the truth appeared):
- bed night tone 96.0 Hz before the draw, 19.4 Hz mid-hold
  (designed 19.2 — varispeed pitch honesty).
- ticks/0.5s: 2 early build -> 6 late (hazard design ~5.5x; sparse
  counts, direction and magnitude read).
- whoosh POWER-weighted centroid: full 2217 Hz vs soft 813 Hz =
  2.73x — draw power audibly IS air speed.
- strain tremor, late hold: 8.0 Hz envelope peak (design ramp
  4 -> 9; the 1s window averages the tail, ~7.9 expected).
Mix lesson (segment profile as the ruler): first master let a
random fire crackle (0.55 peak) out-shout the release (0.29) —
the climax must own the piece; fire trimmed 0.55 -> 0.42, release
raised, now release holds both global peak (0.43) and top segment
rms, and the arc rises bed 0.035 -> strain 0.055 -> release 0.057.

Verdict: the dilation-bed trick is worth shipping — it makes the
draw legible with eyes closed, which is the pairing rule's audio
half for the whole slomo system, not just one cue. The tick
family and twang+whoosh scale naturally by frac (game passes one
number). Integration pointer left in nock dev/LOG.md.


## 2026-08-09 — session 19: ear candy

e19_earcandy.py — three jars, no concept, just pleasure:
- stinger (7.8s one-shot): the podcast-ident recipe. Marimba rise
  through F major penta (glass doubling +12), landing on glass F5
  detuned 2.5c so it beats against itself; two bowed-glass swells
  peak just AFTER the landing (bell hands off to pad); pentatonic
  sympathetic bank shimmers under everything; 2.8s FDN tail.
- clicks (13s one-shot): the click cabinet. thock = body mode +
  contact + sub thump (the desk is a layer); pen press/release
  pair (release lower + softer); bubble pops incl. a rising
  triplet; camera shutter (mirror slap + two wood ticks); marble
  bounce train, intervals *0.78/hop, pitch stiffening 1%/contact.
  Bounce ratio measured from the RENDER: 0.777 vs 0.780 designed.
- soothe (32s seamless loop): creamy PADsynth F2+C3+F3 breathing
  at 7.5 breaths/min — 4 whole cycles/loop so the seam is phase-
  exact, and the envelope FFT confirms bin 4 dominates. Glass
  armonica bowls on the penta, sub F1 under the same breath, four
  music-box sparkles into the ping-pong. seam p64.6.

Width lesson re-confirmed on the soothe: level-panned bowls left
the loop at corr +0.778 (>250 Hz); moving them to ITD placement
(arrival time, e16 recipe) + wider pans opened it to +0.379 with
nothing else touched.

## 2026-08-04 — session 18d: The Alembic (capstone)

songs/the_alembic.py — 76.2s, E minor @63, 20 bars, the three
worlds in one seamless loop: simmer (cauldron + creamy pad,
freq-shifted +2.6 Hz so the whole room is slightly wrong) ->
work (E3 anvils 3:2 vs escapement, bar stock humming, boiler
chuff) -> pour (plink polyrhythm + glass stirs, anvils lighter)
-> transmission (ring-mod vocalise @113 Hz carrier, theremin
swoop, grain debris) -> settle (plink echoes, steam sigh, back
to simmer). Ratchet winding-bursts mark every section seam; the
transmission's ping-pong tail wraps the loop and haunts bar 1.

The arc, measured per section: 0.085 / 0.124 / 0.133 / 0.145 /
0.088 rms — rises to the transmission, settles for the wrap.
Plinks -3c, taraf 3.57x tuned/detuned, seam p82.4, width +0.49
with centered soloists by intent. First draft buried the voice
under the pad (0.028 vs 0.049 in its own section — full-loop rms
understates sparse buses by sqrt(duty), scale before comparing);
climax now wins its bars.

## 2026-08-04 — session 18c: the transmission

e18 "The Transmission" (32s @60): the alien palette measured.
- Ring mod on a sung vocalise (Radiophonic trick): dry C4
  fundamental suppressed to 0.05x, sidebands land at exactly
  f +- 111 Hz at ~0.5x each. The formant MOTION survives the
  destroyed harmonic series — it still speaks, but it's metal.
- Bode shifter on an airy 'oo' pad: partial 2 measured moving
  +4.0 Hz for a +3.69 Hz shift (within the 0.5 Hz bin) — every
  partial moves the same ABSOLUTE amount, the sheen no detune
  can make.
- Theremin answer: pure sine whose f0 steps land BETWEEN the
  keys (float midi), 0.38 s portamento kernel — the swoop is the
  melody, vibrato arrives late.
- Grain debris: the sung phrase scattered +12/+19, shifted with
  the pad so the sparkle disagrees with itself the same way.
Sub trimmed from loudest-thing-in-the-piece (0.071) to floor
(0.046); soloists centered by intent, width +0.45 from pad and
debris. seam p68.6.

## 2026-08-04 — session 18b: the forge

e17 "The Forge" (25.7s, F @112): Rheingold by way of the boiler
room. Master anvil (F3) on the dotted-quarter cycle = 3:2 against
the clockwork escapement's straight eighths (tick-tock alternates
pitch AND pallet/pan); apprentice answers off-cycle on C4/F4;
ratchet winding-bursts (accelerating rim trains) at phrase seams;
boiler chuff + steam vents; all metal in ir_tank. seam p84.7.

The taraf saga — three wrong rulers before a right one:
1. First "sympathetic bank" measured identical tuned vs detuned
   (1.00x): I had passed mix=0.0, which returns the DRY signal —
   I was measuring the input twice. (The 477.6 Hz "hum" was the
   anvil bus itself. mix is wet/dry, 1.0 = wet only.)
2. Fixed, driven from the TANK bus: ratio only 1.4x — the tank's
   11-mode wash is spectrally dense, so a string at ANY tuning
   finds something to resonate with. A detuned-control comparison
   needs a SPARSE drive spectrum to mean anything.
3. Driven from the DRY anvils: 3.81x tuned/detuned, loudest
   partial 474.6 Hz vs the anvil ring's 474.9 — the bar stock
   sings the ring itself. Physically nicer too (the stock hangs
   by the anvils; the room comes after).
Also: ITD placement comb-filters the MONO SUM that sympathetic()
drives from — arrival-time stereo can silently rob a downstream
mono-keyed processor. Same family as the duck-bus lesson.

Bar stock tuned to what the anvils RADIATE (fundamentals + 2.72x
rings, float midi), not to F pitch classes — first draft's meter
caught 475 Hz dominating a bank tuned to F's.

## 2026-08-04 — session 18: the potion (bubbles, and an anvil)

Director's brief for the new season: space alien sci-fi, bubbling
potions, industrial workshop (Rheingold hammers by way of the
Spirited Away boiler room); polyrhythms, timbre words (airy,
swoopy, creamy, crisp), stereo space without gimmicks.

New instruments:
- texture.bubble()/bubbles() — van den Doel liquid sounds: damped
  sine at the Minnaert resonance with the signature RISING chirp
  f(t) = f0(1 + 0.1 d t), d = 0.13 f0 + 0.0072 f0^1.5. Measured
  within 1% of prediction at three sizes, and the rise ratio is
  SCALE-INVARIANT (~1.41, +590 cents: ring time ~ 1/d cancels
  chirp rate ~ d) — why mixed sizes read as one material.
- modal.ANVIL — designed, documented as such: fast clank
  fundamental under a tight inharmonic face-mode pair
  (2.72:2.736) with the longest ring. Measured: ring t60 3.4x
  clank, beat 3.0 Hz vs 3.12 designed.

e16 "The Potion" (30.5s, E minor penta @63): bubbles() cauldron;
creamy pad (steep-tilt PADsynth through slow chorus); two plink
voices — bubble() as pitched music box, damp < 1 — in euclid(7,16)
vs euclid(5,12) polyrhythm through ping-pong tape echo; two
bowed-glass stirs. Plinks tune themselves the winds' way: render
one, measure the onset (chirp reads +55c sharp of f0), pre-
compensate. Final -3c. seam p96.7.

Stereo lessons, both new metrology:
- Level pan keeps a mono blip lag-0 correlated at ANY pan; what
  decorrelates a POPULATION is time-of-arrival — ~0.9 ms far-ear
  ITD + one opposite-wall bounce (the pot's acoustics) took the
  fizz field from +0.78 to +0.03. ITD on the plinks took the mix
  from +0.54 to +0.34.
- The correlation meter has the same leak the duck meter had: a
  2nd-order 250 Hz HP lets the LOUD centered glugs (70-220 Hz,
  physically the pot's one throat) dominate and report the wide
  fizz as mono. Judge width per material AND per band: the fizz
  field measures above the glug band (4th-order, 500 Hz).

## 2026-07-31 — session 17: the front door (pre-digest housekeeping)

README rewritten to index all sixteen modules and — more
importantly — to enshrine the night's metrology rules ("verify by
numbers, and distrust the ruler": bus-not-mix, HPS pitch,
power-weighted centroids, crest for transients, norm=False for
comparisons, per-material width, secant tuning, quantize test
inputs). dev_smoke.py: every module imported and exercised — 54
checks, 0 failures, 1.3s. The library's health is now one command.

## 2026-07-31 — play session 16: texture.py, weather from statistics

Procedural nature after Farnell's Designing Sound: rain (Poisson
chirp-droplets over the averaged far wash), wind (noise through
random-walk wandering resonances — walks close their loops for
seam safety), fire (crackle + rumble surge + hiss flares). Two
fixes with lessons: a CLOSED walk doesn't make a seamless
resonator — the filter STATE must warm on the tail too (wind seam
p99.2 -> p93); and droplet audibility is a CREST-FACTOR question,
not an energy question (1.1x energy but 4.9 -> 9.6 crest — 
transients live in peaks, not sums). e15: rain -> wind -> fire
triptych, crossfading.

## 2026-07-31 — play session 15: the gong (modal.py grows a tam-tam)

Real gongs BLOOM — nonlinear mode coupling (Chaigne/Touze plates)
cascades strike energy upward, shimmer arriving AFTER the thud.
gong() fakes the cascade honestly: the low-mode bed DIPS as the
shimmer envelope rises (energy visibly moves), strike-bend
settles flat, dark thump.

Double metric lesson: LINEAR-magnitude centroid lied in both
directions (bin-count bias made the silent tail read 'bright');
POWER-weighted centroid then exposed that the first synth had no
bloom at all — the fix had to be physics (the transfer), not the
ruler. Bloom now verified across seeds: centroid rises into ~1s
then falls (182->226->64 shape).

e14: three gongs (G1/D2/G2) into the FDN tail.

## 2026-07-31 — play session 14: rhythm.py, the composer's graph paper

euclid (Bjorklund, verified against Toussaint's canon: 3/8
tresillo, 5/8 cinquillo, 5/16 bossa, 5/12 bell — counts exact,
max-evenness proven), rotate/swing/prob/onsets, and SCALES — the
interval tables loam has been hardcoding per-song (hijaz, hijaz
kar, nahawand, kurd, modes, pentatonics) with scale_notes and
quantize_to. e13: five kit voices each on their own euclid
(5/16, 3/8, 7/16 swung, 11/16, 2/5 cross-meter) with a Hijaz Kar
psaltery walk on euclid(5,12) — onset counts verified per bar.

## 2026-07-31 — play session 13: "The Long Stair" (capstone)

96s seamless piece playing EVERYTHING from tonight at once: the
barberpole falls forever under a padsynth bed (the descent that
never arrives), church bells through the ir_bone convolution mark
the depths, psaltery on tape echo, ladder-filtered pulse bass,
sparse kick ducking every bus, the voice sings its sentence and
rests, the ney replies with one overblown peak, and the taraf
hums back at all of them. FDN room on the melodic bus, limiter
on the master.

First-take render: seam p27, sectional rms 0.151/0.176/0.173/
0.162 (breathes, doesn't lurch), peak 0.900. Thirteen modules,
one instrument.

## 2026-07-31 — play session 12: lofi.py, age as an effect

gramophone() / worn_tape(): wow+flutter (cycle-quantized time
warp), Poisson crackle (fine dust + rare big pops), surface hiss,
soft-edged dropouts, 60 Hz hum, the bandwidth funnel with a horn
resonance, tanh squash.

Parameterization bug worth remembering: first draft specified
wobble depth as POSITION (seconds), so pitch deviation scaled
with wobble RATE — the fast flutter swung 3x harder than the slow
wow (161 cents of warble!). Depths now mean PITCH fraction;
position amplitude = depth/(2*pi*rate). Measured after: 25.6c p2p
on a 21c design. Pop counter needed a 15ms refractory window (one
oscillating snap = dozens of threshold crossings; 15.7/s read on
a 1.2/s design).

e12: the night's own vocalise, dry for the statement — then the
needle drops. Band funnel measured 34 dB.

## 2026-07-31 — play session 11: shift.py, sidebands and the staircase

Bode frequency shifter via circular FFT Hilbert — every partial
moves by the same Hz (not ratio): harps become bells, voices
ghosts. Ring mod alongside. Seam-craft-native: the analytic
signal is circular by definition, shift quantized to whole
cycles/loop. barber() = feedback delay with a shift inside the
loop: every echo returns a few Hz higher — the endless staircase.

Verified EXACT: 220/440/660 +37 -> 257/477/697 with the original
at -240 dB; ring 440x100 -> 340/540; psaltery stem 587/880 ->
631/924 (+44.0 on the nose, checked on the BUS per the rule —
the first check read the mix and saw only the pad). One test bug
worth keeping: an unquantized INPUT chord failed the barber seam
check at p100 — the module was innocent; quantize test inputs too.

e11: psaltery dry then ghost-shifted over a forever-rising
barber wash. Seam p41.

## 2026-07-31 — play session 10: convolution spaces, rooms that don't exist

space.py grew synthesized impulse responses + convolution:
ir_room (4-band noise, per-band decay — highs die faster, early
reflection sparks), ir_tank (the decay RINGS: inharmonic decaying
sines over a short wash), ir_bone (MARROW's own: 900-3200 Hz
cavity chitter, dense early cluster), convolve_loop (CIRCULAR
convolution — seamless by mathematical construction, the most
elegant loop-safety in the library: no warming, no wrapping code,
the DFT does it), convolve_tail (linear, for one-shots).

Verified: Schroeder band-T60s land on design (2.09 vs 2.0 mid,
1.15 vs 0.9 high); tank tail spectral contrast 10,000x (rings);
bone band contrast 23.7 dB; circular seam within distribution.
e10: one bell + psaltery phrase through all three rooms back to
back — tail rms/centroid separate them numerically (cathedral
.0052/2563, tank .0035/1827, bone .0024/3016).

## 2026-07-31 — play session 9: voice.py, the hermit hums

Source-filter singing (Klatt lineage): Rosenberg glottal pulse
(flow DERIVATIVE for brightness) with accumulated phase — pitch
glides can't click — plus jitter, shimmer, delayed vibrato, and
aspiration breathed through the same formant bank. Parallel
resonators recomputed per 128 samples so vowels MORPH mid-note
(diphthongs). sing() renders a legato vocalise from
[(midi, beats, vowel-or-morph-pair)].

Verified: F1/F2 land 698/1112 vs 730/1090 targets; pitch +8..+18c
across a line; vibrato 95c p2p (spec 70 + jitter — operatic,
kept); portamento max-delta clean. e09: the voice SINGS a
sentence, rests, answers — and the RMS contour proves the grammar
(0.186 statement / 0.032 rest / 0.202 answer / 0.031 wrap) — the
standing melody rule, verified numerically for the first time.
The voice also drives the taraf: the room hums back.

## 2026-07-31 — play session 8: analog.py, edges and the ladder

polyBLEP saw/pulse (Valimaki band-limited edges), supersaw (7
detuned saws, JP-8000 layout), Huovilainen-style Moog ladder
(4 cascaded tanh one-poles, feedback, per-sample scalar loop at
a fine 0.05s per rendered second).

Verified: polyBLEP drops the alias floor -16.7 -> -41.4 dB;
ladder self-oscillates at res>1 with the squeal near cutoff (454
vs 440); slope measures ~17.5 dB/oct vs the ideal 24 and the
resonance peak sits ~7% flat of nominal — the tanh stages soften
and warp exactly like hardware under drive, documented as
character not bug. Supersaw center voice at equal gain was
re-correlating the channels (bus 0.81); quieter center + near-
zero bleed -> 0.38.

e08_acid: 15s acid line (pulse through swept ladder, accents,
filter opening over the loop) + supersaw pad Dm->Bb + four-on-
floor, everything sidechained to the kick. Seam p64.

## 2026-07-31 — play session 7: dyn.py, the invisible hand

env_follow (attack/release poles, circular warm), compress
(feed-forward, log domain, soft knee), duck (proper sidechain —
the kick-duck every song hand-rolled, retired), transient
(fast-minus-slow differential shaper), limiter (lookahead sliding
max via maximum_filter1d — the first draft's index-matrix version
wanted 700 MB for 16s).

Verified crisp: compressor +12 dB step in -> +5.0 out (spec +4.5,
rest is follower ripple); duck depth 9.0 dB on a 9 spec and -10.0
on a 10; transient +6.0/+0.1 attack/sustain; limiter ceiling
0.950 exact with bit-exact passthrough below.

Metric lesson #5 (the theme hardened into a rule): MEASURE THE
BUS, NOT THE MIX — in the full mix the kick owns the very windows
where the duck acts, and the comparison buried itself (0.306 vs
0.301). Same failure as the drone-under-ney and the normalized
taraf. RULE: verify a processor on its own bus, pre-mix, always.

e07_pump: four-on-floor, pad unducked first half / ducked second.

## 2026-07-31 — play session 6: sympathetic strings (the taraf)

strings.sympathetic(): a bank of driven Karplus-Strong loops tuned
to a chord/scale that hum along with any input — sitar taraf,
piano-pedal-down, the bone resonating with what strikes it.
Fractional delays, t60-calibrated, alternating pans, seam-safe via
full extra warm pass.

Verified: one click in -> all 7 strings ring 59-72 dB above the
spectral floor at exactly their tuned Hz; resonance selectivity
2.5x (D pluck vs Eb pluck into a D string, tail energy).

METRIC LESSON #4 tonight (a theme: the instrument is easy, the
ruler is hard): per-call peak normalization INVERTED the
selectivity measurement — the resonant ring's big buildup peak got
scaled down harder than the off-resonant case, measuring 0.1x when
physics says 2.5x. Cross-call energy comparisons need norm=False;
the flag now exists and the docstring warns.

e06_taraf: drum groove + psaltery phrase through a D-minor taraf.

## 2026-07-31 — play session 5: mod.py, the effects that swim

chorus (N-voice wobbling circular delay, per-channel LFO phases),
flanger (short sweeping comb, unrolled feedback), phaser (cascaded
time-varying allpasses, 128-sample piecewise-constant blocks).
LFOs cycle-quantized, reads circular — loop-safe by construction.

Verified: chorus mono->stereo corr 1.000 -> 0.693; phaser notch
contrast +12 dB with allpass RMS ratio exactly 1.000; flanger comb
= 6x autocorrelation peak at its delay lag. Metric lesson again:
spectral contrast on 50ms of noise is ~30 dB of intrinsic variance
(useless for combs) — autocorrelation at the delay lag is the
honest comb detector; note the peak smears across the sweep range,
that's the sweep working. e05_swim: pad dry->chorus->+phaser
halves, drums through jet-plane flanger.

## 2026-07-30 — play session 4: winds.py, the flute that tunes itself

Waveguide flute after Cook's slide-flute (jet delay -> cubic x-x^3
-> bore delay -> reflection lowpass back into both). ney() preset =
breathier, darker. Overblow is PHYSICAL: shorten the jet delay
(faster air) and the octave speaks — verified x2.005.

This one fought back; the debugging trail is the treasure:
- Waveguide tuning: compensate the reflection filter's phase delay
  AT f0, not its DC limit c/(1-c) (DC limit alone left the high
  register 47c sharp... then the compensation masked the real bug).
- The cubic's zeros at +-1 KILL the jet if pressure pins it there —
  overblow-by-pressure died to silence; keep the operating point
  inside |x| < 1/sqrt(3) and overblow by jet delay instead.
- Mode competition is winner-take-all chaos: ~15-25% of (note,
  seed) combos speak the 12th, deterministic per seed, IMMUNE to
  priming (drive-path or bore-preload), filter slope, and pressure.
  Accepted fix: THE INSTRUMENT LISTENS TO ITSELF — render, measure,
  reseed on wrong mode, retune on wrong pitch (8/48 escapes -> 0-1).
- argmax-pitch LIES: a note whose 3rd harmonic edges the
  fundamental by 4% reads as a mode jump that never happened
  (chased that ghost for two rounds). Harmonic product spectrum
  (sp[k]*sp[2k]*sp[3k]) is the honest fundamental detector.
- Unit-gain pitch correction PING-PONGS when the plant gain is ~2
  (A4 oscillated +-140c forever): secant-method steps (estimate
  local gain from the last two takes) converge. Fractional delay
  on BOTH lines or the response staircases.
- Never measure one pitch inside a mix — the in-context check
  read the glass drone under every ney note (-1200c exactly).
  Verify stems, then mix.

State: mean |err| 22c, worst ~55c (flute), ney preset looser
(+-80c observed) — folk intonation, honestly documented. e04: 32s
ney sentence over bowed glass, overblown peak, seam p26.

## 2026-07-30 — play session 3: spectral.py, phase-vocoder surgery

freeze / stretch / cross_synth on hand-rolled STFT (4096/1024 hann).
- freeze: one frame's magnitudes resynthesized forever; per-frame
  phase advance + jitter blend (0 = buzzy organ, 1 = noise; ~0.3 =
  alive-but-still). Wrapped overlap-add = seamless loop. Verified:
  a church bell frozen mid-ring holds RMS flat to std 0.0015 over
  12s, seam p93 of a tiny distribution.
- stretch: classic Flanagan/Dolson phase vocoder with phase
  unwrapping. 6x on a pluck: duration x5.53 (edge-frame loss),
  pitch EXACTLY preserved (880.0 -> 880.0 Hz).
- cross_synth: A's magnitudes on B's phases, `whiten` blends B's
  per-band envelope, `punch` gates frames by B's broadband energy
  (the vocoder's envelope follower). Choir x drum groove = the
  room learns to talk.

Honest metric note: drum-envelope correlation of the talking choir
plateaus ~0.5-0.6 for ANY frame size (4096 down to 512) — the
squared-energy metric is dominated by kick-band overlap with the
choir fundamental and under-reports the audible gating. Lesson:
when a metric stops responding to the knob that obviously changes
the sound, suspect the metric before the sound.

## 2026-07-30 — play session 2: drums.py, the simulated kit

The classic analog drum recipes as library voices (every song so
far hand-rolled its own kick): pitch-drop kick with band-limited
beater click, two-tone + wire-band snare, 808 hat (six-square
inharmonic cluster through a high bandpass), 808 clap (three fast
bursts riding a fourth), tom/conga with band-limited skin/slap,
540+800 Hz square-pair cowbell, rim, shaker. e02: per-voice
spectral-centroid inspection + an 8-bar groove @102.

Lessons measured, not guessed:
- Raw noise transients POISON the centroid: first kick read 3913 Hz
  (a hi-hat number) from 4 ms of unfiltered click; band-limiting
  the click dropped it to 617 Hz. Same fix tom 5164->873,
  conga 5979->1290. Centroid inspection catches what peak/RMS miss.
- Equal-power pan 0.55 is only ~1.6 dB of channel difference —
  "hard" panning must approach ±1 (0.85 here) to decorrelate.
- A drums-only loop measures mono-ish (corr 0.82 >250Hz) BECAUSE
  the snare/clap backbone belongs in the center; alternating
  hat/shaker pans are the width that actually registers. Judge
  width targets per-material, not one number for everything.

## 2026-07-30 — play session 1: the kit grows six limbs

Research: PADsynth (Nasca / ZynAddSubFX docs), FDN reverb design
(Jot via Smith's PASP), modal tables (measured bell analysis;
marimba bars tuned 1:4:10, xylophone 1:3:6; church bell
hum/prime/tierce/quint/nominal = 0.5/1/1.2/1.5/2).

New modules, each verified numerically before commit:
- pads.py — PADsynth: Gaussian-band spectra on the loop's own DFT
  grid = seam CANNOT exist; independent phase draws per channel =
  free decorrelated stereo; formant_amps + vowel tables = seamless
  choir. (seam_report upgraded to percentile-rank of the wrap step.)
- modal.py — strike/bow over mode tables (bell, church bell,
  marimba, xylophone, glass, wood). Fundamentals land exact.
- strings.py — Karplus-Strong + Jaffe-Smith (pick-position comb,
  damping blend, fractional-delay tuning), period-block vectorized.
- space.py — 8-line Householder FDN reverb (mutually-prime delays,
  t60-calibrated, block-vectorized: 3s in 0.02s; loop-safe via
  double-pass warm) + circular tape echo with cycle-quantized wow.
- shape.py — wavefold (animatable drive), chebyshev (weights[k] =
  harmonic k+1, exact on a sine), bitcrush, pre-emphasized tape_sat.
- grain.py — wrapped Hann grain clouds; +12 into the FDN = shimmer.

Showcase: songs/reliquary.py — "Reliquary", 72s, D aeolian @60.
Choir bed mouths oh->ah across the loop, church bells (the tierce
supplies the minor third), one psaltery sentence with its rest and
low answer (standing grammar), bowed glass in the rests, folded
drone breathing, faint +12/+19 shimmer, everything in the FDN room.
seam p24 (clickless), stereo corr >250Hz = +0.056, peak 0.900.

## 2026-07-30 — spin-off

Director: "spin off the music composition library to its own repo,
and take the next few hours just playing around with new ideas for
sound transformations, effects, simulated samples, and so on. you
can look up research papers too."

Extracted the shared engine from marrow/dev/music/hermits.py into
`loam/` (SR, hz, Loop, stereo, ad_env, write_wav; added
seam_report). Moved the three composition scripts to `songs/`;
hermits.py now imports the library, the two elders stay as written.
Determinism check: loam render of the hermit suite is byte-identical
to a render from the original marrow script. MARROW keeps the .oggs.
