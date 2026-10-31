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
    # On the string-facing (-Z, profile_y < 0) side of the soundbox, attenuate the upper-left
    # stringward bead (profile_x < 0) toward the cove (-.73) and scale the -Z depth so the
    # string-facing stone surface stays at least 34 mm behind the string plane (z - 0.20):
    str_rim=(broad[:,0]<0)&(broad[:,1]<-.73)
    broad[str_rim,1]=-.73+.15*(broad[str_rim,1]+.73)
    profiles+=(broad-profile)[None]*body_weight[:,None,None]
    profiles=plain[None]+relief[:,None,None]*(profiles-plain[None])
    scale_neg=1.0-body_weight[:,None]*(1.0-np.minimum(1.0,.166/np.maximum(d*.77,1e-6))[:,None])
    profiles[:,:,1]=np.where(profiles[:,:,1]<0,profiles[:,:,1]*scale_neg,profiles[:,:,1])
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

def gothic_rib_profile():
    """Carved Gothic/Elven arch-rib section: filleted base, twin concave hollow
    chamfer coves on the flanks, and a keeled ogival ridge crest at (0, +1).
    Star-shaped about (0, 0) so end-cap fans are manifold."""
    half=np.array([
        [-1.00,-.42],[-.96,-.68],[-.82,-.84],[-.55,-.92],[0.00,-.95],
        [.55,-.92],[.82,-.84],[.96,-.68],[1.00,-.42],
        [.92,-.08],[.74,.22],[.56,.48],[.38,.72],[.18,.91],[0.00,1.00],
        [-.18,.91],[-.38,.72],[-.56,.48],[-.74,.22],[-.92,-.08]
    ])
    return half

def collar_profile(n=36,power=5.0,flutes=0,flute_depth=0.0):
    """Smooth turned superellipse (squircle) collar section that cleanly encloses
    the rectangular bead corners (+-.90, +-.98) of handrail_profile() around the
    entire 360-degree perimeter without any stone corners poking through."""
    ang=np.linspace(0.,2.*np.pi,n,endpoint=False)
    ca=np.cos(ang); sa=np.sin(ang)
    sx=np.sign(ca)*(np.abs(ca)**(2./power))
    sy=np.sign(sa)*(np.abs(sa)**(2./power))
    if flutes>0 and flute_depth>0.0:
        mod=1.0-flute_depth*(1.0-np.cos(flutes*ang)**2)
        sx*=mod; sy*=mod
    return np.c_[sx,sy]

def fluted_calyx_profile(lobes=12):
    """Star-convex fluted Gothic/Elven calyx capital cross-section built on a
    superellipse envelope so it wraps handrail_profile() without corner bleed."""
    return collar_profile(n=lobes*4,power=4.5,flutes=lobes,flute_depth=.05)

def elven_leaf_profile():
    """Thin, flat, lenticular elven leaf-blade section with sharp lateral margins
    (+-1, 0) and a raised dorsal/ventral midrib vein."""
    return np.array([
        [-1.00,0.00],[-.78,-.28],[-.46,-.48],[-.16,-.68],[0.00,-.85],
        [.16,-.68],[.46,-.48],[.78,-.28],[1.00,0.00],
        [.78,.34],[.46,.62],[.16,.84],[0.00,1.00],
        [-.16,.84],[-.46,.62],[-.78,.34]
    ])

def _leaf_blade(p_root,u_tang,u_out,u_side,length=.135,width=.030,thickness=.0036):
    """Sculpt a curved, flat, pointed elven leaf blade springing from `p_root`,
    arching along `u_tang` and oriented so its wide blade (`width`) lies flat
    tangentially along the branch surface while its thin section (`thickness`)
    faces outward along `u_out` (never sticking out edge-on like a fin)."""
    from .sweep import transport_frames
    u_tang=np.asarray(u_tang,dtype=float); u_tang/=np.linalg.norm(u_tang)+1e-9
    u_out=np.asarray(u_out,dtype=float); n_out=u_out/(np.linalg.norm(u_out)+1e-9)
    u_side=np.asarray(u_side,dtype=float)
    pts=[
        p_root,
        p_root+u_tang*(length*.32)+n_out*(length*.12)+u_side*(length*.10),
        p_root+u_tang*(length*.68)+n_out*(length*.18)+u_side*(length*.18),
        p_root+u_tang*length+n_out*(length*.14)+u_side*(length*.22),
    ]
    crv=sample_curve(pts,14)
    u=np.linspace(0.,1.,len(crv))
    w=np.interp(u,[0.,.16,.46,.76,1.],[width*.22,width*.86,width,width*.56,width*.09])
    d=np.interp(u,[0.,.5,1.],[thickness*1.20,thickness,thickness*.48])
    tangents,normals,binormals=transport_frames(crv)
    p0=elven_leaf_profile()
    profiles=np.zeros((len(crv),len(p0),2),dtype=float)
    for i in range(len(crv)):
        t_i=tangents[i]
        b_out=n_out-np.dot(n_out,t_i)*t_i
        b_norm=np.linalg.norm(b_out)
        b_out=b_out/b_norm if b_norm>1e-6 else binormals[i]
        b_lat=np.cross(b_out,t_i)
        b_lat/=np.linalg.norm(b_lat)+1e-9
        c_ln=float(np.dot(b_lat,normals[i])); c_lb=float(np.dot(b_lat,binormals[i]))
        c_on=float(np.dot(b_out,normals[i])); c_ob=float(np.dot(b_out,binormals[i]))
        px=p0[:,0]*w[i]; py=p0[:,1]*d[i]
        profiles[i,:,0]=px*c_ln+py*c_on
        profiles[i,:,1]=px*c_lb+py*c_ob
    return sweep(crv,1.0,1.0,profile=profiles)

