"""Editable acoustic bodies. Dimensions and input positions are in Godot metres."""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from layout import BAR, bar_frame_plan


def vec(p):
    return Vector((p[0], -p[2], p[1]))


def surface_uv(data):
    # Metric planar coordinates per face preserve scale around bores and rims.
    uv=data.uv_layers.active or data.uv_layers.new(name='Workshop grain')
    for face in data.polygons:
        n=face.normal
        axis=max(range(3),key=lambda k:abs(n[k]))
        u,v=((1,2),(0,2),(0,1))[axis]
        for i in face.loop_indices:
            p=data.vertices[data.loops[i].vertex_index].co
            uv.data[i].uv=(p[u],p[v])


def mesh(name, verts, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata([vec(p) for p in verts], [], faces)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    surface_uv(data)
    data.materials.append(bpy.data.materials[mat])
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj


def apply(obj, modifier):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def finish(obj, radius):
    bevel = obj.modifiers.new('Broken edges', 'BEVEL')
    bevel.width = radius
    bevel.segments = 3
    apply(obj, bevel)
    obj.data.use_auto_smooth = True
    obj.data.auto_smooth_angle = .65
    for face in obj.data.polygons:
        face.use_smooth = True
    normals = obj.modifiers.new('Face normals', 'WEIGHTED_NORMAL')
    apply(obj, normals)
    while len(obj.data.materials)>1:
        obj.data.materials.pop(index=len(obj.data.materials)-1)
    for face in obj.data.polygons:
        face.material_index=0
    surface_uv(obj.data)
    return obj


def loft(name, rows, mat, wrap=False):
    count = len(rows[0])
    faces = []
    for j in range(len(rows) if wrap else len(rows)-1):
        a, b = j*count, ((j+1) % len(rows))*count
        for i in range(count):
            k = (i+1) % count
            faces.append((a+i, a+k, b+k, b+i))
    if not wrap:
        faces.extend([tuple(range(count)), tuple(range((len(rows)-1)*count, len(rows)*count))])
    return mesh(name, [p for row in rows for p in row], faces, mat)


def turn(name, centre, profile, mat, count=48):
    x, y, z = centre
    angles = [math.tau*k/count for k in range(count)]
    rows = [[(x+r*math.cos(a), y+h, z+r*math.sin(a)) for a in angles] for r,h in profile]
    return loft(name, rows, mat, wrap=True)


def subtract(obj, cutter):
    mod = obj.modifiers.new('Cut '+cutter.name, 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cutter
    apply(obj, mod)
    bpy.data.objects.remove(cutter, do_unlink=True)


def blank(name, centre, size, mat):
    x,y,z = centre
    w,h,d = (v/2 for v in size)
    return loft(name, [[(x-w,y-h,z+k),(x+w,y-h,z+k),(x+w,y+h,z+k),(x-w,y+h,z+k)] for k in (-d,d)], mat)


def drill(start, end, radius):
    a, b = vec(start), vec(end)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=(b-a).length, location=(a+b)/2)
    cutter = bpy.context.object
    cutter.rotation_mode = 'QUATERNION'
    cutter.rotation_quaternion = (b-a).to_track_quat('Z','Y')
    return cutter


def marimba(elements, width):
    plan = bar_frame_plan(elements)
    for i, (el, res) in enumerate(zip(sorted(elements,key=lambda e:e['a'][0]), plan['resonators'])):
        a, b = np.array(el['a']), np.array(el['b'])
        x,y,z = (a+b)/2
        length = abs(b[2]-a[2])
        thick = BAR['thick']
        rows = []
        for u in np.linspace(-1.,1.,41):
            # Stop the arch before the suspension bores. Leave more wood
            # under the shorter treble bars, whose pitch needs less undercut.
            arch = max(0., 1.-(u/.53)**2)**2
            bottom = y-thick + thick*(.59-.19*i/max(1,len(elements)-1))*arch
            zz = z+.5*length*u
            rows.append([(x-width/2,bottom,zz),(x+width/2,bottom,zz),(x+width/2,y,zz),(x-width/2,y,zz)])
        obj = loft(el['id']+' bar', rows, 'Rosewood')
        for posts in plan['posts'].values():
            p,q = posts[i:i+2]
            subtract(obj, drill((p['x'],plan['cord_y'],p['z']), (q['x'],plan['cord_y'],q['z']), .009))
        finish(obj,.0045)
        sounding_mode(obj,(x,y,z),length,'bar')
        r,L = res['radius'],res['length']
        tube = turn(el['id']+' resonator',(res['x'],res['top'],res['z']),
                    [(r,-L),(r,-.012),(r+.002,-.006),(r,0),(r-.005,0),(r-.006,-.007),(r-.006,-L)],'Satin brass')
        finish(tube,.001)


def block(el, width):
    a,b = np.array(el['a']),np.array(el['b'])
    x,y,z = (a+b)/2
    length = abs(b[2]-a[2])
    thick = BAR['thick']
    obj = blank(el['id']+' bar',(x,y-thick/2,z),(width,thick,length),'Rosewood')
    # The two overlapping cuts leave a long thin tongue above an enclosed
    # air chamber. Its narrow mouth opens through the audience-facing end.
    cavity = blank('Air chamber',(x,y-.059,z+.07*length),
                   (width-.035,.061,length*.70),'Rosewood')
    subtract(obj,cavity)
    mouth = blank('Tongue opening',(x,y-.038,z+.46*length),
                  (width-.038,.019,.23*length),'Rosewood')
    subtract(obj,mouth)
    # An end slit alone is obscured by the fascia from above. Two side kerfs
    # free the tongue along its grain and expose the depth of the chamber.
    for side in (-1,1):
        kerf = blank('Tongue kerf',(x+side*(width/2-.020),y-.020,z+.15*length),
                     (.006,.062,.74*length),'Rosewood')
        subtract(obj,kerf)
    finish(obj,.004)
    sounding_mode(obj,(x,y,z),length,'block')


def bell_shell(el, low):
    a,b = np.array(el['a']),np.array(el['b'])
    x,y,z = (a+b)/2
    sid = el['id']
    r = .168*2**(-(el['midi']-low)/28)
    z += .48*r
    profile = [(.12,-.006),(.24,0),(.51,0),(.59,-.012),(.61,-.037),
               (.60,-.093),(.62,-.18),(.72,-.29),(.88,-.382),(.99,-.412),
               (1,-.428),(.984,-.435),(.94,-.434),(.91,-.414),(.84,-.395),
               (.67,-.30),(.58,-.19),(.55,-.09),(.55,-.046),(.50,-.024),
               (.25,-.020),(.12,-.023)]
    # The chuck holds the crown true. Tooling below it retains a slight
    # oval, a wheel-cut skirt and the two beads where the lip was dressed.
    phase = int(sid[-2:])*1.731
    profile[7:7] = [(.646,-.216),(.679,-.254)]
    profile[10:10] = [(.757,-.320),(.800,-.351)]
    profile[13:13] = [(.909,-.392),(.937,-.396),(.944,-.399),(.936,-.402)]
    rows=[]
    for k,h in profile:
        depth=max(0.,-h/.435)
        row=[]
        for j in range(144):
            a=math.tau*j/144
            r_tool = r*k*(1.+depth*(.019*math.sin(2*a+phase)+.008*math.sin(3*a-phase)))
            wheel = max(0.,1.-((h+.29)/.105)**2)**2 * max(0.,math.cos(12*a+.12*math.sin(3*a+phase)))**2
            r_tool -= .0038*wheel
            row.append((x+r_tool*math.cos(a),y+h+.0018*depth**2*math.sin(2*a-phase),z+r_tool*math.sin(a)))
        rows.append(row)
    shell=finish(loft(sid+' bell',rows,'Smoked glass bells',wrap=True),.0008)
    sounding_mode(shell,(x,y,z),.435,'bell')
    return shell


def bell_mount(sid):
    post=bpy.data.objects[sid+' post']
    top=max(v.co.z for v in post.data.vertices)
    bottom=min(v.co.z for v in post.data.vertices)
    # A turned steel arbor necks down through the glass. The lock ring can
    # be gripped below the crown without loading the speaking skirt.
    profile=[(.004,bottom),(.032,bottom),(.032,bottom+.028),(.024,bottom+.035),
             (.020,bottom+.043),(.019,bottom+.060),(.012,top-.056),
             (.018,top-.054),(.018,top-.042),(.012,top-.040),(.012,top),(.004,top)]
    blank_post=finish(turn('Turned arbor',(0,0,0),profile,'Blued steel'),.0007)
    post.data=blank_post.data
    bpy.data.objects.remove(blank_post,do_unlink=True)
    collar=finish(turn(sid+' lock ring',(0,0,0),[(.011,top-.043),(.023,top-.043),
                       (.026,top-.040),(.026,top-.028),(.023,top-.025),(.011,top-.025)],
                       'Phosphor bronze',24),.0007)
    collar.parent=post
    flange=bpy.data.objects[sid+' post flange']
    for i in range(3):
        angle=i*math.tau/3+.23
        x,z=.054*math.cos(angle),.054*math.sin(angle)
        screw=turn(sid+' flange screw',(x,.010,z),[(.0004,-.004),(.008,-.004),
                   (.0105,-.001),(.0105,.001),(.0085,.004),(.0004,.004)],'Blued steel',28)
        cut=blank('Driver slot',(x,.014,z),(.025,.004,.0022),'Blued steel')
        subtract(screw,cut)
        finish(screw,.0004)
        screw.parent=flange


def bell(el, low):
    a,b=np.array(el['a']),np.array(el['b'])
    x,y,z=(a+b)/2
    sid=el['id']
    r=.168*2**(-(el['midi']-low)/28)
    z+=.48*r
    bell_shell(el,low)
    for label,lo,hi,rad,mat,n in [
            ('seat',-.048,-.021,.24*r,'Wool felt',40),
            ('crown',-.020,.005,.20*r,'Phosphor bronze',48),
            ('washer',.005,.010,.23*r,'Wool felt',40),
            ('cap nut',.010,.024,.15*r,'Satin brass',6)]:
        finish(turn(sid+' '+label,(x,y,z),[(.009,lo),(rad,lo),(rad,hi),(.009,hi)],mat,n),.0015)
    for suffix in (' post',' post flange'):
        bpy.data.objects[sid+suffix].location.y -= .48*r
    bell_mount(sid)
    # A stud continues the centre post through the bore and into the nut.
    bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=.010,depth=.083,location=vec((x,y-.018,z)))
    stud=bpy.context.object
    stud.name=sid+' threaded spindle'
    stud.data.materials.append(bpy.data.materials['Blued steel'])


