"""The consolidated rulers — every measurement this library has had
to learn the hard way, in one module, with the hard-way version as
the default.

The log's recurring lesson: the instrument is easy, the ruler is
hard. Until now every experiment hand-rolled its measurements and
paid the tuition again. Each function below encodes a specific
earned rule (cited from LOG.md); experiments should reach here
first and hand-roll only what is genuinely new.

House rules these tools assume but cannot enforce:
- Measure a processor on its OWN BUS, never in the mix.
- Per-call peak normalization inverts cross-call energy
  comparisons — render comparison material with norm off.
- Judge stereo width PER MATERIAL (a centered drum backbone is
  correct, not a failure).
"""

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

from . import SR


def _mono(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=1) if x.ndim == 2 else x


def hps_pitch(x: np.ndarray, fmin: float = 40.0, fmax: float = 2500.0,
        nharm: int = 5, tol_bins: int = 3) -> float:
    """Fundamental via harmonic product spectrum. Earned rules:
    plain argmax lies when a harmonic edges the fundamental (e04);
    multiplying downsampled spectra makes only the true f0's comb
    line up. And (e40) PARTIALS ARE NOT BINS: exact-bin
    downsampling demands partial h sit exactly at bin h*i, but
    real partials drift a bin or three (inharmonicity, window
    edges) — one missed high partial lands on log(~0) and the
    true candidate loses to its own 3rd harmonic. Dilating the
    magnitudes (local max over +/-tol_bins) before the harmonic
    sum forgives the drift. Then the octave rescue (same cycle):
    an instrument can NOTCH a low harmonic (a pluck picked at 0.2
    of the string zeroes partial 5), sabotaging the true
    candidate's product while 2*f0's harmonic set dodges the
    notch — so if genuine energy sits AT a subharmonic of the
    winner, the subharmonic is the fundamental. "Genuine" is
    two-sided: a modest fraction of the winner (>= 6%) AND far
    above the spectral floor (>= 8x the dilated median) — a KS
    fundamental can be 12x weaker than its own 2nd partial and
    still be unmistakably a partial, not noise. Deepened in e44
    from seed-dependent octave errors: the winner can be harmonic
    SIX or EIGHT of the truth (divisors 2..4 rescue onto the
    wrong octave), and a true fundamental can be under 1% of the
    winner yet thousands of times the floor — so divisors run
    2..8 and strong LOCAL CONTRAST (>= 200x the median of a DONUT
    around the sub — neighborhood minus the dilated peak itself;
    calibrated between a measured phantom at 96x and the weakest
    true starved fundamental at 638x)
    qualifies a sub even when the fraction-of-winner test says
    no. Local, not global: a long window's global floor is
    minuscule and a decaying signal's broadband low skirt clears
    any absolute multiple of it (that bug cost e42's open string
    its octave for one commit) — but a skirt is FLAT where a
    real fundamental is a peak, and the donut keeps the peak
    from vouching for itself."""
    from scipy.ndimage import maximum_filter1d
    m = _mono(x)
    w = m * np.hanning(len(m))
    raw = np.abs(np.fft.rfft(w))
    mag = maximum_filter1d(raw, 2 * tol_bins + 1)
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    i0 = _hps_core(mag, f, fmin, fmax, nharm)
    # the dilated contest names the RIDGE; the raw spectrum names
    # the bin within it. A pure tone's 7-bin plateau ties exactly
    # and argmax takes the low edge — 3 bins = 48 cents at 220 Hz
    a = max(i0 - tol_bins, 0)
    return float(f[a + int(np.argmax(raw[a:i0 + tol_bins + 1]))])


# structural-witness bars for the strict octave rescue (see the
# calibration note at the use site); module-level so calibration
# sweeps can vary them
STRUCT_BAR = 50.0      # on-grid peak must clear 50x its donut
STRUCT_COUNT = 2       # and >=2 of 4 witnesses must be live


def _sub_structure(raw, fj, df, d):
    """How many unexplained multiples of a sub-candidate hold
    ON-GRID energy in the RAW spectrum. For a /d rescue, the
    winner's comb explains every multiple of d — and the most
    common phantom is 'half of something real', whose EVEN
    multiples are that voice's own harmonics (e51: a d=4
    candidate at hz(57)/2 harvested witnesses at o=2 and o=6
    from voice 57 itself). Purely-odd witness sets were tried
    and refuse TRUE d>=3 rescues (5,7,11,13 x fj are damped
    high partials; the honest evidence at o=2,4 was carrying
    them) — so the set stays the first four o with o % d != 0,
    but at least one LIVE witness must be ODD: an odd multiple
    is the one thing a 2*fj comb can never supply. One more
    demand, for every d: the IMMUNE witness — the first o in
    {7, 11, 13} with o % d != 0 — must be live. A chord
    SUPPLIES a half-of-something-real phantom's other odd
    witnesses: with a perfect fifth in the chord, 3*(root/2)
    IS the fifth and 9*(root/2) is the fifth's h3, exactly;
    with a major third, 5*(root/2) sits 14 c from the third's
    octave, inside the window (e51's vamp beat 8: F major's
    own C and A testified for F/2 and dragged the root to
    midi 41, first as a d=2 rescue, then — once o=7 was
    demanded there — reborn as d=3 under a winner at the
    chord's FIFTH, its witnesses the same chord tones). No
    chord interval is 7:2, 11:2 or 13:2 — and every measured
    true rescue had its immune witness live (>=58x donut)
    while every phantom read it dead (<=6x). The immune
    demand also retires a measured lucky rescue: a d=5 fire
    43 cents off the truth (o7 dead) that min(subs) preferred
    to the honest d=2 an octave up. Witnesses are read in
    RAW, which no null ever touches: the e50 single-witness
    failure (a just fifth nulling 3*f_lo == 2*f_hi out of the
    residue) cannot recur — a shared bin is still live in
    raw, and sharing IS evidence here. Each
    witness is read within +/-2 RAW bins of o*fj (fj already
    _partial_refine'd): a real sub-fundamental puts partials
    exactly there, while another voice's partial that merely
    wanders near lands OFF-grid and the tight window excludes it
    (the dilated spectrum, +/-tol bins wide, cannot — e51's first
    probe read 8000x 'support' for a phantom from a neighbor's
    partial inside the dilation). Live = peak >= STRUCT_BAR x
    the local raw donut median."""
    def _live(o):
        b = int(round(o * fj / df))
        if b + 3 >= len(raw):
            return False
        pk = raw[b - 2:b + 3].max()
        dn = np.median(np.concatenate([
                raw[max(b - 30, 0):max(b - 8, 0)],
                raw[b + 8:b + 31]]) + 1e-12)
        return bool(pk >= STRUCT_BAR * dn)

    immune = next(o for o in (7, 11, 13) if o % d)
    if not _live(immune):
        return 0
    live = odd_live = 0
    for o in [o for o in range(2, 13) if o % d][:4]:
        if _live(o):
            live += 1
            odd_live += o % 2
    return live if odd_live else 0


