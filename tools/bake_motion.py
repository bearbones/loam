"""Bake the clockwork performance for playback (formlab/bake.py, `loam-motion/1`).

    python3 tools/bake_motion.py                          # both assets that have a score
    python3 tools/bake_motion.py --asset=clockwork [--hz=240] [--score=PATH]

The score defaults to the one the manifest was built from
(harness/assets/<asset>.json, "score"). tools/build_clockwork.py runs this at
the end of every build; run it by hand after re-exporting a score without
rebuilding the model (the harness refuses a stale bake and says so).
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from formlab import bake

def main(argv):
    opts = dict(a[2:].split('=', 1) for a in argv if a.startswith('--') and '=' in a)
    assets = [opts['asset']] if 'asset' in opts else ['clockwork', 'clockwork_expanded']
    hz = int(opts.get('hz', 240)); status = 0
    for asset in assets:
        manifest = ROOT/'harness'/'assets'/f'{asset}.json'
        score = Path(opts.get('score') or json.loads(manifest.read_text())['score'])
        if not score.exists():
            print(f'MOTION BAKE: {asset}: no score at {score} (run its song script first)'); status = 1; continue
        bake.bake(score, manifest, asset=asset, hz=hz)
    return status

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
