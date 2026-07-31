# loam — log (newest at top)

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
