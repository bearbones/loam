# loam — log (newest at top)

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
