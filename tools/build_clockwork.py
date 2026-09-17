"""Rebuild editable clockwork models: blender -b -t 2 -P tools/build_clockwork.py -- [score.json] [asset-name].
Coordinates in the manifest are Godot metres; score geometry is scaled uniformly 3x.
Rigid links have explicit pivots; runtime analytic IK drives them, not baked note clips.
"""
import bpy, json, math, sys, subprocess, shutil
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix
ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
score = json.loads(Path(args[0] if args else ROOT/'render/chamber/score.json').read_text())
name = args[1] if len(args)>1 else 'clockwork'
out = ROOT/'harness/assets'
sys.path.insert(0,str(ROOT/'tools'))
from blender_forms import make_form
sys.path.insert(0,str(ROOT/'formlab'))
from layout import string_endpoints,bar_frame_plan,board_z,harp_base_plan,bench_plan,bench_elements,BAR,BENCH,BELL,BOARD
# formlab.rig / clearance / layout_search are numpy-only (no SciPy) so they run here too.
import rig as arm_rig, clearance as arm_clearance, layout_search
# Pure Python preparation keeps SciPy and structural logic out of Blender's runtime.
recipe=ROOT/'render/form-study/recipe.json'

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def vec(p): return Vector((p[0], -p[2], p[1]))
def material(n, rgb, metallic=0, rough=.4):
    m=bpy.data.materials.new(n); m.diffuse_color=(*rgb,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*rgb,1)
    p.inputs['Metallic'].default_value=metallic; p.inputs['Roughness'].default_value=rough
    return m
brass=material('Satin brass',(.56,.31,.09),.78,.28)
steel=material('Blued steel',(.065,.11,.13),.8,.3)
wood=material('Oiled walnut',(.13,.048,.022),0,.32)
spruce=material('Spruce soundboard',(.65,.46,.23),0,.4)
rose=material('Rosewood',(.3,.085,.035),0,.34)
felt=material('Wool felt',(.78,.68,.48),0,.9)
wire=material('Silver strings',(.65,.7,.72),.8,.25)
glass=material('Smoked glass bells',(.16,.46,.4),.55,.18)
black=material('Charcoal enamel',(.022,.032,.035),.35,.4)
# Subtle grain follows local coordinates; exported base material remains usable in Godot.
def finish(o,n,m,bevel=0):
    o.name=n; o.data.materials.append(m)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new('Machined edges','BEVEL'); mod.width=bevel; mod.segments=3
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in o.data.polygons: p.use_smooth=True
    if bevel:
        o.data.use_auto_smooth=True
        weighted=o.modifiers.new('Face weighted normals','WEIGHTED_NORMAL'); weighted.keep_sharp=True
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=weighted.name)
    return o
def box(n,p,s,m,bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=vec(p)); o=bpy.context.object; o.scale=(s[0],s[2],s[1]); return finish(o,n,m,bevel)
def cyl(n,p,r,h,m):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=h,location=vec(p)); return finish(bpy.context.object,n,m,.009)
def ball(n,p,r,m):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=r,location=vec(p)); return finish(bpy.context.object,n,m)
def beam(n,a,b,r,m):
    o=cyl(n,(Vector(a)+Vector(b))/2,r,(Vector(b)-Vector(a)).length,m)
    o.rotation_mode='QUATERNION'; o.rotation_quaternion=(vec(b)-vec(a)).to_track_quat('Z','Y'); return o
def text(n,body,p,size=.12,yaw=0.):
    # Upright, facing +z; yaw turns it about the vertical (Godot radians, +x toward -z) to lie on an angled face.
    bpy.ops.object.text_add(location=vec(p)); o=bpy.context.object; o.name=n; o.data.body=body; o.data.align_x='CENTER'; o.data.size=size; o.data.extrude=.001
    o.rotation_euler=(math.pi/2,0,yaw); o.data.materials.append(brass)
    bpy.ops.object.convert(target='MESH')
def gear(n,p,r=.15):
    # One joined mesh: hub, toothed perimeter, and a contrasting axle remain visible.
    before=set(bpy.data.objects); o=cyl(n,p,r*.78,.07,brass)
    o.rotation_euler=(math.pi/2,0,0)
    for i in range(16):
        a=math.tau*i/16
        t=box(n+' tooth',(p[0]+r*.86*math.cos(a),p[1]+r*.86*math.sin(a),p[2]),(r*.28,r*.22,.07),brass,.008)
        t.rotation_euler[1]=-a
    bpy.ops.object.select_all(action='DESELECT')
    for ob in set(bpy.data.objects)-before: ob.select_set(True)
    bpy.context.view_layer.objects.active=o; bpy.ops.object.join(); o.name=n
    return o
