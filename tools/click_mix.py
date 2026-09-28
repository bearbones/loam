#!/usr/bin/env python3
"""Lay the ratchet's clicks under a passage of the master so they can be heard
outside the harness: a listening mix, not a render.

    godot --headless --path harness -s dev/dump_clicks.gd -- --out=/tmp/click.wav > /tmp/clicks.txt
    python3 tools/click_mix.py /tmp/clicks.txt /tmp/click.wav --start 45 --seconds 10 --out /tmp/mix.wav
    ffmpeg -loop 1 -i still.png -i /tmp/mix.wav -shortest -pix_fmt yuv420p /tmp/mix.mp4

The clicks are placed at the times the motion bake lists (`Rig.click_times`, (one a
click, at the landing) at the harness's level: CLICK_DB (-12) under the master
(performance.gd). With --clicks-only the master is left out so the ticks can
be judged on their own.
"""
import argparse, sys, wave
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CLICK_DB = -12.0


def read_wav(path):
    with wave.open(str(path), 'rb') as w:
        rate = w.getframerate(); n = w.getnframes(); ch = w.getnchannels(); width = w.getsampwidth()
        raw = w.readframes(n)
    assert width == 2, f'{path}: expected 16-bit PCM'
    data = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32767.0
    return rate, data.reshape(-1, ch)


def write_wav(path, rate, data):
    data = np.clip(data, -1, 1)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(data.shape[1]); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((data * 32767).astype('<i2').tobytes())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('clicks', help='dump_clicks.gd output (CLICK aid t teeth lines)')
    ap.add_argument('sample', help='the click WAV dump_clicks.gd wrote')
    ap.add_argument('--master', default=str(ROOT / 'render/chamber/chamber.wav'))
    ap.add_argument('--start', type=float, default=45.0)
    ap.add_argument('--seconds', type=float, default=10.0)
    ap.add_argument('--clicks-only', action='store_true')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    times = [float(l.split()[2]) for l in Path(a.clicks).read_text().splitlines() if l.startswith('CLICK ')]
    rate, click = read_wav(a.sample)
    click = click[:, 0]
    n = int(a.seconds * rate)
    mix = np.zeros((n, 2))
    if not a.clicks_only:
        mrate, master = read_wav(a.master)
        assert mrate == rate, f'master at {mrate} Hz, click at {rate} Hz'
        seg = master[int(a.start * rate): int(a.start * rate) + n]
        if seg.shape[1] == 1: seg = np.repeat(seg, 2, axis=1)
        mix[:len(seg)] += seg
    gain = 10 ** (CLICK_DB / 20)
    placed = 0
    for t in times:
        i = int(round((t - a.start) * rate))
        if i < 0 or i >= n: continue
        m = min(len(click), n - i)
        mix[i:i + m, 0] += click[:m] * gain
        mix[i:i + m, 1] += click[:m] * gain
        placed += 1
    peak = np.abs(mix).max()
    if peak > .98: mix *= .98 / peak
    write_wav(a.out, rate, mix)
    print(f'{placed} clicks in {a.seconds:.1f} s from {a.start:.1f} s -> {a.out} (peak {peak:.2f})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
