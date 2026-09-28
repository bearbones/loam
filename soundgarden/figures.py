"""Figures for docs/soundgarden-abstract-space.md: python3 -m soundgarden.figures [--out DIR]

Spectrograms of one starter through each representation, so the trade-offs are
visible rather than asserted: the original render, its sinusoidal + residual
resynthesis (B), Griffin-Lim from its own descriptor grid (the decoder's loss
alone), and the learned-latent reconstruction decoded the same way (C).
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from loam import SR
from .describe import describe
from .latent import DEFAULT_DIR, Autoencoder, decode_audio
from .sms import analyze as sms_analyze, synthesize
from .stft import HOP, stft
from .synth import ANCHORS, render

ROOT = Path(__file__).resolve().parents[1]


def panel(ax, audio, title):
    mag = 20 * np.log10(np.abs(stft(audio)).T + 1e-6)
    mag -= mag.max()
    ax.imshow(mag, origin="lower", aspect="auto", vmin=-80, vmax=0, cmap="magma",
              extent=[0, len(audio) / SR, 0, SR / 2 / 1000])
    ax.set_ylim(0, 8)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("s")


def tone_figures(out):
    """C2: tones through the additive decoder, and the two latent walks side by side."""
    from loam import hz
    from loam.modal import BELL, bow
    from loam.pads import VOWELS, formant_amps, padsynth_stereo
    from loam.winds import flute
    from .match import load_wav
    from .tone import DEFAULT_DIR as TONE_DIR, profile, synthesize as additive
    f0 = hz(60)
    sources = [("Flute", flute(f0, 1.2)), ("PADsynth 'ah'", padsynth_stereo(1.0, f0, formant_amps(f0, 48, VOWELS["ah"])).mean(axis=1)),
               ("Bowed bell (inharmonic)", bow(f0, 1.5, BELL))]
    figure, axes = plt.subplots(2, len(sources), figsize=(4.2 * len(sources), 6.4), sharey=True)
    for column, (name, x) in enumerate(sources):
        panel(axes[0, column], x, f"{name}: original")
        panel(axes[1, column], additive(profile(x, f0), seconds=len(x) / SR), "C2 · 64 harmonics + 24 noise bands, additive")
    axes[0, 0].set_ylabel("kHz"); axes[1, 0].set_ylabel("kHz")
    figure.tight_layout()
    figure.savefig(out / "tone-resynthesis.png", dpi=110)
    plt.close(figure)
    print(f"Wrote {out / 'tone-resynthesis.png'}")
    walks = [(DEFAULT_DIR / "walk-decoded.wav", "C · struck-sound latent walk, Griffin-Lim decoder"),
             (TONE_DIR / "walk-additive.wav", "C2 · tone latent walk, additive decoder")]
    if all(path.exists() for path, _ in walks):
        figure, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=False)
        for ax, (path, title) in zip(axes, walks):
            panel(ax, load_wav(path.read_bytes(), seconds=30), title)
            ax.set_ylabel("kHz")
        figure.tight_layout()
        figure.savefig(out / "latent-walks.png", dpi=110)
        plt.close(figure)
        print(f"Wrote {out / 'latent-walks.png'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/soundgarden-abstract-space")
    parser.add_argument("--latent", type=Path, default=DEFAULT_DIR / "model.npz")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    tone_figures(args.out)
    model = Autoencoder.load(args.latent) if args.latent.exists() else None
    for name, vector in [ANCHORS[0], ANCHORS[3]]:
        x = render(vector)
        seconds = len(x) / SR
        grid = np.array(describe(x)["grid"])
        columns = [(x, f"{name}: original render"),
                   (synthesize(sms_analyze(x)), "B · sinusoidal + residual resynthesis"),
                   (decode_audio(grid, seconds), "Griffin-Lim from its own 24×8 grid")]
        if model is not None:
            columns.append((decode_audio(model.decode(model.encode(grid))[0], seconds), "C · latent (6-D) → grid → Griffin-Lim"))
        figure, axes = plt.subplots(1, len(columns), figsize=(4.2 * len(columns), 3.4), sharey=True)
        for ax, (audio, title) in zip(axes, columns):
            panel(ax, audio, title)
        axes[0].set_ylabel("kHz")
        figure.tight_layout()
        path = args.out / f"{name.lower().replace(' ', '-')}-representations.png"
        figure.savefig(path, dpi=110)
        plt.close(figure)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
