"""Checks contour correspondence and closed topology on the real harp joints."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formlab.recipes import harp_backbone,handrail_profile
from formlab.sweep import validate_mesh
root=Path(__file__).resolve().parents[1]
layout=json.loads((root/'harness/assets/clockwork.json').read_text())
for mid in ('harp','rake'):
    frame,info,_=harp_backbone([s for s in layout['strings'].values() if s['mid']==mid])
    assert validate_mesh(frame)['ok']
    sides=len(handrail_profile());p=frame.path
    assert len(frame.vertices)==len(p)*sides # no buried end caps at any joint
    edges=np.unique(np.sort(np.concatenate([frame.faces[:,[0,1]],frame.faces[:,[1,2]],frame.faces[:,[2,0]]]),axis=1),axis=0)
    assert len(frame.vertices)-len(edges)+len(frame.faces)==0 # one closed genus-one frame
    t=np.roll(p,-1,0)-np.roll(p,1,0);ds=np.linalg.norm(t,axis=1);t/=ds[:,None]
    curvature=np.linalg.norm(np.roll(t,-1,0)-np.roll(t,1,0),axis=1)/ds
    assert max(curvature*frame.widths)<.95 # no inner contour folding through the local bend centre
    for joint in info['joins']:
        i=joint['start'];j=i+joint['count']
        incoming=p[i]-p[i-1];incoming/=np.linalg.norm(incoming)
        outgoing=p[j%len(p)]-p[(j-1)%len(p)];outgoing/=np.linalg.norm(outgoing)
        assert incoming@joint['tangent_start']>.995
        assert outgoing@joint['tangent_end']>.985
    assert -.02<frame.vertices[:,1].min()<.015 # floor contact, not floating supports
    print(mid,'JOINTS PASS:',len(p),'shared rings; max bend occupancy',float(max(curvature*frame.widths)))
