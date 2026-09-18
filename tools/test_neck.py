"""The harp's and the rake's necks carry their strings the way a harp's does.

    python3 tools/test_neck.py            # both built assets

From each built layout: the action plate stands on the neck's string-side
face (its bead crests), proud toward the strings by NECK['plate'] and clear
of the string plane; every disc sits on the plate with its fork pins reaching
past the string plane on either side of the string; the bridge pin stands at
the plate on the +x side of the string and the tuning pin, through the neck
and out its far face, on the -x side, so the dead length leans from one to
the other; the manifest recorded the dead length's turning points the Godot
scene draws; the recipe puts no ferrule at a string's upper end.
"""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from formlab.layout import NECK,neck_plan,pin_wrap
from formlab.recipes import action_plate,neck_faces,harp_frame,harp_backbone
from formlab.sweep import validate_mesh

failures=[]
def check(ok,msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def run(layout_path):
    print(f'== {layout_path.name}')
    layout=json.loads(layout_path.read_text())
    for mid in ('harp','rake'):
        els=sorted([dict(s,id=sid) for sid,s in layout['strings'].items() if s['mid']==mid],key=lambda e:e['a'][0])
        if not els: continue
        plane=els[0]['a'][2]; faces=neck_faces(els); backbone,_,_=harp_backbone(els); V=backbone.vertices
        plate,far=action_plate(els); P=plate.vertices; F=far.vertices
        check(validate_mesh(plate)['ok'] and validate_mesh(far)['ok'] and validate_mesh(backbone)['ok'],f'{mid}: both plates and the backbone are closed meshes')
        worst_far=0
        # The plate stands on the crests: its inner face at the neck's string-side
        # face, its outer face NECK['plate'] nearer the strings, and every point of
        # it between the string plane and the neck's centre.
        gap=min(f['face'] for f in faces.values())-plane
        check(gap>=NECK['plate']+2*NECK['disc_half']+.02,f'{mid}: neck face {gap*1000:.0f} mm off the string plane leaves room for the plate and discs')
        check(P[:,2].min()>plane+.02 and P[:,2].max()<plane+.20,f'{mid}: plate between the string plane and the neck ({P[:,2].min()-plane:.3f}..{P[:,2].max()-plane:.3f} m)')
        worst=1e9
        for e in els:
            f=faces[e['id']]; b=np.array(e['b']); n=neck_plan(e['b'],f['face'],f['back'],discs=mid=='harp')
            near=P[abs(P[:,0]-b[0])<.03]   # the plate's rings at this string (profile corners, not its centreline)
            worst=min(worst,abs(near[:,2].min()-n['plate_out']))
            worst_far=max(worst_far,abs(F[abs(F[:,0]-b[0])<.03][:,2].max()-(f['back']+NECK['plate'])))
            # the discs on the plate, the fork pins either side of the string, past the plane
            for d in n['discs']:
                c=d['centre']; check(abs(c[2]+d['half']-n['plate_out'])<1e-9 and abs(c[0]-b[0])<1e-9,f'{e["id"]}: disc at y+{c[1]-b[1]:.3f} sits on the plate over the string')
                xs=sorted(p[0] for p in d['pins'])
                check(xs[0]<b[0]-NECK['fork_r']-.003 and xs[1]>b[0]+NECK['fork_r']+.003 and d['pin_tip']<plane-.005 and d['pins'][0][2]<c[2],
                      f'{e["id"]}: fork pins straddle the string and reach {(plane-d["pin_tip"])*1000:.0f} mm past its plane')
            br=n['bridge']; tp=n['pin']
            check(br['centre'][0]>b[0]+br['r']-1e-9 and br['z'][0]<plane and abs(br['z'][1]-n['plate_out'])<1e-9,f'{e["id"]}: bridge pin at the plate on the +x side, through the string plane')
            check(tp['centre'][0]+tp['r']<b[0]-.01 and tp['z'][0]<plane and tp['z'][1]>f['back']+NECK['plate']+.02 and tp['key'][2]>tp['z'][1],
                  f'{e["id"]}: tuning pin -x of the string, through the neck and the far plate, key proud of it')
            # the pin passes inside the neck's height and clear of the neighbouring strings
            check(f['y']-NECK['pin_y']-b[1]<.16,f'{e["id"]}: tuning pin at y+{NECK["pin_y"]:.3f} lies within the neck (centreline y+{f["y"]-b[1]:.3f})')
            others=[o for o in els if o is not e]; nearest=min(abs(o['b'][0]-tp['centre'][0]) for o in others)
            check(nearest>tp['r']+.01,f'{e["id"]}: tuning pin {nearest*1000:.0f} mm from the nearest other string')
            # the dead length: b, up the string line to the bridge, then leaning to the pin
            dead=n['dead']; check(dead[0]==list(e['b']) and dead[1][0]==b[0] and dead[1][1]>b[1] and dead[2][1]>dead[1][1] and dead[2][0]<dead[1][0],
                                  f'{e["id"]}: dead length b -> bridge -> tuning pin')
            rec=e.get('neck'); check(rec is not None and rec['bridge']==br['contact'] and rec['pin']==tp['contact'],f'{e["id"]}: manifest carries the dead length\'s turning points')
            # ...and winds on the tuning pin toward the neck: the manifest's wrap is the plan's,
            # on the pin's axis at the string plane; the pin has room short of the plate for the
            # turns of this string's gauge coil beside coil; and the coil clears the neighbouring
            # strings' pins and dead lengths.
            w=pin_wrap(tp,n['plate_out']); wr=.0035*2**((64-e['midi'])/18); coil_r=w['r']+2*wr
            check(rec is not None and rec.get('wrap')==w and w['centre'][:2]==tp['centre'] and w['centre'][2]==plane and w['r']==tp['r'],f'{e["id"]}: manifest carries the wrap on the tuning pin')
            check(w['room']>=w['turns']*2*wr+wr and plane+w['room']<n['plate_out'],f'{e["id"]}: {w["turns"]} turns of {wr*1000:.1f} mm wire fit the {w["room"]*1000:.0f} mm of pin short of the plate')
            c=np.array(tp['centre']); gap=1e9
            for o in others:
                on=neck_plan(o['b'],faces[o['id']]['face'],faces[o['id']]['back'],discs=mid=='harp'); orad=.0035*2**((64-o['midi'])/18)
                gap=min(gap,np.linalg.norm(c-np.array(on['pin']['centre']))-on['pin']['r']-coil_r,np.linalg.norm(c-np.array(on['bridge']['centre']))-on['bridge']['r']-coil_r)
                for p,q in zip(on['dead'][:-1],on['dead'][1:]):
                    p=np.array(p[:2]); q=np.array(q[:2]); t=np.clip(np.dot(c-p,q-p)/np.dot(q-p,q-p),0,1)
                    gap=min(gap,np.linalg.norm(c-(p+t*(q-p)))-orad-coil_r)
            check(gap>.02,f'{e["id"]}: the coil clears the neighbouring strings\' pins and dead lengths by {gap*1000:.0f} mm')
        check(worst<.006,f'{mid}: the plate\'s outer face is where the plan says it is (worst {worst*1000:.1f} mm)')
        check(worst_far<.006,f'{mid}: the far plate is seated on the far face at every string (worst {worst_far*1000:.1f} mm)')
        # no ferrule at the string tops: the pieces beyond the backbone all start at a foot
        pieces=harp_frame(els)[1:]
        check(len(pieces)==len(els) and all(any(np.allclose(p.path[0],e['a']) for e in els) for p in pieces),f'{mid}: one ferrule per string, at its foot only')

if __name__=='__main__':
    for p in (ROOT/'harness/assets/clockwork.json',ROOT/'harness/assets/clockwork_expanded.json'):
        if p.exists(): run(p)
    print('NECK: '+('FAIL' if failures else 'PASS'))
    sys.exit(1 if failures else 0)
