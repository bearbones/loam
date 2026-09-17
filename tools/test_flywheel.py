"""The chamber's flywheel is carried and driven the way a real one is.

    python3 tools/test_flywheel.py            # both built assets

From each built layout's `flywheel` plan (formlab.layout.flywheel_plan): the
axle runs through the wheel's centre and both bearing housings; the housings
sit in their blocks on pedestals standing on the sole plate on the floor,
clear of the wheel's faces and hub; the drive pulley is on the axle and the
belt pulley on a stub axle between two ears on the cabinet's end face, in the
drive pulley's plane; each belt band is a true outer tangent of the two
pulleys; and the whole assembly keeps clear of every arm's sweep, every rail
and every obstacle the rail search was promised (except the cabinet face the
bracket bolts to).
"""
import json,sys,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from formlab.layout import flywheel_plan,FLYWHEEL
from formlab import gantry as G
from formlab.rig import Rig
from formlab.clearance import segment_distance

failures=[]
def check(ok,msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def on_axis(p,a,b,r):
    """Distance of point p from the axis of cylinder (a,b) — 0 when it lies on it."""
    a=np.array(a); b=np.array(b); p=np.array(p); u=(b-a)/np.linalg.norm(b-a)
    return float(np.linalg.norm((p-a)-((p-a)@u)*u))

def run(layout_path,score_path):
    print(f'== {layout_path.name}')
    layout=json.loads(layout_path.read_text()); score=json.loads(score_path.read_text())
    plan=layout.get('flywheel'); check(plan is not None,'the layout carries the flywheel plan')
    if plan is None: return
    c=np.array(plan['centre']); r=plan['r']; C=plan['cyls']; B=plan['boxes']; F=FLYWHEEL
    fresh=flywheel_plan(tuple(plan['centre']),r,cabinet_x=-1.8,floor=plan['floor'])
    check(json.dumps(fresh,sort_keys=True)==json.dumps(plan,sort_keys=True),'the recorded plan is what the plan function gives now')
    a,b,_=C['axle']
    check(on_axis(c,a,b,0)<1e-9 and a[2]<c[2]-F['width']/2 and b[2]>c[2]+F['width']/2,'the axle runs through the wheel centre and out both faces')
    for tag in ('back','front'):
        ha,hb,hr=C[tag+' housing']; z=(ha[2]+hb[2])/2
        check(on_axis(ha,a,b,0)<1e-9 and a[2]<=min(ha[2],hb[2]) and b[2]>=max(ha[2],hb[2]),f'{tag} housing on the axle, inside its ends')
        gap=abs(z-c[2])-F['housing_w']/2-max(F['width'],F['hub_w'])/2
        check(gap>=.02,f'{tag} housing clears the wheel face and hub by {gap*1000:.0f} mm')
        (bc,bs)=B[tag+' block']; (pc,ps)=B[tag+' pedestal']
        check(abs(bc[2]-z)<1e-9 and bc[1]+bs[1]/2>ha[1]-hr and bc[1]+bs[1]/2<ha[1],f'{tag} block under the housing, its top inside the housing\'s circle')
        check(abs(pc[2]-z)<1e-9 and abs((pc[1]+ps[1]/2)-(bc[1]-bs[1]/2))<1e-9 and abs((pc[1]-ps[1]/2)-(plan['floor']+F['sole'][1]))<1e-9,
              f'{tag} pedestal from the sole plate up to the block')
        for k in ('l','r'):
            qa,qb,_=C[f'{tag} bolt {k}']; check(abs(qa[1]-(bc[1]+bs[1]/2))<1e-9 and abs(qa[0]-bc[0])<=bs[0]/2,f'{tag} bolt {k} stands on the block top')
    (sc,ss)=B['sole']; check(abs(sc[1]-ss[1]/2-plan['floor'])<1e-9 and all(abs(B[t+' pedestal'][0][2]-sc[2])+F['pedestal'][1]/2<=ss[2]/2 for t in ('back','front')),
                             'the sole plate lies on the floor under both pedestals')
    # the drive: pulleys in one plane, the belt pulley between its ears on the cabinet's end face
    da,db,dr=C['drive pulley']; pa,pb,pr=C['belt pulley']; sa,sb,sr=C['stub axle']
    check(on_axis(da,a,b,0)<1e-9 and a[2]<=min(da[2],db[2]),'the drive pulley is keyed on the axle')
    check(abs((da[2]+db[2])/2-(pa[2]+pb[2])/2)<1e-9,'the belt pulley lies in the drive pulley\'s plane')
    check(on_axis(pa,sa,sb,0)<1e-9 and min(sa[2],sb[2])<min(pa[2],pb[2]) and max(sa[2],sb[2])>max(pa[2],pb[2]),'the belt pulley turns on its stub axle')
    cab=[o for o in layout['obstacles'] if abs(o[0][0]+1.8)<1e-6 and abs(o[1][0]-1.8)<1e-6]
    check(len(cab)==1,'the cabinet obstacle is where the bracket expects it')
    for tag,end in (('back',sa),('front',sb)):
        ec,es=B[tag+' ear']
        check(abs(ec[0]+es[0]/2-(-1.8))<1e-9 and abs(ec[2]-(pa[2]+pb[2])/2)-es[2]/2-F['pulley_w']/2>=.01,f'{tag} ear stands off the cabinet end face, clear of the pulley')
        check(ec[0]-es[0]/2<end[0]<ec[0]+es[0]/2 and ec[2]-es[2]/2<end[2]<ec[2]+es[2]/2 and ec[1]-es[1]/2<end[1]<ec[1]+es[1]/2,f'the stub axle ends inside the {tag} ear')
    for i,band in enumerate(plan['belt']):
        n=np.array(band['normal']); p=np.array(band['a'][:2]); q=np.array(band['b'][:2])
        c1=c[:2]; c2=np.array(plan['belt_pulley_centre'][:2])
        tangent=abs(abs(n@(p-c1))-dr)<1e-9 and abs(abs(n@(q-c2))-pr)<1e-9 and abs(np.linalg.norm(p-c1)-dr)<1e-9 and abs(np.linalg.norm(q-c2)-pr)<1e-9
        along=abs((q-p)@n)<1e-9
        check(tangent and along,f'belt band {i} is an outer tangent of both pulleys ({math.degrees(band["angle"]):.1f} deg)')
    # the assembly against everything that moves and everything promised
    lo,hi=np.array(plan['bounds'][0]),np.array(plan['bounds'][1])
    rig=Rig(score,layout); times=rig.sample_times(30)
    poses={aid: rig.poses(aid,times) for aid in layout['arms']}
    caps=G._caps(layout,poses,1); worst=(1e9,'')
    def box_gap(P,Q,rr):
        # capsule (P,Q,rr) vs the AABB: nearest point of each segment sample to the box
        best=1e9
        for s in np.linspace(0,1,9):
            X=P+(Q-P)*s; d=np.linalg.norm(np.maximum(np.maximum(lo-X,X-hi),0),axis=1)-rr; best=min(best,float(d.min()))
        return best
    for aid,arm in caps.items():
        for name,(P,Q,ra) in arm.items():
            g=box_gap(P,Q,ra)
            if g<worst[0]: worst=(g,f'{aid} {name}')
        for A,Bp,rr in list(G.rail_bars(layout['arms'][aid]))+list(G.rail_racks(layout['arms'][aid])):
            g=box_gap(A[None],Bp[None],rr)
            if g<worst[0]: worst=(g,f'rail {aid}')
    check(worst[0]>=.05,f'the assembly clears every arm and rail by {worst[0]:.3f} m ({worst[1]})')
    for k,(olo,ohi) in enumerate(layout['obstacles']):
        olo=np.array(olo); ohi=np.array(ohi); apart=float(np.linalg.norm(np.maximum(np.maximum(olo-hi,lo-ohi),0)))
        if k==0: check(apart<1e-9 and hi[0]<=olo[0]+1e-9,'the bracket meets the cabinet at its end face and nothing crosses it')
        else: check(apart>=.05,f'clear of obstacle {k} by {apart:.3f} m')

if __name__=='__main__':
    for lp,sp in ((ROOT/'harness/assets/clockwork.json',ROOT/'render/chamber/score.json'),
                  (ROOT/'harness/assets/clockwork_expanded.json',ROOT/'render/clockwork/score.json')):
        if lp.exists(): run(lp,sp)
    print('FLYWHEEL: '+('FAIL' if failures else 'PASS'))
    sys.exit(1 if failures else 0)