def bell(n,p):
    # Hollow spun bell: wall profile down to an open lip and back up inside.
    profile=[(.025,.12),(.075,.08),(.08,-.03),(.11,-.2),(.155,-.31),(.14,-.315),(.095,-.2),(.065,-.03),(.06,.065),(.025,.09)]
    vertices=[]; faces=[]; count=48
    for r,y in profile:
        for k in range(count):
            a=math.tau*k/count; vertices.append(tuple(vec((p[0]+r*math.cos(a),p[1]+y,p[2]+r*math.sin(a)))))
    for j in range(len(profile)-1):
        for k in range(count):
            a=j*count+k; b=j*count+(k+1)%count; faces.append((a,b,b+count,a+count))
    mesh=bpy.data.meshes.new(n); mesh.from_pydata(vertices,[],faces); mesh.update()
    o=bpy.data.objects.new(n,mesh); bpy.context.collection.objects.link(o); o.data.materials.append(glass)
    for poly in mesh.polygons: poly.use_smooth=True
    return o
manifest={'harp_display_length_scale':1.7,'pedal_animation':'static reference hardware','model':name+'.glb','strings':{},'arms':{},'mechanisms':{},'gears':[]}
# The stage reaches back to z -4.7 so the bell rails' gantries stand on it, not over its edge.
box('Stage',(0,-.18,-.675),(13,.32,8.05),black,.12)
for x in (-5.8,5.8):
    for z in (-4.05,2.8): cyl('Stage foot',(x,-.4,z),.22,.3,brass)
