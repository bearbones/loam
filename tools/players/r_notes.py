"""Rulers 25 (notes) and 26 (invariants) of docs/goals/the-players.md.

25 reads the composer's ledger the score carries (songs/chamber.py's
ask_pluck / ask_rake: intended, as written, substituted, dropped), the
expanded song's refusals, and the stems against the hashes recorded in
docs/goals/the-players.stems.json — a milestone that changes the music on
purpose rewrites that file (`python3 tools/players/r_notes.py --record-stems`)
and says so in LOG.md.

26 runs the rulers the players must not break, as subprocesses: every ruler
of docs/articulated-arms.md, test_rail_cache, and the harness/dev checks
(headless) on both assets. The Python suites measure both assets in one run,
so they run once per process and report on each asset; the Godot checks run
per asset. PLAYERS_SKIP_INVARIANTS=1 skips them (the result is n/a, which
--gate refuses: a gate always runs them).
"""
import hashlib, json, os, re, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from players.core import INFO, Result, ROOT

GOAL = ROOT/'docs/goals/the-players.md'
STEMS = ROOT/'docs/goals/the-players.stems.json'

# ---- 25 notes -------------------------------------------------------------
MAX_DROPS = 9           # after every milestone
END_DROPS = 6           # at the end (M11)
END_AS_WRITTEN = 228

def _done(milestone):
    for line in GOAL.read_text().splitlines():
        if re.match(rf'\|\s*{milestone}\s*\|', line) and re.search(r'\|\s*done\b[^|]*\|\s*$', line): return True
    return False

def stem_hashes(score_path):
    """sha256 of every rendered audio file the score names, plus the mix and the string shapes."""
    doc = json.loads(Path(score_path).read_text()); d = Path(score_path).parent
    files = sorted(set(doc.get('stems', {}).values()) | {'chamber.wav', 'shapes.f32'})
    return {f: hashlib.sha256((d/f).read_bytes()).hexdigest() for f in files if (d/f).exists()}

def notes(S):
    st = S.score.get('stats', {}); out = []
    if S.asset == 'chamber':
        if 'intended' not in st:
            return [Result(25, 'ledger', 'all', {}, False, 'score.json carries no ledger: re-render songs/chamber.py')]
        drops = len(st['dropped']); subs = len(st['substituted'])
        v = dict(intended=st['intended'], as_written=st['as_written'], substituted=subs, dropped=drops)
        out.append(Result(25, 'drops', 'all', v, drops <= MAX_DROPS, f'<= {MAX_DROPS} after every milestone'))
        end = drops <= END_DROPS and st['as_written'] >= END_AS_WRITTEN
        out.append(Result(25, 'drops at the end', 'all', v, end if _done('M11') else INFO,
                          f'<= {END_DROPS} drops and >= {END_AS_WRITTEN} as written, judged once M11 is done'))
    else:
        r = int(st.get('refused', -1))
        out.append(Result(25, 'refusals', 'all', dict(refused=r, asked=st.get('asked')), r == 0))
    ref = json.loads(STEMS.read_text()).get(S.asset) if STEMS.exists() else None
    now = stem_hashes(S.score_path)
    if ref is None:
        out.append(Result(25, 'stems', 'all', dict(files=len(now)), False, f'no recorded hashes in {STEMS.name}'))
    else:
        changed = sorted(f for f in set(ref) | set(now) if ref.get(f) != now.get(f))
        out.append(Result(25, 'stems', 'all', dict(files=len(now), changed=changed), not changed,
                          'bit-identical to the recorded stems unless the milestone changed the music (then re-record)'))
    return out

# ---- 26 invariants --------------------------------------------------------
PY = sys.executable
EXPANDED_SCORE = str(ROOT/'render/clockwork/score.json')
SUITE = [   # (name, argv): each measures both assets in one run
    ('test_score_plan', [PY, 'tools/test_score_plan.py']),
    ('test_formlab', [PY, 'tools/test_formlab.py']),
    ('test_form_joints', [PY, 'tools/test_form_joints.py']),
    ('test_linkage_tools', [PY, 'tools/test_linkage_tools.py']),
    ('test_gantry', [PY, 'tools/test_gantry.py']),
    ('test_oil_cups', [PY, 'tools/test_oil_cups.py']),
    ('test_pawl', [PY, 'tools/test_pawl.py']),
    ('test_motion', [PY, 'tools/test_motion.py']),
    ('test_bake', [PY, 'tools/test_bake.py']),
    ('test_rail_cache', [PY, 'tools/test_rail_cache.py']),
    ('test_form_joint_seats', ['blender', '-b', '-t', '2', '--python-exit-code', '1', '-P', 'tools/test_form_joint_seats.py']),
]
GODOT = [   # (name, script, {asset: user args})
    ('test_clockwork', 'dev/test_clockwork.gd', dict(chamber=[], expanded=['--asset=clockwork_expanded', '--score='+EXPANDED_SCORE])),
    ('test_performance', 'dev/test_performance.gd', dict(chamber=[], expanded=['--expanded'])),
    ('test_load', 'dev/test_load.gd', dict(chamber=[], expanded=['--score='+EXPANDED_SCORE])),
]
TIMEOUT = 1800
_suite = {}             # the Python suite's results, once per process

def _run(name, argv):
    exe = shutil.which(argv[0]) if not os.path.isabs(argv[0]) else argv[0]
    if exe is None: return name, dict(ok=False, s=0.0, tail=f'{argv[0]} not on PATH')
    t0 = time.time()
    try:
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT)
        ok, text = p.returncode == 0, p.stdout+p.stderr
    except subprocess.TimeoutExpired:
        ok, text = False, f'timed out after {TIMEOUT} s'
    tail = [l for l in text.splitlines() if 'FAIL' in l or 'Error' in l][:6] if not ok else []
    return name, dict(ok=ok, s=round(time.time()-t0, 1), tail=' | '.join(tail)[:400] or (text.strip().splitlines() or [''])[-1][:200])

def _godot(script, args):
    return ['godot', '--headless', '--path', str(ROOT/'harness'), '-s', script]+(['--']+args if args else [])

def invariants(S):
    if os.environ.get('PLAYERS_SKIP_INVARIANTS'):
        return [Result(26, 'invariants', 'all', {}, None, 'skipped (PLAYERS_SKIP_INVARIANTS)')]
    jobs = [] if _suite else list(SUITE)
    jobs += [(f'{n}[{S.asset}]', _godot(script, args[S.asset])) for n, script, args in GODOT]
    with ThreadPoolExecutor(max_workers=6) as pool:
        done = dict(pool.map(lambda j: _run(*j), jobs))
    for n, _ in SUITE:
        if n in done: _suite[n] = done.pop(n)
    out = []
    for n, r in list(_suite.items())+list(done.items()):
        out.append(Result(26, n, 'all', dict(seconds=r['s']), r['ok'], '' if r['ok'] else r['tail']))
    return out

RULERS = {25: notes, 26: invariants}

if __name__ == '__main__':
    if '--record-stems' in sys.argv:
        from players.core import ASSETS
        doc = {a: stem_hashes(c['score']) for a, c in ASSETS.items()}
        STEMS.write_text(json.dumps(doc, indent=1, sort_keys=True)+'\n')
        print(f'recorded {sum(map(len, doc.values()))} hashes -> {STEMS.relative_to(ROOT)}')
