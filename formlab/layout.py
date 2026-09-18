"""Score geometry -> world string endpoints (world = 3 x score units).

A mechanism whose score carries `fanned` positions (Mechanism.fan) is laid
out straight from pos: the planner, the arm clearance rule and the model
then agree on where every string is. Older scores without the flag keep
the display-only harp/rake fan that used to live here."""
import math


def string_endpoints(mechanism, string):
    mid=mechanism['id']; mp=mechanism['pos']; sp=string['pos']
    x=3*(mp[0]+sp[0]); z=3*(mp[2]+sp[2]); length=3*string['length']*(1.7 if mid=='harp' else 1.0)
    struck=mechanism['kind']=='struck'
    y=(1.35 if struck else 2.05+3*mp[1])+3*sp[1]
    if mechanism.get('fanned') and not struck:
        # pos is the string's foot on the diagonal soundboard; it rises from there.
        return [x,y,z],[x,y+length,z]
    if mid in ('harp','rake'):
        xs=[s['pos'][0] for s in mechanism['strings']]
        lengths=[s['length'] for s in mechanism['strings']]
        u=math.log(max(lengths)/string['length'])/math.log(max(lengths)/min(lengths))
        if mid=='harp': u=u**.70
        span=3*(max(xs)-min(xs))*(.34 if mid=='harp' else .70)
        x=3*mp[0]+span*(u-.5)
        # A diagonal soundboard gathers the strings into a traditional triangular frame.
        y=.66+(1.64 if mid=='harp' else 1.36)*u
        return [x,y,z],[x,y+length,z]
    if struck: return [x,y,z-length/2],[x,y,z+length/2]
    return [x,y-length/2,z],[x,y+length/2,z]


# The bar instrument's construction (numpy-only: Blender imports this module bare).
# A free-free bar's fundamental has its nodes 22.4 % in from each end; a mallet
# instrument hangs every bar on a cord through holes drilled there, so the rails
# that carry the cord follow the node lines and converge toward the short, high
# bars. Below each bar a closed quarter-wave tube resonates; the end frames are
# as wide as the local rail spread, so the bass end stands broader.
NODE=.2242
BAR=dict(thick=.11, rail_gap=.03)                    # bar thickness; bar underside to rail top
RAIL=dict(half_y=.03, half_z=.035, over=.30)         # 60 mm deep, 70 mm wide, .30 m past the end bars
END=dict(inset=.06, upright=.10, half_x=.045, taper=.06, foot=.22, foot_half_y=.04, foot_half_x=.06)
BOARD=dict(y=.70, half_y=.11, half_z=.0125, over=.05)
RESONATOR=dict(top_gap=.03, r_max=.09, rail_gap=.012, c=343.0)
def bar_nodes(a,b):
    """The two nodal points of a bar between its ends a and b (lists, world)."""
    d=[b[i]-a[i] for i in range(3)]
    return [[a[i]+d[i]*NODE for i in range(3)],[b[i]-d[i]*NODE for i in range(3)]]
def resonator(midi,node_half,rail_half_z=RAIL['half_z']):
    """Closed quarter-wave tube for one bar: (radius, length) in world metres.

    world = 3 x real: the real tube is c/4f less the open-end correction .61 r;
    its radius is capped so the tube hangs between the rails with a gap."""
    f=440*2**((midi-69)/12); r=min(RESONATOR['r_max'],node_half-rail_half_z-RESONATOR['rail_gap'])
    return r, 3*RESONATOR['c']/(4*f)-.61*r