def soundbox(mid, board):
    rings = np.array(board[:-2]).reshape(-1,8,3)
    rings = rings[np.linspace(0,len(rings)-1,49,dtype=int)]
    centre = rings.mean(axis=1)
    half = (rings[:,3]-rings[:,0])/2
    half[:,2] = 0.
    # Seven broad staves over the diagonal back, closed at both ends;
    # each shell section returns on its inner surface with 9 mm wall stock.
    rows = []
    depths = np.linspace(.103,.186,len(rings))
    angles=np.linspace(0,math.pi,15)
    for p,w,d in zip(centre,half,depths):
        row=[]
        for inner in (False,True):
            for theta in (reversed(angles) if inner else angles):
                offset = w*math.cos(theta)*(.95 if inner else 1.02)
                offset[2] = -.012+(d-(.009 if inner else 0))*math.sin(theta)
                row.append(p+offset)
        rows.append(row)
    shell=loft(mid+' staved soundbox', rows,'Oiled walnut')
    for frac in (.25,.53,.79):
        i=round(frac*(len(rows)-1))
        p=centre[i]
        along=centre[i+1]-centre[i-1]
        along[2]=0
        along/=np.linalg.norm(along)
        across=np.array([-along[1],along[0],0])
        size=np.linalg.norm(half[i])
        ends=[]
        for depth in (.01,depths[i]+.045):
            ends.append([p+along*(1.05*size*math.cos(t))+across*(.38*size*math.sin(t))+[0,0,depth]
                         for t in np.linspace(0,math.tau,48,endpoint=False)])
        subtract(shell,loft('Oval access port',ends,'Oiled walnut'))
    finish(shell,.0018)
    for i in (0,-1):
        # End blocks close the cavity between spruce and the arched back.
        cap=np.array(rows[i][:15])
        step=(centre[1]-centre[0]) if i==0 else (centre[-2]-centre[-1])
        finish(loft(mid+' soundbox end',[cap,cap+.15*step],'Oiled walnut'),.001)


    purfling(mid,centre,half,depths)


