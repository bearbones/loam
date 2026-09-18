"""Instrument form recipes built from the authoritative visual layout."""
import numpy as np
from scipy.interpolate import PchipInterpolator
from .sweep import sample_curve,sweep,validate_mesh
from .joints import rounded_loop,section_field,smoothstep
from .layout import RAIL,END,BOARD,NECK,EYELET

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
    # Only at the string's foot: its upper end runs on past the neck's action to
    # a bridge pin and its tuning pin (layout.neck_plan), as a harp's does. The
    # ferrule's mouth wears the eyelet the string leaves by (layout.eyelet_plan).
    for s in elements:
        ep=np.array(s['a']); dest=ep+np.array(EYELET['barrel'])
        path=sample_curve([ep,ep+(dest-ep)*.5,dest],10)
        meshes.append(sweep(path,np.linspace(*EYELET['ferrule'],len(path)),.027,sides=12))
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

def _neck(elements):
    """The backbone's neck samples: path, half-widths, and the world z of the
    string-side face (the bead crests, at profile depth 1) and the far face."""
    frame,info,_=harp_backbone(elements)
    indices=np.flatnonzero(np.array(info['labels'])==1)[3:-3]
    c=elements[0]['a'][2]+.20; d=frame.depths[indices]
    return frame.path[indices].copy(),frame.widths[indices],c-d,c+d

def action_plate(elements):
    """A pedal harp's neck is plated on both faces. Two constant-gauge brass
    plates seated on the bead crests, spanning the neck's height and standing
    NECK['plate'] proud: the first on the string-side face, where the discs,
    fork pins and bridge pins mount; the second on the far face, which the
    tuning pins pass through to their square heads."""
    path,w,face,back=_neck(elements)
    profile=np.array([[-1,-.7],[-.96,-1],[.96,-1],[1,-.7],[1,.7],[.96,1],[-.96,1],[-1,.7]])
    plates=[]
    for z in (face-NECK['plate']/2,back+NECK['plate']/2):
        p=path.copy(); p[:,2]=z; plates.append(sweep(p,.9*w,NECK['plate']/2,profile=profile))
    return plates

def neck_faces(elements):
    """Per string id: the world z of the neck's string-side face and far face at
    that string (the sample nearest its upper end), for layout.neck_plan."""
    path,_,face,back=_neck(elements); out={}
    for s in elements:
        b=np.array(s['b']); i=int(np.argmin(np.hypot(path[:,0]-b[0],path[:,1]-(b[1]+.16))))
        out[s['id']]=dict(face=float(face[i]),back=float(back[i]),y=float(path[i,1]))
    return out

TIMBER=np.array([[-1,-.8],[-.9,-1],[.9,-1],[1,-.8],[1,.8],[.9,1],[-.9,1],[-1,.8]])   # chamfered rectangle
def _timber(points,width,depth,count=None):
    """A straight or gently curved sawn member; width/depth are half-extents per sweep()'s frame rule."""
    path=sample_curve(points,count or max(12,4*len(points)))
    n=len(path); w=np.linspace(*width,n) if np.ndim(width) else width; d=np.linspace(*depth,n) if np.ndim(depth) else depth
    return sweep(path,w,d,profile=TIMBER)