def bar_frame_plan(elements,floor=-.01):
    """Every number the bar frame, its hardware and the text need, from the bars alone."""
    import numpy as np
    bars=sorted(elements,key=lambda s:s['a'][0])
    A=np.array([s['a'] for s in bars],float); B=np.array([s['b'] for s in bars],float)
    x=A[:,0]; top=A[:,1]; zc=(A[:,2]+B[:,2])/2; length=np.linalg.norm(B-A,axis=1); half=NODE*length
    nodes=np.array([bar_nodes(a,b) for a,b in zip(A,B)])      # (n,2,3): back (−z), front (+z)
    bottom=float(top.min())-BAR['thick']; rail_top=bottom-BAR['rail_gap']; rail_y=rail_top-RAIL['half_y']
    over=RAIL['over']; xs=np.r_[x[0]-over,x,x[-1]+over]
    def extend(z):
        s0=(z[1]-z[0])/(x[1]-x[0]); s1=(z[-1]-z[-2])/(x[-1]-x[-2])
        return np.r_[z[0]-s0*over,z,z[-1]+s1*over]
    rails={'back':np.c_[xs,np.full(len(xs),rail_y),extend(nodes[:,0,2])],
           'front':np.c_[xs,np.full(len(xs),rail_y),extend(nodes[:,1,2])]}
    cross_y=rail_y-RAIL['half_y']-END['half_x']                # the rails sit on the crosspiece
    ends=[]
    for xe in (xs[0]+END['inset'],xs[-1]-END['inset']):
        zb=float(np.interp(xe,xs,rails['back'][:,2])); zf=float(np.interp(xe,xs,rails['front'][:,2]))
        ends.append(dict(x=float(xe),z_back=zb,z_front=zf,uprights=[zb-END['upright'],zf+END['upright']],
                         cross_y=float(cross_y),foot=[zb-END['foot'],zf+END['foot']],floor=floor))
    # The name board hangs on the front uprights' faces; its line is straight between them.
    bz=[e['uprights'][1]+END['half_x']+BOARD['half_z'] for e in ends]
    board=dict(x=[ends[0]['x']-BOARD['over'],ends[1]['x']+BOARD['over']],z=bz,y=BOARD['y'])
    cord_y=float(top.min())-BAR['thick']/2
    posts={}
    for side,k in (('back',0),('front',1)):
        px=np.r_[x[0]-(x[1]-x[0])/2,(x[:-1]+x[1:])/2,x[-1]+(x[-1]-x[-2])/2]
        posts[side]=[dict(x=float(p),z=float(np.interp(p,xs,rails[side][:,2])),y0=float(rail_top),y1=cord_y+.02) for p in px]
    res=[]
    for s,h,xx,zz in zip(bars,half,x,zc):
        r,L=resonator(float(s['midi']),float(h)); res.append(dict(id=s.get('id'),x=float(xx),z=float(zz),radius=float(r),length=float(L),top=bottom-RESONATOR['top_gap']))
    stretch=dict(y=.13,z=float(zc.mean()),x=[ends[0]['x'],ends[1]['x']])
    bank=dict(y=bottom-RESONATOR['top_gap']-.06,z=float(zc.mean()),x=[ends[0]['x'],ends[1]['x']])
    return dict(rails=rails,rail_y=float(rail_y),rail_top=float(rail_top),bar_bottom=bottom,cord_y=cord_y,ends=ends,
                board=board,posts=posts,resonators=res,stretcher=stretch,bank=bank,nodes=nodes)
PEDALS=('D','C','B','E','F','G','A')            # left foot: D C B (outside in); right foot: E F G A
def harp_base_plan(left,zz,floor=-.01,with_pedals=True):
    """A harp's base: a box the column and body foot seat in, with a crown and a
    sole. With `with_pedals` (a pedal harp) seven pedals leave slots in its front face
    (toward the soundbox, +x), three on the left of the string plane and four on
    the right, treads on the floor; without (the rake, strung like a lever harp)
    it is a plain plinth.

    Kept inside the obstacle the rail search is promised (x left-.82..+.46,
    y to .36, z ±.58) so changing the base never moves a rail."""
    box=dict(x=[left-.72,left+.30],y=[floor+.05,.29],z=[zz-.46,zz+.46])
    crown=dict(y=[.29,.335],inset=-.02); sole=dict(y=[floor,floor+.05],inset=.04)   # inset: per side, negative grows
    zs=[-.36,-.24,-.12,.09,.20,.31,.42]
    pedals=[]
    for note,dz in zip(PEDALS if with_pedals else (),zs):
        z=zz+dz; x0=box['x'][1]
        pedals.append(dict(note=note,z=z,slot=[x0,.06,.19],lever=[[x0-.10,.125,z],[x0+.30,.055,z]],tread=[x0+.30,.045,z],pivot=[x0-.10,.125,z]))
    return dict(box=box,crown=crown,sole=sole,pedals=pedals,front_x=box['x'][1])
