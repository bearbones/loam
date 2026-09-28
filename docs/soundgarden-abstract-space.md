# Soundgarden beyond the named dimensions

Status, 2026-09-13. Three ways to explore sound as an abstract space were
discussed, all three were built to a point where they can be run and heard,
and the first was finished into the instrument. This note records the
reasoning, what each prototype measures, and where each one stops.

## The question

The instrument explores a ten-parameter struck-resonator recipe through an XY
pad. The parameters have names: material, ring, brightness, and so on. The
wish was to explore a space that is not organized by those names.

The starting reference was a bag-of-frames music classifier from fifteen
years ago: 13 MFCCs plus first and second derivatives per 12 ms window,
randomly subsampled to 10,000 vectors per song. The paper noted that the
waveform cannot be reconstructed from that representation, which raised the
question of whether an ordered version could be, and whether such a
representation could carry an explorer.

### What MFCCs keep and lose

Even with every frame in order, 13 MFCCs plus deltas do not give the waveform
back, for three independent reasons:

- Phase is discarded before the mel step. Only magnitudes survive.
- The mel filterbank collapses hundreds of FFT bins into a few dozen bands,
  and truncating the DCT to 13 coefficients keeps only the smooth envelope.
  Individual partials, beating pairs, and inharmonicity are averaged away.
- The deltas add nothing once frames are ordered: they are computed from
  neighbors.

What the ordered sequence preserves is the envelope trajectory, the vocoder
half of a sound. Modern neural vocoders invert 80-band log-mel spectrograms
convincingly, which shows that a higher resolution mel magnitude plus a
learned prior is perceptually near-invertible. 13 coefficients are the lossy
end of that spectrum. The 12 ms half-overlapping window gives a 6 ms hop,
about 10,000 frames per minute, which matches the paper's count.

One useful fact: Euclidean distance on a full-length MFCC vector equals
Euclidean distance on the log-mel vector it came from, because the DCT is
orthogonal. So for distances, log-mel bands are the same thing without the
truncation.

### Where abstraction can live

The question splits into two things that are easy to conflate:

- **Coordinates**: how you navigate. Cheap to change, no new dependencies.
- **Generator**: what sounds exist at all. This is the real ceiling. The
  resonator has five modes and one noise burst. No coordinate system makes it
  bow a string.

Three architectures follow, and all three were built.

## A. Perceptual coordinates over the recipe (finished)

The recipe stays the object of truth, since it is always reconstructable and
the journal already stores it. What changed is the measurement and the pad.

**Descriptor** (`soundgarden/describe.py`). Each render is described by 24
mel bands (60 Hz to 12 kHz) averaged inside 8 log-spaced time windows from
5 ms to 1.5 s, in dB relative to the loudest cell, clipped at −80 dB. Struck
sounds decay exponentially, so log time gives the first 50 ms and the last
second equal weight. The grid is level-invariant; level and transient
sharpness travel in the four older scalar features. Together they form a
196-number embedding with fixed scales, so adding a candidate never changes
old distances. The grid weight was calibrated so a random pad gesture moves
the scalar and grid parts by similar amounts.

**Sensitivity**. Eleven renders give a forward-difference Jacobian norm per
recipe dimension: how much the embedding moves per logit step. About 120 ms.
At Porcelain, ring and material are the most audible dimensions; bloom and
beating barely register in this descriptor. The UI shows these as bars under
each parameter.

**Field blend** (`soundgarden/field.py`, mirrored in `web/space.js`). A slider
from 1 to 10 sets how many recipe dimensions each pad axis blends. At one end
each axis is a single dimension and the pad explores exactly two. At the other
end each axis blends all ten with near-even magnitudes. Between, the count
grows linearly and the magnitudes slide from random toward equal. Signs are
always random. The two axes are orthogonalized, with a redraw if they collapse.
Both languages round the slider position the same way and the tests check the
same properties in both.

**Even by ear**. With the toggle on, "Keep & turn field" asks the server for a
plane whose dimension weights are inverse sensitivity, clipped to a 4× range.
Each blended dimension then contributes a similar amount of measured change.
The server also measures the embedding distance across each axis and suggests
a range. Wider clips pushed the pad into inaudible dimensions and saturated the
range at its maximum; the current clip leaves about one plane in eight there.
Axis labels rank parameters by audible contribution, not raw weight, because
an ear-weighted plane deliberately gives quiet parameters large weights.

**Match a sound file** (`soundgarden/match.py`, `/api/match`). Any PCM WAV up
to 8 MB is trimmed to 3 s, described the same way, and its pitch is estimated
from the lowest strong spectral peak. Candidates are the starters plus every
accepted recipe in the discovery journal, rendered at that pitch. The closest
three are refined with Nelder-Mead in logit space. This is the MFCC idea used
correctly: as a loss, not as a representation to invert.