def purfling(mid, centres, halves, depths):
    verts,faces=[],[]
    for index in (2,4,10,12):
        theta=math.pi*index/14
        base=len(verts)
        for c,w,d in zip(centres,halves,depths):
            u=w/np.linalg.norm(w)
            p=c+w*1.02*math.cos(theta)+[0,0,-.012+d*math.sin(theta)]
            for side,h in [(-1,-.001),(1,-.001),(1,.0018),(-1,.0018)]:
                verts.append(p+side*.0018*u+[0,0,h])
        for j in range(len(centres)-1):
            a=base+4*j
            for k in range(4):
                l=(k+1)%4
                faces.append((a+k,a+l,a+4+l,a+4+k))
        faces.extend([tuple(range(base,base+4)),tuple(range(len(verts)-4,len(verts)))])
    mesh(mid+' soundbox purfling',verts,faces,'Spruce soundboard')


def grille_rails():
    for y in (.198,.803):
        finish(blank('Chamber grille rail',(0,y,-1.26),(3.42,.044,.065),'Phosphor bronze'),.006)
        for x in (-1.69,1.69):
            finish(blank('Chamber grille cleat',(x,y,-1.295),(.065,.077,.098),'Phosphor bronze'),.005)


def interior(mid):
    # The inside face of the spruce panel only receives light through the
    # ports. Reserve a matte, occlusion-tinted finish for that face.
    panel=bpy.data.objects['form_'+mid+'_soundboard']
    timber=bpy.data.materials.get('Spruce interior')
    if timber is None:
        timber=bpy.data.materials['Spruce soundboard'].copy()
        timber.name='Spruce interior'
        timber.diffuse_color=(.12,.065,.027,1)
        shader=timber.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value=timber.diffuse_color
        shader.inputs['Roughness'].default_value=.84
    panel.data.materials.append(timber)
    # Both faces and the ferrule seats are supplied in the board's common
    # frame. Its laminated back lies beyond the middle of its Z extent.
    corners=[-v[1] for v in panel.bound_box]
    threshold=.5*(max(corners)+min(corners))
    for face in panel.data.polygons:
        if -face.center.y>threshold:
            face.material_index=len(panel.data.materials)-1