def _hps_core(mag, f, fmin, fmax, nharm, strict_sub=False,
        raw=None, tol_bins=3, struct_sub=False):
    """The HPS contest + octave rescue on a prepared (dilated)
    magnitude spectrum. Shared by hps_pitch and dyad_pitches.
    strict_sub=True drops the local-contrast rescue clause — for
    a NULLED residue spectrum, whose half-cut null edges mimic
    locally-contrasting peaks and invite phantom /2../4 rescues
    (e44: a clean 831 Hz voice dragged two octaves down).

    Contest rules earned across e44/e45 (each clause paid for by
    a measured failure): every member's log contribution is
    floored at -60 dB of peak, so junk is UNIFORMLY silent
    evidence (unfloored, log(junk) swings tens of units on
    leakage luck and a subharmonic wins on whose junk was less
    tiny); a bin below -120 dB of peak holds no energy of its own
    and is not eligible to win at all (a pure sine ties every
    subharmonic candidate — argmax must not fall to the band
    edge); the strong-own-bin bonus breaks the remaining exact
    ties in the true bin's favor. Evidence above the floor weighs
    by log SIZE, never by one-member-one-vote: a counting contest
    let a -44 dB ring-over shard outvote a 0 dB fundamental
    (e44's beat residues, where a low candidate harvests one
    shard from each ringing neighbor)."""
    clampv = 1e-6 * mag.max()
    silent = mag < clampv
    mag = np.maximum(mag, clampv)   # the rescue's donut floor
    # the contest (e45, twice revised): log product with every
    # member's contribution FLOORED at the strong bar (-60 dB of
    # peak), plus a strong-own-bin bonus that dominates the sum.
    # The floor makes everything below the bar UNIFORMLY silent
    # evidence — a pure tone then ties all subharmonic candidates
    # exactly (junk can't outrank evidence bin by bin) and the
    # own-bin bonus breaks the tie. Above the bar, evidence weighs
    # in proportion to its log size: a counting contest (+1000 per
    # strong member, the first e45 attempt) let a -44 dB ring-over
    # shard outvote a 0 dB fundamental — in a beat-segment residue
    # a LOW candidate harvests one shard from each ringing
    # neighbor and wins 4 votes to 3 (e44 beats 2/26, the 5:2
    # near-miss of interval 16 nulling voice 2's even partials).
    strongv = 1e-3 * mag.max()
    mm = np.maximum(mag, strongv)
    acc = np.log(mm + 1e-12).copy()
    acc[silent] = -np.inf
    acc += 500.0 * (mag >= strongv)
    for h in range(2, nharm + 1):
        dec = np.log(mm[::h] + 1e-12)
        acc[:len(dec)] += dec
    band = (f >= fmin) & (f <= fmax)
    acc[~band] = -np.inf
    i0 = int(np.argmax(acc))
    floor = np.median(mag) + 1e-12
    subs = []
    for d in range(2, 9):
        j = int(round(i0 / d))
        if f[j] < fmin or mag[j] < 8.0 * floor:
            continue
        # strict mode (nulled residues): size cannot decide the
        # rescue — e50 measured true-rescue and phantom fractions
        # OVERLAPPING at 0.06-0.12 (a bar of 0.12 exiled five
        # certified triad shapes; phantoms fired at up to 0.54).
        # STRUCTURE can (e51, measured on those labeled cases):
        # a real sub-fundamental holds on-grid energy at the
        # multiples the winner's comb can't explain — every true
        # rescue showed 4/4 witnesses live, phantoms 0-1 (junk
        # once scraped 2, which the max-struct ranking below
        # outvotes; the immune-witness demand in _sub_structure
        # blocks the chord-supplied families). A SINGLE
        # odd-harmonic witness was tried in e50 and is
        # structurally blind — chords eat it (a just fifth nulls
        # 3*f_lo == 2*f_hi, a major third 5*f_lo == 4*f_hi, a
        # major triad's root loses both) — but 2-of-4 survives
        # what chords eat. The 0.06 size floor still applies.
        if strict_sub or struct_sub:
            st = _sub_structure(raw, _partial_refine(raw,
                    f[j], f[1], tol_bins), f[1], d)
            st_ok = st >= STRUCT_COUNT
            if strict_sub:
                # nulled residues: no contrast clause (null edges
                # mimic contrast, the e44 lesson) — size floor
                # AND structure
                if st_ok and mag[j] >= 0.06 * mag[i0]:
                    subs.append((-st, j))
            else:
                # polyphonic first pass (struct_sub): structure
                # is the primary witness — size only confirms
                # the bin holds energy at all (>= -80 dB of the
                # winner, plus the 8x-floor guard above). A true
                # voice under a mix's octave-up winner measured
                # frac 0.028 (e51 NEWb1) — below any honest size
                # floor, and dilation lifts the donut too far
                # for the 200x contrast clause — with 4/4
                # witnesses live; the phantom that size fired at
                # frac 0.22 (NEWb10) had 0 live.
                if st_ok and mag[j] >= 1e-4 * mag[i0]:
                    subs.append((-st, j))
        elif mag[j] >= 0.06 * mag[i0]:
            subs.append(j)
        else:
            donut = np.median(np.concatenate([
                    mag[max(j - 25, 0):max(j - 7, 0)],
                    mag[j + 8:j + 26]]) + 1e-12)
            # the -80 dB gate (e45): a numerically CLEAN spectrum
            # (synthetic partials) has floor and donut near the
            # 1e-12 guard, so leakage sidelobes show huge local
            # contrast — demand the sub also be at least 1e-4 of
            # the winner before contrast can vouch for it
            if mag[j] >= 200.0 * donut and mag[j] >= 1e-4 * mag[i0]:
                subs.append(j)
    if subs:
        # structural modes rank fired rescues by STRUCTURE first,
        # depth second: min(subs) alone let a junk d=3 with a
        # scraped-by struct of 2 shadow a true d=2 with 4/4 live
        # (e51 phantom-score beat 11 — the deepest fired rescue
        # is not the best-evidenced one). Legacy mode keeps pure
        # min: deepest divisor (e44's h6/h8 winners).
        if strict_sub or struct_sub:
            i0 = min(subs)[1]
        else:
            i0 = min(subs)
    return i0


def _partial_refine(raw, f0, df, tol_bins):
    """Sub-bin f0 from where the partials ACTUALLY sit in the
    undilated spectrum (dilation smears peak position +/-tol bins
    — a full semitone at 100 Hz with 0.5 s windows). MEDIAN of
    per-partial estimates, not a weighted mean: in a mix, one
    window can catch the OTHER voice's partial (a twelfth away,
    voice 2's fundamental sits 17 Hz off harmonic 3) and a mean
    lets that single interloper drag f0 a semitone sharp."""
    est = []
    for h in range(1, 7):
        c = h * f0 / df
        a = int(round(c)) - (tol_bins + 2)
        b = int(round(c)) + tol_bins + 3
        if b >= len(raw) or a < 0:
            break
        j = a + int(np.argmax(raw[a:b]))
        pos = float(j)
        if 0 < j < len(raw) - 1 and raw[j] > 0:
            # log-parabola sub-bin peak (a single-partial tone
            # must not be quantized to the bin grid)
            la, lb, lc = np.log(raw[j - 1:j + 2] + 1e-30)
            den = la - 2 * lb + lc
            if den < 0:
                pos = j + min(max(0.5 * (la - lc) / den, -0.5), 0.5)
        est.append((raw[j], pos / h))
    if not est:
        return f0
    wmax = max(w for w, _ in est)
    # only STRONG partials vote (>= -60 dB of the strongest): a
    # pure tone has one real partial, and letting junk windows
    # vote hands the median to sidelobe noise
    strong = [p for w, p in est if w >= 1e-3 * wmax]
    return float(np.median(strong)) * df


def _null_comb(mag, f0, df, tol_bins):
    """Null one voice's refined harmonic comb. The fill sits
    BELOW the contest's -60 dB evidence floor (e45): a filled bin
    must read as uniform silence, or every low candidate harvests
    evidence from the null plateaus. Null WIDE — the dilated
    ridge extends tol_bins past the true peak, and partial drift
    grows with h."""
    out = mag.copy()
    med = min(float(np.median(mag)), 4e-4 * float(mag.max()))
    h = 1
    while True:
        c = h * f0 / df
        if c >= len(out):
            break
        wid = tol_bins + max(3, int(round(0.025 * h * f0 / df)))
        a = int(round(c)) - wid
        out[max(a, 0):a + 2 * wid + 1] = med
        h += 1
    return out


