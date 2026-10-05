#!/usr/bin/env python3
"""Lay the ratchet's clicks under a passage of the master so they can be heard
outside the harness: a listening mix, not a render.

    godot --headless --path harness -s dev/dump_clicks.gd -- --out=/tmp/click.wav > /tmp/clicks.txt
    python3 tools/click_mix.py /tmp/clicks.txt /tmp/click.wav --start 45 --seconds 10 --out /tmp/mix.wav
    ffmpeg -loop 1 -i still.png -i /tmp/mix.wav -shortest -pix_fmt yuv420p /tmp/mix.mp4

The clicks are placed at the times the motion bake lists (`Rig.click_times`: one
a stepped or homing landing, a hammer click, or a mallet freewheel's crossing of
a tooth) at the harness's level: CLICK_DB (-12) under the master (performance.gd).
A click whose pawl rides the tips (the CLICK line's pawl column, 1) is the ride
tick (dump_clicks.gd writes it beside the click WAV, `<click>_ride.wav`; pass
--ride to name another), RIDE_DB (-9) lighter. An older dump without the pawl
and step columns reads as every click a stepped drop.

By default each click sounds at its own time. --fps N plays them as the
harness does at N frames a second: every click lands at the end of its frame,
a stepped click a voice of its own, and a frame's freewheel clicks one voice
louder by their summed power (performance.gd freewheel_voice). With
--clicks-only the master is left out so the ticks can be judged on their own.
"""
import argparse, sys, wave
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CLICK_DB = -12.0
RIDE_DB = -9.0     # a ride click against a drop click (performance.gd)


def read_clicks(path):
    """[(t, pawl, step)] from dump_clicks.gd's CLICK lines (aid t teeth [pawl step])."""
    out = []
    for l in Path(path).read_text().splitlines():
        if not l.startswith('CLICK '): continue
        f = l.split()
        out.append((float(f[2]), int(f[4]) if len(f) > 4 else 0, int(f[5]) if len(f) > 5 else 1))
    return out


def voices(clicks, fps=0.0):
    """[(t, ride, db)] the voices the clicks make, db over CLICK_DB: each click
    its own at its time (fps 0), or batched as the harness's frames are."""
    if not fps:
        return [(t, bool(pawl), RIDE_DB if pawl else 0.0) for t, pawl, _ in clicks]
    frames = {}
    for t, pawl, step in clicks:
        f = int(np.ceil(t*fps-1e-9)); d = frames.setdefault(f, [0, 0, 0])
        d[0 if step else (2 if pawl else 1)] += 1
    out = []
    for f, (stepped, drop, ride) in sorted(frames.items()):
        t = f/fps
        out.extend((t, False, 0.0) for _ in range(stepped))
        if drop == 0 and ride: out.append((t, True, RIDE_DB+10*np.log10(ride)))
        elif drop: out.append((t, False, 10*np.log10(drop+ride*10**(RIDE_DB/10))))
    return out


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
    ap.add_argument('--ride', help='the ride tick WAV (default: <sample>_ride.wav beside it; the click sample if absent)')
    ap.add_argument('--fps', type=float, default=0.0, help='batch the clicks into frames as the harness does (0: each at its own time)')
    ap.add_argument('--master', default=str(ROOT / 'render/chamber/chamber.wav'))
    ap.add_argument('--start', type=float, default=45.0)
    ap.add_argument('--seconds', type=float, default=10.0)
    ap.add_argument('--clicks-only', action='store_true')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    clicks = read_clicks(a.clicks)
    rate, click = read_wav(a.sample)
    click = click[:, 0]
    ride_path = Path(a.ride) if a.ride else Path(a.sample).with_name(Path(a.sample).stem+'_ride'+Path(a.sample).suffix)
    tick = click
    if ride_path.exists():
        rrate, tick = read_wav(ride_path); tick = tick[:, 0]
        assert rrate == rate, f'ride tick at {rrate} Hz, click at {rate} Hz'
    elif any(pawl for _, pawl, _ in clicks): print(f'no ride tick at {ride_path}: ride clicks use the click sample')
    n = int(a.seconds * rate)
    mix = np.zeros((n, 2))
    if not a.clicks_only:
        mrate, master = read_wav(a.master)
        assert mrate == rate, f'master at {mrate} Hz, click at {rate} Hz'
        seg = master[int(a.start * rate): int(a.start * rate) + n]
        if seg.shape[1] == 1: seg = np.repeat(seg, 2, axis=1)
        mix[:len(seg)] += seg
    placed = rides = 0
    for t, ride, db in voices(clicks, a.fps):
        i = int(round((t - a.start) * rate))
        if i < 0 or i >= n: continue
        s = tick if ride else click; gain = 10 ** ((CLICK_DB + db) / 20)
        m = min(len(s), n - i)
        mix[i:i + m, 0] += s[:m] * gain
        mix[i:i + m, 1] += s[:m] * gain
        placed += 1; rides += ride
    peak = np.abs(mix).max()
    if peak > .98: mix *= .98 / peak
    write_wav(a.out, rate, mix)
    print(f'{placed} click voices ({rides} ride ticks{f", {a.fps:g} fps frames" if a.fps else ""}) in {a.seconds:.1f} s from {a.start:.1f} s -> {a.out} (peak {peak:.2f})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