def grille():
    grille_rails()
    bars=[ob for ob in bpy.data.objects if ob.name.startswith('Chamber grille')]
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bars: ob.select_set(True)
    bpy.context.view_layer.objects.active=bars[0]
    bpy.ops.object.join()
    bars[0].name='Chamber grille'


def cabinet():
    case = blank('Chamber cabinet',(0,.49,-1.6),(3.6,.85,.65),'Oiled walnut')
    # A shell with a continuous back and shelf below the grille.
    subtract(case,blank('Sound opening',(0,.54,-1.43),(3.32,.61,.64),'Oiled walnut'))
    finish(case,.032)
    for y in (.275,.795):
        finish(blank('Chamber pinblock',(0,y,-1.59),(3.28,.055,.09),'Spruce soundboard'),.008)
    # A bank of paired sympathetic wires on two shared bridges.
    # Batch the speaking lengths and the tuning pins into two material draws.
    groups = {m:([],[]) for m in ('Silver strings','Satin brass')}
    def rod(mat,a,b,r):
        a,b=np.array(a),np.array(b)
        axis=b-a
        axis/=np.linalg.norm(axis)
        u=np.cross(axis,[0,0,1] if abs(axis[2])<.9 else [0,1,0])
        u/=np.linalg.norm(u)
        v=np.cross(axis,u)
        verts,faces=groups[mat]
        base=len(verts)
        for p in (a,b):
            verts.extend(p+r*(math.cos(t)*u+math.sin(t)*v) for t in np.linspace(0,math.tau,10,endpoint=False))
        faces.extend((base+i,base+(i+1)%10,base+10+(i+1)%10,base+10+i) for i in range(10))
        faces.extend([tuple(range(base,base+10)),tuple(range(base+10,base+20))])
    for i in range(24):
        x=-1.53+i*.132
        for dx in (-.012,.012):
            rod('Silver strings',(x+dx,.275,-1.532),(x+dx+.045,.795,-1.532),.0038)
        for y,xx in ((.275,x),(.795,x+.045)):
            rod('Satin brass',(xx,y,-1.58),(xx,y,-1.521),.018)
    for mat,(v,f) in groups.items():
        mesh('Chamber '+('sympathetic strings' if mat=='Silver strings' else 'bridge pins'),v,f,mat)