def bar_frame(plan):
    """Marimba construction from formlab.layout.bar_frame_plan: two rails under the
    bars' nodal lines, each end a foot, two uprights and a crosspiece the rails
    rest on, a low stretcher between the ends and a name board on the front
    uprights. Every piece is a closed sweep; the wood joins where they overlap."""
    R=plan['rails']; pieces=[]
    for side in ('back','front'):                                   # +X path: width->Y, depth->Z
        pieces.append(_timber(R[side],RAIL['half_y'],RAIL['half_z'],64))
    for e in plan['ends']:
        xe=e['x']; y0=e['floor']
        zb,zf=e['uprights']; cy=e['cross_y']
        pieces.append(_timber([[xe,cy,zb-END['half_x']-.03],[xe,cy,(zb+zf)/2],[xe,cy,zf+END['half_x']+.03]],END['half_x'],END['half_x']))   # +Z path: width->Y, depth->X
        for zu in (zb,zf):                                          # +Y path: width->X, depth->Z (tapering upward)
            pieces.append(_timber([[xe,y0+END['foot_half_y'],zu],[xe,(y0+cy)/2,zu],[xe,cy+END['half_x']*.6,zu]],(END['taper'],END['half_x']),(END['taper'],END['half_x'])))
        fb,ff=e['foot']
        pieces.append(_timber([[xe,y0+END['foot_half_y'],fb],[xe,y0+END['foot_half_y'],(fb+ff)/2],[xe,y0+END['foot_half_y'],ff]],END['foot_half_y'],END['foot_half_x']))
    s=plan['stretcher']; xa,xb=s['x']
    pieces.append(_timber([[xa,s['y'],s['z']],[(xa+xb)/2,s['y'],s['z']],[xb,s['y'],s['z']]],.04,.045))
    b=plan['board']; (x0,x1),(z0,z1)=b['x'],b['z']
    pieces.append(_timber([[x0,b['y'],z0],[(x0+x1)/2,b['y'],(z0+z1)/2],[x1,b['y'],z1]],BOARD['half_y'],BOARD['half_z']))
    return pieces

def pack(name,pieces,material,classification,materials=None):
    """One recipe object. `material` names the object's material; `materials`
    (optional, one name per piece) gives pieces their own — a horn plectrum in
    a brass ferrule — as material slots on the one mesh (blender_forms.make_form,
    profiled finish only)."""
    reports=[validate_mesh(m) for m in pieces]
    if not all(r['ok'] for r in reports): raise ValueError((name,reports))
    if materials is not None and len(materials)!=len(pieces): raise ValueError((name,'one material per piece',len(materials),len(pieces)))
    entry=dict(name=name,material=material,classification=classification,
               pieces=[m.to_dict() for m in pieces],component_checks=reports)
    if materials is not None: entry['piece_materials']=list(materials)
    return entry

def bench_frame(plan):
    """Trestle-bench construction from formlab.layout.bench_plan: two rails, a
    bearer under each element, at each end a crossbar the rails rest on with
    two splayed legs and a tie between them, a stretcher tying the ends at the
    ties' height, and a fascia board hung on the bearers' front ends."""
    from .layout import BENCH as B
    pieces=[]
    for side in ('back','front'):
        (xa,y,z),(xb,_,_)=plan['rails'][side]
        pieces.append(_timber([[xa,y,z],[(xa+xb)/2,y,z],[xb,y,z]],B['rail_half_y'],B['rail_half_z']))            # +X: width->Y, depth->Z
    for b in plan['bearers']:
        za,zb=b['z']; pieces.append(_timber([[b['x'],b['y'],za],[b['x'],b['y'],(za+zb)/2],[b['x'],b['y'],zb]],B['bearer_half_y'],B['bearer_half_x']))   # +Z: width->Y, depth->X
    for e in plan['ends']:
        xe=e['x']; za,zb=e['z']; cy=e['cross_y']
        pieces.append(_timber([[xe,cy,za-B['cross_half']-.02],[xe,cy,(za+zb)/2],[xe,cy,zb+B['cross_half']+.02]],B['cross_half'],B['cross_half']))
        for l in e['legs']:                                        # built upward from the toe: width->X, depth->Z, tapering toward the toe
            toe=np.array(l['toe']); top=np.array(l['top'])+[0,B['cross_half']*.6,0]
            pieces.append(_timber([toe,(toe+top)/2,top],(B['leg_toe'],B['leg_top']),(B['leg_toe'],B['leg_top'])))
        ta,tb=e['tie_z']; pieces.append(_timber([[xe,e['tie_y'],ta-.02],[xe,e['tie_y'],(ta+tb)/2],[xe,e['tie_y'],tb+.02]],.03,.035))
    s=plan['stretcher']; xa,xb=s['x']
    pieces.append(_timber([[xa,s['y'],s['z']],[(xa+xb)/2,s['y'],s['z']],[xb,s['y'],s['z']]],.035,.04))
    b=plan['board']; x0,x1=b['x']
    pieces.append(_timber([[x0,b['y'],b['z']],[(x0+x1)/2,b['y'],b['z']],[x1,b['y'],b['z']]],BOARD['half_y']*.6,BOARD['half_z']))
    return pieces