for x in range(-6,7): box('Floor inlay',(x,-.008,-.675),(.008,.004,7.65),brass,.001)
for m in score['instrument']['mechanisms']:
    mid=m['id']; struck=m['kind']=='struck'; mp=m['pos']; x=mp[0]*3; z=mp[2]*3
    base_y=1.35 if struck else 2.05+mp[1]*3
    # arm_clearance_m: the planner's promise that two arms of this mechanism stay
    # this far apart along x at every moment (world = 3 x score units).
    manifest['mechanisms'][mid]={'center':[x,base_y,z], 'kind':m['kind'], 'material':m['material'], 'arm_clearance_m':3*float(m.get('arm_clearance',0.0))}
    span=m['span']*3
    # The bars hang on a marimba frame built by formlab (form_bars_stand); every
    # other struck instrument sits on a trestle bench (form_<mid>_stand).
    framed=mid=='bars'; benched=struck and not framed
    ends=[]
    for i,s in enumerate(m['strings']):
        sx=x+s['pos'][0]*3; sy=base_y+s['pos'][1]*3; sz=z+s['pos'][2]*3; length=s['length']*3
        a,b=string_endpoints(m,s)
        if struck:
            if m['material']=='glass':
                bell(s['id']+' bell',(sx,sy-.12,sz))
                cyl(s['id']+' crown',(sx,sy-.0225,sz),.12,.045,brass)
            else:
                box(s['id']+' bar',(sx,sy-BAR['thick']/2,sz),(min(.24,span/len(m['strings'])*.7),BAR['thick'],length),rose)
                if m['material']=='wood':
                    box(s['id']+' slit',(sx,sy+.001,sz+.07),(.19,.006,.018),black,.002)
        else:
            for ep in (a,b):
                ball(s['id']+' anchor',ep,.035,brass)
                beam(s['id']+' pin',ep,[ep[0],ep[1],ep[2]-.1],.022,steel)
        ends.append((a,b))
        manifest['strings'][s['id']]={'a':a,'b':b,'mid':mid,'struck':struck,'midi':s['midi'],'pick':s['pick_default']}
    if framed:
        # Hardware on the marimba frame: cord posts with rubber cushions, the cord through the
        # bars' node holes, closed quarter-wave resonators on their bank rod, glides, and the
        # plaque and note names on the name board. The wooden frame itself is form_bars_stand.
        plan=bar_frame_plan([dict(manifest['strings'][s['id']],id=s['id']) for s in m['strings']])
        for side,posts in plan['posts'].items():
            for i,p in enumerate(posts):
                beam(f'{mid} {side} post {i}',(p['x'],p['y0'],p['z']),(p['x'],p['y1'],p['z']),.012,brass)
                ball(f'{mid} {side} cushion {i}',(p['x'],p['y1'],p['z']),.016,black)
            for p,q in zip(posts[:-1],posts[1:]):
                beam(f'{mid} {side} cord',(p['x'],plan['cord_y'],p['z']),(q['x'],plan['cord_y'],q['z']),.006,black)
        for r in plan['resonators']:
            cyl(r['id']+' resonator',(r['x'],r['top']-r['length']/2,r['z']),r['radius'],r['length'],brass)
            cyl(r['id']+' resonator mouth',(r['x'],r['top']-.002,r['z']),r['radius']*.82,.008,black)
            cyl(r['id']+' resonator stop',(r['x'],r['top']-r['length']+.015,r['z']),r['radius']*1.06,.03,brass)
        bank=plan['bank']; beam(mid+' resonator bank',(bank['x'][0],bank['y'],bank['z']),(bank['x'][1],bank['y'],bank['z']),.018,steel)
        for e in plan['ends']:
            for zz in e['foot']: cyl(mid+' glide',(e['x'],e['floor']+.006,zz+.04 if zz<e['z_back'] else zz-.04),.035,.024,brass)
        # The board runs at the converging rails' angle; the text turns with it and sits 2 mm off its face.
        bx,bz=plan['board']['x'],plan['board']['z']; yaw=math.atan2(-(bz[1]-bz[0]),bx[1]-bx[0]); off=.0145
        face=lambda xx:(xx+off*math.sin(yaw),board_z(plan,xx)+off*math.cos(yaw))   # along the face normal (sin yaw, cos yaw)
        xm=(bx[0]+bx[1])/2; fx,fz=face(xm)
        text(mid+' plaque',mid.upper()+'  /  '+m['material'].upper(),(fx,.605,fz),.095,yaw)
        for s in m['strings']:
            sx=manifest['strings'][s['id']]['a'][0]; fx,fz=face(sx); text(s['id']+' note',str(int(s['midi'])),(fx,.735,fz),.06,yaw)
    if benched:
        # Mounts on the bench's bearers (formlab.layout.bench_plan): a call bell's base
        # flange and centre post up into its crown, rubber pads at a block's nodal points;
        # the plaque and note names on the fascia board.
        plan=bench_plan(bench_elements([dict(manifest['strings'][s['id']],id=s['id']) for s in m['strings']],m['material']))
        for mt in plan['mounts']:
            if mt['kind']=='post':
                cyl(mt['id']+' post',(mt['x'],(mt['y0']+mt['y1'])/2,mt['z']),BELL['post_r'],mt['y1']-mt['y0'],brass)
                cyl(mt['id']+' post flange',(mt['x'],mt['y0']+.01,mt['z']),BELL['flange_r'],.02,brass)
            else:
                for k,zn in enumerate(mt['z']): box(f"{mt['id']} pad {k}",(mt['x'],mt['y0']+BENCH['pad']/2,zn),(.06,BENCH['pad'],.05),black,.004)
        bd=plan['board']; bz=bd['z']+BOARD['half_z']+.002; xm=(bd['x'][0]+bd['x'][1])/2
        text(mid+' plaque',mid.upper()+'  /  '+m['material'].upper(),(xm,bd['y']-.03,bz),.036)
        for s in m['strings']:
            text(s['id']+' note',str(int(s['midi'])),(manifest['strings'][s['id']]['a'][0],bd['y']+.028,bz),.04)
    if mid in ('harp','rake'):
        left=min(v['a'][0] for v in manifest['strings'].values() if v['mid']==mid)
        # The harp's base (formlab.layout.harp_base_plan): a box the column and body
        # foot seat in, with a crown and a sole; on the pedal harp seven pedals leave
        # slots in its front face toward the soundbox, three left of the string plane
        # and four right. The rake, strung like a lever harp, stands on the plain plinth.
        hb=harp_base_plan(left,z+.20,with_pedals=mid=='harp'); tag=mid.title()+' '
        def slab(label,xs,ys,zs,mat,bevel):
            return box(tag+label,((xs[0]+xs[1])/2,(ys[0]+ys[1])/2,(zs[0]+zs[1])/2),(xs[1]-xs[0],ys[1]-ys[0],zs[1]-zs[0]),mat,bevel)
        bx,by,bz=hb['box']['x'],hb['box']['y'],hb['box']['z']
        slab('pedal box' if hb['pedals'] else 'base',bx,by,bz,wood,.03)
        for label,part,mat,bev in (('base crown',hb['crown'],wood,.014),('base sole',hb['sole'],black,.008)):
            i=part['inset']; slab(label,[bx[0]+i,bx[1]-i],part['y'],[bz[0]+i,bz[1]-i],mat,bev)
        for p in hb['pedals']:
            sx,sy,sh=p['slot']; box('Harp pedal '+p['note']+' slot',(sx,sy+sh/2,p['z']),(.012,sh,.034),black,.002)
            beam('Harp pedal '+p['note']+' lever',p['lever'][0],p['lever'][1],.016,steel)
            box('Harp pedal '+p['note']+' tread',p['tread'],(.17,.036,.07),black,.01)
            pv=Vector(p['pivot']); beam('Harp pedal '+p['note']+' pivot',pv-Vector((0,0,.03)),pv+Vector((0,0,.03)),.022,brass)
    if mid=='harp':
        for sid,spec in manifest['strings'].items():
            if spec['mid']!=mid:continue
            b=Vector(spec['b'])
            for row,dy in enumerate((.135,.045)):
                centre=b+Vector((0,dy,.34))
                beam(sid+' action disc '+str(row),centre-Vector((0,0,.013)),centre+Vector((0,0,.013)),.025,wire)
                for sign in (-1,1):
                    pin=centre+Vector((sign*.016,sign*.009,0))
                    beam(sid+' fork pin',pin,pin+Vector((0,0,.042)),.007,steel)
            tuning=b+Vector((0,.22,.35))
            beam(sid+' tuning pin',tuning-Vector((0,0,.1)),tuning+Vector((0,0,.055)),.015,wire)
            box(sid+' tuning key',tuning+Vector((0,0,.059)),(.025,.025,.025),steel,.003)
    for k,act in enumerate(m['actuators']):
        aid=act['id']
        # Rail height/depth and link lengths are decided by the clearance search
        # below, once every string of every mechanism is known.
        xs=[manifest['strings'][sid]['a'][0] for sid in act['reach']]
        manifest['arms'][aid]={'mid':mid,'kind':act['kind'],'index':k,'reach_x':[min(xs),max(xs)]}