def sounding_mode(obj, centre, length, family):
    """First visible deformation; 1.0 is the displacement at a full blow."""
    obj.shape_key_add(name='Basis')
    mode=obj.shape_key_add(name='Voicing')
    mode.slider_min=-1.
    x,y,z=centre
    for vertex in mode.data:
        xx,yy,zz=vertex.co.x,vertex.co.z,-vertex.co.y
        if family=='bar':
            u=2*(zz-z)/length
            # Zero motion under both suspension bores. The ends move in phase.
            vertex.co.z+=.0024*(u*u-.5516**2)
        elif family=='block':
            u=min(1.,max(0.,(zz-z+.22*length)/(.72*length)))
            skin=min(1.,max(0.,(yy-y+.042)/.018))
            vertex.co.z-=.0021*u*u*skin
        else:
            # Ovalisation of the skirt. The mounting crown is a displacement node.
            depth=min(1.,max(0.,(y-yy)/.435))
            angle=math.atan2(zz-z,xx-x)
            movement=.004*depth**2*math.cos(2*angle)
            vertex.co.x+=movement*math.cos(angle)
            vertex.co.y-=movement*math.sin(angle)


def slide_tube(name, xs, radii, mat):
    angles=np.linspace(0,math.tau,24,endpoint=False)
    profile=[(xs[0],radii[0]),(xs[1],radii[0]),(xs[1],radii[1]),(xs[0],radii[1])]
    return finish(loft(name,[[(x,.020+r*math.cos(t),r*math.sin(t)) for t in angles]
                             for x,r in profile],mat,wrap=True),.001)


def mallet_holder(aid, cfg):
    # The motor turns a pinion at the fixed guide. The far stick rides an
    # inner slide with a shoulder at the pin and overlap even at full splay.
    housing=slide_tube('Guide sleeve',(-.049,.406),(.019,.013),'Phosphor bronze')
    slide = slide_tube(aid+'__inner_slide',(-.445,-.017),(.012,.007),'Blued steel')
    dial=turn('Feed dial',(0,.044,0),[(.006,-.006),(.032,-.006),(.032,.005),(.006,.005)],'Satin brass',32)
    # A marked keyway makes rotation legible in close-up.
    subtract(dial,blank('Dial key',(.022,.050,0),(.021,.006,.004),'Satin brass'))
    finish(dial,.001)
    for label,obj,density in [('shank',housing,8800),('inner_slide',slide,7850),('splay_sector',dial,8500)]:
        bm=bmesh.new()
        bm.from_mesh(obj.data)
        cfg['masses'][label]=round(abs(bm.calc_volume())*density,4)
        bm.free()
    for label,source in [('shank',housing),('splay_sector',dial)]:
        target=bpy.data.objects[aid+'__'+label]
        target.data=source.data
        bpy.data.objects.remove(source,do_unlink=True)

