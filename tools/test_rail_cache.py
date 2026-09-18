"""Ruler for the rail search's cache key.

    python3 tools/test_rail_cache.py

The rail plan is an hour-long search whose answer is cached
(`render/form-study/rails-cache.json`, keyed by `layout_search._mech_key`).
A key that misses an input is worse than no cache: a stale plan is only
visible as a red ruler after a 7 minute build, and the motion redesign of
2026-09-17 did exactly that — the rails were planned against the old sweep
and the rulers re-measured them against the new one.

This ruler holds the key to its promise: touching any module the plan is
measured against, or any motion constant, changes it. The keep-flag's escape
hatch (`build_clockwork.py --rails=keep`) is checked by `test_gantry` through
the manifest's `stale_rails` note; here we check that keep-mode finds the
stored plan at all and marks the layout when it does.
"""
import json, sys, copy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from formlab import layout_search as LS
from formlab import rig as rig_module

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def fixture():
    """The smallest score and layout `_mech_key` will read: one mechanism, one
    actuator, one string. The key hashes text and numbers, never the search."""
    mech = dict(id='m', kind='struck', material='wood',
                actuators=[dict(id='m_arm0', kind='mallet', home='s0', reach=['s0'], approach_s=.12, travel_s=.1)],
                strings=[dict(id='s0', midi=60, pick_default=.5)])
    score = dict(total_s=4.0, instrument=dict(mechanisms=[mech]),
                 events=[dict(mech='m', actuator='m_arm0', t=1.0, t_move=.5, t_free=1.4, strings=['s0'])])
    layout = dict(strings={'s0': dict(a=[0, 1, 0], b=[0, 1, .5], mid='m', struck=True, midi=60, pick=.5)},
                  mechanisms={'m': dict(center=[0, 1, 0], kind='struck', arm_clearance_m=0.0)},
                  arms={'m_arm0': dict(mid='m', kind='mallet', index=0, reach_x=[0, 1])}, obstacles=[])
    return score, layout, mech

def key_of(score, layout, mech):
    return LS._mech_key(score, layout, mech, 30, .08, {})

