"""Instrument form recipes built from the authoritative visual layout."""
import numpy as np
from scipy.interpolate import PchipInterpolator
from .sweep import sample_curve,sweep,validate_mesh
from .joints import rounded_loop,section_field,smoothstep

STYLES=('carved','ribbed','shell')
def handrail_profile():
    """A moulded section: fillet, bead, concave cove and a recessed broad face.

    Coordinates are explicit so the hollows survive mesh finishing. The front
    and back are mirrored; the closed profile is star-shaped for end-cap fans.
    """
    front=np.array([[-1,0],[-1,.63],[-.98,.84],[-.9,.98],[-.8,1],
        [-.73,.94],[-.70,.80],[-.68,.66],[-.62,.56],[-.52,.52],
        [-.43,.57],[-.39,.66],[-.39,.73],[.39,.73],[.39,.66],
        [.43,.57],[.52,.52],[.62,.56],[.68,.66],[.70,.80],
        [.73,.94],[.8,1],[.9,.98],[.98,.84],[1,.63],[1,0]])
    return np.vstack([front,front[-2:0:-1]*[1,-1]])

def harp_backbone(elements,style='carved'):
    """One closed contour network for column, neck, soundbox and their joints."""
    a=np.array([s['a'] for s in elements]); b=np.array([s['b'] for s in elements])
    order=np.argsort(a[:,0]);a=a[order];b=b[order]
    left,right=a[0,0],a[-1,0];z=a[0,2]+.20
    colx=left-(.46 if elements[0]['mid']=='harp' else .28)
    foot=np.array([left-.32,-.16,z]);capital=np.array([colx,b[0,1]+.22,z]);knee=np.array([right+.34,b[-1,1]+.06,z])
    column=sample_curve([foot,[colx if elements[0]['mid']=='harp' else left-.46,.32,z],[colx,.76,z],[colx,1.20,z],capital],130)
    neck=sample_curve([capital,*np.c_[b[:,0],b[:,1]+.16,np.full(len(b),z)].tolist(),knee],180)
    body=sample_curve([foot,[left-.12,.34,z],*np.c_[a[:,0]+.065,a[:,1]-.13,np.full(len(a),z)].tolist(),knee],180)
    path,labels,joins=rounded_loop([column,neck,body[::-1]],[.34,.36 if elements[0]['mid']=='harp' else .23,.23])
    controls=[([left-.25,.53,z],.12,.22),([left-.29,1.1,z],.105,.15),
        ([left-.28,capital[1]-.36,z],.12,.135),([left+.15,b[0,1]+.06,z],.155,.14),
        (neck[len(neck)//2],.15,.14),(knee,.105,.12),
        (body[int(len(body)*.76)],.145,.19),(body[int(len(body)*.50)],.225,.25),
        (body[int(len(body)*.28)],.255,.30),(foot,.075,.32)]
    w,d=section_field(path,controls)
    # Unmatched detail at the foot fades into a plain receiving surface; indexed
    # beads/coves remain fully present through both upper, matching joints.
    relief=smoothstep((path[:,1]-.16)/.22)
    if style=='shell': relief*=.8
    profile=handrail_profile();profiles=np.broadcast_to(profile,(len(path),*profile.shape)).copy()
    angle=np.linspace(np.pi,0,len(profile)//2+1)
    front=np.c_[np.cos(angle),.73*np.sin(angle)]
    plain=np.vstack([front,front[-2:0:-1]*[1,-1]])
    body_weight=np.zeros(len(path));ii=np.flatnonzero(labels==2);u=np.linspace(0,1,len(ii))
    body_weight[ii]=smoothstep(u/.14)*smoothstep((1-u)/.14)
    broad=profile.copy();broad[:,0]=np.interp(profile[:,0],[-1,-.70,-.39,.39,.70,1],[-1,-.92,-.80,.80,.92,1])
    profiles+=(broad-profile)[None]*body_weight[:,None,None]
    profiles=plain[None]+relief[:,None,None]*(profiles-plain[None])
    return sweep(path,w,d,closed=True,profile=profiles),dict(joins=joins,labels=labels.tolist(),body_weight=body_weight.tolist()),body

def harp_frame(elements,style='carved',section=None):
    backbone,_,_=harp_backbone(elements,style)
    meshes=[backbone]
    # Functional ferrules terminate inside the receiving frame. They are not
    # decorative moulding ends and remain individually closed components.
    for s in elements:
        for key,sign in (('a',-1),('b',1)):
            ep=np.array(s[key]); dest=ep+np.array([.035 if sign<0 else 0,sign*.13,.20])
            path=sample_curve([ep,ep+(dest-ep)*.5,dest],10)
            meshes.append(sweep(path,np.linspace(.024,.04,len(path)),.027,sides=12))
    return meshes

def soundboard(elements):
    """Inset face follows the receiving section exactly and feathers below it."""
    frame,info,_=harp_backbone(elements)
    indices=np.flatnonzero((np.array(info['labels'])==2)&(frame.path[:,1]>.44))[5:-5]
    path=frame.path[indices].copy();w=frame.widths[indices];d=frame.depths[indices]
    u=np.linspace(0,1,len(path));fade=smoothstep(u/.05)*smoothstep((1-u)/.04)
    face_offset=d*.73+.003-.007*(1-fade)
    profile=np.array([[-1,-.7],[-.95,-1],[.95,-1],[1,-.7],[1,.7],[.95,1],[-.95,1],[-1,.7]])
    # Restrained, ruled taper leaves a substantial walnut border. The ends
    # sink into the face without shrinking into teardrop-shaped tips.
    panel_width=np.minimum(w*.52,np.linspace(.055,.13,len(path)))
    panel=sweep(path,panel_width*(.90+.10*fade),.0015,profile=profile)
    # Reuse the receiving XY frames: resweeping an offset 3D centre-line would
    # tilt the wide inset through the soundbox and produce ragged intersections.
    panel.vertices[:len(path)*len(profile),2]+=np.repeat(face_offset,len(profile))
    panel.vertices[-2:,2]+=face_offset[[0,-1]]
    panel.path[:,2]+=face_offset
    return [panel]

def action_plate(elements):
    frame,info,_=harp_backbone(elements)
    indices=np.flatnonzero(np.array(info['labels'])==1)[3:-3]
    # A constant-gauge plate cut in a plane, rather than a swelling 3D sweep.
    path=frame.path[indices].copy();path[:,1]-=.065;path[:,2]=.318+elements[0]['a'][2]
    profile=np.array([[-1,-.7],[-.96,-1],[.96,-1],[1,-.7],[1,.7],[.96,1],[-.96,1],[-1,.7]])
    return [sweep(path,.078,.004,profile=profile)]

def branching_stand(center,span):
    """Second application: load-collection heuristic, not a solved stand."""
    x,_,z=center; pieces=[]
    for side in (-1,1):
        zz=z+side*.3
        # Central trunk, two spreading roots, two forks supporting the existing bed.
        paths=[([[x,.06,zz],[x,.28,zz],[x,.48,zz]], [.16,.12]),
               ([[x-span*.31,.035,zz],[x-span*.19,.12,zz],[x,.32,zz]],[.13,.12]),
               ([[x+span*.31,.035,zz],[x+span*.19,.12,zz],[x,.32,zz]],[.13,.12]),
               ([[x,.3,zz],[x-span*.18,.53,zz],[x-span*.41,.68,zz]],[.14,.09]),
               ([[x,.3,zz],[x+span*.18,.53,zz],[x+span*.41,.68,zz]],[.14,.09])]
        for controls,radii in paths:
            path=sample_curve(controls,48)
            pieces.append(sweep(path,np.linspace(*radii,len(path)),np.linspace(*radii,len(path))*.8))
    return pieces

def pack(name,pieces,material,classification):
    reports=[validate_mesh(m) for m in pieces]
    if not all(r['ok'] for r in reports): raise ValueError((name,reports))
    return dict(name=name,material=material,classification=classification,
                pieces=[m.to_dict() for m in pieces],component_checks=reports)