| Target | Result |
| --- | --- |
| A starter rendered at G4, matched blind | Recovered exactly (distance 0.001), pitch 67 |
| A Loam church-bell strike | Distance 0.13, pitch 48, metallic hollow recipe |
| Time with the 156-trial journal, idle CPU | About 10 s |

A distance near zero means the resonator can make that sound. A distance of
0.13 means "the closest this resonator gets", which for a bell is a bright,
long, hollow alloy. That is the honest limit of option A: the map is not onto.

**Journal migration**. Older journals lack descriptors. On resume the explorer
re-renders every recipe, checks that the recorded measurements reproduce to
1e-5, and fills in the descriptor. This is a stronger compatibility proof than
the old source hash, which covered the search code as well and would have
forced a fresh directory for any search change. The synthesis hash remains and
still fails closed. The existing 150-trial library migrated in place.

## B. Sinusoidal plus residual (prototype)

`soundgarden/sms.py`. A struck sound becomes a list of partials, each with a
frequency ratio to the fundamental, an amplitude, an exponential decay rate,
and an attack time, plus a 24 × 8 noise envelope on the same log-time grid
for everything the partials miss. Partial frequencies come from a zero-padded
whole-signal spectrum with parabolic peak interpolation; amplitudes are
tracked per STFT frame and fitted by weighted log-linear regression. The
residual is the STFT with partial bins masked out, reduced to band power.
Synthesis is decaying sines plus noise shaped through the STFT. Morphing pairs
partials by rank and interpolates log frequency, log amplitude, log decay, and
dB residual.

This representation reconstructs audio, which MFCCs cannot, and it can be
fitted to any recording, so a recording becomes a recipe of a few hundred
numbers. Phase is discarded, so the result is "the same partials and noise",
not the same waveform.

| Starter | Partials found | Grid distance, resynthesis to original | Nearest other starter |
| --- | --- | --- | --- |
| Porcelain | 8 | 0.50 | 1.32 |
| Hollow timber | 24 | 0.73 | 2.42 |
| Slow glass | 13 | 0.54 | 2.61 |
| Small alloy | 16 | 0.47 | 1.32 |

Every resynthesis is closer to its own original than to any other starter.
The figures show partials preserved as lines. Two honest defects: the drive
stage's difference tones are picked up as sub-fundamental partials (ratio
0.307 at Porcelain), and beating pairs that the tanh limited in the original
sum in phase at the onset, so Small alloy resynthesizes with a higher peak.

```sh
python3 -m soundgarden.sms --demo --out render/sms-morph.wav       # Porcelain → Small alloy, 5 steps
python3 -m soundgarden.sms bell.wav --out bell-resynth.wav --json bell.json
python3 -m soundgarden.sms a.wav --morph b.wav --steps 7 --out morph.wav
```

## C. A learned latent (prototype)

`soundgarden/latent.py`. A NumPy autoencoder, 192 → 64 → 6 → 64 → 192 with
tanh hidden layers and Adam, trained on descriptor grids of 1,500 random
recipes. No torch; the whole thing trains in under a minute on the CPU.

| Held-out reconstruction MSE | |
| --- | --- |
| Autoencoder, 6-D latent | 0.00106 |
| PCA, 6 components | 0.00156 |
| Predict the mean | 0.01772 |

Six unnamed numbers explain about 94% of the grid variance, and the
nonlinearity buys a third less error than a linear latent of the same width.
The latent is genuinely abstract: no coordinate has a name.

Two decoders show the whole trade-off:

- **Griffin-Lim** from the decoded grid gives a generator not bound to the
  resonator. But it hears through 24 bands and 8 time anchors, so partials
  blur into bands and the attack smears, as the third and fourth panels of
  the figures show. The latent reconstruction is nearly identical to the
  grid's own Griffin-Lim decode: the model is not the bottleneck, the decoder
  is. This is exactly the transient problem that makes mel-only latents a poor
  fit for struck sounds.
- **Nearest recipe**: the decoded grid's nearest training grids give recipes
  that the real synth renders exactly. Perfect audio, resonator-bound sounds.
  This decoder blends back into option A.

```sh
python3 -m soundgarden.latent --train 1500 --epochs 300
python3 -m soundgarden.latent --walk 8      # writes both decodings of one latent traversal
```

A serious version is RAVE (Caillon and Esling, 2021): a variational
autoencoder with an adversarial waveform decoder trained on hours of audio.
It runs on the machine's GPU and would need torch, a corpus, and a rethink of
the instrument's reproducibility promises, since a trained artifact replaces
deterministic code as the source of truth.

## C2. A tone as the primitive (prototype)

The struck sound was the wrong primitive for a learned latent. Its descriptor
has a time axis, and inverting a time-frequency grid is where the Griffin-Lim
decoder loses the attack. A stationary tone has no time axis. Its descriptor
is one spectrum, and one spectrum can be decoded exactly by additive
synthesis, with no phase recovery at all. Time then becomes a separate
factor, applied after the tone: per-partial decay rates, exactly what the
sinusoidal model of option B already measures.

