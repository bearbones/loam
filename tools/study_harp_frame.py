"""Equal-volume variable-depth neck benchmark with explicit assumed inputs.
Run from repo root: python3 tools/study_harp_frame.py. No Blender dependency.
"""
import json,sys
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formlab.frame import solve
ROOT=Path(__file__).resolve().parents[1]; out=ROOT/'render/form-study'; out.mkdir(exist_ok=True,parents=True)
score=json.loads((ROOT/'render/chamber/score.json').read_text())
harp=next(m for m in score['instrument']['mechanisms'] if m['id']=='harp')
anchors=np.array([[3*(harp['pos'][0]+s['pos'][0]),
    2.05+3*(harp['pos'][1]+s['pos'][1])+1.5*s['length']] for s in harp['strings']])
curve=PchipInterpolator(anchors[:,0],anchors[:,1]+.2)
width=.22; h0=.22; E=10e9; tension=100.
# Each control interval subdivides exactly; string loads remain at actual anchor X.
def problem(subdivision, controls=None):
    x=np.unique(np.concatenate([np.linspace(a,b,subdivision+1) for a,b in zip(anchors[:-1,0],anchors[1:,0])]))
    nodes=np.c_[x,curve(x)]; edges=np.c_[np.arange(len(x)-1),np.arange(1,len(x))]
    F=np.zeros((len(x),3))
    for ax in anchors[:,0]: F[np.argmin(abs(x-ax)),1]-=tension
    depths=np.full(len(edges),h0) if controls is None else np.interp((x[:-1]+x[1:])/2,anchors[:,0],controls)
    result=solve(nodes,edges,F,[0,1,2,3*len(x)-3,3*len(x)-2,3*len(x)-1],E,width,depths)
    return result,nodes,depths
base,_,_=problem(4)
V=base['volume']; scale=base['compliance']
def objective(h):
    r,_,_=problem(4,h)
    return r['compliance']/scale + .012*np.sum(np.diff(h,2)**2)/h0**2
constraint={'type':'eq','fun':lambda h:(problem(4,h)[0]['volume']-V)/V}
opt=minimize(objective,np.full(len(anchors),h0),method='SLSQP',bounds=[(.10,.38)]*len(anchors),constraints=[constraint],options={'maxiter':100,'ftol':1e-10})
if not opt.success: raise RuntimeError(opt.message)
records=[]
for n in (2,4,8,16):
    rb,_,_=problem(n); ro,_,_=problem(n,opt.x)
    records.append(dict(subdivision=n,elements=15*n,uniform_compliance=rb['compliance'],variable_compliance=ro['compliance'],
        reduction=1-ro['compliance']/rb['compliance'],uniform_volume=rb['volume'],variable_volume=ro['volume'],
        uniform_max_deflection_m=float(np.linalg.norm(rb['displacement'][:,:2],axis=1).max()),
        variable_max_deflection_m=float(np.linalg.norm(ro['displacement'][:,:2],axis=1).max()),residual=ro['residual']))
result=dict(classification='solved illustrative planar neck, not a structural certification of the display mesh',
 assumptions=dict(E_Pa=E,width_m=width,mean_depth_m=h0,string_tension_N=tension,supports='both end translations and rotations clamped; piers assumed rigid',
                 excluded='self weight, lower rail, root flexibility, joints, anisotropy, torsion, buckling and dynamics'),
 x=anchors[:,0].tolist(),depth_m=opt.x.tolist(),refinement=records)
assert abs(records[1]['variable_volume']/records[1]['uniform_volume']-1)<1e-7
assert records[-1]['reduction']>.03
assert max(r['residual'] for r in records)<1e-5
assert abs(records[-1]['variable_compliance']/records[-2]['variable_compliance']-1)<.02
(out/'structure.json').write_text(json.dumps(result,indent=2))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(2,1,figsize=(10,7),layout='constrained')
axes[0].plot(anchors[:,0],np.full(len(anchors),h0),label='Uniform depth',color='#aaa')
axes[0].plot(anchors[:,0],opt.x,label='Variable depth, same volume',color='#996329',linewidth=3)
axes[0].set(xlabel='Neck x (assumed m)',ylabel='Section depth (m)',title='An illustrative neck: redistribute the same material');axes[0].legend();axes[0].grid(alpha=.2)
for label,h,color in [('Uniform',None,'#888'),('Variable',opt.x,'#996329')]:
    r,n,_=problem(16,h);axes[1].plot(n[:,0],r['displacement'][:,1]*1000,label=label,color=color)
axes[1].set(xlabel='Neck x (assumed m)',ylabel='Vertical displacement (mm)',title=f"Compliance reduced {records[-1]['reduction']:.1%}; assumptions are in structure.json")
axes[1].legend();axes[1].grid(alpha=.2)
fig.savefig(out/'structure.png',dpi=160)
print(json.dumps(result,indent=2))
