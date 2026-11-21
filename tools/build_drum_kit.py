"""Build Overcrank's kit and seated automaton. Run in Blender from the repo root."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'formlab'), str(ROOT/'tools')]
from pillar_players import Casting, UP, X, Z, spindle
from acoustic_bodies import vec

OUT = ROOT/'harness/assets'
O = np.zeros(3)
TAU = math.tau
BRASS, STEEL, DARK = 'Bearing brass', 'Blued steel', 'Gunmetal'
RED, GREEN, CREAM, RUBBER = 'Oxblood lacquer', 'Petrol enamel', 'Ivory enamel', 'Rubber'
SKIN, BRONZE, WOOD, EYE = 'Coated head', 'Hammered bronze', 'Hickory', 'Optical amber'
layout = {'voices': {}, 'upper': .51, 'lower': .51, 'stick': .356, 'bead': .009,
          'thigh': .49, 'shin': .46, 'beater_length': .286, 'beater_radius': .037,
          'chest': [0,.98,-.70], 'shoulder': [.317,.432,.011]}
kit = None


def material(name, rgb, metallic, roughness):
    m=bpy.data.materials.new(name)
    color=tuple(((int(rgb[i:i+2],16)/255+.055)/1.055)**2.4 for i in (0,2,4))+(1.,)
    m.diffuse_color=color
    m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=color
    bs.inputs['Metallic'].default_value=metallic
    bs.inputs['Roughness'].default_value=roughness
    if name==EYE:
        bs.inputs['Emission Color'].default_value=color
        bs.inputs['Emission Strength'].default_value=1.6


def rod(part,a,b,r,mat,segments=16):
    a,b=np.array(a),np.array(b)
    part.lathe(a,b-a,[(0.,r*.83),(.002,r),(np.linalg.norm(b-a)-.002,r),(np.linalg.norm(b-a),r*.83)],mat,segments)


def ring(part,c,axis,r,t,mat):
    # The inner lip is a real return around the hoop.
    u=np.cross(axis,Z if abs(axis[2])<.8 else UP);u/=np.linalg.norm(u)
    v=np.cross(axis,u)
    rows=[]
    for a in np.linspace(0,TAU,97):
        d=math.cos(a)*u+math.sin(a)*v
        rows.append([c+(r+t*math.cos(b))*d+t*math.sin(b)*axis for b in np.arange(8)*TAU/8])
    part.loft(rows,mat)


def rounded(part,profiles,mat):
    rows=[]
    for y,rx,rz,z in profiles:
        rows.append([(rx*math.copysign(abs(math.cos(a))**.50,math.cos(a)),y,
                      z+rz*math.copysign(abs(math.sin(a))**.50,math.sin(a))) for a in np.arange(48)*TAU/48])
    part.loft(rows,mat)


def lettering(text,at,size,mat,name):
    font=bpy.data.curves.new(name,'FONT')
    font.body=text;font.align_x='CENTER';font.align_y='CENTER';font.size=size;font.space_character=1.22
    font.extrude=.00045;font.bevel_depth=.00015
    ob=bpy.data.objects.new(name,font);bpy.context.collection.objects.link(ob)
    ob.location=vec(at);ob.rotation_euler.x=math.pi/2
    font.materials.append(bpy.data.materials[mat])
    bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    bpy.ops.object.convert(target='MESH')
    ob.select_set(False)


def tripod(part,x,z,top,spread):
    c=np.array([x,0,z])
    part.lathe(c,UP,[(.024,.021),(.33,.021),(.335,.027),(.36,.027),(.365,.016),(top-.035,.014),(top,.012)],STEEL)
    for a in np.arange(3)*TAU/3+.32:
        d=np.array([math.cos(a),0,math.sin(a)])
        foot=c+d*spread+UP*.025
        rod(part,c+UP*.32,foot,.011,STEEL)
        rod(part,c+UP*.16,foot*.72+(c+UP*.32)*.28,.006,DARK)
        part.lathe(foot,d+.20*UP,[(-.028,.017),(.025,.019),(.043,.014)],RUBBER)


def drum(name,c,r,depth,axis):
    c=np.array(c);axis=np.array(axis)
    horiz=name=='kick'
    start=c-axis*depth
    u=X;v=np.cross(axis,u)
    # Thin wall, rolled hoops, individual hooked tension rods and hex nuts.
    wall=[]
    for angle in np.linspace(0,TAU,97):
        radial=u*math.cos(angle)+v*math.sin(angle)
        wall.append([start+axis*h+radial*rr for h,rr in
                     [(.006,r-.012),(.006,r-.003),(.013,r),(depth-.013,r),(depth-.006,r-.003),(depth-.006,r-.012)]])
    kit.loft(wall,RED)
    for h in (.012,depth-.012):
        ring(kit,start+axis*h,axis,r+.006,.008,STEEL if not horiz else WOOD)
        ring(kit,start+axis*(h+(.017 if h<depth/2 else -.017)),axis,r+.002,.0027,BRASS)
    for i in range(10 if r>.23 else 8):
        a=TAU*(i+.5)/(10 if r>.23 else 8)
        radial=math.cos(a)*u+math.sin(a)*v
        base=start+radial*(r+.012)
        kit.lathe(base,axis,[(depth*.29,.008),(depth*.33,.017),(depth*.41,.018),
                             (depth*.44,.012),(depth*.58,.012),(depth*.62,.018),(depth*.68,.017),(depth*.72,.008)],STEEL,16)
        for lo,hi in ((.010,.35*depth),(.65*depth,depth-.010)):
            rod(kit,base+axis*lo,base+axis*hi,.0045,BRASS,12)
        for h in (.008,depth-.015):
            kit.lathe(base,axis,[(h,.008),(h+.008,.008)],STEEL,6)
    if horiz:
        # Audience-side resonant head with a brass-bound microphone port.
        layout['batter_z']=float(start[2])
        port=c+np.array([.148,-.122,0])
        rows=[]
        for a in np.linspace(0,TAU,97):
            d=X*math.cos(a)+UP*math.sin(a)
            rows.append([port+d*.063,c+d*(r-.007),c+d*(r-.007)-Z*.002,port+d*.063-Z*.002])
        kit.loft(rows,CREAM)
        ring(kit,port+Z*.0007,Z,.064,.005,BRASS)
        sleeve=[]
        for a in np.linspace(0,TAU,65):
            d=X*math.cos(a)+UP*math.sin(a)
            sleeve.append([port+d*.063,port+d*.062-Z*.12,port+d*.064-Z*.12,port+d*.065])
        kit.loft(sleeve,RUBBER)
        lettering('L O A M',c+[0,.076,.004],.103,DARK,'Kick drum maker')
        lettering('P E R C U S S I O N',c+[0,.014,.004],.027,DARK,'Kick drum imprint')
        for side in (-1,1):
            rod(kit,c+[side*.36,-.15,-.12],c+[side*.49,-.42,-.06],.018,STEEL)
        skin=Casting();skin.lathe(O,Z,[(-.003,r-.006),(0,r-.006)],SKIN,96)
        skin.object(name+' head',position=start)
        return
    ring(kit,c+axis*.001,axis,r+.0005,.005,STEEL)
    for h in (.27,.75):
        ring(kit,start+axis*(depth*h),axis,r+.0005,.00085,CREAM)
    badge=c-UP*(depth*.5)+Z*(r+.003)
    kit.lathe(badge,Z,[(0,.030),(.003,.031),(.005,.028)],BRASS,8)
    kit.lathe(badge+Z*.005,Z,[(0,.017),(.0015,.018)],DARK,8)
    for sign in (-1,1):
        kit.lathe(badge+X*(sign*.022)+Z*.004,Z,[(0,.002),(.003,.002)],STEEL,12)
    if name=='snare':
        # The snare bed, wire ribbons, butt plate and throw lever are on the shell.
        for k in range(-8,9):
            x=k*.0028
            rod(kit,start+[x,-.002,-r*.82],start+[x,-.002,r*.82],.00075,STEEL,8)
        rod(kit,start+[r*.87,.04,.10],start+[r*.87,.13,.14],.009,BRASS)
    skin=Casting()
    rows=[]
    for rho in np.linspace(.001,r-.004,17):
        rows.append([rho*(X*math.cos(a)+Z*math.sin(a)) for a in np.arange(80)*TAU/80])
    skin.points.extend(p for row in rows for p in row)
    for j in range(16):
        for k in range(80):
            a=j*80+k;b=j*80+(k+1)%80
            skin.faces.append((a,b,b+80,a+80));skin.slots.append(0)
    skin.faces.append(tuple(range(79,-1,-1)));skin.slots.append(0)
    skin.materials.append(SKIN)
    skin.object(name+' head',position=c)
    layout['voices'][name]=dict(center=c.tolist(),radius=r,kind='skin',normal=[0,1,0])
    if name=='floor':
        for a in np.arange(3)*TAU/3:
            d=X*math.cos(a)+Z*math.sin(a); end=c+d*(r+.064);end[1]=.026
            rod(kit,c-depth*.4*UP+d*(r+.015),end,.009,STEEL)
            kit.ball(end,.018,RUBBER)
    elif name=='snare':
        tripod(kit,c[0],c[2],c[1]-depth,.22)
    else:
        collar=np.array([0.,.83,.45])
        rod(kit,collar,c-depth*UP,.021,STEEL)
        kit.ball(collar,.042,DARK)


def cymbal(name,center,r,normal):
    c=np.array(center);n=np.array(normal,dtype=float);n/=np.linalg.norm(n)
    u=X-n*n[0];u/=np.linalg.norm(u);v=np.cross(n,u)
    metal=Casting()
    # Reversed rows close underneath at the central sleeve; the edge is thin.
    section=[(.015,.063),(.061,.064),(.110,.055),(.19,.046),(.26,.027),
             (.36,.022),(.52,.016),(.68,.010),(.81,.005),(.94,.001),(1.,-.002)]
    rows=[]
    for lower in (False,True):
        for k,h in section if not lower else reversed(section):
            height=(h*(r/.30)-(.003 if lower else 0))
            row=[]
            for a in np.arange(96)*TAU/96:
                rad=(r*k)*(1+.003*k*math.sin(5*a+.4)+.0018*k*math.sin(9*a))
                row.append(rad*(u*math.cos(a)+v*math.sin(a))+n*(height+.0016*k*k*math.sin(3*a)))
            rows.append(row)
    metal.loft(rows,BRONZE)
    metal.object(name+' plate',position=c)
    # Pick contacts on the actual hammered bow, with normals measured on
    # the adjacent facets. The motion rig carries them with the rocking plate.
    around=12 if c[0]<0 else 36
    spots=[]
    for k in range(around-4,around+5):
        pt=rows[7][k]
        normal=np.cross(rows[7][k+1]-rows[7][k-1],rows[8][k]-rows[6][k])
        normal/=np.linalg.norm(normal)
        if np.dot(normal,n)<0:normal=-normal
        spots.append(dict(point=pt.tolist(),normal=normal.tolist()))
    layout['voices'][name]=dict(center=c.tolist(),radius=r,kind='metal',normal=n.tolist(),spots=spots)
    tripod(kit,c[0],c[2],c[1]+.04,.26)
    kit.lathe(c,n,[(.027,.016),(.047,.021),(.066,.018),(.072,.012),(.094,.008)],DARK,24)
    rod(kit,c+n*.080-u*.024,c+n*.080+u*.024,.006,STEEL)
    if name=='hat':
        # Matched outer lips meet when the left pedal pulls the clutch down.
        lip=np.array(rows[len(section)])
        bottom=Casting()
        mirror=[]
        for row in rows:
            points=np.array(row)
            points[:,1]=2*lip[:,1]-points[:,1]-.00008
            mirror.append(points)
        bottom.loft(mirror,BRONZE)
        bottom.object('Hat bottom',position=c)
        layout['hat_lip']=lip[0].tolist()
        rod(kit,c-UP*.06,np.array([.53,.08,-.40]),.006,STEEL)


def links(side):
    sign=-1 if side=='right' else 1
    for name,length,r in [('upper',layout['upper'],.071),('lower',layout['lower'],.055)]:
        arm=Casting()
        arm.ball(O,r*1.1,DARK);arm.ball(UP*length,r*.92,BRASS)
        spindle(arm,O,X,r*.81,r*2.5)
        arm.lathe(O,UP,[(.035,r*.64),(.057,r*.90),(.069,r*.98),(.13,r),
                        (length*.65,r*.64),(length*.73,r*.57)],GREEN,36)
        arm.lathe(O,UP,[(length*.68,r*.63),(length*.73,r*.63),(length*.74,r*.42),(length-.024,r*.42)],STEEL,28)
        for d in (-1,1):
            rod(arm,[d*r*.68,.082,-.016],[d*r*.42,length-.037,-.016],.0075,BRASS)
        arm.object(side+' '+name)
    # A forked palm and knurled opposing fingers close on a rotating stick collet.
    palm=Casting();palm.ball(O,.045,DARK)
    rounded(palm,[(-.040,.032,.029,0),(-.025,.049,.038,0),(.018,.052,.038,0),(.038,.038,.023,0)],GREEN)
    for k in (-1,0,1):
        y=k*.019
        rod(palm,[sign*.030,y,.006],[sign*.041,y,.043],.010,BRASS)
        rod(palm,[sign*.041,y,.043],[sign*.003,y,.049],.009,BRASS)
    spindle(palm,O,X,.018,.105)
    palm.object(side+' palm')
    stick=Casting()
    stick.lathe(O,UP,[(-.125,.0075),(-.122,.010),(-.106,.011),(.149,.010),
                       (.255,.009),(.321,.0054),(.337,.0048),(.350,.0056)],WOOD,32)
    stick.ball(UP*layout['stick'],layout['bead'],WOOD)
    for y in (-.055,-.043,-.031):
        stick.lathe(O,UP,[(y,.0108),(y+.004,.0108)],DARK,32)
    stick.object(side+' stick')
    foot=Casting()
    rounded(foot,[(-.021,.049,.107,.061),(-.009,.060,.123,.064),
                  (.016,.061,.115,.065),(.032,.052,.085,.071),(.040,.034,.045,.072)],GREEN)
    for z in (.05,.085,.115):
        rod(foot,[-.046,.023,z],[.046,.023,z],.006,BRASS)
    foot.object(side+' boot')
    for name in ('thigh','shin'):
        leg=Casting()
        length=layout[name]
        leg.ball(O,.053,BRASS);leg.ball(UP*length,.045,DARK)
        leg.lathe(O,UP,[(.020,.045),(.052,.068),(.105,.064),(length*.71,.044)],GREEN)
        rod(leg,UP*.16,UP*(length-.022),.033,STEEL)
        leg.object(side+' '+name)


def player():
    frame=Casting()
    rounded(frame,[(-.16,.14,.11,-.01),(-.12,.19,.135,0),(-.039,.206,.131,0),(-.015,.17,.11,0)],GREEN)
    for y in np.arange(-.010,.135,.027):
        frame.lathe(O,UP,[(y,.095),(y+.012,.132),(y+.022,.098)],DARK,36)
    rounded(frame,[(.077,.137,.111,0),(.106,.165,.13,0),(.22,.216,.146,.008),
                   (.37,.267,.155,0),(.416,.25,.149,0),(.451,.193,.115,0)],GREEN)
    for s in (-1,1):
        c=np.array([s*.317,.432,.011])
        rod(frame,c-X*.09,c+X*.09,.055,STEEL)
        frame.ball(c,.087,BRASS)
        for y in (.155,.37):
            frame.lathe(np.array([s*(.105 if y<.2 else .202),y,.143]),Z,[(0,.010),(.010,.010)],BRASS,6)
    for side in (-1,1):
        rod(frame,[side*.121,.122,.109],[side*.191,.313,.143],.004,BRASS)
        rod(frame,[side*.191,.313,.143],[side*.196,.387,.138],.004,BRASS)
    for y in (.18,.215,.25,.285):
        rod(frame,[-.072,y,.154],[.072,y,.154],.007,DARK)
    frame.lathe(np.array([0,.341,.155]),Z,[(0,.038),(.008,.037),(.014,.030)],BRASS)
    frame.lathe(np.array([0,.341,.165]),Z,[(0,.024),(.009,.023)],CREAM)
    rod(frame,[0,.341,.178],[.014,.355,.178],.0025,DARK)
    frame.lathe(O,UP,[(.421,.066),(.482,.081),(.497,.062),(.55,.059)],STEEL)
    frame.object('Torso casting')
    head=Casting()
    rounded(head,[(-.105,.076,.077,0),(-.087,.121,.099,0),(-.029,.155,.113,0),
                  (.089,.161,.120,0),(.132,.130,.105,0),(.147,.083,.077,0)],GREEN)
    for side in (-1,1):
        c=np.array([side*.077,.044,.110])
        head.lathe(c,Z,[(-.003,.062),(.012,.068),(.030,.064),(.040,.054)],BRASS,40)
        head.lathe(c,Z,[(.035,.052),(.045,.052),(.052,.040)],DARK,40)
        head.lathe(c,Z,[(.048,.034),(.057,.030),(.063,.020)],EYE,40)
        head.lathe(c+X*.003,Z,[(.060,.018),(.065,.015),(.067,.012)],DARK,32)
        head.ball(c+[.008,.008,.068],.0034,CREAM)
        head.lathe(np.array([side*.144,.044,-.015]),side*X,[(0,.055),(.018,.054),(.029,.038)],BRASS)
    for y in (-.045,-.027,-.009):
        rod(head,[-.051,y,.111],[.051,y,.111],.0048,DARK)
    rounded(head,[(.104,.157,.13,.014),(.113,.169,.145,.014),(.124,.163,.139,.013),(.138,.132,.109,0)],DARK)
    head.object('Optic housing')
    for side in ('right','left'):links(side)


def home_pose():
    """Seat every rigid part in the portable GLB, including in a plain glTF viewer."""
    def unit(v):
        return v/np.linalg.norm(v)
    def basis(direction,pin=X):
        y=unit(direction)
        x=unit(pin-y*np.dot(y,pin))
        return np.column_stack((x,y,np.cross(x,y)))
    def put(name,at,axes=None):
        if axes is None:axes=np.eye(3)
        rot=Matrix([vec(axes[:,0]),-vec(axes[:,2]),vec(axes[:,1])]).transposed()
        bpy.data.objects[name].matrix_world=Matrix.Translation(vec(at))@rot.to_4x4()
    def pair(names,root,tip,pole,a,b):
        axis=unit(tip-root)
        bend=unit(pole-axis*np.dot(axis,pole))
        d=np.linalg.norm(tip-root)
        along=(a*a-b*b+d*d)/(2*d)
        joint=root+along*axis+bend*np.sqrt(a*a-along*along)
        pin=np.cross(axis,bend)
        put(names[0],root,basis(joint-root,pin));put(names[1],joint,basis(tip-joint,pin))
    chest=np.array(layout['chest'])
    put('Torso casting',chest)
    put('Optic housing',chest+[0,.589,.028])
    for name,side in [('left',1),('right',-1)]:
        grip=np.array([side*.45,1.41,-.35])
        frame=basis(np.array([side*.32,.42,.82]))
        wrist=grip-frame[:,2]*.041
        shoulder=chest+np.array(layout['shoulder'])*[side,1,1]
        pair([name+' upper',name+' lower'],shoulder,wrist,np.array([side,-.42,-.46]),layout['upper'],layout['lower'])
        put(name+' stick',grip,frame);put(name+' palm',wrist,frame)
        heel=np.array(layout['pedals'][name])
        ankle=heel+[0,.040,.011]
        put(name+' boot',ankle)
        pair([name+' thigh',name+' shin'],chest+[side*.137,-.142,.029],ankle,
             np.array([side*.42,.1,1.]),layout['thigh'],layout['shin'])
        toe=heel+[0,.005,.244]
        pin=np.array(layout['beater'])+[.022,.039,-.040] if side<0 else np.array(layout['voices']['hat']['center'])-[0,.93,0]
        axes=basis(pin-toe)
        axes[:,1]*=np.linalg.norm(pin-toe)
        put(name+' pedal strap',toe,axes)


def build():
    global kit
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for spec in [(BRASS,'af8853',.76,.31),(STEEL,'9db2b7',.81,.24),(DARK,'313c42',.66,.32),
                 ('Woven rug','65413a',.01,.96),(RED,'a43122',.32,.28),(GREEN,'296660',.43,.32),(CREAM,'e8d8b7',.09,.48),
                 (RUBBER,'292b2a',.02,.79),(SKIN,'ddcfb7',.02,.70),(BRONZE,'cb9f55',.77,.29),
                 (WOOD,'d59c60',.01,.37),(EYE,'ffb345',.18,.21)]:
        material(*spec)
    kit=Casting()
    kit.lathe(np.array([0,-.55,0]),UP,[(0,2.33),(.44,2.33),(.48,2.35),(.54,2.35),(.55,2.33)],DARK,144)
    kit.lathe(O,UP,[(.0003,1.77),(.003,1.77)],'Woven rug',128)
    ring(kit,np.array([0,-.065,0]),UP,2.346,.008,BRASS)
    for name,c,r,d in [('snare',[.215,.97,-.105],.214,.14),('high',[.238,1.17,.32],.18,.195),
                        ('mid',[-.198,1.16,.34],.204,.234),('floor',[-.628,.91,-.092],.235,.36)]:
        drum(name,c,r,d,UP)
    drum('kick',[0,.446,.81],.427,.52,Z)
    for args in [('hat',[.83,1.17,-.105],.206,[0,1,0]),('ride',[-.80,1.35,.23],.303,[.11,1,-.07]),
                 ('crash_l',[.73,1.49,.45],.262,[-.14,1,-.11]),('crash_r',[-.53,1.56,.54],.248,[.15,1,-.12])]:
        cymbal(*args)
    # The footboard turns about its heel hinge; the beater turns about the axle.
    layout['pedals']={'right':[-.108,.05,-.20], 'left':[.61,.05,-.45]}
    for side,base in layout['pedals'].items():
        c=np.array(base);pedal=Casting()
        rounded(pedal,[(-.007,.054,.130,.12),(.006,.054,.130,.12)],STEEL)
        for z in np.arange(.045,.235,.029):
            rod(pedal,[-.037,.008,z],[.037,.008,z],.0025,DARK)
        pedal.object(side+' footboard',position=c)
        rod(kit,c-X*.075,c+X*.075,.012,BRASS)
        rod(kit,c-UP*.023,c+Z*.33-UP*.023,.020,DARK)
    layout['beater']=[-.108,.175,.160]
    pivot=np.array(layout['beater'])
    rod(kit,pivot-X*.077,pivot+X*.077,.018,BRASS)
    for side in (-1,1):
        rod(kit,pivot+side*X*.062,[pivot[0]+side*.062,.02,.11],.015,STEEL)
    for side in ('right','left'):
        strap=Casting()
        rounded(strap,[(0,.010,.003,0),(.02,.011,.004,0),(.98,.011,.004,0),(1.,.009,.003,0)],DARK)
        strap.object(side+' pedal strap')
    beater=Casting()
    spindle(beater,O,X,.043,.088)
    rod(beater,O,[.022,.039,-.040],.012,BRASS)
    rod(beater,O,UP*layout['beater_length'],.008,STEEL);beater.ball(UP*layout['beater_length'],layout['beater_radius'],CREAM)
    beater.object('Kick beater',position=pivot)
    for i in range(3):
        a=TAU*i/3
        rod(kit,[0,.46,-.80],[.26*math.cos(a),.021,-.80+.26*math.sin(a)],.016,STEEL)
    kit.lathe(np.array([0,0,-.80]),UP,[(.04,.028),(.54,.03),(.64,.039),(.72,.035)],STEEL)
    kit.lathe(np.array([0,.69,-.80]),UP,[(0,.185),(.02,.208),(.077,.206),(.095,.184)],RUBBER,64)
    rod(kit,[0,.76,-.78],[0,.96,-.70],.085,DARK)
    player()
    static=kit.object('Kit stands and shells')
    # Broad flat resonant head annuli keep their plane normals through to the port.
    for f in static.data.polygons:
        if static.data.materials[f.material_index].name==CREAM:f.use_smooth=False
    home_pose()
    bpy.ops.export_scene.gltf(filepath=str(OUT/'drum_kit.glb'),export_format='GLB',export_yup=True,export_apply=True)
    (OUT/'drum_kit.json').write_text(json.dumps(layout,indent=2)+'\n')


if __name__=='__main__':build()