def mallet_support(aid,cfg):
    # A sliding stay joins the wrist crosshead to the proximal stick pivot.
    # The gland, polished piston and their bearing pins occupy the outer cheek.
    pieces = []
    for name,profile,mat in [
            ('wrist_guide',[(.012,.015),(.022,.015),(.022,.035),(.018,.043),
                            (.018,.386),(.022,.39),(.022,.405),(.012,.405)],'Phosphor bronze'),
            ('wrist_plunger',[(.003,.012),(.015,.012),(.015,.028),(.0115,.032),
                              (.0115,.414),(.003,.414)],'Blued steel')]:
        link=finish(turn(aid+'__'+name,(0,0,0),profile,mat),.0007)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.022)
        eye=bpy.context.object
        eye.data.materials.append(bpy.data.materials[mat])
        bpy.ops.object.select_all(action='DESELECT')
        eye.select_set(True); link.select_set(True)
        bpy.context.view_layer.objects.active=link
        bpy.ops.object.join()
        pieces.append((name,link,8800 if name=='wrist_guide' else 7850))
    for target,end in [('wristhead',-.056),('shank',-.032)]:
        angles=np.linspace(0,math.tau,32,endpoint=False)
        profile=[(-.143,.007),(-.143,.015),(-.135,.017),(-.132,.010),
                 (-.106,.010),(-.102,.015),(end,.015),(end,.007)]
        axle=finish(loft(aid+' '+target+' stay pin',
                         [[(x,r*math.cos(t),r*math.sin(t)) for t in angles] for x,r in profile],
                         'Satin brass',wrap=True),.0007)
        axle.parent=bpy.data.objects[aid+'__'+target]
    for name,obj,density in pieces:
        bm=bmesh.new()
        bm.from_mesh(obj.data)
        cfg['masses'][name]=round(abs(bm.calc_volume())*density,4)
        bm.free()


def palm_stud(aid,cfg):
    # The rod's transverse pin carries a spherical end. A shouldered stud
    # threads into the shank below it and captures that end between the cheeks.
    x,y,z=cfg['drives']['wrist_flex']['mount_offset']
    shank=bpy.data.objects[aid+'__shank']
    floor=max(v.co.z for v in shank.data.vertices)-y
    profile=[(.003,floor-.009),(.011,floor-.009),(.011,floor-.002),
             (.017,floor-.001),(.017,floor+.004),(.015,floor+.006),
             (.011,floor+.007),(.009,-.016),(.007,-.014),(.007,-.008)]
    for a in np.linspace(-.97,math.pi/2-.08,24):
        profile.append((.0115*math.cos(a),.0115*math.sin(a)))
    stud=finish(turn(aid+' palm stud',(0,0,0),profile,'Phosphor bronze'),.0004)
    stud.parent=shank
    stud.location=vec((x,y,z))


def carrier_seat(aid,cfg):
    # A spherical rod end on the outer wrist pin gives the folded linkage a
    # lateral separation from the palm socket, including at its parked pose.
    from mathutils import Quaternion
    treble=cfg['kind']=='pick' and cfg['index']==2
    reach=.32 if treble else .135
    root=reach-.055
    profile=[(root,.013),(root-.005,.022),(root-.022,.022),(root-.024,.015),
             (.054,.015),(.050,.011),(.028,.011),(.024,.014)]
    for t in np.linspace(.8,math.pi-.09,20):
        profile.append((.022*math.cos(t),.022*math.sin(t)))
    angles=np.linspace(0,math.tau,32,endpoint=False)
    seat=finish(loft(aid+'__carrier_seat',[[(x,r*math.cos(t),r*math.sin(t)) for t in angles]
                                         for x,r in profile],'Phosphor bronze'),.0007)
    seat.parent=bpy.data.objects[aid+'__wristhead']
    seat.location=vec((reach if treble else -reach,0,0))
    # The outer harp wrists fold back along their rails. The treble socket
    # sits on the opposite cheek to clear the middle player on crossed reaches.
    seat.rotation_mode='QUATERNION'
    roll=0.
    if cfg['kind']=='pick':
        roll=math.radians(11.) if cfg['index']==1 else -math.pi/3
    seat.rotation_quaternion=Quaternion((1,0,0),roll)@Quaternion((0,0,1),math.pi if treble else 0.)