def _torus_collar(p_axis,r_wx,r_dz,bulge=.020,profile=None,sides=28):
    """Turned architectural torus/astragal collar moulding with a smooth convex
    profile (`r_inner -> r_peak -> r_inner`) that wraps cleanly around a member."""
    if profile is None: profile=collar_profile(sides,power=5.0)
    crv=sample_curve(p_axis,12)
    u=np.linspace(0.,1.,len(crv))
    env=np.sin(np.pi*u)**.75
    wx=np.asarray(r_wx)+bulge*env
    dz=np.asarray(r_dz)+bulge*env
    return sweep(crv,wx,dz,profile=profile,sides=sides)

def harp_tracery(elements):
    """Rivendell-inspired architectural harp & rake construction:
    1. Sculpted Fluted Root Socles (forepillar & soundbox foot) with turned
       bronze/brass torus collars and gothic root buttress arches.
    2. Full-height intertwining white-stone Gothic pillar boughs running from
       the Root Socle into the base of the Crown Capital astragal.
    3. Fluted Calyx Crown Capital, satin-brass Abacus Rim, Solid-Webbed Spiral
       Scroll Volute with bronze rosette eyes, and Neck-Shoulder Collar.
    4. Gothic Dorsal Crest along the Harmonic Neck with brass spine & leaf vines.
    5. Proud Treble Knee Scroll Corbel, Throat Collar, and Solid-Webbed Volute.
    6. Carved white-stone Soundbox Cheek Mouldings, Brass Border Fillets, and
       Keel Spine framing the Sitka spruce soundboard clear of string eyelets.
    7. Counter-spiraling golden-brass & phosphor-bronze vines with flat,
       tangentially-oriented elven leaf blades."""
    a=np.array([s['a'] for s in elements]); b=np.array([s['b'] for s in elements])
    order=np.argsort(a[:,0]); a=a[order]; b=b[order]
    left,right=float(a[0,0]),float(a[-1,0])
    z=float(a[0,2])+.20
    frame,info,_=harp_backbone(elements)
    labels=np.array(info['labels'])
    rib_prof=gothic_rib_profile()
    calyx_prof=fluted_calyx_profile(12)
    ring_prof=collar_profile(36,power=5.0)
    round_prof=collar_profile(32,power=2.0)
    pieces=[]; mats=[]
    def add(mesh,mat='wood'):
        pieces.append(mesh); mats.append(mat)

    i_col=np.flatnonzero(labels==0.0); i_cap=np.flatnonzero(labels==0.5); i_neck=np.flatnonzero(labels==1.0)
    i_knee=np.flatnonzero(labels==1.5); i_body=np.flatnonzero(labels==2.0)

    # Full vertical forepillar shaft runs through i_col and the lower 28% of i_cap right into the Crown Capital astragal:
    n_cap_col=max(3,int(len(i_cap)*.28))
    pil_idx=np.r_[i_col,i_cap[:n_cap_col]]
    col_p0=frame.path[pil_idx]; col_w0=frame.widths[pil_idx]; col_d0=frame.depths[pil_idx]
    cx_foot=float(np.interp(.34,col_p0[:,1],col_p0[:,0]))
    y_pil_top=float(col_p0[-1,1])

    # 1. Sculpted Fluted Root Socle, Soundbox Foot Socle & Gothic Root Buttress Arches on the pedestal crown (y = 0.335):
    x_root_top=float(np.interp(.54,col_p0[:,1],col_p0[:,0]))
    root_axis=[[cx_foot,.31,z],[.5*(cx_foot+x_root_top),.42,z],[x_root_top,.54,z]]
    crv_root=sample_curve(root_axis,18)
    ur=np.linspace(0.,1.,len(crv_root))
    add(sweep(crv_root,np.interp(ur,[0.,.45,1.],[.166,.144,.122]),np.interp(ur,[0.,.45,1.],[.248,.216,.182]),profile=calyx_prof),'wood')
    for y_ring,r_wx,r_dz,h_r,bulge_r,mat_r in (
        (.338,.164,.244,.026,.020,'bronze'),
        (.392,.150,.224,.020,.016,'brass'),
        (.522,.126,.188,.020,.015,'bronze'),
    ):
        xr=float(np.interp(y_ring,[.31,.54],[cx_foot,x_root_top]))
        ring_p=[[xr,y_ring-h_r,z],[xr,y_ring,z],[xr,y_ring+h_r,z]]
        add(_torus_collar(ring_p,r_wx,r_dz,bulge=bulge_r,profile=ring_prof),mat_r)

    # Soundbox Foot Socle where the lower soundbox rises from the right side of the pedestal crown:
    body_lo=frame.path[i_body[::-1]]; bw_lo=frame.widths[i_body[::-1]]; bd_lo=frame.depths[i_body[::-1]]
    bx_foot=float(np.interp(.34,body_lo[:,1],body_lo[:,0]))
    bx_top=float(np.interp(.48,body_lo[:,1],body_lo[:,0]))
    w_sbf0=float(np.interp(.34,body_lo[:,1],bw_lo)); d_sbf0=float(np.interp(.34,body_lo[:,1],bd_lo))
    w_sbf1=float(np.interp(.48,body_lo[:,1],bw_lo)); d_sbf1=float(np.interp(.48,body_lo[:,1],bd_lo))
    sb_foot_p=[[bx_foot,.31,z],[.5*(bx_foot+bx_top),.395,z],[bx_top,.48,z]]
    crv_sbf=sample_curve(sb_foot_p,14)
    usbf=np.linspace(0.,1.,len(crv_sbf))
    add(sweep(crv_sbf,np.interp(usbf,[0.,1.],[w_sbf0*1.12,w_sbf1*1.08]),np.interp(usbf,[0.,1.],[d_sbf0*.78,d_sbf1*.76]),profile=calyx_prof),'wood')
    sbf_ring=[[bx_foot,.322,z],[.5*(bx_foot+bx_top),.348,z],[.3*bx_foot+.7*bx_top,.374,z]]
    add(_torus_collar(sbf_ring,w_sbf0*1.15,d_sbf0*.80,bulge=.016,profile=ring_prof),'brass')

    # Sweeping gothic stone & brass root buttress arches bridging the pillar root to the soundbox foot:
    for sgn_z in (-1.,1.):
        z_arch=z+sgn_z*.135
        arch_pts=[[x_root_top,.50,z_arch],[.5*(x_root_top+bx_top),.36,z_arch+sgn_z*.024],[bx_top,.47,z_arch]]
        crv_a=sample_curve(arch_pts,24)
        ua=np.linspace(0.,1.,len(crv_a))
        ta=.58+.42*np.sin(np.pi*ua)
        add(sweep(crv_a,.032*ta,.026*ta,profile=rib_prof),'wood')
        arch_br=[[x_root_top,.51,z_arch+sgn_z*.016],[.5*(x_root_top+bx_top),.37,z_arch+sgn_z*.038],[bx_top,.48,z_arch+sgn_z*.016]]
        add(sweep(sample_curve(arch_br,20),.013,.013,profile=rib_prof),'brass')

    # 2. Full-height helically twisting carved white-stone gothic branch boughs (terminating inside the Crown Capital astragal):
    n_c=44
    y_col=np.linspace(.34,y_pil_top,n_c)
    x_col=np.interp(y_col,col_p0[:,1],col_p0[:,0])
    cw_sub=np.interp(y_col,col_p0[:,1],col_w0)
    cd_sub=np.interp(y_col,col_p0[:,1],col_d0)
    cp_sub=np.c_[x_col,y_col,np.full(n_c,z)]
    u_col=np.linspace(0.,1.,n_c)
    flare_lo=np.maximum(0.,1.-u_col/.16)**2*.036
    flare_hi=np.maximum(0.,(u_col-.82)/.18)**2*.024
    for k in range(4):
        th=k*(np.pi/2.)+1.65*np.pi*u_col
        rx=cw_sub*.98+flare_lo+flare_hi
        rz=cd_sub*.95+flare_lo+flare_hi
        pts=np.c_[cp_sub[:,0]+rx*np.cos(th),cp_sub[:,1],cp_sub[:,2]+rz*np.sin(th)]
        crv=sample_curve(pts,56)
        uc=np.linspace(0.,1.,len(crv))
        w_b=.036-.004*uc+.008*np.maximum(0.,(uc-.82)/.18)
        d_b=.032-.003*uc+.006*np.maximum(0.,(uc-.82)/.18)
        add(sweep(crv,w_b,d_b,profile=rib_prof),'wood')
    # Counter-twisting slender gothic stone ribs forming open pointed lancet windows:
    for k in range(2):
        th=k*np.pi-1.30*np.pi*u_col+.40
        rx=cw_sub*1.02+.010*np.sin(np.pi*u_col)+flare_lo*.65+flare_hi*.65
        rz=cd_sub*.98+.010*np.sin(np.pi*u_col)+flare_lo*.65+flare_hi*.65
        pts=np.c_[cp_sub[:,0]+rx*np.cos(th),cp_sub[:,1],cp_sub[:,2]+rz*np.sin(th)]
        crv=sample_curve(pts,48)
        add(sweep(crv,.022,.020,profile=rib_prof),'wood')

    # 3. Sculpted Fluted Calyx Crown Capital, Abacus Moulding, Solid-Webbed Scroll Volute & Neck-Shoulder Collar:
    cap_start=max(2,int(len(i_cap)*.24))
    cap_end=min(len(i_cap)-2,int(len(i_cap)*.78))
    cap_indices=i_cap[cap_start:cap_end]
    cap_sub=frame.path[cap_indices]; cap_w=frame.widths[cap_indices]; cap_d=frame.depths[cap_indices]
    p_ast0=cap_sub[0]; p_ast1=cap_sub[min(3,len(cap_sub)-1)]
    t_ast=p_ast1-p_ast0; t_ast/=np.linalg.norm(t_ast)+1e-9
    w_ast=float(cap_w[0]); d_ast=float(cap_d[0])
    # Turned phosphor-bronze & satin-brass astragal collars at the base of the Crown Capital:
    ast_axis=[p_ast0-t_ast*.026,p_ast0,p_ast0+t_ast*.026]
    add(_torus_collar(ast_axis,w_ast*1.16,d_ast*1.16,bulge=.022,profile=ring_prof),'bronze')
    ast_hi=[p_ast0+t_ast*.018,p_ast0+t_ast*.038,p_ast0+t_ast*.058]
    add(_torus_collar(ast_hi,w_ast*1.19,d_ast*1.19,bulge=.016,profile=ring_prof),'brass')

    # Flaring 12-fluted white-stone Calyx Bell Capital (superellipse envelope cleanly enclosing the backbone):
    crv_calyx=sample_curve(cap_sub,28)
    ucx=np.linspace(0.,1.,len(crv_calyx))
    w_local_cx=np.interp(ucx,np.linspace(0.,1.,len(cap_w)),cap_w)
    d_local_cx=np.interp(ucx,np.linspace(0.,1.,len(cap_d)),cap_d)
    flare_cx=np.interp(ucx,[0.,.35,.72,1.],[1.14,1.24,1.32,1.16])
    add(sweep(crv_calyx,w_local_cx*flare_cx,d_local_cx*flare_cx,profile=calyx_prof),'wood')

    # Sculpted satin-brass Abacus Moulding crowning the calyx bell:
    idx_aba=int(len(cap_sub)*.72)
    p_aba=cap_sub[idx_aba]; w_aba=float(cap_w[idx_aba]); d_aba=float(cap_d[idx_aba])
    t_aba=cap_sub[min(len(cap_sub)-1,idx_aba+2)]-cap_sub[max(0,idx_aba-2)]
    t_aba/=np.linalg.norm(t_aba)+1e-9
    aba_axis=[p_aba-t_aba*.024,p_aba,p_aba+t_aba*.024]
    add(_torus_collar(aba_axis,w_aba*1.30,d_aba*1.30,bulge=.020,profile=ring_prof),'brass')

    # Turned bronze Neck-Shoulder Collar where the harmonic neck emerges from the capital (well left of string 0):
    idx_sh=i_cap[-3]
    p_sh=frame.path[idx_sh]; w_sh=float(frame.widths[idx_sh]); d_sh=float(frame.depths[idx_sh])
    t_sh=frame.path[i_cap[-1]]-frame.path[i_cap[-5]]
    t_sh/=np.linalg.norm(t_sh)+1e-9
    sh_axis=[p_sh-t_sh*.022,p_sh,p_sh+t_sh*.022]
    add(_torus_collar(sh_axis,w_sh*1.15,d_sh*1.15,bulge=.018,profile=ring_prof),'bronze')

    # Solid-Webbed Elven Spiral Scroll Volute crowning the capital crest (w < 0.45*R everywhere so zero inner pinching):
    cap_apex=cap_sub[np.argmax(cap_sub[:,1])]
    sp_cx=float(cap_apex[0])-.038; sp_cy=float(cap_apex[1])+.058
    drum_p=[[sp_cx,sp_cy,z-.152],[sp_cx,sp_cy,z],[sp_cx,sp_cy,z+.152]]
    add(_torus_collar(drum_p,.098,.098,bulge=.010,profile=round_prof),'wood')
    th_sp=np.linspace(-.35*np.pi,1.45*np.pi,40)
    r_sp=np.linspace(.112,.038,len(th_sp))
    vol_pts=np.c_[sp_cx-r_sp*np.cos(th_sp),sp_cy+r_sp*np.sin(th_sp),np.full(len(th_sp),z)]
    crv_vol=sample_curve(vol_pts,44)
    uv=np.linspace(0.,1.,len(crv_vol))
    add(sweep(crv_vol,np.interp(uv,[0.,.5,1.],[.040,.026,.015]),np.interp(uv,[0.,.5,1.],[.168,.160,.154]),profile=rib_prof),'wood')
    vol_in=np.c_[sp_cx-(r_sp*.84)*np.cos(th_sp),sp_cy+(r_sp*.84)*np.sin(th_sp),np.full(len(th_sp),z)]
    add(sweep(sample_curve(vol_in,36),np.linspace(.016,.010,36),np.linspace(.174,.160,36),profile=rib_prof),'brass')
    eye_p=[[sp_cx,sp_cy,z-.174],[sp_cx,sp_cy,z],[sp_cx,sp_cy,z+.174]]
    add(_torus_collar(eye_p,.038,.038,bulge=.008,profile=round_prof),'bronze')

    # 4. Continuous Gothic Dorsal Crest along the Harmonic Neck (strictly on the +n_up ridge,
    #    keeping 100% of the brass action_plate, discs, bridge pins, and tuning pins open and proud):
    arch_idx=np.r_[i_cap[-4:],i_neck,i_knee[:len(i_knee)//3]]
    arch_p=frame.path[arch_idx]; arch_w=frame.widths[arch_idx]; arch_d=frame.depths[arch_idx]
    idx_n=np.linspace(0,len(arch_p)-1,38).astype(int)
    np_sub=arch_p[idx_n]; nw_sub=arch_w[idx_n]; nd_sub=arch_d[idx_n]
    tang_n=np.gradient(np_sub,axis=0); tang_n/=np.linalg.norm(tang_n,axis=1)[:,None]
    n_up=np.c_[-tang_n[:,1],tang_n[:,0],np.zeros(len(np_sub))]
    n_up/=np.linalg.norm(n_up,axis=1)[:,None]
    u_nk=np.linspace(0.,1.,len(np_sub))
    crest_pts=np_sub+n_up*(nw_sub*.88)[:,None]
    crv_nk=sample_curve(crest_pts,56)
    un=np.linspace(0.,1.,len(crv_nk))
    tn=.52+.48*smoothstep(un/.10)*smoothstep((1.-un)/.10)
    add(sweep(crv_nk,.042*tn,.146*tn,profile=rib_prof),'wood')
    spine_pts=np_sub+n_up*(nw_sub*1.16)[:,None]
    crv_sp=sample_curve(spine_pts,48)
    us_p=np.linspace(0.,1.,len(crv_sp))
    tsp=.55+.45*smoothstep(us_p/.10)*smoothstep((1.-us_p)/.10)
    add(sweep(crv_sp,.018*tsp,.152*tsp,profile=rib_prof),'brass')

    # 5. Proud Sculpted Treble Knee Scroll Corbel, Throat Collar & Solid-Webbed Volute (w < 0.45*R everywhere):
    idx_kth=i_body[4]
    p_kth=frame.path[idx_kth]; w_kth=float(frame.widths[idx_kth]); d_kth=float(frame.depths[idx_kth])
    t_kth=frame.path[i_body[7]]-frame.path[i_body[1]]
    t_kth/=np.linalg.norm(t_kth)+1e-9
    kth_axis=[p_kth-t_kth*.022,p_kth,p_kth+t_kth*.022]
    add(_torus_collar(kth_axis,w_kth*1.15,d_kth*1.12,bulge=.018,profile=ring_prof),'bronze')

    knee_idx=np.r_[i_neck[-5:],i_knee,i_body[:8]]
    kp_raw=frame.path[knee_idx]; kw_raw=frame.widths[knee_idx]; kd_raw=frame.depths[knee_idx]
    idx_k=np.linspace(0,len(kp_raw)-1,26).astype(int)
    kp_sub=kp_raw[idx_k]; kw_sub=kw_raw[idx_k]; kd_sub=kd_raw[idx_k]
    tang_k=np.gradient(kp_sub,axis=0); tang_k/=np.linalg.norm(tang_k,axis=1)[:,None]
    n_out_k=np.c_[-tang_k[:,1],tang_k[:,0],np.zeros(len(kp_sub))]
    n_out_k/=np.linalg.norm(n_out_k,axis=1)[:,None]
    hood_pts=kp_sub+n_out_k*(kw_sub*.92)[:,None]
    crv_hood=sample_curve(hood_pts,38)
    uh=np.linspace(0.,1.,len(crv_hood))
    th_hood=.45+.55*np.sin(np.pi*uh)**.80
    add(sweep(crv_hood,.046*th_hood,.148*th_hood,profile=rib_prof),'wood')
    hood_brass=kp_sub+n_out_k*(kw_sub*1.20)[:,None]
    crv_hb=sample_curve(hood_brass,34)
    uhb=np.linspace(0.,1.,len(crv_hb))
    th_hb=.45+.55*np.sin(np.pi*uhb)**.80
    add(sweep(crv_hb,.018*th_hb,.154*th_hb,profile=rib_prof),'brass')

    # Solid-Webbed Spiral Knee Scroll Volute projecting proudly from the outer treble shoulder:
    i_kmax=int(np.argmax(kp_sub[:,0]))
    k_apex=kp_sub[i_kmax]; kw_apex=float(kw_sub[i_kmax])
    kv_cx=float(k_apex[0])+kw_apex+.032; kv_cy=float(k_apex[1])+.024
    kdrum_p=[[kv_cx,kv_cy,z-.132],[kv_cx,kv_cy,z],[kv_cx,kv_cy,z+.132]]
    add(_torus_collar(kdrum_p,.072,.072,bulge=.008,profile=round_prof),'wood')
    th_kv=np.linspace(-.25*np.pi,1.35*np.pi,36)
    r_kv=np.linspace(.086,.030,len(th_kv))
    kv_pts=np.c_[kv_cx+r_kv*np.cos(th_kv),kv_cy+r_kv*np.sin(th_kv),np.full(len(th_kv),z)]
    crv_kv=sample_curve(kv_pts,38)
    ukv=np.linspace(0.,1.,len(crv_kv))
    add(sweep(crv_kv,np.interp(ukv,[0.,.5,1.],[.032,.022,.012]),np.interp(ukv,[0.,.5,1.],[.146,.140,.134]),profile=rib_prof),'wood')
    kv_in=np.c_[kv_cx+(r_kv*.84)*np.cos(th_kv),kv_cy+(r_kv*.84)*np.sin(th_kv),np.full(len(th_kv),z)]
    add(sweep(sample_curve(kv_in,32),np.linspace(.014,.009,32),np.linspace(.152,.140,32),profile=rib_prof),'brass')
    kv_eye=[[kv_cx,kv_cy,z-.154],[kv_cx,kv_cy,z],[kv_cx,kv_cy,z+.154]]
    add(_torus_collar(kv_eye,.028,.028,bulge=.006,profile=round_prof),'bronze')

    # 6. Carved white-stone Soundbox Cheek Mouldings, Brass Border Fillets & Keel Spine
    #    (proud on the +-Z faces along the +n_back side, framing the Sitka spruce soundboard clear of all string eyelets):
    body_mask=(labels==2.0)&(frame.path[:,1]>=.38)
    body_p=frame.path[body_mask][::-1]; body_w=frame.widths[body_mask][::-1]; body_d=frame.depths[body_mask][::-1]
    idx_b=np.linspace(2,len(body_p)-2,32).astype(int)
    bp_sub=body_p[idx_b]; bw_sub=body_w[idx_b]; bd_sub=body_d[idx_b]
    tang_b=np.gradient(bp_sub,axis=0); tang_b/=np.linalg.norm(tang_b,axis=1)[:,None]
    # Outward XY normal pointing down-and-right (the back/underbelly of the soundbox, opposite the strings):
    n_back=np.c_[tang_b[:,1],-tang_b[:,0],np.zeros(len(bp_sub))]
    n_back/=np.linalg.norm(n_back,axis=1)[:,None]
    # Dorsal Keel Spine along +n_back:
    for scale_k,r_k,mat_k in ((.96,.032,'wood'),(1.10,.016,'brass')):
        crv_k=sample_curve(bp_sub+n_back*(bw_sub*scale_k)[:,None],40)
        uk=np.linspace(0.,1.,len(crv_k))
        tk=.50+.50*smoothstep(uk/.10)*smoothstep((1.-uk)/.10)
        add(sweep(crv_k,r_k*tk,r_k*1.3*tk,profile=rib_prof),mat_k)
    # Proud +-Z Cheek Mouldings & Brass Fillets framing the lower/back border of the spruce soundboard:
    for sgn_z in (-1.,1.):
        z_eff=bd_sub if sgn_z>0 else np.minimum(bd_sub,.172)
        for w_pos,z_mul,r_c,mat_c in ((.62,.94,.024,'wood'),(.46,.97,.013,'brass')):
            off_c=n_back*(bw_sub*w_pos)[:,None]+np.c_[np.zeros(len(bp_sub)),np.zeros(len(bp_sub)),sgn_z*z_eff*z_mul]
            crv_c=sample_curve(bp_sub+off_c,40)
            uc_b=np.linspace(0.,1.,len(crv_c))
            tc_b=.55+.45*smoothstep(uc_b/.08)*smoothstep((1.-uc_b)/.08)
            add(sweep(crv_c,r_c*tc_b,r_c*tc_b,profile=rib_prof),mat_c)

    # 7. Counter-spiraling golden-brass & phosphor-bronze vines with flat, tangentially-oriented Elven Leaf Blades:
    for v_idx,v_mat in ((0,'brass'),(1,'bronze')):
        leaf_mat='bronze' if v_mat=='brass' else 'brass'
        # 7a. Column climbing vine riding outside the carved white-stone branch boughs (stopping cleanly below the capital astragal):
        th_v=v_idx*np.pi+1.95*np.pi*u_col+.55
        rx_v=cw_sub*1.14+flare_lo+flare_hi*.5+.010
        rz_v=cd_sub*1.08+flare_lo+flare_hi*.5+.010
        v_col=np.c_[cp_sub[:,0]+rx_v*np.cos(th_v),cp_sub[:,1],cp_sub[:,2]+rz_v*np.sin(th_v)]
        crv_vc=sample_curve(v_col,56)
        add(sweep(crv_vc,.012,.012,sides=12),v_mat)
        for u_lf in (.14,.28,.42,.56,.70,.84):
            k_lf=min(len(cp_sub)-2,max(1,int(round(u_lf*(len(cp_sub)-2)))))
            th0=float(th_v[k_lf])
            sgn_l=1. if (int(round(u_lf*14))+v_idx)%2==0 else -1.
            p_root=v_col[k_lf]
            u_tang=v_col[k_lf+1]-p_root; u_tang/=np.linalg.norm(u_tang)+1e-9
            u_out=np.array([np.cos(th0),0.08,np.sin(th0)]); u_out/=np.linalg.norm(u_out)
            u_side=sgn_l*np.array([-np.sin(th0),0.15,np.cos(th0)]); u_side/=np.linalg.norm(u_side)
            add(_leaf_blade(p_root,u_tang,u_out,u_side,.135,.030,.0036),leaf_mat)

        # 7b. Harmonic neck vine riding along the +-Z flanks of the upper dorsal crest:
        sgn_nv=-1. if v_idx==0 else 1.
        w_nv=nw_sub*1.04+.012*np.sin(2.4*np.pi*u_nk+v_idx*np.pi)
        z_nv=sgn_nv*(nd_sub*.42+.014)
        pts_nv=np_sub+n_up*w_nv[:,None]+np.c_[np.zeros(len(np_sub)),np.zeros(len(np_sub)),z_nv]
        crv_nv=sample_curve(pts_nv,48)
        add(sweep(crv_nv,.011,.011,sides=12),v_mat)
        for frac_l in (.16,.34,.52,.70,.86):
            il=int((len(np_sub)-3)*frac_l)
            p_start=pts_nv[il]; p_dir=pts_nv[il+2]-p_start; p_dir/=np.linalg.norm(p_dir)+1e-9
            u_out_n=np.array([0.,0.,sgn_nv])+n_up[il]*.25
            u_side_n=n_up[il]*(1. if int(frac_l*10)%2==0 else -.6)
            add(_leaf_blade(p_start,p_dir,u_out_n,u_side_n,.125,.028,.0034),leaf_mat)

        # 7c. Soundbox border vine riding along the outer +-Z stone cheek on the +n_back side:
        ub_v=np.linspace(0.,1.,len(bp_sub))
        sgn_b=-1. if v_idx==0 else 1.
        w_frac=.68+.08*np.sin(2.2*np.pi*ub_v+v_idx*np.pi)
        z_eff_v=bd_sub if sgn_b>0 else np.minimum(bd_sub,.172)
        z_cheek=sgn_b*(z_eff_v*.96+.010)
        pts_bv=bp_sub+n_back*(bw_sub*w_frac)[:,None]+np.c_[np.zeros(len(bp_sub)),np.zeros(len(bp_sub)),z_cheek]
        crv_bv=sample_curve(pts_bv,44)
        add(sweep(crv_bv,.012,.011,sides=12),v_mat)
        for frac_b in (.16,.36,.56,.76,.90):
            ib=int((len(bp_sub)-3)*frac_b)
            p_start=pts_bv[ib]; p_dir=pts_bv[ib+2]-p_start; p_dir/=np.linalg.norm(p_dir)+1e-9
            u_out_b=np.array([0.,0.,sgn_b])
            u_side_b=n_back[ib]*(.45 if int(frac_b*10)%2==0 else -.45)
            add(_leaf_blade(p_start,p_dir,u_out_b,u_side_b,.125,.028,.0034),leaf_mat)
    return pieces,mats


def soundboard(elements):
    """Sitka spruce soundboard panels on both the front (+z) and string-facing (-z)
    faces of the soundbox, plus a turned Sitka spruce ferrule-seat boss directly
    behind each brass string-foot eyelet so 100% of every eyelet sits on spruce
    while 100% of every string and eyelet lip/flange stands proud in front."""
    a=np.array([s['a'] for s in elements])
    order=np.argsort(a[:,0]); a=a[order]
    frame,info,_=harp_backbone(elements)
    indices=np.flatnonzero((np.array(info['labels'])==2)&(frame.path[:,1]>.36))[2:-2]
    path=frame.path[indices].copy();w=frame.widths[indices];d=frame.depths[indices]
    tang=np.gradient(path,axis=0); tang/=np.linalg.norm(tang,axis=1)[:,None]
    # Stringward normal in XY (pointing up-and-left from frame.path toward s['a']):
    n_str=np.c_[tang[:,1],-tang[:,0],np.zeros(len(path))]
    n_str/=np.linalg.norm(n_str,axis=1)[:,None]
    if np.dot(a.mean(axis=0)[:2]-path.mean(axis=0)[:2],n_str.mean(axis=0)[:2])<0:
        n_str=-n_str
    u=np.linspace(0,1,len(path));fade=smoothstep(u/.05)*smoothstep((1-u)/.04)
    face_pos=d*.76+.006-.006*(1-fade)
    # On the string-facing (-Z) side, cap face_offset at 0.172 m (z >= z_str + 0.028 m, 6 mm proud
    # of the capped -Z stone cove at 0.166 m, and 5 mm behind the deepest rim of the tilted brass eyelets):
    face_neg=np.minimum(d*.76,.166)+.006-.006*(1-fade)
    profile=np.array([[-1,-.7],[-.95,-1],[.95,-1],[1,-.7],[1,.7],[.95,1],[-.95,1],[-1,.7]])
    panel_center=path+n_str*(w*.04)[:,None]
    panel_width=w*.80*(.92+.08*fade)
    panels=[]
    for sgn,face_offset in ((1.,face_pos),(-1.,face_neg)):
        panel=sweep(panel_center.copy(),panel_width,.0035,profile=profile)
        off=sgn*face_offset
        panel.vertices[:len(path)*len(profile),2]+=np.repeat(off,len(profile))
        panel.vertices[-2:,2]+=off[[0,-1]]
        panel.path[:,2]+=off
        panels.append(panel)
    # Turned Sitka spruce ferrule-seat boss aligned with EYELET['barrel'] directly behind each brass eyelet flange:
    u_barrel=np.array(EYELET['barrel'],dtype=float)
    u_ax=u_barrel/np.linalg.norm(u_barrel)
    for pt_a in a:
        p0=pt_a+u_ax*(EYELET['flange_h']+.0003)
        p1=pt_a+u_ax*.115
        seat_crv=sample_curve([p0,.5*(p0+p1),p1],10)
        panels.append(sweep(seat_crv,np.linspace(.0365,.040,len(seat_crv)),np.linspace(.0365,.040,len(seat_crv)),sides=24))
    return panels

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
    from .drives import pack_masses
    reports=[validate_mesh(m) for m in pieces]
    if not all(r['ok'] for r in reports): raise ValueError((name,reports))
    if materials is not None and len(materials)!=len(pieces): raise ValueError((name,'one material per piece',len(materials),len(pieces)))
    entry=dict(name=name,material=material,classification=classification,
               pieces=[m.to_dict() for m in pieces],component_checks=reports)
    if materials is not None: entry['piece_materials']=list(materials)
    pack_masses(entry)
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