def board_z(plan,x):
    b=plan['board']; return b['z'][0]+(b['z'][1]-b['z'][0])*(x-b['x'][0])/(b['x'][1]-b['x'][0])


# The chamber's flywheel (numpy-free). A flywheel is carried on an axle in two
# plummer blocks — split bearing housings bolted to pedestals on a sole plate —
# one either side of the wheel, and it drives something: a pulley on the axle's
# back end and a flat belt to a pulley on a bracket at the chamber cabinet's end.
# The wheel's axis is world z (it faces the house); Godot turns it a bar a turn.
FLYWHEEL=dict(width=.07, hub_r=.09, hub_w=.12, axle_r=.03, axle=(-.34,.22), bearing_z=.16, housing_r=.065, housing_w=.10,
              block=(.20,.06,.11), pedestal=(.14,.10), sole=(.30,.03,.54), bolt_r=.012, bolt_h=.012, bolt_x=.08,
              pulley_z=-.27, pulley_r=.12, pulley_w=.06, belt_pulley_r=.10, belt_w=.05, belt_t=.006,
              ear=(.18,.26,.03), ear_gap=.05, stub_r=.022,
              teeth=52)   # the rim's ring gear: 52 teeth at the pinions' 15 mm module reach the wheel's radius (formlab.gear.profile)
def flywheel_plan(centre,r,cabinet_x,floor=-.01):
    """Every solid of the flywheel assembly, from the wheel's centre (world),
    its radius, and the x of the cabinet end face the belt pulley's bracket
    bolts to (the wheel stands beyond that face). Boxes are (centre, size);
    cylinders are (a, b, radius) along their axis."""
    F=FLYWHEEL; cx,cy,cz=centre; bz=F['bearing_z']
    plan=dict(centre=list(centre),r=r,teeth=FLYWHEEL['teeth'],boxes={},cyls={},floor=floor)
    B=plan['boxes']; C=plan['cyls']
    C['hub']=([cx,cy,cz-F['hub_w']/2],[cx,cy,cz+F['hub_w']/2],F['hub_r'])
    C['axle']=([cx,cy,cz+F['axle'][0]],[cx,cy,cz+F['axle'][1]],F['axle_r'])
    for side in (-1,1):
        z=cz+side*bz; tag='back' if side<0 else 'front'
        C[tag+' housing']=([cx,cy,z-F['housing_w']/2],[cx,cy,z+F['housing_w']/2],F['housing_r'])
        bw,bh,bl=F['block']; B[tag+' block']=([cx,cy-F['housing_r']+bh/2-.02,z],[bw,bh,bl])
        top=cy-F['housing_r']+bh-.02-bh   # the block's underside
        pw,pl=F['pedestal']; B[tag+' pedestal']=([cx,(floor+F['sole'][1]+top)/2,z],[pw,top-floor-F['sole'][1],pl])
        for sx in (-1,1):
            C[f'{tag} bolt {"l" if sx<0 else "r"}']=([cx+sx*F['bolt_x'],top+bh,z],[cx+sx*F['bolt_x'],top+bh+F['bolt_h'],z],F['bolt_r'])
    B['sole']=([cx,floor+F['sole'][1]/2,cz],list(F['sole']))
    pz=cz+F['pulley_z']; C['drive pulley']=([cx,cy,pz-F['pulley_w']/2],[cx,cy,pz+F['pulley_w']/2],F['pulley_r'])
    # the belt pulley on its bracket: two ears standing off the cabinet's end face, a stub axle between them
    ew,eh,et=F['ear']; ex=cabinet_x-ew/2
    for side in (-1,1):
        B[('back' if side<0 else 'front')+' ear']=([ex,cy,pz+side*(F['pulley_w']/2+F['ear_gap']+et/2)],[ew,eh,et])
    qx=cabinet_x-ew+F['belt_pulley_r']*.3; plan['belt_pulley_centre']=[qx,cy,pz]
    span=F['pulley_w']/2+F['ear_gap']+et/2; C['stub axle']=([qx,cy,pz-span],[qx,cy,pz+span],F['stub_r'])   # into each ear's mid-thickness
    C['belt pulley']=([qx,cy,pz-F['pulley_w']/2],[qx,cy,pz+F['pulley_w']/2],F['belt_pulley_r'])
    # the flat belt: the two outer tangents between the pulleys, and a wrap round each
    r1,r2=F['pulley_r'],F['belt_pulley_r']; dx,dy=qx-cx,0.0; d=math.hypot(dx,dy); ux,uy=dx/d,dy/d; vx,vy=-uy,ux
    beta=math.acos((r1-r2)/d); plan['belt']=[]
    for s in (-1,1):
        nx,ny=ux*math.cos(beta)+s*vx*math.sin(beta),uy*math.cos(beta)+s*vy*math.sin(beta)
        p1=[cx+r1*nx,cy+r1*ny]; p2=[qx+r2*nx,cy+r2*ny]
        plan['belt'].append(dict(a=[p1[0],p1[1],pz],b=[p2[0],p2[1],pz],angle=math.atan2(p2[1]-p1[1],p2[0]-p1[0]),
                                 length=math.hypot(p2[0]-p1[0],p2[1]-p1[1]),normal=[nx,ny]))
    plan['wraps']=[([cx,cy,pz],r1+F['belt_t']/2),([qx,cy,pz],r2+F['belt_t']/2)]
    plan['bounds']=_plan_bounds(plan)
    return plan