def jointed_digit(entry, palette):
    from blender_forms import make_form
    from mathutils import Matrix
    art = entry['articulation']
    parent = None
    for i, suffix in enumerate(('', '_middle', '_distal')):
        pivot = vec(art['pivots'][i])
        indices = [j for j,g in enumerate(art['groups']) if g==i]
        materials = [entry['piece_materials'][j] for j in indices]
        local = dict(entry, name=entry['name']+suffix, material=materials[0],
                     pieces=[entry['pieces'][j] for j in indices], piece_materials=materials)
        obj,_ = make_form(local,palette)
        obj.data.transform(Matrix.Translation(-pivot))
        if parent:
            obj.parent = parent
            obj.location = pivot-vec(art['pivots'][i-1])
        parent = obj
    marker=bpy.data.objects.new(entry['name'].replace('__digit_', '__pad_'), None)
    bpy.context.collection.objects.link(marker)
    marker.parent=parent
    marker.location=vec(art['pad'])-vec(art['pivots'][-1])
    marker.empty_display_size=.003


def build(layout, score, boards):
    for m in score['instrument']['mechanisms']:
        mid=m['id']
        elements=[dict(layout['strings'][s['id']],id=s['id']) for s in m['strings']]
        width=min(.24,m['span']*3/len(elements)*.7)
        if mid in boards:
            soundbox(mid,boards[mid])
            interior(mid)
        elif mid=='bars':
            marimba(elements,width)
        elif m['material']=='wood':
            for el in elements:
                block(el,width)
        elif m['material']=='glass':
            low=min(el['midi'] for el in elements)
            for el in elements:
                bell(el,low)
    cabinet()
    grille()
    for aid,cfg in layout["arms"].items():
        if cfg["kind"] in ("pick","rake"):
            carrier_seat(aid,cfg)
            palm_stud(aid,cfg)
        if cfg.get("hands",0)>=2 and cfg["kind"]=="mallet":
            mallet_holder(aid,cfg)
            mallet_support(aid,cfg)

def place_carrier(aid, wrist, mount, length):
    """Fold both rigid links toward one pole, with a common knee pin axis."""
    from mathutils import Matrix
    seat=bpy.data.objects[aid+'__carrier_seat']
    offset=seat.location
    wrist=wrist+Vector((offset.x,offset.z,-offset.y))
    ref=seat.rotation_quaternion@vec((0,1,0))
    folded=Vector((ref.x,ref.z,-ref.y))
    along=(mount-wrist).normalized()
    axis=seat.rotation_quaternion@vec((1,0,0))
    forward=Vector((axis.x,axis.z,-axis.y))
    bend=forward.rotation_difference(along)@folded
    height=math.sqrt(max(0.,length**2-(mount-wrist).length_squared/4))
    knee=(mount+wrist)/2+height*bend
    axle=bend.cross(along).normalized()
    for part,a,b in [('wrist_crank',wrist,knee),('wrist_rod',knee,mount)]:
        y=(b-a).normalized()
        # Godot basis columns (x,y,z) become Blender (x,-z,y).
        frame=Matrix([vec(axle),-vec(axle.cross(y)),vec(y)]).transposed()
        bpy.data.objects[aid+'__'+part].matrix_world=Matrix.Translation(vec(a))@frame.to_4x4()
