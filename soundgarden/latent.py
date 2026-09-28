"""Prototype C: a learned latent space over log-mel grids, in NumPy.

    python3 -m soundgarden.latent --train 1500 --epochs 300   # renders, fits, reports
    python3 -m soundgarden.latent --walk 8                    # latent traversal → WAV

A small autoencoder (192 → 64 → 6 → 64 → 192, tanh hidden layers, Adam) is
trained on descriptor grids of random recipes. The latent is abstract: its six
coordinates have no names. Two decoders are provided, and the difference
between them is the whole story of this approach:

- decode_audio: latent → grid → magnitude spectrogram → Griffin-Lim. This is a
  generator not bound to the resonator, but it hears through an 80 dB mel grid
  with 8 time anchors, so attacks smear and partials blur into bands.
- nearest_recipes: latent → nearest training grids → their recipes, rendered by
  the real synth. Exact audio, but only sounds the resonator can make.

A serious version of this is RAVE (Caillon & Esling 2021): a variational
autoencoder with an adversarial waveform decoder, trained on hours of audio,
which would need torch and a GPU session. The NumPy model here is the smallest
thing that demonstrates the shape of the idea and its costs honestly.
"""
import argparse
from pathlib import Path
import time

import numpy as np

from loam import SR
from .describe import ANCHORS_S, BANDS, TIMES, FLOOR_DB, _BANK, describe
from .stft import HOP, NFFT, frame_times, griffin_lim
from .synth import render, wav_bytes

VERSION = "soundgarden-latent/0"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "render/soundgarden-latent"


def dataset(count, seed=11):
    rng = np.random.default_rng(seed)
    vectors = rng.uniform(.025, .975, (count, 10))
    grids = np.array([describe(render(v.tolist()))["grid"] for v in vectors])
    return grids, vectors


class Autoencoder:
    def __init__(self, sizes=(BANDS * TIMES, 64, 6), seed=0):
        rng = np.random.default_rng(seed)
        dims = list(sizes) + list(sizes[-2::-1])  # 192, 64, 6, 64, 192
        self.params = []
        for a, b in zip(dims[:-1], dims[1:]):
            self.params += [rng.standard_normal((a, b)) * np.sqrt(2 / (a + b)), np.zeros(b)]
        self.mean = np.zeros(sizes[0])
        self.scale = np.ones(sizes[0])
        self.latent = sizes[-1]
        self.low, self.high = -1.0, 0.0  # decode clip; fit() widens it to the data's range

    def _forward(self, x):
        acts = [x]
        h = x
        for i in range(0, len(self.params), 2):
            h = h @ self.params[i] + self.params[i + 1]
            if i // 2 in (0, 2):  # tanh on the two hidden layers only
                h = np.tanh(h)
            acts.append(h)
        return acts

    def encode(self, grids):
        x = (np.atleast_2d(grids) - self.mean) / self.scale
        return self._forward(x)[2]

    def decode(self, z):
        h = np.tanh(np.atleast_2d(z) @ self.params[4] + self.params[5])
        y = h @ self.params[6] + self.params[7]
        return np.clip(y * self.scale + self.mean, self.low, self.high)

    def reconstruct(self, grids):
        return self.decode(self.encode(grids))

    def fit(self, grids, epochs=300, batch=64, lr=2e-3, seed=0, log=None):
        rng = np.random.default_rng(seed)
        self.mean = grids.mean(axis=0)
        self.scale = grids.std(axis=0) + 1e-3
        self.low, self.high = float(grids.min()), float(grids.max())
        x_all = (grids - self.mean) / self.scale
        m = [np.zeros_like(p) for p in self.params]
        v = [np.zeros_like(p) for p in self.params]
        step = 0
        for epoch in range(epochs):
            order = rng.permutation(len(x_all))
            total = 0.0
            for start in range(0, len(order), batch):
                x = x_all[order[start:start + batch]]
                acts = self._forward(x)
                y = acts[-1]
                grads = [None] * len(self.params)
                d = 2 * (y - x) / x.size
                for layer in (3, 2, 1, 0):
                    h_in = acts[layer]
                    grads[2 * layer] = h_in.T @ d
                    grads[2 * layer + 1] = d.sum(axis=0)
                    if layer > 0:
                        d = d @ self.params[2 * layer].T
                        if layer - 1 in (0, 2):
                            d = d * (1 - h_in ** 2)
                step += 1
                for i, g in enumerate(grads):
                    m[i] = .9 * m[i] + .1 * g
                    v[i] = .999 * v[i] + .001 * g * g
                    self.params[i] -= lr * (m[i] / (1 - .9 ** step)) / (np.sqrt(v[i] / (1 - .999 ** step)) + 1e-8)
                total += float(((y - x) ** 2).mean()) * len(x)
            if log and (epoch % 50 == 0 or epoch == epochs - 1):
                log(f"epoch {epoch} train mse {total / len(x_all):.4f}")
        return self

    def save(self, path):
        np.savez(path, version=VERSION, mean=self.mean, scale=self.scale, latent=self.latent, clip=[self.low, self.high], *self.params)

    @classmethod
    def load(cls, path):
        data = np.load(path, allow_pickle=False)
        if str(data["version"]) != VERSION:
            raise ValueError("Latent model version mismatch.")
        model = cls.__new__(cls)
        model.params = [data[f"arr_{i}"] for i in range(8)]
        model.mean, model.scale, model.latent = data["mean"], data["scale"], int(data["latent"])
        model.low, model.high = (float(data["clip"][0]), float(data["clip"][1])) if "clip" in data else (-1.0, 0.0)
        return model


