"""Bake the clockwork performance for playback (formlab/bake.py, `loam-motion/2`).

    python3 tools/bake_motion.py                          # both assets that have a score
    python3 tools/bake_motion.py --asset=clockwork [--hz=240] [--score=PATH]

The score defaults to this tree's (formlab.bake.DEFAULT_SCORES, relative to
the repository root: render/chamber/score.json for clockwork,
render/clockwork/score.json for clockwork_expanded), and the bake is written
next to it. A manifest's own "score" is the absolute path it was built from;
when that is another file it is reported, not used, so a bake in a copied tree
never reads or writes the original's. An asset with no default needs --score.
tools/build_clockwork.py bakes at the end of every build; run this by hand
after re-exporting a score without rebuilding the model (the harness refuses a
stale bake, or an older format, and says so).
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
        if opts.get('score'):
            score = Path(opts['score'])
        elif asset in bake.DEFAULT_SCORES:
            score = bake.default_score(asset, ROOT)
        else:
            print(f'MOTION BAKE: {asset}: no default score for this asset (known: {", ".join(bake.DEFAULT_SCORES)}); '
                  f'pass --score=PATH'); status = 1; continue
        if not score.exists():
            print(f'MOTION BAKE: {asset}: no score at {score} (run its song script first)'); status = 1; continue
        built = json.loads(manifest.read_text()).get('score') if manifest.exists() else None
        if built and Path(built).resolve() != score.resolve():
            print(f'MOTION BAKE: {asset}: the manifest was built from {built}; baking {score} (this tree\'s)')
        bake.bake(score, manifest, asset=asset, hz=hz)
    return status

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
