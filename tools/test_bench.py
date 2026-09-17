"""The trestle benches follow their construction rules. python3 tools/test_bench.py

Rails along the row on a trestle at each end, a bearer under every element,
mounts that reach the element (pads at a block's nodes, a bell's post into its
crown) and nothing above any element's underside; the bench stays inside the
footprint of the plank bed it replaced, so the gantry plan is unmoved.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formlab.layout import bench_plan,bench_elements,bar_nodes,BENCH,BELL,BAR
from formlab.recipes import bench_frame
from formlab.sweep import validate_mesh
root=Path(__file__).resolve().parents[1]
layout=json.loads((root/'harness/assets/clockwork_expanded.json').read_text())
fails=[]
def check(label,ok,detail=''):
    print(('  PASS ' if ok else '  FAIL ')+label+(': '+str(detail) if detail else ''))
    if not ok: fails.append(label)
benched=[mid for mid,m in layout['mechanisms'].items() if m['kind']=='struck' and mid!='bars']
check('the expanded rig has benched instruments',len(benched)>=2,benched)
for mid in benched:
    mech=layout['mechanisms'][mid]
    els=bench_elements([dict(s,id=sid) for sid,s in layout['strings'].items() if s['mid']==mid],mech['material'])
    plan=bench_plan(els); pieces=bench_frame(plan)
    xs=np.array([s['a'][0] for s in els]); under=min(s['underside'] for s in els)
    if mech['material']=='glass':
        check(mid+': bell undersides are the lip, drop+mouth below the strike point',all(abs(s['a'][1]-s['underside']-BELL['drop']-BELL['mouth'])<1e-9 for s in els))
    else:
        check(mid+': block undersides are one bar thickness below the strike point',all(abs(s['a'][1]-s['underside']-BAR['thick'])<1e-9 for s in els))
    check(mid+': rails run past both end elements',plan['x'][0]<xs.min()-.2 and plan['x'][1]>xs.max()+.2)
    check(mid+': bearer tops one pad below the lowest underside',abs(plan['top']-(under-BENCH['pad']))<1e-9)
    check(mid+': a bearer under every element at its x',sorted(b['x'] for b in plan['bearers'])==sorted(xs.tolist()))
    check(mid+': bearers rest on the rails',all(abs(b['y']-BENCH['bearer_half_y']-plan['rail_top'])<1e-9 for b in plan['bearers']))
    for mt,s in zip(plan['mounts'],sorted(els,key=lambda s:s['a'][0])):
        if mt['kind']=='post':
            check(mid+' '+mt['id']+': post rises from the bearer into the crown',abs(mt['y0']-plan['top'])<1e-9 and s['top']-BELL['post_in']-1e-9<=mt['y1']<s['top'])
            check(mid+' '+mt['id']+': post fits the bell mouth',BELL['flange_r']<.14 and BELL['post_r']<.05)
        else:
            n=bar_nodes(s['a'],s['b'])
            check(mid+' '+mt['id']+': pads at the block\'s nodal points',np.allclose(mt['z'],[n[0][2],n[1][2]]) and abs(mt['y1']-s['underside'])<1e-9)
    for e in plan['ends']:
        check(mid+': legs splay outward to the floor',all(abs(l['toe'][2]-plan['z'])>abs(l['top'][2]-plan['z']) and l['toe'][1]<l['top'][1] for l in e['legs']))
        check(mid+': tie meets the legs between floor and crossbar',e['floor']<e['tie_y']<e['cross_y'] and e['tie_z'][0]<e['tie_z'][1])
    V=np.concatenate([p.vertices for p in pieces])
    check(mid+': nothing above the lowest underside',V[:,1].max()<under)
    check(mid+': feet on the floor',V[:,1].min()>=-.02)
    cx,cz=mech['center'][0],mech['center'][2]
    check(mid+': inside the old bed footprint (z ±.75, x within the bed)',abs(V[:,2]-cz).max()<.75 and V[:,0].min()>cx-(xs.max()-xs.min())/2-.5 and V[:,0].max()<cx+(xs.max()-xs.min())/2+.5)
    reports=[validate_mesh(p) for p in pieces]
    check(mid+': every timber piece closed with positive volume',all(r['ok'] for r in reports),[r for r in reports if not r['ok']][:2])
    promised=[o for o in layout['obstacles'] if o[0][0]<plan['x'][0]<=o[1][0] and o[0][2]<plan['z']<o[1][2]]
    check(mid+': bench promised to the rail search as an obstacle',len(promised)==1)
    if promised:
        lo,hi=promised[0]
        check(mid+': bench inside its promised obstacle',V[:,0].min()>=lo[0] and V[:,0].max()<=hi[0] and V[:,1].max()<=hi[1] and V[:,2].min()>=lo[2] and V[:,2].max()<=hi[2],(lo,hi,V.min(0).round(3),V.max(0).round(3)))
    check(mid+': fascia hangs below the front rail, in front of the bearers',plan['board']['y']<plan['rail_y'] and plan['board']['z']>max(b['z'][1] for b in plan['bearers']))
if fails: raise SystemExit('BENCH: FAIL '+', '.join(fails))
print('BENCH: PASS')