def pca_baseline(grids, components=6):
    """Linear autoencoder of the same width, to show what the nonlinearity buys."""
    mean = grids.mean(axis=0)
    _, _, vt = np.linalg.svd(grids - mean, full_matrices=False)
    basis = vt[:components]
    return lambda g: (np.atleast_2d(g) - mean) @ basis.T @ basis + mean


def grid_to_magnitude(grid, seconds=1.0):
    """Expand a 24×8 grid to a frames × bins magnitude spectrogram."""
    db = np.asarray(grid, dtype=float).reshape(BANDS, TIMES) * -FLOOR_DB
    frames = 1 + int(seconds * SR) // HOP
    log_anchor = np.log(ANCHORS_S)
    lt = np.log(np.maximum(frame_times(frames), ANCHORS_S[0] * .5))
    band_db = np.empty((frames, BANDS))
    slope = (db[:, -1] - db[:, -2]) / (log_anchor[-1] - log_anchor[-2])
    for b in range(BANDS):
        band_db[:, b] = np.interp(lt, log_anchor, db[b])
        beyond = lt > log_anchor[-1]
        band_db[beyond, b] = db[b, -1] + np.minimum(slope[b], 0) * (lt[beyond] - log_anchor[-1])
    power = 10 ** (band_db / 10)
    bin_weights = _BANK.T / np.maximum(_BANK.sum(axis=0)[:, None], 1e-12)
    return np.sqrt(power @ bin_weights.T)


def decode_audio(grid, seconds=1.0, iterations=40, seed=0):
    n = int(seconds * SR)
    audio = griffin_lim(grid_to_magnitude(grid, seconds), n, iterations, seed)
    fade = min(int(.02 * SR), n)
    audio[-fade:] *= np.linspace(1, 0, fade)
    return (audio / (np.max(np.abs(audio)) + 1e-12) * .5).astype(np.float32)


def nearest_recipes(grid, grids, vectors, count=3):
    order = np.argsort(np.linalg.norm(grids - np.asarray(grid), axis=1))[:count]
    return vectors[order].tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--train", type=int, help="Render this many random recipes and fit")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--walk", type=int, help="Decode this many steps between two random latents")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()
    args.dir.mkdir(parents=True, exist_ok=True)
    if args.train:
        t0 = time.time()
        grids, vectors = dataset(args.train, args.seed)
        print(f"Rendered and described {args.train} recipes in {time.time() - t0:.1f} s", flush=True)
        split = int(len(grids) * .85)
        model = Autoencoder(seed=args.seed).fit(grids[:split], args.epochs, log=print)
        test = grids[split:]
        mse = lambda a, b: float(((a - b) ** 2).mean())
        print(f"held-out mse: autoencoder {mse(model.reconstruct(test), test):.5f} | pca-6 {mse(pca_baseline(grids[:split])(test), test):.5f} | mean {mse(grids[:split].mean(axis=0), test):.5f}")
        model.save(args.dir / "model.npz")
        np.savez(args.dir / "dataset.npz", grids=grids, vectors=vectors)
        print(f"Saved {args.dir / 'model.npz'}")
    if args.walk:
        model = Autoencoder.load(args.dir / "model.npz")
        data = np.load(args.dir / "dataset.npz")
        rng = np.random.default_rng(args.seed + 1)
        z = model.encode(data["grids"][rng.choice(len(data["grids"]), 2, replace=False)])
        gap = np.zeros(int(.15 * SR), dtype=np.float32)
        decoded, rendered = [], []
        for i in range(args.walk):
            grid = model.decode(z[0] + (z[1] - z[0]) * i / max(args.walk - 1, 1))[0]
            decoded += [decode_audio(grid), gap]
            rendered += [render(nearest_recipes(grid, data["grids"], data["vectors"], 1)[0]), gap]
        (args.dir / "walk-decoded.wav").write_bytes(wav_bytes(np.concatenate(decoded)))
        (args.dir / "walk-nearest-recipe.wav").write_bytes(wav_bytes(np.concatenate(rendered)))
        print(f"Wrote {args.dir / 'walk-decoded.wav'} (Griffin-Lim) and walk-nearest-recipe.wav (real synth)")


if __name__ == "__main__":
    main()
