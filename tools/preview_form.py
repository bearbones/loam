"""Headless studio preview of formlab pieces, without touching the clockwork assets.

    python3 tools/preview_form.py OUT.json            # any script that dumps parts
    blender -b -t 2 -P tools/preview_form.py -- OUT.json OUT.png [azimuth_deg] [elevation_deg] [size]

Input JSON: {"parts":[{"name":..,"material":"brass|steel|wood|felt","pieces":[Mesh.to_dict()...],
"position":[x,y,z],"basis":[[xx,xy,xz],[yx..],[zx..]]}, ...], "look_at":[x,y,z]}
Godot right-handed Y-up coordinates in; the same convert() as blender_forms.
Workbench render with studio lighting, so it runs on any machine in seconds.
"""
import sys, json, math
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
src = Path(args[0]); out = Path(args[1] if len(args) > 1 else src.with_suffix('.png'))
azimuth = float(args[2]) if len(args) > 2 else 35.0
elevation = float(args[3]) if len(args) > 3 else 18.0
size = int(args[4]) if len(args) > 4 else 1400
doc = json.loads(src.read_text())

def convert(p): return (p[0], -p[2], p[1])
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
palette = dict(brass=(.62, .44, .16, 1), steel=(.16, .2, .23, 1), wood=(.28, .12, .06, 1), felt=(.8, .72, .55, 1),
               wire=(.75, .78, .8, 1), bronze=(.55, .35, .18, 1), spruce=(.7, .55, .3, 1))
mats = {}
for k, rgb in palette.items():
    m = bpy.data.materials.new(k); m.diffuse_color = rgb; m.roughness = .35 if k in ('brass', 'steel', 'wire', 'bronze') else .6
    m.metallic = .9 if k in ('brass', 'steel', 'wire', 'bronze') else 0.0; mats[k] = m
lo = Vector((1e9,)*3); hi = Vector((-1e9,)*3)
for part in doc['parts']:
    verts = []; faces = []
    for piece in part['pieces']:
        off = len(verts); verts.extend(convert(v) for v in piece['vertices'])
        faces.extend(tuple(off+i for i in f) for f in piece['faces'])
    mesh = bpy.data.meshes.new(part['name']); mesh.from_pydata(verts, [], faces); mesh.update()
    for p in mesh.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(part['name'], mesh); bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mats.get(part.get('material', 'brass'), mats['brass']))
    pos = part.get('position', [0, 0, 0]); B = part.get('basis')
    if B is not None:
        # Godot basis columns x,y,z -> Blender via the axis permutation P: (x,y,z)->(x,-z,y)
        P = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
        M = Matrix(((B[0][0], B[1][0], B[2][0]), (B[0][1], B[1][1], B[2][1]), (B[0][2], B[1][2], B[2][2])))
        ob.matrix_world = Matrix.Translation(Vector(convert(pos))) @ (P @ M @ P.transposed()).to_4x4()
    else:
        ob.location = convert(pos)
    for v in ob.data.vertices:
        w = ob.matrix_world @ v.co
        lo = Vector(min(a, b) for a, b in zip(lo, w)); hi = Vector(max(a, b) for a, b in zip(hi, w))
centre = Vector(convert(doc['look_at'])) if doc.get('look_at') else (lo+hi)/2
radius = max((hi-lo).length/2, .05)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_cavity = True; scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.show_shadows = True; scene.display.shading.show_specular_highlight = True
scene.display.shading.studio_light = 'paint.sl' if 'paint.sl' in [s.name for s in bpy.context.preferences.studio_lights] else scene.display.shading.studio_light
scene.render.resolution_x = size; scene.render.resolution_y = int(size*.66); scene.render.film_transparent = False
scene.world = bpy.data.worlds.new('w'); scene.world.color = (.12, .13, .14)
cam = bpy.data.cameras.new('c'); cam.lens = 45
co = bpy.data.objects.new('c', cam); bpy.context.collection.objects.link(co); scene.camera = co
az = math.radians(azimuth); el = math.radians(elevation)
direction = Vector((math.cos(el)*math.sin(az), -math.cos(el)*math.cos(az), math.sin(el)))
zoom = float(doc.get('zoom', 1.0))
co.location = centre+direction*radius*4.2/zoom
co.rotation_euler = (centre-co.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = str(out); bpy.ops.render.render(write_still=True)
print('PREVIEW:', out, len(doc['parts']), 'parts')