def _plan_bounds(plan):
    lo=[1e9]*3; hi=[-1e9]*3
    def take(p,e):
        for i in range(3): lo[i]=min(lo[i],p[i]-e[i]); hi[i]=max(hi[i],p[i]+e[i])
    c=plan['centre']; take(c,[plan['r'],plan['r'],FLYWHEEL['width']/2])
    for centre,size in plan['boxes'].values(): take(centre,[s/2 for s in size])
    for a,b,r in plan['cyls'].values():
        for p in (a,b): take(p,[r]*3)
    for (p,r) in plan['wraps']: take(p,[r,r,FLYWHEEL['belt_w']/2])
    return [lo,hi]


# The neck's hardware (numpy-free: Blender's builder and the ruler read it).
# A harp's strings run close to ONE side of the neck, and that side carries
# the action: the brass plate seated on the neck's bead crests, and for each
# string two discs whose fork pins straddle the string. Above the discs the
# string bears on a bridge pin at the plate and then leans to its tuning pin,
# which passes through the neck and the plate on its far face so its square
# head stands proud there, where the tuning key goes. The string's speaking
# length ends at `b`; the dead length from there to the tuning pin is drawn
# but never sounds.
NECK=dict(plate=.008, disc_r=.022, disc_half=.013, rows=(.06,.125), fork=(.016,.009), fork_r=.007, straddle=.012,
          bridge_y=.175, bridge_r=.006, pin_y=.225, pin_r=.015, pin_lean=.035, pin_through=.04, key=.025)
