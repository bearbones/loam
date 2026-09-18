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
import json,sys,math,struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from formlab.layout import flywheel_plan,spoke_centre,spoke_section,FLYWHEEL
from formlab.gear import profile
from formlab import gantry as G
from formlab.rig import Rig
from formlab.clearance import segment_distance

failures=[]
def check(ok,msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def glb_vertices(path,name):
    """World-space vertices of the named node's mesh in a binary glTF: the JSON
    chunk names the node and its accessor, the BIN chunk holds the floats, and
    the node's own translation/rotation/scale puts them in the scene (the
    builder parents nothing, so a node's transform is its world placement)."""
    b=path.read_bytes()
    if b[:4]!=b'glTF': raise ValueError(f'{path} is not a binary glTF')
    n=struct.unpack_from('<I',b,12)[0]; js=json.loads(b[20:20+n]); off=20+n
    m=struct.unpack_from('<I',b,off)[0]; binc=b[off+8:off+8+m]
    node=next((x for x in js['nodes'] if x.get('name')==name),None)
    if node is None or 'mesh' not in node: raise KeyError(f'no mesh node {name!r} in {path.name}')
    V=[]
    for prim in js['meshes'][node['mesh']]['primitives']:
        acc=js['accessors'][prim['attributes']['POSITION']]; bv=js['bufferViews'][acc['bufferView']]
        start=bv.get('byteOffset',0)+acc.get('byteOffset',0); stride=bv.get('byteStride',12)
        if stride==12: V.append(np.frombuffer(binc,dtype='<f4',count=acc['count']*3,offset=start).reshape(-1,3))
        else: V.append(np.stack([np.frombuffer(binc,dtype='<f4',count=3,offset=start+k*stride) for k in range(acc['count'])]))
    V=np.concatenate(V).astype(float)
    x,y,z,w=node.get('rotation',[0,0,0,1])
    R=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
    return (V*np.array(node.get('scale',[1,1,1])))@R.T+np.array(node.get('translation',[0,0,0]))

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
        # the split housing: the cap's D-section closes the seat over the flange whose
        # underside is the block's top; studs up through the flange, nuts on them,
        # the oil cup on the cap's crown
        cap=plan.get('caps',{}).get(tag); top=bc[1]+bs[1]/2
        check(cap is not None,f'{tag} block has a cap');
        if cap is None: continue
        fx,ft=cap['flange']
        check(abs(cap['centre'][0]-ha[0])<1e-9 and abs(cap['centre'][1]-ha[1])<1e-9 and abs(cap['centre'][2]-z)<1e-9 and cap['r']>hr and cap['w']>=F['housing_w'],
              f'{tag} cap sits on the housing, its wall {(cap["r"]-hr)*1000:.0f} mm proud')
        check(abs(cap['split']-top)<1e-9 and abs((ha[1]-ft/2)-top)<1e-9 and fx<=bs[0]/2+.03,f'{tag} flange underside is the block top, split at the axle')
        for k in ('l','r'):
            sa,sb,sr=C[f'{tag} stud {k}']; na,nb,nr=C[f'{tag} nut {k}']
            clear=math.sqrt(cap['r']**2-(ft/2)**2)
            check(abs(sa[0]-sb[0])<1e-9 and sa[1]<top and sb[1]>nb[1] and clear+sr<abs(sa[0]-bc[0])<=fx-sr and abs(sa[0]-bc[0])<=bs[0]/2 and abs(sa[2]-z)<1e-9,
                  f'{tag} stud {k} rises out of the block through the flange, outside the cap\'s wall')
            check(abs(na[0]-sa[0])<1e-9 and abs(na[2]-sa[2])<1e-9 and abs(na[1]-(ha[1]+ft/2))<1e-9 and nb[1]>na[1] and nr>sr,f'{tag} nut {k} sits on the flange round its stud')
        oa,ob,orr=C[tag+' oil cup']; la,lb,lr=C[tag+' oil cup lid']
        check(abs(oa[0]-ha[0])<1e-9 and abs(oa[2]-z)<1e-9 and abs(oa[1]-(ha[1]+cap['r']))<1e-9 and ob[1]>oa[1] and abs(la[1]-ob[1])<1e-9 and lb[1]>la[1] and lr>orr,
              f'{tag} oil cup stands on the cap\'s crown under its lid')
    # the casting: a rim under the teeth's roots, spokes from the hub boss to it, inside the wheel's width
    S=plan.get('spokes'); check(S is not None,'the plan casts the wheel with spokes')
    if S is not None:
        prof=profile(int(plan['teeth']),r); depth=prof['r_hub']-S['r_rim']; span=S['r_rim']-S['r_hub']
        check(depth>=.04 and span>=.15,f'the rim is {depth*1000:.0f} mm deep under the roots and the spokes span {span*1000:.0f} mm')
        check(abs(S['r_hub']-C['hub'][2])<1e-9 and S['root'][0]<=S['r_hub'] and max(S['root'][1],S['tip'][1])<=F['width']/2 and S['tip'][0]<=S['root'][0],
              'spokes rooted in the hub boss, tapering to the rim, inside the wheel\'s width')
        # the built wheel itself: every vertex between hub and rim lies on a spoke (the disc is gone)
        glb=layout_path.with_suffix('.glb')
        if glb.exists():
            V=glb_vertices(glb,'Chamber flywheel')-c; rho=np.hypot(V[:,0],V[:,1])
            web=(rho>S['r_hub']+.03)&(rho<S['r_rim']-.03); Q=V[web]; u=(rho[web]-S['r_hub'])/span
            on=np.zeros(len(Q),bool)
            for i in range(S['count']):
                cen=np.array([spoke_centre(S,i,ui) for ui in u]); w=np.array([spoke_section(S,ui)[0] for ui in u])
                on|=np.hypot(Q[:,0]-cen[:,0],Q[:,1]-cen[:,1])<=w+.012
            spoked=len(Q)>=S['count']*20
            check(spoked and on.all() and abs(V[:,2]).max()<=F['width']/2+.002,
                  f'the built wheel is spoked: {len(Q)} vertices between hub and rim, {int((~on).sum())} off a spoke, {abs(V[:,2]).max()*1000:.0f} mm half-width')
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