def dyad_pitches(x: np.ndarray, fmin: float = 60.0,
        fmax: float = 2000.0, nharm: int = 5,
        tol_bins: int = 3) -> tuple:
    """Both fundamentals of a two-voice mix, blind: HPS finds the
    stronger voice, its refined harmonic comb is nulled to the
    spectral median, and a second HPS pass reads the survivor.
    Returns (lo_hz, hi_hz). Earned rules: null WIDE (the dilated
    ridge extends tol_bins past the true peak, and partial drift
    grows with h), and refine BEFORE nulling (a semitone-sharp f1
    estimate misaligns every null and poisons the residue).
    Honest limits: octave/unison dyads are invisible (voice 2's
    partials are a subset of voice 1's), and below ~midi 40 a
    0.5 s window gives the fundamental too few cycles to trust."""
    from scipy.ndimage import maximum_filter1d
    m = _mono(x)
    w = m * np.hanning(len(m))
    raw = np.abs(np.fft.rfft(w))
    mag = maximum_filter1d(raw, 2 * tol_bins + 1)
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    df = f[1]
    f1 = _partial_refine(raw,
            f[_hps_core(mag, f, fmin, fmax, nharm,
                    struct_sub=True, raw=raw, tol_bins=tol_bins)],
            df, tol_bins)
    mag2 = _null_comb(mag, f1, df, tol_bins)
    f2 = _partial_refine(raw,
            f[_hps_core(mag2, f, fmin, fmax, nharm,
                    strict_sub=True, raw=raw, tol_bins=tol_bins)],
            df, tol_bins)
    lo, hi = sorted((float(f1), float(f2)))
    return (lo, hi)


def triad_pitches(x: np.ndarray, fmin: float = 60.0,
        fmax: float = 2000.0, nharm: int = 5,
        tol_bins: int = 3) -> tuple:
    """All three fundamentals of a three-voice mix, blind, by
    ITERATED SUBTRACTION (e50): HPS names the strongest voice,
    its refined comb is nulled, the residue names the second,
    both combs are nulled, the twice-cut residue names the last.
    Returns (lo, mid, hi) Hz. Residue passes run strict (no
    donut rescue — null edges mimic contrast, the e44 lesson).
    Contract measured on a systematic pluck-triad suite (e50,
    636 triads): no PAIR among the three voices may be a
    harmonic COINCIDENCE — within ~40 cents of n:1 for n=2..8,
    i.e. intervals {12, 19 (and its 20 penumbra), 24, 28, 31,
    34, 36} — and at most ONE pair may be 16 (5:2 survives a
    single null cut, not two). Shapes passing those rules still
    only measure 92% overall; the VERIFIED subset — shapes
    (i1, i2) that read perfectly across roots 45..62 under the
    structural-witness rescue (e51, _sub_structure) — is
    {(3,3),(3,4),(3,7),(3,8),(3,15),(4,3),(4,4),(4,7),(7,4),
    (7,7),(7,8),(7,9),(7,16),(8,3),(8,8),(8,9),(8,21),(9,4),
    (9,7),(9,8),(9,21),(15,15),(21,8)} — 23 shapes, minor and
    major triads in root position and inversions, diminished
    included. (Under the size-only 0.12 rescue bar this set
    was NINE: true-rescue and phantom size fractions overlap
    at 0.06-0.12, a blind spot structure resolved.) The third
    read is the least defended: it faces a spectrum where
    every collision fell to a null. Compose from the verified
    subset."""
    from scipy.ndimage import maximum_filter1d
    m = _mono(x)
    w = m * np.hanning(len(m))
    raw = np.abs(np.fft.rfft(w))
    mag = maximum_filter1d(raw, 2 * tol_bins + 1)
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    df = f[1]
    f1 = _partial_refine(raw,
            f[_hps_core(mag, f, fmin, fmax, nharm,
                    struct_sub=True, raw=raw,
                    tol_bins=tol_bins)], df, tol_bins)
    mag2 = _null_comb(mag, f1, df, tol_bins)
    f2 = _partial_refine(raw,
            f[_hps_core(mag2, f, fmin, fmax, nharm,
                    strict_sub=True, raw=raw,
                    tol_bins=tol_bins)], df, tol_bins)
    mag3 = _null_comb(mag2, f2, df, tol_bins)
    f3 = _partial_refine(raw,
            f[_hps_core(mag3, f, fmin, fmax, nharm,
                    strict_sub=True, raw=raw,
                    tol_bins=tol_bins)], df, tol_bins)
    return tuple(sorted((float(f1), float(f2), float(f3))))


def pitch_contour(x: np.ndarray, win_s: float = 0.22,
        hop_s: float = 0.05, fmin: float = 60.0,
        fmax: float = 2000.0) -> tuple:
    """Pitch vs time: hps in hopping windows, refined to sub-bin
    by actual partial positions (_partial_refine — a 0.22 s
    window's raw bin is ~70 cents at 110 Hz; the refinement
    divides that by the harmonic count). Returns (times, hz) as
    arrays; times are window CENTERS, so a linear glide reads
    exactly and a plateau's ends smear by win_s/2. Built for e45's
    meend: the ruler that turns 'it bends' into cents.

    Dilation here is +/-1 bin, not hps_pitch's +/-3: dilation is
    a FREQUENCY tolerance, and this window's bins are 2.3x wider
    — at +/-3 bins (13.6 Hz) a low candidate borrows the true
    peak's main lobe at several harmonics at once and a pure
    tone reads at the band edge."""
    from scipy.ndimage import maximum_filter1d
    m = _mono(x)
    n = int(win_s * SR)
    hop = int(hop_s * SR)
    ts, fs = [], []
    for a in range(0, len(m) - n, hop):
        seg = m[a:a + n]
        w = seg * np.hanning(n)
        raw = np.abs(np.fft.rfft(w))
        mag = maximum_filter1d(raw, 3)
        f = np.fft.rfftfreq(n, 1.0 / SR)
        i0 = _hps_core(mag, f, fmin, fmax, 5)
        fs.append(_partial_refine(raw, f[i0], f[1], 2))
        ts.append((a + n / 2) / SR)
    return (np.array(ts), np.array(fs))


def dwell_seconds(ts: np.ndarray, fs: np.ndarray, tonic_hz: float,
        tol_cents: float = 35.0) -> np.ndarray:
    """Contour dwell time per chromatic class relative to a tonic:
    12 floats, seconds spent within tol_cents of each class. Built
    for e46's alap — a raga's note HIERARCHY (which degrees the
    line actually lives on) becomes a measured claim instead of a
    vibe. Frames farther than tol_cents from every class (i.e.
    mid-glide) vote nowhere: a meend is motion, not residence —
    which is also the honest reason this consumes pitch_contour
    output rather than a chroma vector (chroma integrates ENERGY,
    crediting loud glides to whatever bins they cross)."""
    ts = np.asarray(ts, dtype=float)
    fs = np.asarray(fs, dtype=float)
    out = np.zeros(12)
    if len(ts) < 2:
        return out
    dt = float(np.median(np.diff(ts)))
    c = 1200.0 * np.log2(fs / tonic_hz)
    k = np.round(c / 100.0)
    dev = c - 100.0 * k
    for kk, dv in zip(k.astype(int) % 12, dev):
        if abs(dv) <= tol_cents:
            out[kk] += dt
    return out