def neck_plan(b,face_z,back_z,discs=True):
    """Every point of one string's neck hardware, from its upper end `b`, the
    world z of the neck's string-side face (its bead crests at the string) and
    of its far face. The plate stands `plate` proud of the crests toward the
    string; the discs sit on the plate; every pin on the string side reaches
    `straddle` past the string plane. The bridge pin stands on the +x side of
    the string so the dead length above it leans -x to the tuning pin."""
    x,y,z0=b; d=NECK; plate_out=face_z-d['plate']
    rows=[]
    for dy in (d['rows'] if discs else ()):
        centre=[x,y+dy,plate_out-d['disc_half']]
        rows.append(dict(centre=centre,r=d['disc_r'],half=d['disc_half'],
                         pins=[[x+s*d['fork'][0],y+dy+s*d['fork'][1],plate_out-2*d['disc_half']] for s in (-1,1)],pin_tip=z0-d['straddle']))
    bridge=dict(centre=[x+d['bridge_r'],y+d['bridge_y']],z=[z0-d['straddle'],plate_out],r=d['bridge_r'],contact=[x,y+d['bridge_y'],z0])
    tx=x-d['pin_lean']; ty=y+d['pin_y']; head_z=back_z+d['pin_through']
    pin=dict(centre=[tx-d['pin_r'],ty],z=[z0-d['straddle'],head_z],r=d['pin_r'],contact=[tx,ty,z0],key=[tx-d['pin_r'],ty,head_z+d['key']/2])
    return dict(plate_out=float(plate_out),discs=rows,bridge=bridge,pin=pin,dead=[[x,y,z0],bridge['contact'],pin['contact']])

# The dead length does not stop where it meets the tuning pin: it winds on. A
# harp string wraps its pin between the string plane and the neck, coil on
# coil, and the coil is what a tuner's eye reads. The wire arrives from the
# bridge below on the pin's +x side and goes on up over the pin (counter-
# clockwise seen from +z), advancing toward the neck a wire's diameter a turn.
WRAP=dict(turns=2.5, clear=.003)
def pin_wrap(pin,plate_out):
    """Where one string's dead length winds on its tuning pin, from `neck_plan`'s
    pin and plate: the helix's axis point on the string plane, the pin's radius
    the wire winds on, the turns, and the room along the pin from the plane to
    just short of the plate's outer face. The wire's gauge decides the pitch."""
    cx,cy=pin['centre']; z0=pin['contact'][2]
    return dict(centre=[cx,cy,z0],r=pin['r'],turns=WRAP['turns'],room=float(plate_out-z0-WRAP['clear']))


# A trestle bench for the struck elements that sit on it (the glass bells, the
# temple blocks): two straight rails along the row on a splayed-leg trestle at
# each end, a bearer across the rails under every element, and the element's
# own mount on its bearer — rubber pads at a block's nodal points (it rings
# like a bar), a call bell's base flange and centre post reaching up into its
# crown. A fascia hung on the bearers' front ends carries the names.
BENCH=dict(rail_z=.20, rail_half_y=.035, rail_half_z=.04, over=.25, bearer_half_y=.03, bearer_half_x=.035, bearer_over=.06,
           pad=.02, leg_splay=.16, leg_top=.05, leg_toe=.038, cross_half=.045, tie=.45, board_drop=.10, end_inset=.08)
BELL=dict(drop=.12, mouth=.315, post_r=.03, post_in=.05, flange_r=.075)   # bell() profile: top at drop above its origin, lip mouth below
def bench_elements(strings,material):
    """Annotate struck elements with what the bench needs: their underside, top and mount kind."""
    out=[]
    for s in strings:
        y=s['a'][1]
        if material=='glass': out.append(dict(s,underside=y-BELL['drop']-BELL['mouth'],top=y,mount='post'))
        else: out.append(dict(s,underside=y-BAR['thick'],top=y,mount='pads'))
    return out
