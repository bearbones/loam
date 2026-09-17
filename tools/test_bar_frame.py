"""The bar instrument's frame follows its construction rules. python3 tools/test_bar_frame.py

Rails under the bars' nodal lines, end frames as wide as the local rail spread,
closed quarter-wave resonators between the rails, posts between the bars, and a
frame that stays inside the old bed's footprint so the gantry plan is unmoved.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formlab.layout import bar_frame_plan,bar_nodes,resonator,board_z,NODE,BAR,RAIL,END,RESONATOR
from formlab.recipes import bar_frame
from formlab.sweep import validate_mesh
root=Path(__file__).resolve().parents[1]
layout=json.loads((root/'harness/assets/clockwork.json').read_text())
bars={sid:dict(s,id=sid) for sid,s in layout['strings'].items() if s['mid']=='bars'}
plan=bar_frame_plan(list(bars.values()))
fails=[]
def check(label,ok,detail=''):
    print(('  PASS ' if ok else '  FAIL ')+label+(': '+str(detail) if detail else ''))
    if not ok: fails.append(label)

# Nodes 22.4 % in from each end, on the bar's own line.
s=bars['bars00']; a,b=np.array(s['a']),np.array(s['b']); n=np.array(bar_nodes(a,b))
check('nodes sit NODE in from each end',np.allclose(n[0],a+(b-a)*NODE) and np.allclose(n[1],b-(b-a)*NODE))
# The rails pass through every bar's nodes and converge toward the high bars.
xs=np.array([s['a'][0] for s in bars.values()]); order=np.argsort(xs)
for side,k in (('back',0),('front',1)):
    R=plan['rails'][side]; miss=[]
    for s in bars.values():
        nz=bar_nodes(s['a'],s['b'])[k][2]; miss.append(abs(np.interp(s['a'][0],R[:,0],R[:,2])-nz))
    check(f'{side} rail runs through the node line (max miss {max(miss)*1000:.1f} mm)',max(miss)<1e-9)
spread=plan['rails']['front'][:,2]-plan['rails']['back'][:,2]
check('rails converge toward the short bars',np.all(np.diff(spread)<0),[round(v,3) for v in spread])
check('rails run RAIL.over past the end bars',np.isclose(plan['rails']['back'][0,0],xs.min()-RAIL['over']) and np.isclose(plan['rails']['back'][-1,0],xs.max()+RAIL['over']))
# Rail top sits the declared gap under the bars; the cord runs at mid-thickness.
bottom=min(s['a'][1] for s in bars.values())-BAR['thick']
check('rail top is rail_gap under the bars',np.isclose(plan['rail_top'],bottom-BAR['rail_gap']))
check('cord at the bars\' mid-thickness',np.isclose(plan['cord_y'],bottom+BAR['thick']/2))
# Posts stand between bars (never inside one) and top out under the bar tops.
half_w=min(.24,2.7/len(bars)*.7)/2
for side,posts in plan['posts'].items():
    inside=[p for p in posts if any(abs(p['x']-x)<half_w+.012 for x in xs)]
    check(f'{side} posts stand clear of every bar',not inside,[round(p['x'],3) for p in inside])
    check(f'{side} posts and cushions stay under the bar tops',all(p['y1']+.016<bottom+BAR['thick'] for p in posts))
    check(f'{side} has one post per gap plus one past each end bar',len(posts)==len(bars)+1)
# Resonators: quarter-wave with the open-end correction, capped to hang between the rails.
r,L=resonator(69.0,.2); check('A4 tube is c/4f less .61 r (world x3)',np.isclose(L,3*RESONATOR['c']/(4*440)-.61*r) and r==RESONATOR['r_max'])
r,L=resonator(74.0,.118); check('a narrow node spread caps the tube radius',np.isclose(r,.118-RAIL['half_z']-RESONATOR['rail_gap']))
res=sorted(plan['resonators'],key=lambda r:r['x'])
check('tubes shorten toward the high bars',all(p['length']>q['length'] for p,q in zip(res,res[1:])),[round(r['length'],3) for r in res])
for rr in res:
    s=bars[rr['id']]; nz=bar_nodes(s['a'],s['b']); inner=min(abs(nz[k][2]-rr['z']) for k in (0,1))-RAIL['half_z']
    check(f'{rr["id"]} tube keeps {RESONATOR["rail_gap"]*1000:.0f} mm from the rails',inner-rr['radius']>=RESONATOR['rail_gap']-1e-9,f'{(inner-rr["radius"])*1000:.1f} mm')
    check(f'{rr["id"]} tube hangs from under the bar and clears the stretcher',np.isclose(rr['top'],bottom-RESONATOR['top_gap']) and rr['top']-rr['length']>plan['stretcher']['y']+.06)
# Ends: the bass end stands broader; every foot is on the floor; the board is on the front uprights.
e0,e1=plan['ends']
check('bass end frame is broader than the treble end',(e0['z_front']-e0['z_back'])>(e1['z_front']-e1['z_back'])+.1)
check('uprights stand END.upright outside the rails',all(np.isclose(e['uprights'],[e['z_back']-END['upright'],e['z_front']+END['upright']]).all() for e in plan['ends']))
check('rails rest on the crosspieces',all(np.isclose(e['cross_y']+END['half_x'],plan['rail_y']-RAIL['half_y']) for e in plan['ends']))
check('name board face is proud of the front uprights',all(np.isclose(plan['board']['z'][i]-END['half_x'],e['uprights'][1]+.0125) for i,e in enumerate(plan['ends'])))
check('board_z interpolates between the ends',np.isclose(board_z(plan,plan['board']['x'][0]),plan['board']['z'][0]) and np.isclose(board_z(plan,plan['board']['x'][1]),plan['board']['z'][1]))
# The swept frame: every piece closed; nothing above the bars' underside; within the old bed's footprint.
pieces=bar_frame(plan); reports=[validate_mesh(m) for m in pieces]
check(f'all {len(pieces)} frame pieces are closed, positive-volume meshes',all(r['ok'] for r in reports),[r for r in reports if not r['ok']])
V=np.concatenate([m.vertices for m in pieces])
check('no timber reaches the bars\' underside',V[:,1].max()<bottom-.01,f'top {V[:,1].max():.3f} vs bars {bottom:.3f}')
check('feet stand on the stage',abs(V[:,1].min()-(-.01))<1e-6,round(float(V[:,1].min()),4))
zc=float(np.mean([(s['a'][2]+s['b'][2])/2 for s in bars.values()]))
check('frame stays inside the old bed footprint in z (gantry plan unmoved)',V[:,2].min()>zc-.75 and V[:,2].max()<zc+.75,(round(float(V[:,2].min()),3),round(float(V[:,2].max()),3)))
check('frame stays within .45 m of the end bars in x',V[:,0].min()>xs.min()-.45 and V[:,0].max()<xs.max()+.45)
for m in pieces[:2]:   # rails: a +X path puts the 60 mm depth in Y and the 70 mm width in Z
    ext=m.vertices[:-2].reshape(-1,len(m.vertices[:-2])//len(m.path),3)
    check('rail section is 60 mm deep by 70 mm wide',np.isclose(ext[5,:,1].max()-ext[5,:,1].min(),2*RAIL['half_y'],atol=1e-3) and np.isclose(ext[5,:,2].max()-ext[5,:,2].min(),2*RAIL['half_z'],atol=1e-3))
# The frame's footprint is promised to the rail search (build_clockwork.py) up to the bars' underside.
V=np.concatenate([p.vertices for p in bar_frame(plan)])
promised=[o for o in layout['obstacles'] if o[0][0]<V[:,0].min() and V[:,0].max()<o[1][0] and o[0][2]<V[:,2].min() and V[:,2].max()<o[1][2] and abs(o[1][1]-plan['bar_bottom'])<1e-9]
check('frame promised to the rail search as an obstacle up to the bar underside',len(promised)==1)
if fails: raise SystemExit('BAR FRAME: FAIL '+', '.join(fails))
print('BAR FRAME: PASS')