def ornament_profile(ts: np.ndarray, fs: np.ndarray,
        min_rate: float = 1.0) -> tuple:
    """Oscillation (rate_hz, depth_cents) of a pitch-contour
    segment around its median — the gamak/andolan ruler (e47).
    Rate is the dominant line of the cents-contour spectrum at or
    above min_rate, log-parabola interpolated; depth is half the
    robust peak-to-peak ((p95 - p5) / 2) of the cents contour.
    HONEST LIMIT (measured, e47): the contour under FM is NOT a
    plain moving average — each partial's refined peak sits where
    the oscillation DWELLS (its extremes), so depth attenuation
    is milder than the sinc story (0.95 at 3 Hz and 0.88 at 6 Hz
    with 0.08 s windows on a harmonic-rich source) but still
    real: calibrate depth against a synthetic control of the SAME
    instrument class at the same rate and window. Same-class
    means HARMONIC-RICH — a bare FM sine gives the contour no
    partials to refine against and one glitch per quarter-cycle
    reads as rate-multiplied junk (a 6 Hz ornament measured 24
    Hz). Rate passes through the smoothing untouched."""
    ts = np.asarray(ts, dtype=float)
    fs = np.asarray(fs, dtype=float)
    c = 1200.0 * np.log2(fs / np.median(fs))
    c = c - c.mean()
    dt = float(np.median(np.diff(ts)))
    sp = np.abs(np.fft.rfft(c * np.hanning(len(c))))
    fr = np.fft.rfftfreq(len(c), dt)
    sel = np.where(fr >= min_rate)[0]
    j = int(sel[int(np.argmax(sp[sel]))])
    pos = float(j)
    if 0 < j < len(sp) - 1:
        la, lb, lc = np.log(sp[j - 1:j + 2] + 1e-30)
        den = la - 2 * lb + lc
        if den < 0:
            pos = j + min(max(0.5 * (la - lc) / den, -0.5), 0.5)
    rate = pos * float(fr[1])
    depth = float((np.percentile(c, 95) - np.percentile(c, 5)) / 2)
    return (rate, depth)