# The sympathetic chamber is a resonant body, with an envelope-driven pressure gauge.
box('Chamber cabinet',(0,.49,-1.6),(3.6,.85,.65),wood,.09)
for i in range(23):
    box('Chamber grille',(-1.58+i*.144,.5,-1.26),(.045,.61,.05),brass,.012)
text('Chamber name','L O A M   /   THE CHAMBER',(0,.18,-1.21),.11)
gear('Chamber flywheel',(-2.4,.53,-1.5),.4)
ball('chamber__lamp',(1.8,.54,-1.25),.085,glass)
# Static volumes the arms must stay out of (the cabinet, the harp's and the rake's bases).
manifest['obstacles']=[[[-1.8,.06,-1.925],[1.8,.92,-1.275]]]
for based in ('harp','rake'):
    if based not in manifest['mechanisms']: continue
    left=min(v['a'][0] for v in manifest['strings'].values() if v['mid']==based); zz=manifest['mechanisms'][based]['center'][2]+.20
    manifest['obstacles'].append([[left-.82,0,zz-.58],[left+.46,.36,zz+.58]])
# Every struck instrument's frame is a promise too: its footprint up to the elements'
# undersides (the marimba frame, the benches). The mallets come from above; a rail
# or a pick arm from another mechanism must not run through the frame.
for m in score['instrument']['mechanisms']:
    if m['kind']!='struck': continue
    els=[dict(manifest['strings'][s['id']],id=s['id']) for s in m['strings']]; c=manifest['mechanisms'][m['id']]['center']
    if m['id']=='bars':
        plan=bar_frame_plan(els); xs=plan['rails']['back'][:,0]
        manifest['obstacles'].append([[float(xs.min())-.05,0,c[2]-.75],[float(xs.max())+.05,plan['bar_bottom'],c[2]+.75]])
    else:
        plan=bench_plan(bench_elements(els,m['material'])); reach=BENCH['rail_z']+BENCH['leg_splay']+.06
        manifest['obstacles'].append([[plan['x'][0]-.05,0,plan['z']-reach],[plan['x'][1]+.05,plan['underside'],plan['z']+reach]])
# Rails, posts and link lengths from the clearance search over the whole score.
manifest['score']=str(Path(args[0]).resolve() if args else (ROOT/'render/chamber/score.json').resolve())
layout_search.plan_arms(score,manifest,cache=str(ROOT/'render/form-study/rails-cache.json'))
for aid,cfg in manifest['arms'].items():
    ry=cfg['root_y']; rz=cfg['root_z']; x0,x1=cfg['reach_x']
    # Independent rails explain overlap in the score's reach windows. The bars run
    # 0.26 m past the window into the rail heads; heads, masts and plinths are
    # formlab.gantry objects placed by build_forms.py (see docs/articulated-arms.md).
    for dy in (-.075,.075): beam(aid+' rail',(x0-.26,ry+dy,rz),(x1+.26,ry+dy,rz),.024,steel)
    g=gear(aid+'__gear',(0,0,0),.13); manifest['gears'].append(g.name)
    # A pinion above or below the carriage lies flat (its axle vertical): the disc is built
    # upright in the Godot x-y plane, so undo the cylinder's tilt for those mounts.
    if cfg.get('pinion','back') in ('up','down'): g.rotation_euler=(0,0,0)
