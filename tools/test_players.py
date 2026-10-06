"""The players' rulers (docs/goals/the-players.md, "Acceptance").

    python3 tools/test_players.py --report [--asset=chamber|expanded] [--only=1,3,8] [--save=PATH] [--skip-invariants]
    python3 tools/test_players.py --gate [--asset=...]
    python3 tools/test_players.py --gate=M1 [--gate=M2 | --gate=M1,M2] [--asset=...] [--skip-invariants]

--report prints every ruler's measure on both assets (or one), scope by scope,
with PASS / FAIL against the goal's target, n/a where there is nothing to
measure yet, or info for a number the goal reports but does not judge (yet). --save writes the same as JSON (the goal's "today" cells were
regenerated from such a file: docs/goals/the-players.today.json).

--gate reads the goal's milestone table, and for every milestone whose status
is `done` runs the rulers its gate names, in its scope, and fails if any
result in that scope is FAIL. A ruler that is n/a in a gated scope fails too:
a milestone that claims a ruler must have given it something to measure.
--gate=M1 gates the named milestone(s) instead, whether or not their status
is done (repeat the flag or give a comma list): how a milestone in progress
checks itself against its own gate before it is marked done.

--skip-invariants (or PLAYERS_SKIP_INVARIANTS=1 in the environment) skips
ruler 26's slow subprocesses (the harness tests, the rail cache, the
bake checks): ruler 26 then reports n/a, so a gate that names 26 fails on
it. Use it for a fast --report; never for the gate that marks a milestone done.

The rulers live in tools/players/r_*.py; each exports RULERS = {n: fn}, fn
taking a players.core.Subject and returning [Result]. The measuring core
(sampling, contacts, declared structure) is tools/players/core.py.
"""
import importlib, json, os, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT))
from players import core

GOAL = ROOT/'docs/goals/the-players.md'

# Each milestone's gate: (ruler, scope) or (ruler, scope, names). A scope is a
# tuple of arm kinds, or 'all'; names, when given, keep only the results whose
# name starts with one of them (a milestone that gates part of a ruler: M1's
# "10 (b, c, d)", "1 (bars head)"). It mirrors the goal's milestone table
# ("gate" column); the table is the spec, this is its executable form, and the
# two change together. M1's '1 brisk' is the ceiling on the travels its '1 tool'
# p95 leaves out while r_motion.BRISK_UNTIL_M8 (no such row when it is False).
# M2's ruler 3 is the row '3 lead (IOI >= 0.25 s)' (A14: the contacts with IOI
# >= 0.25 s; M7 gates the full '3 preparation'), and its 22 on the harps is
# sync and repeat (A15: harp homing moves to M7) while the rake's 22 is whole
# (it homes in M2). M2 also gates the rake's '15 tip accel' (A20 D3: the
# comb's tool point <= 10 g; the rest of ruler 15 stays M9) and the harps'
# '3 poise still' (A26 D7: every declared poise holds the tool point still;
# the rake's announce holds are 14's, gated whole). Names match by prefix, so
# no gated name may be the prefix of a row it must not take ('3 lead', '3
# preparation', '3 hand-off' and '3 poise still' are not; '15 tip accel' is
# ruler 15's only row so named).
MALLETS = ('mallet',); SERVO = ('pick', 'rake'); HARP = ('pick',); RAKE = ('rake',)
MILESTONE_GATES = {
    'M0': [(26, 'all')],
    'M1': [(n, MALLETS) for n in (3, 4, 5, 6, 7, 8, 9, 11, 19, 21, 22)]
          +[(10, MALLETS, ('10b', '10c', '10d')), (1, MALLETS, ('1 tool', '1 brisk')), (25, 'all'), (26, 'all')],
    'M2': [(3, SERVO, ('3 lead',)), (3, HARP, ('3 poise still',)), (5, SERVO), (6, SERVO), (14, RAKE), (15, RAKE, ('15 tip accel',)),
           (22, HARP, ('sync', 'repeat')), (22, RAKE), (25, 'all'), (26, 'all')],
    'M3': [(26, 'all')],
    'M4': [(16, 'all', ('16 limits',)), (17, 'all'), (18, 'all'), (26, 'all')],
    'M5': [(n, ('mallet', 'hammer')) for n in (1, 7, 8, 10, 15, 16, 17, 22, 23)]+[(25, 'all'), (26, 'all')],
    'M6a': [],
    'M6b': [(25, 'all'), (26, 'all')],
    'M7': [(n, HARP) for n in (1, 3, 4, 5, 12, 13, 15, 16, 22, 23)]+[(25, 'all'), (26, 'all')],
    'M8': [(n, MALLETS) for n in (19, 1, 10, 22, 23)]+[(25, 'all'), (26, 'all')],
    'M9': [(n, RAKE) for n in (1, 5, 6, 14, 15, 17, 23)]+[(25, 'all'), (26, 'all')],
    'M10': [(n, 'all') for n in range(1, 27) if n != 2],
    'M11': [(n, 'all') for n in range(1, 27)],
}
# Rulers that only exist on some assets: the screen ruler measures the film,
# and only the chamber has one.
ONLY_ON = {2: ('chamber',)}

def modules():
    for path in sorted((HERE/'players').glob('r_*.py')):
        yield importlib.import_module(f'players.{path.stem}')