def bench_plan(elements,floor=-.01):
    """Every number the bench, its mounts and its text need, from the annotated elements."""
    import numpy as np
    B=BENCH; els=sorted(elements,key=lambda s:s['a'][0])
    x=np.array([s['a'][0] for s in els],float); zc=np.array([(s['a'][2]+s['b'][2])/2 for s in els],float); zm=float(zc.mean())
    under=min(s['underside'] for s in els)
    bearer_top=under-B['pad']; bearer_y=bearer_top-B['bearer_half_y']
    rail_top=bearer_y-B['bearer_half_y']; rail_y=rail_top-B['rail_half_y']
    x0,x1=float(x[0]-B['over']),float(x[-1]+B['over'])
    rails={'back':[[x0,rail_y,zm-B['rail_z']],[x1,rail_y,zm-B['rail_z']]],'front':[[x0,rail_y,zm+B['rail_z']],[x1,rail_y,zm+B['rail_z']]]}
    zb,zf=zm-B['rail_z']-B['bearer_over'],zm+B['rail_z']+B['bearer_over']
    bearers=[dict(id=s.get('id'),x=float(xx),y=float(bearer_y),z=[zb,zf],top=float(bearer_top)) for s,xx in zip(els,x)]
    cross_y=rail_y-B['rail_half_y']-B['cross_half']
    ends=[]
    for xe in (x0+B['end_inset'],x1-B['end_inset']):
        legs=[dict(top=[xe,cross_y,zm+sign*B['rail_z']],toe=[xe,floor+.02,zm+sign*(B['rail_z']+B['leg_splay'])]) for sign in (-1,1)]
        ty=floor+B['tie']*(cross_y-floor)           # the tie meets each leg where it has splayed to at that height
        tz=[float(np.interp(ty,[floor+.02,cross_y],[l['toe'][2],l['top'][2]])) for l in legs]
        ends.append(dict(x=float(xe),cross_y=float(cross_y),z=[zm-B['rail_z'],zm+B['rail_z']],legs=legs,tie_y=float(ty),tie_z=tz,floor=floor))
    stretcher=dict(y=ends[0]['tie_y'],z=zm,x=[ends[0]['x'],ends[1]['x']])
    board=dict(x=[x0+.03,x1-.03],y=float(rail_y-B['board_drop']),z=float(zf+BOARD['half_z']))
    mounts=[]
    for s,b in zip(els,bearers):
        if s['mount']=='post':
            mounts.append(dict(id=b['id'],kind='post',x=b['x'],z=float((s['a'][2]+s['b'][2])/2),y0=bearer_top,y1=s['top']-BELL['post_in']))
        else:
            n=bar_nodes(s['a'],s['b'])
            mounts.append(dict(id=b['id'],kind='pads',x=b['x'],z=[n[0][2],n[1][2]],y0=bearer_top,y1=s['underside']))
    return dict(rails=rails,rail_y=float(rail_y),rail_top=float(rail_top),bearers=bearers,ends=ends,stretcher=stretcher,board=board,
                mounts=mounts,x=[x0,x1],z=zm,top=float(bearer_top),underside=float(under))

# A harp string leaves its soundbox through a brass eyelet: a flanged ring
# seated on the mouth of the ferrule that carries the string down into the
# moulding. The ferrule itself is the recipe's (recipes.harp_frame); its barrel
# offset and gauge live here so the eyelet, the recipe and the ruler agree.
EYELET=dict(barrel=(.035,-.13,.20), ferrule=(.024,.04), flange_r=.034, flange_h=.005, lip_r=.020, lip_t=.008)
def eyelet_plan(a):
    """The eyelet at string foot a: its axis u runs down the ferrule's barrel; a
    flange disc covers the mouth from a down the barrel, and a rounded lip
    stands proud of it round the hole the string leaves by."""
    d=EYELET; a=[float(v) for v in a]; L=math.sqrt(sum(v*v for v in d['barrel'])); u=[v/L for v in d['barrel']]
    flange=dict(a=a,b=[a[i]+u[i]*d['flange_h'] for i in range(3)],r=d['flange_r'])
    lip=dict(centre=[a[i]-u[i]*d['lip_t']/2 for i in range(3)],r=d['lip_r'],t=d['lip_t'],hole=d['lip_r']-d['lip_t']/2)
    return dict(centre=a,axis=u,flange=flange,lip=lip)
