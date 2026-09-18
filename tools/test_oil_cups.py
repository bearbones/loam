"""Every arm's upper link carries an oil cup on its elbow fork, with the room it needs.

    python3 tools/test_oil_cups.py            # both built assets

From each built layout's arms (`oil_cups`, recorded by build_forms from
formlab.linkage.link): every arm's upper link carries one cup on its elbow
fork's +X ear rim, beyond the pin along the link's line, in the ear's own
layer along the pin (so nothing of the arm's own stack shares its space); and,
posed through the whole score, no cup comes within 20 mm of another arm's
sweep, any rail or rack, any string's speaking length, or any obstacle the
rail search was promised. (The lower link's fork works at the wrist, where a
rake's sweep carried a cup to within millimetres of the strings — so none there.)
"""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from formlab.linkage import CUP,cup_height
from formlab.clearance import DEFAULT_SPEC,default_layers,segment_distance
from formlab import gantry as G
from formlab.rig import Rig

failures=[]
def check(ok,msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def run(layout_path,score_path):
    print(f'== {layout_path.name}')
    layout=json.loads(layout_path.read_text()); score=json.loads(score_path.read_text())
    spec=dict(DEFAULT_SPEC); L=default_layers(spec); ear_x=(L['gap']+spec['ear_t'])/2
    rig=Rig(score,layout); times=rig.sample_times(30)
    poses={aid: rig.poses(aid,times) for aid in layout['arms']}
    caps=G._caps(layout,poses,1)
    X=np.array([1.,0,0]); worst=(1e9,'')
    def gap_to_caps(C,rc,arm):
        best=1e9
        for name,(P,Q,r) in arm.items():
            d=segment_distance(C,C,P,Q)-r-rc; best=min(best,float(d.min()))
        return best
    strings=[(np.array(s['a']),np.array(s['b'])) for s in layout['strings'].values()]
    count=0
    for aid,cfg in sorted(layout['arms'].items()):
        cups=cfg.get('oil_cups',[])
        # the upper link only: a cup on the lower link's fork works at the wrist,
        # where a rake's sweep carried it to within millimetres of the strings
        ok=len(cups)==1 and cups[0]['part']=='upper'
        for c in cups:
            cx,cy,cz=c['centre']; length=float(cfg['l1'] if c['part']=='upper' else cfg['l2'])
            ok&=abs(cx-ear_x)<1e-9 and abs(cy-(length+spec['ear_r']))<1e-9 and abs(cz)<1e-9 and c['axis']==[0,1,0]
            ok&=abs(c['h']-cup_height())<1e-9 and c['r']>=CUP['r']
        check(ok,f'{aid}: an oil cup on the upper link\'s elbow fork, +X ear rim, on the link\'s line beyond the pin')
        if not ok: continue
        pose=poses[aid]; count+=len(cups)
        for c in cups:
            A,B=(pose['root'],pose['elbow']) if c['part']=='upper' else (pose['elbow'],pose['wrist'])
            d=B-A; d/=np.linalg.norm(d,axis=1)[:,None]
            C=B+d*(spec['ear_r']+c['h']/2)+X*c['centre'][0]; rc=max(c['r'],c['h']/2)
            for other,arm in caps.items():
                if other==aid: continue
                g=gap_to_caps(C,rc,arm)
                if g<worst[0]: worst=(g,f'{aid} {c["part"]} cup vs {other}')
            for oid,ocfg in layout['arms'].items():
                for P,Q,r in list(G.rail_bars(ocfg))+list(G.rail_racks(ocfg)):
                    g=float((segment_distance(C,C,P[None],Q[None])-r-rc).min())
                    if g<worst[0]: worst=(g,f'{aid} {c["part"]} cup vs rail {oid}')
            for a,b in strings:
                g=float((segment_distance(C,C,a[None],b[None])-rc-.01).min())
                if g<worst[0]: worst=(g,f'{aid} {c["part"]} cup vs a string')
            for k,(lo,hi) in enumerate(layout['obstacles']):
                lo=np.array(lo); hi=np.array(hi); g=float((np.linalg.norm(np.maximum(np.maximum(lo-C,C-hi),0),axis=1)-rc).min())
                if g<worst[0]: worst=(g,f'{aid} {c["part"]} cup vs obstacle {k}')
    check(worst[0]>=.02,f'every cup clears every other arm, rail, string and obstacle by {worst[0]:.3f} m ({worst[1]})')
    print(f'  {count} oil cups; cup {cup_height()*1000:.0f} mm tall on the ear rim, r {CUP["r"]*1000:.0f} mm')

if __name__=='__main__':
    for lp,sp in ((ROOT/'harness/assets/clockwork.json',ROOT/'render/chamber/score.json'),
                  (ROOT/'harness/assets/clockwork_expanded.json',ROOT/'render/clockwork/score.json')):
        if lp.exists(): run(lp,sp)
    print('OIL CUPS: '+('FAIL' if failures else 'PASS'))
    sys.exit(1 if failures else 0)