`soundgarden/tone.py`. The analyzer averages the STFT power over the middle
of a sound, finds the fundamental from the lowest strong peak, and then
searches for a stretch coefficient B such that the partials sit at
k·f0·√(1 + B·k²), the piano-string inharmonicity law. The search scores each
predicted partial by its level above a floor, discounted by how far the
nearest peak is from the prediction, so missing partials score nothing and a
partial caught off-center counts little. The first version summed energy
instead and preferred no stretch, because an empty window at the right
answer scored worse than a wrong window that happened to catch a neighbor.
Peak heights are read with parabolic interpolation in log power, which
removes the Hann scalloping loss of up to 1.4 dB.

The descriptor is 89 numbers: 64 harmonic levels in dB below the strongest,
24 mel-band noise levels measured with the harmonic bins masked out, and the
stretch on a log scale. Everything is pitch-normalized, so pitch is a free
choice at decode time. The decoder is an oscillator bank plus noise shaped
through the STFT to the stored band levels, with the noise targets scaled by
the same window gain as a sine peak so the harmonic-to-noise balance is
preserved.

| Tone | Recovered |
| --- | --- |
| 8 harmonics at known levels, no stretch | levels within 1 dB, stretch 0, noise below −54 dB |
| 12 partials at B = 10⁻³ | B = 1.00·10⁻³ (also at 10⁻⁴ and 5·10⁻³) |
| Analyze, synthesize, analyze again | harmonic levels within 1.2 dB |

**Corpus.** The latent is meant to be a timbre space rather than a recipe
space, so the training set comes from Loam's own tone makers: PADsynth saw
spectra at five tilts and the five vowels, analog saw and three pulse widths,
supersaw, bowed modal tables (glass, bell, wood, marimba, church bell,
anvil), flute (plain and overblown), ney, reed pipe, and plucked strings at
two dampings, each at five pitches, plus 400 random Soundgarden strikes
averaged into tones. 535 tones in 12 s. The singing voice was left out; its
formant bank runs per sample and takes minutes per note. Because a convex
combination of two tone vectors is itself a plausible tone, the training set
is doubled with random pairwise mixes before fitting.

**Latent.** The same NumPy autoencoder as option C, now 89 → 48 → 6 → 48 → 89.

| Held-out reconstruction MSE | |
| --- | --- |
| Autoencoder, 6-D latent | 0.00383 |
| PCA, 6 components | 0.00598 |
| Predict the mean | 0.04884 |

Six numbers explain about 92% of the variance across a corpus that spans
flutes, pads, bowed metal, and plucked strings, and the nonlinearity buys
about a third less error than a linear latent, as before. The difference
from option C is entirely in what comes out of the decoder.

```sh
python3 -m soundgarden.tone --build --train --walk 8    # corpus, fit, traversal WAV
python3 -m soundgarden.tone analyze note.wav --out note-tone.wav --midi 55
```

![Tones through the additive decoder](soundgarden-abstract-space/tone-resynthesis.png)

The flute keeps its harmonic series and its breath, though the breath comes
back somewhat brighter than the original, since 24 bands are a coarse mould
for a noise spectrum. The PADsynth vowel comes back with its formants in
place. The bowed bell shows the honest limit: its partials do not sit on a
stretched harmonic grid, so three of them survive where they happen to land
near a harmonic and the rest are absorbed into a noise band around 2 kHz.
Free partial ratios, as in option B, are the fix, at the cost of a descriptor
whose entries no longer have fixed meanings.

![The two latent walks](soundgarden-abstract-space/latent-walks.png)

The walk is the point of the exercise. The struck-sound walk, top, decodes
eight nearly identical blurred strikes: the Griffin-Lim decoder flattens
whatever the latent varies. The tone walk, bottom, moves from a bright noisy
tone to a clean plucked-string series with the noise falling and the upper
harmonics gaining step by step. That is a latent whose coordinates you could
put on a pad: every point decodes to a distinct, stationary, playable tone at
any pitch.

## Figures

`python3 -m soundgarden.figures` regenerates these from the current code and
the trained latent models.

![Porcelain through each representation](soundgarden-abstract-space/porcelain-representations.png)

![Small alloy through each representation](soundgarden-abstract-space/small-alloy-representations.png)

## Where this leaves things

- The pad now has un-named coordinates with a controllable blend, weighted by
  what the ear notices, and a way in from any recording. Option A is done.
- Option B is the natural next generator: a partial-list recipe family with
  an analyzer, sitting beside the resonator under the same descriptor and
  the same pad. That would make the reachable set as wide as the recordings
  you feed it.
- Option C with a struck-sound primitive is not worth pursuing without a
  waveform decoder. With a tone primitive (C2) the decoder problem disappears
  and the latent walk is already musical. The next step there is to put time
  back as a second factor: per-partial decays and a noise decay over the tone,
  so a latent point plus an envelope model gives a struck or bowed note. The
  additive synthesizer already accepts both.
