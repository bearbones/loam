"""Every plucked string leaves its soundbox through a brass eyelet.

    python3 tools/test_eyelets.py            # both built assets

From each built layout's `eyelets` (formlab.layout.eyelet_plan, one per harp and
rake string): the plan is what the plan function gives for the string's foot; its
axis runs down the recipe ferrule's barrel (the two share EYELET['barrel']) and
the string leaves the other way; the flange covers the ferrule's mouth; the lip
stands proud of the flange, inside its rim, with a hole the string's wire clears;
neighbouring eyelets do not touch; and no eyelet is inside any arm's sweep.
"""
import json,sys,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from formlab.layout import eyelet_plan,EYELET
from formlab import gantry as G
from formlab.rig import Rig

failures=[]
def check(ok,msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def wire_radius(midi):
    """performance.gd's gauge for the string's wire (a display gauge)."""
    return .0035*2**((64-midi)/18)

def run(layout_path,score_path):
    print(f'== {layout_path.name}')
    layout=json.loads(layout_path.read_text()); score=json.loads(score_path.read_text())
    plucked={sid: s for sid,s in layout['strings'].items() if not s['struck']}
    eyelets=layout.get('eyelets',{})
    check(set(eyelets)==set(plucked),f'one eyelet per plucked string ({len(eyelets)} of {len(plucked)})')
    barrel=np.array(EYELET['barrel']); u=barrel/np.linalg.norm(barrel)
    rig=Rig(score,layout); times=rig.sample_times(30)
    poses={aid: rig.poses(aid,times) for aid in layout['arms']}
    caps=G._caps(layout,poses,1); worst=(1e9,'')
    feet={}
    for sid,e in sorted(eyelets.items()):
        s=plucked[sid]; a=np.array(s['a']); b=np.array(s['b'])
        ok=json.dumps(e,sort_keys=True)==json.dumps(eyelet_plan(s['a']),sort_keys=True)
        ax=np.array(e['axis']); fl=e['flange']; lip=e['lip']
        ok&=np.allclose(ax,u) and abs(np.linalg.norm(ax)-1)<1e-9 and (b-a)@ax<0
        ok&=np.allclose(fl['a'],a) and np.allclose(np.array(fl['b'])-a,ax*EYELET['flange_h']) and fl['r']>EYELET['ferrule'][0]+.005
        ok&=(np.array(lip['centre'])-a)@ax<0 and lip['r']+lip['t']/2<fl['r'] and lip['hole']>wire_radius(s['midi'])+.002
        if not ok: check(False,f'{sid}: eyelet on the ferrule mouth, lip proud of the flange, hole clear of the wire')
        feet.setdefault(s['mid'],[]).append(a)
        for aid,arm in caps.items():
            for name,(P,Q,r) in arm.items():
                for t in np.linspace(0,1,9):
                    X=P+(Q-P)*t; d=np.linalg.norm(X-a,axis=1)-r-fl['r']
                    if d.min()<worst[0]: worst=(float(d.min()),f'{sid} vs {aid} {name}')
    check(all(json.dumps(e,sort_keys=True)==json.dumps(eyelet_plan(plucked[sid]['a']),sort_keys=True) for sid,e in eyelets.items()),'every recorded eyelet is what the plan function gives now')
    for mid,A in feet.items():
        A=np.array(A); gaps=[np.linalg.norm(A[i]-A[j]) for i in range(len(A)) for j in range(i+1,len(A))]
        check(min(gaps)>2*EYELET['flange_r']+.02,f'{mid}: neighbouring eyelets keep clear of each other (closest {min(gaps):.3f} m)')
    # The margin is 20 mm, not the 50 mm the frames get: the score plucks the
    # shortest treble strings 0.18 of their length above the foot, so the
    # plectrum legitimately works within a hand's breadth of the eyelet.
    check(worst[0]>=.02,f'every eyelet clears every arm sweep by {worst[0]:.3f} m ({worst[1]})')
    print(f'  {len(eyelets)} eyelets; wire radii {min(wire_radius(s["midi"]) for s in plucked.values())*1000:.1f}..{max(wire_radius(s["midi"]) for s in plucked.values())*1000:.1f} mm; hole {EYELET["lip_r"]-EYELET["lip_t"]/2:.3f} m')

if __name__=='__main__':
    for lp,sp in ((ROOT/'harness/assets/clockwork.json',ROOT/'render/chamber/score.json'),
                  (ROOT/'harness/assets/clockwork_expanded.json',ROOT/'render/clockwork/score.json')):
        if lp.exists(): run(lp,sp)
    print('EYELETS: '+('FAIL' if failures else 'PASS'))
    sys.exit(1 if failures else 0)
