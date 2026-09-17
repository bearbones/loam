"""The harp's pedal base and the rake's plinth keep the rail search's promise. python3 tools/test_harp_base.py"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formlab.layout import harp_base_plan,PEDALS
root=Path(__file__).resolve().parents[1]
layout=json.loads((root/'harness/assets/clockwork.json').read_text())
fails=[]
def check(label,ok,detail=''):
    print(('  PASS ' if ok else '  FAIL ')+label+(': '+str(detail) if detail else ''))
    if not ok: fails.append(label)
for mid in ('harp','rake'):
    strings=[s for s in layout['strings'].values() if s['mid']==mid]
    left=min(s['a'][0] for s in strings); zz=layout['mechanisms'][mid]['center'][2]+.20
    plan=harp_base_plan(left,zz,with_pedals=mid=='harp')
    # The obstacle the rail search is promised for the base (build_clockwork.py); the box must stay inside it.
    promised=[o for o in layout['obstacles'] if abs(o[0][0]-(left-.82))<1e-6]
    check(mid+': base promised to the rail search as an obstacle',len(promised)==1)
    if not promised: continue
    lo,hi=promised[0]
    b=plan['box']
    check(mid+': base box inside the promised obstacle',b['x'][0]>=lo[0] and b['x'][1]<=hi[0] and b['y'][1]+.05<=hi[1] and b['z'][0]>=lo[2] and b['z'][1]<=hi[2],(b,lo,hi))
    check(mid+': column foot seats in the box',b['x'][0]<left-.32<b['x'][1])
    check(mid+': base under the frame\'s footprint',b['z'][0]<zz-.20 and b['z'][1]>zz+.20)
    if mid=='rake':
        check('rake: a plain plinth, no pedals',plan['pedals']==[])
        continue
    notes=[p['note'] for p in plan['pedals']]
    check('seven pedals D C B | E F G A',tuple(notes)==PEDALS)
    zs=[p['z']-zz for p in plan['pedals']]
    check('three pedals left of the string plane, four right',sum(z<0 for z in zs)==3 and sum(z>0 for z in zs)==4)
    check('treads do not overlap (70 mm wide, gap >= 30 mm)',min(np.diff(zs))>=.10)
    check('pedals stay within the base width',all(b['z'][0]+.035<p['z']<b['z'][1]-.02 for p in plan['pedals']))
    check('levers leave the front face and fall to floor treads',all(p['lever'][0][0]<plan['front_x']<p['lever'][1][0] and p['lever'][1][1]<p['lever'][0][1] and p['tread'][1]<.06 for p in plan['pedals']))
    check('slots sit on the front face within the box height',all(p['slot'][0]==plan['front_x'] and p['slot'][1]>=b['y'][0] and p['slot'][1]+p['slot'][2]<=b['y'][1] for p in plan['pedals']))
if fails: raise SystemExit('HARP BASE: FAIL '+', '.join(fails))
print('HARP BASE: PASS')