recipe.parent.mkdir(parents=True,exist_ok=True)
form_layout=recipe.parent/'layout.json'
form_layout.write_text(json.dumps(manifest))
subprocess.run([shutil.which('python3'),str(ROOT/'tools/build_forms.py'),str(form_layout),str(recipe),manifest['score']],check=True)
forms=json.loads(recipe.read_text())
for aid,extra in forms.get('arms',{}).items():
    if aid in manifest['arms']: manifest['arms'][aid].update(extra)
    else: manifest.setdefault('arm_checks',{})[aid]=extra
# Geometry variants share anchors and are selected in Godot with --form or F.
form_colliders=[]
for entry in forms['objects']:
    obj,collider=make_form(entry,{'brass':brass,'wood':wood,'spruce':spruce,'steel':steel,'felt':felt}[entry['material']])
    if not entry.get('local'): form_colliders.append(collider)
# Assemble the articulated rigs at their home poses in the editable Blender file.
# Godot re-poses them every frame with the same rule (clockwork_motion.gd).
P=Matrix(((1,0,0),(0,0,-1),(0,1,0)))   # Godot axes -> Blender axes, as vec()
R=arm_rig.Rig(score,manifest)
for aid,cfg in manifest['arms'].items():
    p=R.pose(aid,-10.0); o1=Vector(cfg['o1']); o2=Vector(cfg['o2'])
    root,elbow,wrist,tip=(Vector(p[k]) for k in ('root','elbow','wrist','tip'))
    pinion=root+Vector(arm_clearance.pinion_centre(cfg.get('pinion','back')).tolist())    # on its axle, against the rack (formlab.gantry.rack)
    for part,pos in [('carriage',root),('shoulder',root),('elbowhead',elbow),('elbow',elbow),('wristhead',wrist),('wrist',wrist),('tool',tip),('shank',tip),('gear',pinion)]:
        bpy.data.objects[aid+'__'+part].location=vec(pos)
    for part,a,b,o in [('upper',root,elbow,Vector((0,0,0))),('upper2',root,elbow,o1),('lower',elbow,wrist,Vector((0,0,0))),('lower2',elbow,wrist,o2)]:
        x,y,z=arm_clearance.link_basis(np.array([a]),np.array([b]))
        B=Matrix(((x[0][0],y[0][0],z[0][0]),(x[0][1],y[0][1],z[0][1]),(x[0][2],y[0][2],z[0][2])))
        ob=bpy.data.objects[aid+'__'+part]; ob.matrix_world=Matrix.Translation(vec(a+o))@(P@B@P.transposed()).to_4x4()
# Include the added reference hardware in the offline clearance mesh.
hardware_vertices=[];hardware_faces=[]
for obj in list(bpy.data.objects):
    if obj.type!='MESH' or not (obj.name.startswith(('Harp ','Rake ')) or any(tag in obj.name for tag in (' action disc',' fork pin',' tuning pin',' tuning key',' post',' pad '))): continue
    obj.data.calc_loop_triangles();offset=len(hardware_vertices)
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co;hardware_vertices.append([p.x,p.z,-p.y])
    hardware_faces.extend([[offset+i for i in tri.vertices] for tri in obj.data.loop_triangles])
form_colliders.append(dict(name='harp_reference_hardware',vertices=hardware_vertices,faces=hardware_faces))
manifest['forms']=['carved','ribbed','shell']
manifest['form_objects']=[e['name'] for e in forms['objects']]
(ROOT/'render/form-study/collision_meshes.json').write_text(json.dumps(form_colliders,separators=(',',':')))
# Save an editable home assembly and a portable runtime mesh assembly.
bpy.ops.export_scene.gltf(filepath=str(out/(name+'.glb')),export_format='GLB',export_yup=True,export_apply=True)
for obj in bpy.data.objects:
    if obj.name.startswith('form_') and (obj.name.endswith('_ribbed') or obj.name.endswith('_shell')):
        obj.hide_set(True); obj.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models'/(name+'.blend')))
(out/(name+'.json')).write_text(json.dumps(manifest,indent=2))
print('CLOCKWORK MODEL:',len(bpy.data.objects),'objects',out/name)
