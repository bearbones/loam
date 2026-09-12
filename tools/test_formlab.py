"""Independent numeric claims for the small form kernels. python3 tools/test_formlab.py"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formlab import sample_curve,sweep,validate_mesh
from formlab.frame import solve
from formlab.sweep import transport_frames
# Cantilever closed forms, including axial extension and transverse bending.
L=2.; E=7e9; width=.1; h=.2; force=20.; I=width*h**3/12
nodes=np.array([[0.,0.],[L,0.]]); loads=np.array([[0.,0.,0.],[0.,-force,0.]])
r=solve(nodes,[[0,1]],loads,[0,1,2],E,width,h)
assert np.isclose(r['displacement'][1,1],-force*L**3/(3*E*I),rtol=1e-10)
assert np.isclose(r['displacement'][1,2],-force*L**2/(2*E*I),rtol=1e-10)
assert np.isclose(r['reactions'][0,1],force)
assert np.isclose(r['reactions'][0,2],force*L)
loads[1]=[force,0,0]; r=solve(nodes,[[0,1]],loads,[0,1,2],E,width,h)
assert np.isclose(r['displacement'][1,0],force*L/(E*width*h),rtol=1e-10)
# A rigid rotation must rotate displacements, preserving compliance.
angle=.73; rot=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
rotloads=loads.copy();rotloads[:,:2]=loads[:,:2]@rot.T
rr=solve(nodes@rot.T,[[0,1]],rotloads,[0,1,2],E,width,h)
assert np.allclose(rr['displacement'][:,:2],r['displacement'][:,:2]@rot.T,atol=1e-12)
assert np.isclose(rr['compliance'],r['compliance'],rtol=1e-9)
# A swept circle should converge to the analytic cylinder volume, and be closed.
path=np.c_[np.linspace(0,2,50),np.zeros(50),np.zeros(50)]
m=sweep(path,.1,.1,sides=64); check=validate_mesh(m)
assert check['ok'] and abs(check['volume']/(np.pi*.1**2*2)-1)<.002
# Tight, nonplanar curves have finite orthonormal frames, without sudden twist flips.
path=sample_curve([[0,0,0],[1,.5,.3],[1.2,1.3,.6],[.5,2,1]],160)
t,n,b=transport_frames(path)
assert np.max(abs(np.einsum('ij,ij->i',t,n)))<1e-10
assert np.min(np.einsum('ij,ij->i',n[1:],n[:-1]))>.95
assert validate_mesh(sweep(path,.03,.02))['ok']
# Periodic sweep is a closed genus-one mesh: V-E+F = 0.
a=np.linspace(0,2*np.pi,140,endpoint=False); ring=sweep(np.c_[np.cos(a),np.sin(a),a*0],.1,.08,closed=True)
assert validate_mesh(ring)['ok']
edges=np.unique(np.sort(np.concatenate([ring.faces[:,[0,1]],ring.faces[:,[1,2]],ring.faces[:,[2,0]]]),axis=1),axis=0)
assert len(ring.vertices)-len(edges)+len(ring.faces)==0
print('FORMLAB: PASS — axial/bending closed forms, reactions, rotated frame, volume, topology and transport')

# Traditional display uses a declared scale; the acoustic score remains separate.
import json
root=Path(__file__).resolve().parents[1]
score=json.loads((root/'render/chamber/score.json').read_text())
layout=json.loads((root/'harness/assets/clockwork.json').read_text())
for mechanism in score['instrument']['mechanisms']:
    elements=[]
    for string in mechanism['strings']:
        item=layout['strings'][string['id']]
        a,b=np.array(item['a']),np.array(item['b'])
        assert np.isclose(np.linalg.norm(b-a),3*string['length']*(1.7 if mechanism['id']=='harp' else 1),atol=1e-12)
        assert item['pick']==string['pick_default'] and item['midi']==string['midi']
        elements.append(item)
    if mechanism['id'] in ('harp','rake'):
        assert all(np.allclose(np.array(e['b'])[[0,2]],np.array(e['a'])[[0,2]]) for e in elements)
        assert elements[-1]['a'][1]-elements[0]['a'][1]>1.3
        assert elements[-1]['a'][0]-elements[0]['a'][0]<2.4
from formlab.recipes import handrail_profile
profile=handrail_profile()
assert profile[:,1].max()-profile[profile[:,1]>0,1].min()>.4
assert validate_mesh(sweep(path,.1,.12,profile=profile))['ok']
print('HARP LAYOUT: PASS — declared display scale/pitches/picks; ascending soundboard; moulded profile')