def run():
    score, layout, mech = fixture()
    base = key_of(score, layout, mech)
    check(isinstance(base, str) and len(base) == 40, f'the key is a sha1 digest ({base[:12]}…)')

    # 1. the modules the plan is measured against
    check(set(LS.GEOMETRY_SOURCES) == {'rig.py', 'clearance.py', 'linkage.py', 'gantry.py', 'pawl.py'},
          'the key hashes the motion (rig), the space model (clearance) and the '
          'geometry it measures (linkage, gantry, pawl): '+', '.join(LS.GEOMETRY_SOURCES))
    for name in LS.GEOMETRY_SOURCES:
        path = ROOT/'formlab'/name; original = path.read_bytes()
        try:
            path.write_bytes(original+b'\n# rail-cache ruler\n')
            check(key_of(score, layout, mech) != base, f'editing formlab/{name} changes the key')
        finally:
            path.write_bytes(original)
    check(key_of(score, layout, mech) == base, 'and restoring every source restores the key')

    # 2. the motion constants themselves, so tuning one by hand replans
    consts = LS.motion_constants()
    check({'CLICK_S', 'SLEW_S', 'OVERSHOOT', 'COCK', 'RECOIL', 'PITCH'} <= set(consts),
          f'motion_constants() reports the vocabularies ({len(consts)} constants)')
    for name, tweak in (('CLICK_S', .11), ('SLEW_S', .55), ('OVERSHOOT', .2)):
        was = getattr(rig_module, name)
        try:
            setattr(rig_module, name, tweak)
            check(key_of(score, layout, mech) != base, f'tuning {name} ({was} -> {tweak}) changes the key')
        finally:
            setattr(rig_module, name, was)

    # 3. and the inputs it already promised, still
    moved = copy.deepcopy(layout); moved['arms']['m_arm0']['reach_x'] = [0, 1.5]
    check(key_of(score, moved, mech) != base, "an arm's reach window changes the key")
    later = copy.deepcopy(score); later['events'][0]['t'] = 1.25
    check(key_of(later, layout, mech) != base, 'an event time changes the key')

    # 4. keep-mode: it finds the stored plan, and says so in the layout
    cfg = dict(root_y=2.25, root_z=-1.0, l1=1.3, l2=1.3, bend='up', wrist_offset=[0, .28, 0],
               o1=[0, -.11, 0], o2=[0, 0, -.11], pinion='back', margins={'self': .1})
    cache = Path(ROOT/'render/form-study/rails-cache-ruler.json')
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({'a-plan-for-other-inputs': {'m_arm0': cfg}}))
    try:
        kept = copy.deepcopy(layout); lines = []
        LS.plan_arms(score, kept, cache=str(cache), rails='keep', verbose=lines.append)
        check(kept.get('stale_rails') is True, 'a keep-build marks the layout stale_rails')
        check(abs(kept['arms']['m_arm0']['root_y']-cfg['root_y']) < 1e-12, 'a keep-build reuses the stored rail')
        check(any('STALE' in l for l in lines), 'a keep-build says so in the build log: '
              + next((l.strip() for l in lines if 'STALE' in l), '(nothing)'))

        # 4b. keep_from wins over the cache. "Keep" has to mean "keep what
        # this asset was built with": the newest entry stored for a mechanism
        # need not be the one the manifest on disk came from, and trusting it
        # silently re-laid-out three harp arms under a flag whose purpose is
        # to change nothing.
        prior = {'m_arm0': dict(cfg, root_y=1.85, l1=1.1, l2=1.1, pinion='down')}
        kept2 = copy.deepcopy(layout); lines2 = []
        LS.plan_arms(score, kept2, cache=str(cache), rails='keep', keep_from=prior, verbose=lines2.append)
        got = kept2['arms']['m_arm0']
        check(abs(got['root_y']-1.85) < 1e-12 and abs(got['l1']-1.1) < 1e-12 and got['pinion'] == 'down',
              f"keep_from beats the cache (kept root_y={got['root_y']}, l1={got['l1']}, pinion={got['pinion']})")
        check(kept2.get('stale_rails') is True and any('built with' in l for l in lines2),
              'and it is still marked stale and named in the log: '
              + next((l.strip() for l in lines2 if 'STALE' in l), '(nothing)'))
        # An incomplete manifest is not a plan: fall back to the cache, loudly.
        kept3 = copy.deepcopy(layout); lines3 = []
        LS.plan_arms(score, kept3, cache=str(cache), rails='keep',
                     keep_from={'m_arm0': {'root_y': 1.85}}, verbose=lines3.append)
        check(abs(kept3['arms']['m_arm0']['root_y']-cfg['root_y']) < 1e-12
              and any('NEWEST CACHED' in l for l in lines3),
              'a half-written manifest falls back to the cache and says which it used')
        # A manifest with the rail but no margins is also half-written: a
        # keep-build that dropped them once poisoned the next keep-build.
        kept4 = copy.deepcopy(layout); lines4 = []
        LS.plan_arms(score, kept4, cache=str(cache), rails='keep',
                     keep_from={'m_arm0': {k: v for k, v in prior['m_arm0'].items() if k != 'margins'}},
                     verbose=lines4.append)
        check(abs(kept4['arms']['m_arm0']['root_y']-cfg['root_y']) < 1e-12
              and any('NEWEST CACHED' in l for l in lines4),
              'a manifest missing its margins is refused as a record too')
        check(kept2['arms']['m_arm0'].get('margins') == cfg['margins'],
              'a kept plan carries the margins it achieved (test_gantry reads them back)')
        # ...and a replan-build does not silently accept it
        fresh = copy.deepcopy(layout)
        try:
            LS.plan_arms(score, fresh, cache=str(cache), verbose=lambda *a: None)
            searched = not fresh.get('stale_rails')
        except Exception as e:                       # a one-string fixture may have no feasible rail
            searched = True; print(f'    (the default replanned and refused the fixture: {e})')
        check(searched, 'the default re-searches rather than reusing a plan for other inputs')
    finally:
        cache.unlink(missing_ok=True)

if __name__ == '__main__':
    run()
    print('RAIL CACHE: '+('FAIL' if failures else 'PASS'))
    sys.exit(1 if failures else 0)
