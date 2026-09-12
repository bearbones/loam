"""Blender's BVH measures the final union meshes against sampled tool motion.
blender -b -t 2 -P tools/check_form_clearance.py
Every time sample includes all six tools; the exact musical contacts are added.
Pick surfaces use a bounding box sampled at <=10 mm with a conservative spatial
error subtraction. Mallets use their enclosing sphere. No inter-frame proof.
"""
import json,math,hashlib,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]; folder=ROOT/'render/form-study'
sys.path.insert(0,str(ROOT/'tools'))
from mesh_distance import ClosedSurface
objects=json.loads((folder/'collision_meshes.json').read_text())
motion=json.loads((folder/'motion.json').read_text())
layout=json.loads((ROOT/'harness/assets/clockwork.json').read_text())
def signed(tree,p):
    return tree.signed_distance(p)
# Cartesian grid on all six faces of a conservative un-beveled pick envelope.
axes=[[-.017+i*.034/4 for i in range(5)],[i*.14/14 for i in range(15)],[-.02+i*.04/4 for i in range(5)]]
box=[]
for i,x in enumerate(axes[0]):
 for j,y in enumerate(axes[1]):
  for k,z in enumerate(axes[2]):
   if i in (0,4) or j in (0,14) or k in (0,4): box.append(Vector((x,y,z)))
spatial_error=math.sqrt(2)*.01/2
results={}; failures=[]
for style in ('carved','ribbed','shell'):
    trees=[]
    for obj in objects:
        if obj['name'].endswith('_'+style) or obj['name']=='form_bars_stand' or obj['name'].endswith('_soundboard') or obj['name'].endswith('_actionplate') or obj['name']=='harp_reference_hardware':
            tree=ClosedSurface(obj['vertices'],obj['faces'])
            trees.append((obj['name'],tree))
    best=1e9; worst=None; evaluated=0
    for aid,t,tip,radius in motion['rows']:
        tip=Vector(tip)
        sphere=radius>.05
        center=tip+Vector((0,.075 if sphere else .07,0))
        bound=.075 if sphere else math.sqrt(.017**2+.07**2+.02**2)
        for name,tree in trees:
            dc=signed(tree,center)
            if dc-bound-(0 if sphere else spatial_error)>best: continue
            if sphere: clearance=dc-.075
            else:
                clearance=min(signed(tree,tip+p) for p in box)-spatial_error
            evaluated+=1
            if clearance<best:
                best=clearance;worst=dict(arm=aid,time=t,object=name)
    # Existing .035 m anchor spheres must overlap their new support bosses.
    seats=[]
    for name,tree in trees:
        if ('_harp_' in name or '_rake_' in name) and not name.endswith(('_soundboard','_actionplate')):
            mid='harp' if '_harp_' in name else 'rake'
            for sid,s in layout['strings'].items():
                if s['mid']==mid:
                    for end in ('a','b'): seats.append(abs(signed(tree,Vector(s[end]))))
    results[style]=dict(min_tool_clearance_m=best,worst=worst,refined_queries=evaluated,
       max_anchor_seat_distance_m=max(seats),time_hz=motion['hz'],samples=len(motion['rows']),spatial_error_bound_m=spatial_error)
    if best<0:failures.append(style+' tool overlap under conservative envelope')
    if max(seats)>.035:failures.append(style+' anchor gap')
    print(style,results[style],flush=True)
(folder/'clearance.json').write_text(json.dumps(dict(results=results,failures=failures,
  mesh_sha256=hashlib.sha256((folder/'collision_meshes.json').read_bytes()).hexdigest(),
  motion_sha256=hashlib.sha256((folder/'motion.json').read_bytes()).hexdigest(),
  scope='New frame and branching stand vs tools only; does not certify full arm/rail collision, inter-sample motion, or structural safety'),indent=2))
if failures: raise RuntimeError(failures)
print('FORM CLEARANCE: PASS')