def beat_profile(x: np.ndarray, lo: float, hi: float,
        win_s: float = 0.05, trend_s: float = 1.5,
        min_rate: float = 0.25, max_rate: float = 5.0) -> tuple:
    """Amplitude-domain sibling of ornament_profile (e48):
    (rate_hz, depth_db) of the slow beating that rides one band's
    envelope. The envelope is taken in LOG domain and DETRENDED
    (moving mean over trend_s) before its spectrum is read —
    lesson earned: a decaying note's envelope is a ramp whose
    low-frequency energy otherwise wins the contest at the same
    ~0.3 Hz for ANY signal, beating or not (measured: a beatless
    single-pol pluck read an identical 'beat' to a beating one
    until the trend was removed; after detrending, true beats
    show 6-9 dB depth where the beatless floor reads under 3).
    Depth is the robust half peak-to-peak ripple in dB."""
    env = band_env(x, lo, hi, win_s)
    le = np.log(env + 1e-12)
    # e72: clamp the detrend to half the window — a trend_s
    # longer than the signal collapsed the moving-mean slice to
    # an empty/short array and crashed on sub-second windows.
    k = max(min(int(trend_s / win_s) | 1,
            (len(le) // 2) | 1), 3)
    pad = np.concatenate([le[:k][::-1], le, le[-k:][::-1]])
    trend = np.convolve(pad, np.ones(k) / k, "same")[k:-k]
    c = le - trend
    sp = np.abs(np.fft.rfft(c * np.hanning(len(c))))
    fr = np.fft.rfftfreq(len(c), win_s)
    sel = np.where((fr >= min_rate) & (fr <= max_rate))[0]
    j = int(sel[int(np.argmax(sp[sel]))])
    depth_db = 20.0 / np.log(10.0) \
        * (np.percentile(c, 95) - np.percentile(c, 5)) / 2.0
    return (float(fr[j]), float(depth_db))


def centroid_hz(x: np.ndarray) -> float:
    """Spectral centroid, POWER-weighted. Earned rule: magnitude
    weighting lets thousands of tiny high bins outvote three loud
    low ones (session 33: drum centroid 62 vs 1224 Hz was the
    honest depth claim)."""
    m = _mono(x)
    p = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    return float((f * p).sum() / (p.sum() + 1e-12))


def mode_freqs(x: np.ndarray, k: int = 6, fmin: float = 40.0,
        fmax: float = 2000.0, rel: float = 0.02,
        merge: float = 0.0) -> np.ndarray:
    """First k modal peaks of a struck resonator (e55): local
    maxima of the full-signal power spectrum within [fmin, fmax]
    that clear rel * the band's strongest peak, parabolically
    refined, strongest k kept, returned sorted by FREQUENCY.
    The whole-signal FFT is the right window for modes — a ring
    that lasts the file puts each mode in its own bin cluster;
    short windows smear neighbours (the (2,1)/(0,2) membrane
    pair sits 7% apart).

    merge > 0 fuses peaks closer than that relative gap into
    their power-weighted center BEFORE the k-strongest cut.
    Earned on the staircase disc: the cartesian boundary splits
    each degenerate membrane pair a few % apart, and a stack
    fit fed both halves reads one continuum mode as two. A link
    only forms between peaks within 20 dB of each other — a
    carpet of tiny peaks must not chain two real modes into one
    blob (it silently ate a drum's 3rd harmonic in one pickup
    and not the other, e55)."""
    m = _mono(x)
    p = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    lo, hi = np.searchsorted(f, (fmin, fmax))
    band = p[lo:hi]
    bar = rel * band.max()
    peaks = []
    for i in range(2, len(band) - 2):
        if band[i] >= bar and band[i] == band[i - 2:i + 3].max():
            a, b, c = np.log(band[i - 1:i + 2] + 1e-24)
            off = 0.5 * (a - c) / (a - 2 * b + c + 1e-24)
            peaks.append((band[i], f[lo + i] + off * (f[1] - f[0])))
    if merge > 0.0 and peaks:
        byf = sorted((fq, pw) for pw, fq in peaks)
        fused = [[byf[0][0], byf[0][1], byf[0][1]]]
        for fq, pw in byf[1:]:
            f0, p0, pm = fused[-1]
            if fq <= f0 * (1.0 + merge) \
                    and max(pw, pm) <= 100.0 * min(pw, pm):
                fused[-1] = [(f0 * p0 + fq * pw) / (p0 + pw),
                        p0 + pw, max(pm, pw)]
            else:
                fused.append([fq, pw, pw])
        peaks = [(pw, fq) for fq, pw, _ in fused]
    peaks.sort(reverse=True)
    return np.array(sorted(fq for _, fq in peaks[:k]))


def mode_misfit(freqs, f0lo: float, f0hi: float,
        max_int: int = 16):
    """(misfit_cents, f0, ints): how far a set of measured mode
    frequencies sits from the best integer stack f_k = n_k * f0,
    searched over f0 in [f0lo, f0hi] — commensurability, the
    honest form of 'did the loading harmonize the drum' (e55).
    Integers must be DISTINCT (two modes on one tooth is not a
    stack). Operates on FREQUENCIES, not spectral power, because
    a power-weighted comb metric failed the same session it was
    born: over a loaded membrane's dense mode forest a +/-3%
    8-harmonic comb catches ~28% of any spectrum by coverage
    alone, and its verdict FLIPPED with readout convention
    (velocity weighs mode k by k^2 in power) — a ruler that
    answers to the pickup instead of the drum. Mode frequencies
    do not move when the readout changes; only their weights do.
    Keep the caller's f0lo honest: f0 far below the lowest mode
    fits anything (every real gets an integer within half a
    tooth), so anchor f0lo to lowest/4 or better."""
    freqs = np.asarray(freqs, dtype=float)
    best = (1e9, f0lo, ())
    for f0 in np.exp(np.linspace(np.log(f0lo), np.log(f0hi),
            1200)):
        r = freqs / f0
        n = np.clip(np.round(r), 1, max_int)
        if len(set(n.tolist())) < len(n):
            continue
        dev = float(np.mean(np.abs(1200 * np.log2(r / n))))
        if dev < best[0]:
            best = (dev, float(f0), tuple(int(v) for v in n))
    # canonicalize the f0 degeneracy: (4,6,8,10) at f0 is the
    # same fit as (2,3,4,5) at 2*f0 — report the smallest stack
    from math import gcd
    from functools import reduce
    if best[2]:
        g = reduce(gcd, best[2])
        if g > 1:
            best = (best[0], best[1] * g,
                    tuple(v // g for v in best[2]))
    return best


def partial_track(x: np.ndarray, lo: float, hi: float,
        win_s: float = 0.09, hop_s: float = 0.02):
    """(ts, fs): the strongest spectral peak inside [lo, hi] Hz
    per window — ONE partial followed through time (e56). Born
    for the bayan glide, where pitch_contour's HPS is the wrong
    tool: a drum's stack is too sparse and its fundamental too
    low for harmonic voting, but the gliding MODE itself is loud
    and alone in its band. Windows are hann, peaks parabolically
    refined; a window whose band peak is under 1e-6 of its
    global peak reports NaN (silence has no partial). Keep the
    band tight enough to exclude the mode's neighbours — the
    tracker follows the strongest thing you let it see."""
    m = _mono(x)
    w = int(win_s * SR)
    h = int(hop_s * SR)
    hann = np.hanning(w)
    ts, fs = [], []
    for a in range(0, len(m) - w, h):
        seg = m[a:a + w] * hann
        p = np.abs(np.fft.rfft(seg)) ** 2
        f = np.fft.rfftfreq(w, 1.0 / SR)
        bi, bj = np.searchsorted(f, (lo, hi))
        band = p[bi:bj]
        ts.append((a + w / 2) / SR)
        if band.max() < 1e-6 * p.max():
            fs.append(float("nan"))
            continue
        i = int(np.argmax(band))
        j = bi + i
        if 0 < j < len(p) - 1:
            a3, b3, c3 = np.log(p[j - 1:j + 2] + 1e-24)
            off = 0.5 * (a3 - c3) / (a3 - 2 * b3 + c3 + 1e-24)
        else:
            off = 0.0
        fs.append(float(f[j] + off * (f[1] - f[0])))
    return np.array(ts), np.array(fs)


def crest_db(x: np.ndarray) -> float:
    """Crest factor (peak over RMS) in dB — transients are PEAKS,
    not energy sums (e19). Over a ramping gesture, window the
    steady region first or you measure the ramp (e34)."""
    m = _mono(x)
    rms = float(np.sqrt(np.mean(m ** 2)) + 1e-12)
    return 20.0 * np.log10(float(np.max(np.abs(m))) / rms + 1e-12)


def band_density(x: np.ndarray, lo: float, hi: float) -> float:
    """Mean power per sample within [lo, hi] Hz. Earned rule
    (session 35): summed rfft power scales with segment LENGTH —
    a 10 s window against a 7 s one inflated a ratio 0.35 -> 0.71.
    Density (divide by N) compares unequal windows honestly."""
    m = _mono(x)
    p = np.abs(np.fft.rfft(m)) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    sel = (f >= lo) & (f < hi)
    return float(p[sel].sum() / len(m))


def width_corr(x: np.ndarray, above_hz: float = 250.0) -> float:
    """L/R correlation ABOVE ~250 Hz (full-band correlation is
    bass-dominated). +1 mono, 0 decorrelated. Judge the target per
    material."""
    sos = butter(4, above_hz, btype="high", fs=SR, output="sos")
    y = sosfilt(sos, x, axis=0)
    c = np.corrcoef(y[:, 0], y[:, 1])[0, 1]
    return float(c)


def accent_profile(x: np.ndarray, times, attack_s: float = 0.04
        ) -> np.ndarray:
    """Per-onset accent: what the strike ADDS — attack-window
    peak |x| minus the pre-onset window's peak, floored at zero.
    Raw attack peak was tried first (e52) and inherits the
    PRESENCE of any note still ringing through the slot: a
    0.9-amp melody note's tail put a near-melody-size peak in
    every chikari slot it crossed, and the measured hierarchy
    shrank to x1.4 no matter how quiet the chikari got. The
    difference of adjacent peaks cancels the ring (it spans both
    windows at nearly equal level, t60 decay excepted) and keeps
    the strike. Returns one value per time, in order. Measure on
    the bus that carries the accents; compare CLASSES of onsets
    (melody vs filler, downbeat vs upbeat), not absolute
    numbers."""
    m = _mono(x)
    out = []
    n = int(attack_s * SR)
    for t in times:
        a = int(t * SR)
        b = min(a + n, len(m))
        post = float(np.abs(m[a:b]).max()) if b > a else 0.0
        pre = float(np.abs(m[max(a - n, 0):a]).max()) if a > 0 \
            else 0.0
        out.append(max(post - pre, 0.0))
    return np.array(out)


def rms_db(x: np.ndarray) -> float:
    return 20.0 * np.log10(float(np.sqrt(np.mean(_mono(x) ** 2))) + 1e-12)


def rms_contour(x: np.ndarray, nwin: int = 8) -> list:
    """Windowed RMS in dB — the stationarity / hole-and-spike
    ruler (session 35's handover check)."""
    m = _mono(x)
    edges = np.linspace(0, len(m), nwin + 1).astype(int)
    return [20.0 * np.log10(float(np.sqrt(np.mean(
            m[a:b] ** 2))) + 1e-12) for a, b in zip(edges, edges[1:])]


def onset_env(x: np.ndarray, lo: float = 1100.0, hi: float = 3500.0,
        smooth_hz: float = 40.0) -> np.ndarray:
    """Rectified band-limited envelope for pulse-rate reading.
    Earned rules (e34): read rate where pulses stay DISTINCT — the
    high band, whose modes decay fast — and smooth only enough to
    merge waveform cycles, not adjacent pulses."""
    band = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    e = np.abs(sosfilt(band, _mono(x)))
    lp = butter(2, smooth_hz, btype="low", fs=SR, output="sos")
    return sosfiltfilt(lp, e)


def pulse_rate(x: np.ndarray, rate_lo: float, rate_hi: float,
        lo: float = 1100.0, hi: float = 3500.0) -> float:
    """Dominant pulse rate (Hz) via envelope autocorrelation,
    searched only within [rate_lo, rate_hi]. Earned rules (e34):
    a long-ringing low mode makes autocorr read subharmonics
    (23/s -> 11/s), so the envelope comes from the fast-decaying
    band; and the envelope is high-passed at rate_lo/2 so slow
    undulation cannot bias long lags."""
    env = onset_env(x, lo, hi)
    hp = butter(2, max(rate_lo / 2.0, 0.5), btype="high", fs=SR,
            output="sos")
    env = sosfiltfilt(hp, env)
    env = env - env.mean()
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lag_lo = int(SR / rate_hi)
    lag_hi = min(int(SR / rate_lo), len(ac) - 1)
    if lag_hi <= lag_lo:
        return float("nan")
    k = lag_lo + int(np.argmax(ac[lag_lo:lag_hi]))
    return SR / float(k)


def flatness(x: np.ndarray, lo: float = 60.0, hi: float = 2000.0) -> float:
    """Spectral flatness (Wiener entropy: geometric over arithmetic
    mean of power), computed PER OCTAVE BAND over [lo, hi] and
    averaged. ~1 = noise, orders of magnitude lower = tonal comb.
    Born in e38 to measure TONALIZATION (noise in, chord out)
    without smuggling in which pitches — that is a separate
    (chroma) claim. Earned rule, same cycle: a single wide-band
    flatness confounds TILT with tonality — steeply low-tilted
    noise (thunder) measured 'tonal' because most of the window's
    bins were merely empty. Per-octave, tilted noise is still
    locally flat; only a comb is spiky inside its own octave.
    And the octave average is POWER-weighted (the centroid lesson
    again): unweighted, the quiet noise-floor octaves above the
    music outvote the loud combed ones."""
    m = _mono(x)
    p = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    vals, wts = [], []
    edge = lo
    while edge < hi:
        sel = (f >= edge) & (f < min(edge * 2.0, hi))
        if sel.sum() >= 32:
            pb = p[sel]
            gm = np.exp(np.mean(np.log(pb + 1e-30)))
            vals.append(gm / (np.mean(pb) + 1e-30))
            wts.append(float(pb.sum()))
        edge *= 2.0
    if not vals:
        return 1.0
    return float(np.average(vals, weights=wts))


def chroma(x: np.ndarray, lo: float = 60.0, hi: float = 2000.0) -> np.ndarray:
    """Fold spectral POWER into 12 pitch classes (C=0..B=11) over
    [lo, hi], normalized to sum 1. Remember e35: harmonic leakage
    means honest chroma claims are RELATIVE (top-k membership,
    pole comparisons), never absolute floors."""
    m = _mono(x)
    p = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    sel = (f >= lo) & (f <= hi)
    cls = np.mod(np.round(69.0 + 12.0 * np.log2(
            np.maximum(f[sel], 1e-6) / 440.0)), 12).astype(int)
    out = np.zeros(12)
    np.add.at(out, cls, p[sel])
    return out / (out.sum() + 1e-30)


def flux_series(x: np.ndarray, frame: int = 1024,
        hop: int = 256) -> tuple:
    """(flux, dt_s): the spectral-flux TIME SERIES — half-wave-
    rectified frame-to-frame magnitude increase, one value per
    hop. This is the raw material under both flux_spectrum
    (stationary rhythm: read the rate as a line) and any
    self-similarity measurement (transient rhythm: a tihai's
    three phrases correlate at exactly their lag, e76). Public
    since e76 so experiments can slice and correlate it
    directly instead of re-deriving the STFT."""
    m = _mono(x)
    n_fr = 1 + (len(m) - frame) // hop
    idx = np.arange(frame)[None, :] \
        + hop * np.arange(n_fr)[:, None]
    w = np.hanning(frame)
    mags = np.abs(np.fft.rfft(m[idx] * w, axis=1))
    fl = np.sum(np.maximum(mags[1:] - mags[:-1], 0.0), axis=1)
    return fl, hop / SR


def flux_spectrum(x: np.ndarray, frame: int = 1024,
        hop: int = 256) -> tuple:
    """(freqs_hz, magnitude) of the spectral-flux series — the
    RHYTHM SPECTRUM. Born e75: a jhala strum at 8.3 strokes/s
    defeats onset counting from both sides (masking merges
    strokes in the mix; the jawari buzz reads as extra strokes
    on a solo bus) and its amplitude envelope barely ripples
    (ringing tails fill the 120 ms gaps). But the PERIODICITY
    of the flux survives all of it: the stroke rate stands as
    a clear line in the flux spectrum (measured 8.36 Hz against
    a written 8.333, with its octave beside it) even when only
    ~75% of individual strokes are findable. Count events when
    the texture is sparse; read this spectrum when it is dense.
    The mean is removed; window the series before the FFT."""
    fl, dt = flux_series(x, frame, hop)
    fl = fl - fl.mean()
    sp = np.abs(np.fft.rfft(fl * np.hanning(len(fl))))
    fr = np.fft.rfftfreq(len(fl), dt)
    return fr, sp


def onset_times(x: np.ndarray, frame: int = 1024, hop: int = 256,
        k: float = 3.0, min_sep: float = 0.08,
        floor_frac: float = 0.15) -> np.ndarray:
    """Onset times (s) via spectral flux — the half-wave-rectified
    frame-to-frame magnitude increase, peak-picked above a LOCAL
    adaptive threshold (median + k*MAD over a sliding ~1 s
    neighborhood; a global threshold misses soft strikes under
    loud ones). Promised in e36, born in e39, where change
    ringing needed its 360 strikes counted and ordered.
    Earned rule, same cycle: in a rest the local median AND MAD
    collapse together and the threshold chases noise — every ghost
    fired inside the handstroke gaps. The floor (floor_frac of the
    flux's own 90th percentile) keeps silence from becoming
    hypersensitive. Absolute times carry a ~frame/2 latency —
    compare onsets to onsets, or allow that offset when matching
    design times."""
    m = _mono(x)
    n_fr = 1 + (len(m) - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(n_fr)[:, None]
    w = np.hanning(frame)
    mags = np.abs(np.fft.rfft(m[idx] * w, axis=1))
    flux = np.sum(np.maximum(mags[1:] - mags[:-1], 0.0), axis=1)
    flux = np.concatenate([[0.0], flux])
    half = max(int(0.5 * SR / hop), 8)
    floor = floor_frac * np.percentile(flux, 90)
    thr = np.empty_like(flux)
    for i in range(len(flux)):
        seg = flux[max(0, i - half):i + half]
        med = np.median(seg)
        mad = np.median(np.abs(seg - med)) + 1e-12
        thr[i] = max(med + k * mad, floor)
    sep = max(int(min_sep * SR / hop), 1)
    hits = []
    for i in range(1, len(flux) - 1):
        if flux[i] > thr[i] and flux[i] == flux[
                max(0, i - sep):i + sep + 1].max():
            if not hits or i - hits[-1] >= sep:
                hits.append(i)
    return np.array(hits) * hop / SR


def transcribe(x: np.ndarray, min_sep: float = 0.08,
        fmin: float = 80.0, fmax: float = 1500.0,
        max_win: float = 0.5) -> list:
    """MONOPHONIC transcription: onset_times for the whens,
    hps_pitch over each inter-onset window for the whats. Returns
    [(onset_s, midi_float)] — round midi yourself, and remember
    onset latency (see onset_times). Born in e40, where the
    ouroboros canon had to give its tune back from the render.
    Polyphony is a different animal — do not point this at it."""
    m = _mono(x)
    ts = onset_times(x, min_sep=min_sep)
    out = []
    for i, t in enumerate(ts):
        a = int((t + 0.015) * SR)
        end = ts[i + 1] - 0.01 if i + 1 < len(ts) else t + max_win
        b = int(min(end, t + max_win) * SR)
        b = max(b, a + int(0.05 * SR))
        f = hps_pitch(m[a:min(b, len(m))], fmin, fmax)
        out.append((float(t), 69.0 + 12.0 * np.log2(f / 440.0)))
    return out


def band_env(x: np.ndarray, lo: float = 1500.0, hi: float = 6000.0,
        win_s: float = 0.1) -> np.ndarray:
    """Coarse envelope of one band: mean |bandpassed| in win_s bins.
    The primitive under env_peak_s, exposed because RATIOS of two
    band envelopes (same bins, common-mode attack cancelling) are
    how you ask 'what did the process ADD, and when?'"""
    sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    e = np.abs(sosfilt(sos, _mono(x)))
    win = int(win_s * SR)
    return np.array([e[k:k + win].mean()
            for k in range(0, len(e) - win, win)])


def env_peak_s(x: np.ndarray, lo: float = 1500.0, hi: float = 6000.0,
        win_s: float = 0.1) -> float:
    """When does this band's envelope peak? The bloom clock (born
    ad hoc in e41, promoted for e42): a plucked string's highs
    normally peak at t=0 and decay; a jawari bloom peaks LATE.
    Coarse on purpose — win_s bins, so the answer is honest about
    its resolution."""
    return float(np.argmax(band_env(x, lo, hi, win_s))) * win_s


def chroma_uniform(x: np.ndarray, nwin: int = 8,
        lo: float = 60.0, hi: float = 2000.0) -> np.ndarray:
    """Time-uniform chroma: mean of overlapping short-window
    chromas, so every second counts equally. Whole-signal hann
    chroma (plain `chroma`) weights a MOVING line by where the
    window bump lands — e61 measured the same jor crowning F/E
    as a single pass and D when doubled, because the phrase's
    holds sat under different parts of the bump. Stationary
    buses never see this; melodies always will. Promoted after
    its third use (e61 mix, e62 mix, e63)."""
    m = _mono(x)
    W = len(m) // (nwin // 2 + 1)
    acc = np.zeros(12)
    for a in range(0, len(m) - W + 1, W // 2):
        acc += chroma(m[a:a + W], lo, hi)
    return acc / (acc.sum() + 1e-30)


def sympathy_forecast(f0s: np.ndarray, frame_s: float, bank,
        nh_drive: int = 6, nh_string: int = 4,
        tol_cents: float = 15.0, drive_w=None, amp=None,
        integrate: bool = False, cascade: float = 0.0,
        node: float = 0.0, tap: float = 0.0,
        vel: bool = False, comp=None,
        comp_fref: float = 200.0) -> np.ndarray:
    """Score -> halo forward model (e62's lesson made
    predictive): a sympathetic bank hears the harmonic LATTICE,
    not the score — a string lights when ANY driver harmonic
    lands on ANY of its modes, whether the note is sung, crossed
    by a glide, or a fifth away (e62: the 'dark control' lit
    x45 through its h2 on the sung note's h3).

    f0s: driver fundamental per frame in Hz (NaN/0 = silent),
    frame_s seconds per frame. Returns one predicted drive score
    per bank string: sum over frames and harmonic pairs (n, m)
    of power-weighted coincidence (drive_w[n]/m)^2 * amp^2 where
    |n*f0 - m*fs| <= tol_cents. Tolerance is the measured
    coincidence width (e62's lattice hits sat 2-3c apart).

    drive_w: driver harmonic amplitude profile, one weight per
    harmonic (overrides nh_drive). MEASURE it from one steady
    note — the flat 1/n default put the e62 Pa string 5th when
    it measured 1st, because fdbow at xb=0.12 carries its
    fundamental at 0.19 of h2 (e61 saw this: strongest five
    modes are harmonics 2..6).

    amp: per-frame driver amplitude (e.g. the vb envelope).

    integrate: model the bank as a lossless INTEGRATOR — for
    t60 >> phrase length, a string keeps everything it is fed,
    so whole-phrase rms rewards EARLY excitation (e62's Ga
    string, sung 1.6 s but lit last, measured darkest in
    whole-phrase rms). Returns sqrt(mean(cumsum(power))) —
    the rms of the predicted stored-energy trajectory.

    cascade: one-pass BRIDGE model (e63's correction of e62:
    fifth-family recruitment is the jawari bridge, not the bow
    — jawari off, same bowed driver: Pa falls 1.00 -> 0.21 and
    Sa tops the bank). Each string's stored energy re-radiates
    its harmonic stack (1/n) through the bridge and feeds every
    other string by the same coincidence rule, scaled by this
    one coupling constant (0 = bridge silent). Calibrate it on
    ONE steady-note ledger, then freeze it for phrases.

    node/tap/vel: the e64 "v2" receiver weights, every factor
    DERIVED, none fitted. fdsym injects force at x = node and
    reads velocity at x = tap, so mode m couples through
    |sin(node*m*pi)| and speaks through |sin(tap*m*pi)| — at
    fdsym's defaults (node 0.93, tap 0.12) the fundamental
    couples at 0.22 while m=4 couples at 0.78: the bank is
    BUILT to receive and speak through its upper modes.
    vel=True weights readout by mode frequency (velocity, what
    the tap actually measures) instead of the 1/m displacement
    guess. Together these lifted the jawari steady ledger from
    0.76 to 0.88 and the e63 phrase from 0.52 to 0.81 spearman
    with zero free parameters. Certified residual (e62 phrase):
    the sung-late F and lattice-lit C swap extreme ranks — the
    lattice hit outdraws the sung note; open anomaly.

    comp: the e68 "v3" jawari output map — (scale, K, q, p).
    The barrier is a per-string compressor whose variable is
    DISPLACEMENT, not speed: at equal tap-velocity rms a lower
    string swings further (u ~ v/omega), engages the contact
    earlier, and saturates harder. Applied after integration:
    feed = scale*out, x = feed*(comp_fref/fs), out becomes
    feed*(1+(x/K)^q)^(-p). Fit on e64's flat-fed phrase at four
    drive levels (identity below the knee, gain <= 0.21 on the
    overfed sung strings above it). Two lessons carried in the
    form: (1) a frequency-blind compressor CANNOT move a rank —
    any shared monotone map preserves feed order, so the entire
    rank repair lives in the omega-scaling; (2) the law is a
    floor, not a crown: it rescues ledgers the linear model
    inverts (overfed phrases: -0.07 -> 0.81) at the cost of the
    ones the linear model nailed (sparse phrases: 0.98 -> 0.52).
    Use v2 (comp=None) when the phrase feeds stay light; use v3
    when the phrase sings the bank's own strings hard.

    A ranking tool: claims should be rank agreement and
    targeted bright/dark calls, never absolute levels."""
    f0s = np.asarray(f0s, dtype=float)
    ok = np.isfinite(f0s) & (f0s > 0)
    if drive_w is None:
        drive_w = 1.0 / np.arange(1, nh_drive + 1)
    drive_w = np.asarray(drive_w, dtype=float)
    a2 = np.ones(len(f0s)) if amp is None \
        else np.asarray(amp, dtype=float) ** 2
    fref = float(min(bank))
    nb = len(bank)
    rates = np.zeros((nb, len(f0s)))
    for si, fs in enumerate(bank):
        for n in range(1, len(drive_w) + 1):
            for m in range(1, nh_string + 1):
                dev = np.abs(1200.0 * np.log2(
                        np.maximum(n * f0s, 1e-9) / (m * fs)))
                hit = ok & (dev <= tol_cents)
                w = drive_w[n - 1] * (m * fs / fref if vel
                        else 1.0 / m)
                if node > 0.0:
                    w *= abs(np.sin(node * m * np.pi))
                if tap > 0.0:
                    w *= abs(np.sin(tap * m * np.pi))
                rates[si, hit] += w ** 2 * a2[hit]
    if cascade > 0.0:
        E1 = np.cumsum(rates, axis=1) * frame_s
        coup = np.zeros((nb, nb))
        for sj, fj in enumerate(bank):        # radiator
            for si, fs in enumerate(bank):    # receiver
                if si == sj:
                    continue
                for n in range(1, 7):
                    for m in range(1, nh_string + 1):
                        dc = abs(1200.0 * np.log2(
                                (n * fj) / (m * fs)))
                        if dc <= tol_cents:
                            coup[sj, si] += (1.0 / (n * m)) ** 2
        rates = rates + cascade * (coup.T @ E1)
    if integrate:
        out = np.sqrt(np.cumsum(rates, axis=1).mean(axis=1)
                * frame_s)
    else:
        out = rates.sum(axis=1) * frame_s
    if comp is not None:
        sc, K, q, p = comp
        feed = sc * out
        x = feed * (comp_fref / np.asarray(bank, dtype=float))
        out = feed * (1.0 + (x / K) ** q) ** (-p)
    return out


def lock_ratio(x: np.ndarray, f0: float) -> float:
    """Odd/even harmonic ratio — the honest bowed-string regime
    detector (e64). A locked Helmholtz tone carries odd AND
    even harmonics (ratio ~0.4-3 for fdbow); the double-slip
    octave branch is EVEN-ONLY (ratio ~0). Born from a broken
    classifier: 'tallest spectral line = 2*f0' reads a bright
    LOCKED tone (h2 tops fdbow's certified profile) as octave
    — regime is periodicity, not spectral tilt. Compares the
    peak amplitude in ±5% bands around {1,3,5}*f0 vs
    {2,4,6}*f0."""
    m = _mono(x)
    X = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    f = np.fft.rfftfreq(len(m), 1.0 / SR)

    def a(ff):
        s = (f >= ff * 0.95) & (f <= ff * 1.05)
        return float(X[s].max()) if s.any() else 0.0

    odd = a(f0) + a(3 * f0) + a(5 * f0)
    even = a(2 * f0) + a(4 * f0) + a(6 * f0)
    return odd / max(even, 1e-9)


def fund_presence(x: np.ndarray, f0: float,
        fmax: float = 2000.0) -> float:
    """Fundamental presence: peak amplitude in a ±5% band around
    f0 over the strongest line below fmax. THE honest detector
    for the bowed string's fundamental-less multiphonic (born
    e66: a slammed attack plays lines at {2,5,7}*f0 at healthy
    rms for an entire take — level rulers never see it, the
    pitch tracker reads the octave, and lock_ratio is fooled
    because a strong 5*f0 lands in its odd set). Calibrated
    gate 0.05 (e67): the failure it guards against reads
    0.000-0.014, true locked tones 0.09-0.19 — the log-midpoint,
    not a round number. Pair it with lock_ratio: each covers the
    other's blind spot, and e69 leaned on the asymmetry — a
    cracked take read lock_ratio 10-66 (odd-rich, "healthy")
    while fund_presence told the truth."""
    m = _mono(x)
    X = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    s = (f >= f0 * 0.95) & (f <= f0 * 1.05)
    if not s.any():
        return 0.0
    return float(X[s].max() / (X[f < fmax].max() + 1e-12))


def partial_freq(x: np.ndarray, lo: float, hi: float) -> float:
    """Frequency of the strongest spectral line in [lo, hi], by
    parabolic interpolation of the log-magnitude peak. Born e71:
    beat rates between two voices' coinciding partials sit near
    0.2-0.6 Hz, and predicting them as 3*hps_pitch(A) -
    4*hps_pitch(B) fails — hps_pitch's ~0.5c granularity is
    ~0.4 Hz of error at 440 Hz, twice the signal. Reading each
    voice's OWN line directly (5+ s window, parabolic vertex on
    three log bins) resolves ~0.01 Hz, and closed the chain:
    three fourths predicted 0.23/0.60/0.63 Hz from own-bus lines
    and measured 0.23/0.61/0.61 in the mix. The score arithmetic
    3*hz(hi)-4*hz(lo) promised 0.50 Hz where the strings sounded
    0.23 — friction flattening moves the lines, so predict from
    the sounded lines, not the written notes."""
    m = _mono(x)
    X = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    s = np.where((f >= lo) & (f <= hi))[0]
    if len(s) < 3:
        return 0.0
    k = int(s[int(np.argmax(X[s]))])
    if k <= 0 or k >= len(X) - 1:
        return float(f[k])
    a = np.log(X[k - 1] + 1e-12)
    b = np.log(X[k] + 1e-12)
    c = np.log(X[k + 1] + 1e-12)
    denom = a - 2.0 * b + c
    d = 0.0 if abs(denom) < 1e-12 else 0.5 * (a - c) / denom
    # e73: the vertex offset is only meaningful within half a
    # bin — on a flat/noisy spectrum the denominator shrinks and
    # d exploded, returning frequencies far OUTSIDE the search
    # band (a "line" at 372 Hz from a 434-447 Hz search). Clamp,
    # so garbage input yields an in-band number a sanity check
    # can catch, never a confident absurdity.
    d = float(np.clip(d, -0.5, 0.5))
    return float((k + d) * SR / len(m))


def decay_t60(x: np.ndarray, lo: float, hi: float,
        win_s: float = 0.03, hop_s: float = 0.005,
        drop: float = 25.0) -> float:
    """Band decay time to -60 dB: linear fit on the top `drop` dB
    of the band's short-window FFT power envelope, from the
    envelope peak. Memoryless ON PURPOSE (the khali filter lesson
    of e55, re-earned in e59): a narrowband recursive filter
    rings for ~1/bandwidth, and filtfilt squares that — an
    order-4 band 30 Hz wide reads ~140 ms for ANY faster decay,
    measuring itself, and the verdict barely moves as the true
    t60 changes (constant verdict under changing input = broken
    ruler). Windowed FFT power has no feedback; its floor is the
    window length, stated rather than hidden.

    If the band holds no bin at this window length (bins are
    1/win_s wide), the single nearest bin to the band center is
    used — an empty selection otherwise returns silence and fits
    the noise floor. Returns nan when fewer than 4 envelope
    points span the drop: a decay faster than ~win_s is honestly
    unmeasurable at this resolution, not zero."""
    m = _mono(x)
    w = int(win_s * SR)
    hop = int(hop_s * SR)
    hann = np.hanning(w)
    f = np.fft.rfftfreq(w, 1.0 / SR)
    sel = (f >= lo) & (f <= hi)
    if not sel.any():
        sel = np.zeros(len(f), dtype=bool)
        sel[int(np.argmin(np.abs(f - (lo + hi) / 2)))] = True
    env, tt = [], []
    for a in range(0, len(m) - w, hop):
        p = np.abs(np.fft.rfft(m[a:a + w] * hann)) ** 2
        env.append(np.sqrt(p[sel].sum()))
        tt.append((a + w / 2) / SR)
    env = np.asarray(env)
    tt = np.asarray(tt)
    ip = int(np.argmax(env))
    db = 20 * np.log10(env + 1e-15)
    s = np.arange(ip, len(db))[db[ip:] > db[ip] - drop]
    if len(s) < 4:
        return float("nan")
    return float(-60.0 / np.polyfit(tt[s], db[s], 1)[0])


def seam_rank(x: np.ndarray) -> float:
    """Numeric twin of loam.seam_report: percentile rank of the
    wrap step in the adjacent-delta distribution. <= ~0.999 is
    clickless; a genuine click sits beyond the distribution max."""
    step = float(np.max(np.abs(x[0] - x[-1])))
    dd = np.abs(np.diff(x, axis=0))
    return float((dd < step).mean())


def report(x: np.ndarray, name: str = "bus") -> dict:
    """The standard card: the numbers every render should face."""
    d = {
        "name": name,
        "peak": float(np.max(np.abs(x))),
        "rms_db": rms_db(x),
        "crest_db": crest_db(x),
        "centroid_hz": centroid_hz(x),
        "seam_rank": seam_rank(x),
    }
    if x.ndim == 2:
        d["width_corr"] = width_corr(x)
    print(f"[{name}] peak={d['peak']:.3f} rms={d['rms_db']:.1f}dB "
          f"crest={d['crest_db']:.1f}dB centroid={d['centroid_hz']:.0f}Hz "
          f"seam=p{100 * d['seam_rank']:.1f}"
          + (f" width={d['width_corr']:+.3f}" if x.ndim == 2 else ""))
    return d