def rulers():
    out = {}
    for m in modules():
        for n, fn in m.RULERS.items():
            if n in out: raise SystemExit(f'ruler {n} defined twice ({out[n].__module__}, {m.__name__})')
            out[n] = fn
    return dict(sorted(out.items()))

def done_milestones(text=None):
    text = GOAL.read_text() if text is None else text
    done = []
    for line in text.splitlines():
        m = re.match(r'\|\s*(M\d+[ab]?)\s*\|', line)
        if m and re.search(r'\|\s*done\b[^|]*\|\s*$', line): done.append(m.group(1))
    return done

def in_scope(result, scope, subject):
    if scope == 'all': return True
    if result.scope in subject.arms: return subject.kind(result.scope) in scope
    return result.scope in scope or result.scope == 'all'

def run(assets, only=None, verbose=True):
    table = rulers(); results = {}
    for asset in assets:
        S = core.Subject(asset); results[asset] = []
        for n, fn in table.items():
            if only and n not in only: continue
            t0 = time.time()
            try: rs = fn(S)
            except Exception as ex:                         # a crashing ruler is a FAIL, loudly
                import traceback; traceback.print_exc()
                rs = [core.Result(n, 'crashed', 'all', dict(error=repr(ex)), False)]
            for r in rs:
                results[asset].append(r)
                if verbose:
                    mark = 'n/a ' if r.passed is None else 'info' if r.passed == core.INFO else 'PASS' if r.passed else 'FAIL'
                    print(f'  [{asset}] {mark} {r.n:2d} {r.name:<28s} {r.scope:<12s} {_fmt(r.value)}'+(f'  — {r.note}' if r.note else ''))
            if verbose and time.time()-t0 > 5: print(f'  [{asset}]      ruler {n} took {time.time()-t0:.0f} s')
    return results

def _fmt(v):
    def f(x):
        if isinstance(x, float): return f'{x:.4g}'
        if isinstance(x, dict): return '{'+', '.join(f'{k}={f(u)}' for k, u in x.items())+'}'
        if isinstance(x, (list, tuple)): return '['+', '.join(f(u) for u in x[:6])+(', …' if len(x) > 6 else '')+']'
        return str(x)
    return ', '.join(f'{k}={f(u)}' for k, u in v.items())

def gate(assets, milestones=None):
    """Gate the done milestones, or the named ones (`milestones`) whatever
    their status."""
    bad = []
    if milestones:
        unknown = [m for m in milestones if m not in MILESTONE_GATES]
        if unknown: raise SystemExit(f'unknown milestone(s) {", ".join(unknown)}; known: {", ".join(MILESTONE_GATES)}')
        done = list(milestones)
        print(f'milestones gated (named): {", ".join(done)}')
    else:
        done = done_milestones()
        print(f'milestones done: {", ".join(done) or "none"}')
    need = {}
    for m in done:
        for n, scope, *names in MILESTONE_GATES.get(m, []): need.setdefault(n, []).append((m, scope, tuple(names[0]) if names else None))
    if not need: print('nothing gated yet'); return 0
    results = run(assets, only=set(need), verbose=False)
    for asset in assets:
        S = core.Subject(asset)
        for n, claims in sorted(need.items()):
            if asset not in ONLY_ON.get(n, (asset,)): continue
            for m, scope, names in claims:
                rs = [r for r in results[asset] if r.n == n and in_scope(r, scope, S)
                      and (names is None or r.name.startswith(names))]
                kinds = scope if scope == 'all' else [k for k in scope if any(S.kind(a) == k for a in S.arms)]
                if not kinds: continue                      # the asset has no arm of that kind
                if not rs: bad.append(f'{asset}: ruler {n} ({m}) measured nothing in scope {scope}'); continue
                for r in rs:
                    if r.passed == core.INFO: continue          # reported, never gated
                    if r.passed is not True:
                        bad.append(f'{asset}: ruler {n} {r.name} [{r.scope}] ({m}) '+('n/a' if r.passed is None else 'FAIL')+f': {_fmt(r.value)}')
    for b in bad: print('  FAIL '+b)
    print('GATE '+('FAILED' if bad else 'PASSED'))
    return 1 if bad else 0

def main(argv):
    flags = [a[2:].split('=', 1) if '=' in a else (a[2:], None) for a in argv if a.startswith('--')]
    opts = {k: ('1' if v is None else v) for k, v in flags}
    named = [m.strip() for k, v in flags if k == 'gate' and v for m in v.split(',') if m.strip()]
    if 'skip-invariants' in opts: os.environ['PLAYERS_SKIP_INVARIANTS'] = '1'
    assets = [opts['asset']] if 'asset' in opts else list(core.ASSETS)
    if 'gate' in opts: return gate(assets, named or None)
    only = {int(x) for x in opts['only'].split(',')} if 'only' in opts else None
    results = run(assets, only)
    if 'save' in opts:
        doc = {a: [dict(n=r.n, name=r.name, scope=r.scope, value=r.value, passed=r.passed, note=r.note) for r in rs]
               for a, rs in results.items()}
        Path(opts['save']).write_text(json.dumps(doc, indent=1, default=float)+'\n')
        print(f'saved {opts["save"]}')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
